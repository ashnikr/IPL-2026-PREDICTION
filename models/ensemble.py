"""
Ensemble Prediction System.

Combines ML models, Bayesian inference, Monte Carlo simulation,
player form, and venue factors into a final calibrated prediction.
"""

import pickle
import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime

from utils.logger import logger
from config.settings import settings
from models.ml_models import MLModelTrainer
from models.bayesian_model import BayesianPredictor
from models.monte_carlo import MonteCarloSimulator


class EnsemblePrediction:
    """Combine all prediction sources into a final probability."""

    # Model weights (tuned based on CV performance)
    DEFAULT_WEIGHTS = {
        "catboost": 0.25,
        "xgboost": 0.20,
        "lightgbm": 0.15,
        "random_forest": 0.10,
        "logistic_regression": 0.05,
        "bayesian": 0.10,
        "monte_carlo": 0.10,
        "neural_net": 0.05,
    }

    # When we only have team names (no live match features), shift weight to Bayesian/MC
    MINIMAL_WEIGHTS = {
        "catboost": 0.10,
        "xgboost": 0.08,
        "lightgbm": 0.07,
        "random_forest": 0.05,
        "logistic_regression": 0.02,
        "bayesian": 0.35,
        "monte_carlo": 0.28,
        "neural_net": 0.05,
    }

    def __init__(self):
        self.ml_trainer = MLModelTrainer()
        self.bayesian = BayesianPredictor()
        self.monte_carlo = MonteCarloSimulator(n_simulations=10000)
        self.weights = self.DEFAULT_WEIGHTS.copy()
        self._loaded = False
        self._matches_df = None  # cached historical data
        self._has_full_features = False

    def load_all_models(self):
        """Load all trained models from disk."""
        if self._loaded:
            return

        logger.info("Loading all models for ensemble...")
        self.ml_trainer._load_models()
        self.bayesian.load()

        # Load historical data for feature building and Monte Carlo
        try:
            processed = settings.processed_data_dir / "matches_processed.csv"
            if processed.exists():
                self._matches_df = pd.read_csv(processed)
                self.monte_carlo.fit(self._matches_df)
        except Exception as e:
            logger.warning(f"Historical data load failed: {e}")

        self._loaded = True
        logger.info(f"Loaded ML models: {list(self.ml_trainer.models.keys())}")

    def predict_match(
        self,
        team1: str,
        team2: str,
        venue: str = None,
        city: str = None,
        toss_winner: str = None,
        toss_decision: str = None,
        match_features: pd.DataFrame = None,
        weather: dict = None,
        playing_xi_team1: list = None,
        playing_xi_team2: list = None,
    ) -> dict:
        """
        Generate ensemble prediction for a match.

        Returns team1_win_prob, team2_win_prob, confidence, key_factors.
        """
        self.load_all_models()

        predictions = {}
        active_weights = {}

        # Determine if we have full match features or just team names
        self._has_full_features = match_features is not None and not match_features.empty

        # ── 1. ML Model predictions ───────────────────────────────────
        if self._has_full_features:
            weight_source = self.weights
            ml_preds = self.ml_trainer.predict(match_features)
        else:
            weight_source = self.MINIMAL_WEIGHTS
            # Build rich features from historical data
            built_features = self._build_minimal_features(
                team1, team2, venue, city, toss_winner, toss_decision
            )
            ml_preds = self.ml_trainer.predict(built_features) if built_features is not None else {}

        for model_name, probs in ml_preds.items():
            p = float(probs[0]) if len(probs) > 0 else 0.5
            predictions[model_name] = p
            if model_name in weight_source:
                active_weights[model_name] = weight_source[model_name]

        # ── 2. Bayesian prediction ────────────────────────────────────
        if self.bayesian.team_strengths:
            bay_pred = self.bayesian.predict_match(team1, team2)
            predictions["bayesian"] = bay_pred["team1_win_prob"]
            active_weights["bayesian"] = weight_source.get("bayesian", 0.10)

        # ── 3. Monte Carlo simulation ─────────────────────────────────
        if self.monte_carlo.team_params:
            # Pass venue factor based on historical data
            venue_factor = self._get_venue_scoring_factor(venue) if venue else 1.0
            mc_pred = self.monte_carlo.simulate_match(
                team1, team2,
                venue_factor=venue_factor,
                toss_winner=toss_winner,
                toss_decision=toss_decision,
            )
            predictions["monte_carlo"] = mc_pred["team1_win_prob"]
            active_weights["monte_carlo"] = weight_source.get("monte_carlo", 0.10)

        # ── 4. Combine predictions ────────────────────────────────────
        if not predictions:
            return {
                "team1": team1,
                "team2": team2,
                "team1_win_prob": 0.5,
                "team2_win_prob": 0.5,
                "confidence": 0.0,
                "key_factors": ["Insufficient data for prediction"],
                "model_predictions": {},
            }

        # Normalize weights
        total_weight = sum(active_weights.values())
        if total_weight > 0:
            norm_weights = {k: v / total_weight for k, v in active_weights.items()}
        else:
            norm_weights = {k: 1.0 / len(predictions) for k in predictions}

        # Weighted average
        team1_prob = sum(
            predictions[model] * norm_weights.get(model, 0)
            for model in predictions
        )

        # Clip to valid range
        team1_prob = np.clip(team1_prob, 0.02, 0.98)
        team2_prob = 1.0 - team1_prob

        # ── 5. Confidence score ───────────────────────────────────────
        pred_values = list(predictions.values())
        pred_std = np.std(pred_values) if len(pred_values) > 1 else 0.2
        agreement = 1.0 - min(pred_std * 2, 0.5)
        n_models = len(predictions)
        model_coverage = min(n_models / 5, 1.0)
        confidence = round(agreement * 0.7 + model_coverage * 0.3, 3)

        # ── 6. Key factors ────────────────────────────────────────────
        key_factors = self._analyze_key_factors(
            team1, team2, venue, toss_winner, toss_decision,
            predictions, weather,
        )

        # ── 7. Determine predicted winner ─────────────────────────────
        predicted_winner = team1 if team1_prob > 0.5 else team2

        result = {
            "team1": team1,
            "team2": team2,
            "team1_win_prob": round(float(team1_prob), 4),
            "team2_win_prob": round(float(team2_prob), 4),
            "confidence": confidence,
            "predicted_winner": predicted_winner,
            "key_factors": key_factors,
            "model_predictions": {k: round(v, 4) for k, v in predictions.items()},
            "timestamp": datetime.utcnow().isoformat(),
        }

        logger.info(
            f"Prediction: {team1} ({team1_prob:.1%}) vs {team2} ({team2_prob:.1%}) "
            f"| Confidence: {confidence:.1%} | Winner: {predicted_winner}"
        )

        return result

    def _build_minimal_features(
        self, team1, team2, venue, city, toss_winner, toss_decision
    ) -> pd.DataFrame | None:
        """Build a rich feature vector from historical data for any matchup."""
        if not self.ml_trainer.feature_columns:
            return None

        row = {col: 0.0 for col in self.ml_trainer.feature_columns}
        df = self._matches_df

        # ── Toss features ────────────────────────────────────────────
        if toss_winner:
            row["toss_winner_is_team1"] = 1 if toss_winner == team1 else 0
        else:
            row["toss_winner_is_team1"] = 0.5  # Unknown
        if toss_decision:
            row["chose_bat"] = 1 if toss_decision == "bat" else 0
            row["chose_field"] = 1 if toss_decision == "field" else 0
        else:
            row["chose_bat"] = 0.45
            row["chose_field"] = 0.55

        # ── Team strength from Bayesian ──────────────────────────────
        s1_data = self.bayesian.team_strengths.get(team1, {})
        s2_data = self.bayesian.team_strengths.get(team2, {})
        s1 = s1_data.get("mean_strength", 0.5)
        s2 = s2_data.get("mean_strength", 0.5)

        row["team1_win_pct_last5"] = s1
        row["team1_win_pct_last10"] = s1
        row["team1_win_pct_season"] = s1
        row["team2_win_pct_last5"] = s2
        row["team2_win_pct_last10"] = s2
        row["team2_win_pct_season"] = s2
        row["form_diff_last5"] = s1 - s2
        row["form_diff_last10"] = s1 - s2
        row["team1_matches_played"] = s1_data.get("wins", 50) + s1_data.get("losses", 50)
        row["team2_matches_played"] = s2_data.get("wins", 50) + s2_data.get("losses", 50)
        row["experience_diff"] = row["team1_matches_played"] - row["team2_matches_played"]

        # ── Historical stats from real data ──────────────────────────
        if df is not None and not df.empty:
            # Team 1 recent form (last N matches)
            t1_matches = df[(df["team1"] == team1) | (df["team2"] == team1)].tail(10)
            t2_matches = df[(df["team1"] == team2) | (df["team2"] == team2)].tail(10)

            if not t1_matches.empty:
                t1_wins_recent = len(t1_matches[t1_matches["winner"] == team1])
                row["team1_win_pct_last10"] = t1_wins_recent / len(t1_matches)
                t1_last5 = t1_matches.tail(5)
                row["team1_win_pct_last5"] = len(t1_last5[t1_last5["winner"] == team1]) / len(t1_last5)

            if not t2_matches.empty:
                t2_wins_recent = len(t2_matches[t2_matches["winner"] == team2])
                row["team2_win_pct_last10"] = t2_wins_recent / len(t2_matches)
                t2_last5 = t2_matches.tail(5)
                row["team2_win_pct_last5"] = len(t2_last5[t2_last5["winner"] == team2]) / len(t2_last5)

            row["form_diff_last5"] = row["team1_win_pct_last5"] - row["team2_win_pct_last5"]
            row["form_diff_last10"] = row["team1_win_pct_last10"] - row["team2_win_pct_last10"]

            # Momentum (win streaks)
            if not t1_matches.empty:
                streak = 0
                for _, m in t1_matches.iloc[::-1].iterrows():
                    if m.get("winner") == team1:
                        streak += 1
                    else:
                        break
                row["team1_win_streak"] = streak

            if not t2_matches.empty:
                streak = 0
                for _, m in t2_matches.iloc[::-1].iterrows():
                    if m.get("winner") == team2:
                        streak += 1
                    else:
                        break
                row["team2_win_streak"] = streak

            row["momentum_diff"] = row.get("team1_win_streak", 0) - row.get("team2_win_streak", 0)

            # ── Head to head ─────────────────────────────────────────
            h2h = df[
                ((df["team1"] == team1) & (df["team2"] == team2)) |
                ((df["team1"] == team2) & (df["team2"] == team1))
            ]
            if not h2h.empty:
                t1_h2h_wins = len(h2h[h2h["winner"] == team1])
                row["h2h_team1_win_pct"] = t1_h2h_wins / len(h2h)
                row["h2h_total_matches"] = len(h2h)
            else:
                row["h2h_team1_win_pct"] = 0.5
                row["h2h_total_matches"] = 0

            # ── Venue features ───────────────────────────────────────
            if venue:
                vm = df[df["venue"].str.contains(str(venue)[:20], case=False, na=False)]
                if not vm.empty:
                    row["venue_matches"] = len(vm)
                    if "inn1_total_runs" in vm.columns:
                        avg_score = vm["inn1_total_runs"].mean()
                        row["venue_avg_first_score"] = avg_score if pd.notna(avg_score) else 165

                    # Chase win % at venue
                    chase_wins = 0
                    total_decided = 0
                    for _, m in vm.iterrows():
                        if pd.notna(m.get("winner")) and pd.notna(m.get("toss_decision")):
                            total_decided += 1
                            if m["toss_decision"] == "field" and m.get("toss_winner") == m.get("winner"):
                                chase_wins += 1
                            elif m["toss_decision"] == "bat" and m.get("toss_winner") != m.get("winner"):
                                chase_wins += 1
                    row["venue_chase_win_pct"] = chase_wins / total_decided if total_decided > 0 else 0.5

                    # Team venue record
                    t1_vm = vm[(vm["team1"] == team1) | (vm["team2"] == team1)]
                    t2_vm = vm[(vm["team1"] == team2) | (vm["team2"] == team2)]
                    row["team1_venue_win_pct"] = len(t1_vm[t1_vm["winner"] == team1]) / len(t1_vm) if len(t1_vm) > 0 else 0.5
                    row["team2_venue_win_pct"] = len(t2_vm[t2_vm["winner"] == team2]) / len(t2_vm) if len(t2_vm) > 0 else 0.5

            # Home advantage
            home_venues = {
                "Chennai Super Kings": ["Chidambaram", "Chennai"],
                "Mumbai Indians": ["Wankhede", "Mumbai"],
                "Royal Challengers Bengaluru": ["Chinnaswamy", "Bengaluru", "Bangalore"],
                "Kolkata Knight Riders": ["Eden", "Kolkata"],
                "Sunrisers Hyderabad": ["Rajiv Gandhi", "Hyderabad"],
                "Rajasthan Royals": ["Mansingh", "Jaipur"],
                "Delhi Capitals": ["Jaitley", "Feroz Shah", "Delhi"],
                "Punjab Kings": ["PCA", "Mohali"],
                "Lucknow Super Giants": ["Ekana", "Lucknow"],
                "Gujarat Titans": ["Narendra Modi", "Ahmedabad"],
            }
            venue_str = f"{venue or ''} {city or ''}".lower()
            is_home1 = any(h.lower() in venue_str for h in home_venues.get(team1, []))
            is_home2 = any(h.lower() in venue_str for h in home_venues.get(team2, []))
            row["is_home_team1"] = int(is_home1)
            row["is_home_team2"] = int(is_home2)
            row["home_advantage"] = int(is_home1) - int(is_home2)

            # Toss-venue advantage
            chase_pct = row.get("venue_chase_win_pct", 0.5)
            if toss_winner and toss_decision:
                if toss_winner == team1:
                    row["toss_venue_advantage"] = chase_pct if toss_decision == "field" else (1 - chase_pct)
                else:
                    row["toss_venue_advantage"] = (1 - chase_pct) if toss_decision == "field" else chase_pct
            else:
                row["toss_venue_advantage"] = 0.5

            # ── Innings averages (use team historical) ───────────────
            t1_batting = df[df["team1"] == team1]
            t2_batting = df[df["team1"] == team2]
            if "inn1_total_runs" in df.columns:
                row["inn1_total_runs"] = t1_batting["inn1_total_runs"].mean() if not t1_batting.empty and pd.notna(t1_batting["inn1_total_runs"].mean()) else 160
                row["inn2_total_runs"] = t2_batting.get("inn2_total_runs", pd.Series()).mean() if not t2_batting.empty else 155
                if pd.isna(row["inn2_total_runs"]):
                    row["inn2_total_runs"] = 155

            # Average wickets, run rate etc.
            for col_prefix, team_df in [("inn1", t1_batting), ("inn2", t2_batting)]:
                for stat in ["wickets", "fours", "sixes", "run_rate", "powerplay_runs", "middle_overs_runs", "death_overs_runs"]:
                    col = f"{col_prefix}_{stat}"
                    if col in df.columns and not team_df.empty:
                        val = team_df[col].mean()
                        if pd.notna(val):
                            row[col] = val

            # Season features
            row["year"] = 2026
            row["season_progress"] = 0.3  # early season default

            # Average margin
            t1_wins_df = df[df["winner"] == team1]
            t2_wins_df = df[df["winner"] == team2]
            if "result_margin" in df.columns:
                row["team1_avg_margin"] = t1_wins_df["result_margin"].mean() if not t1_wins_df.empty else 0
                row["team2_avg_margin"] = t2_wins_df["result_margin"].mean() if not t2_wins_df.empty else 0
                if pd.isna(row["team1_avg_margin"]):
                    row["team1_avg_margin"] = 0
                if pd.isna(row["team2_avg_margin"]):
                    row["team2_avg_margin"] = 0

        return pd.DataFrame([row])

    def _get_venue_scoring_factor(self, venue: str) -> float:
        """Get venue scoring factor relative to average."""
        if self._matches_df is None or not venue:
            return 1.0
        df = self._matches_df
        vm = df[df["venue"].str.contains(str(venue)[:20], case=False, na=False)]
        if vm.empty or "inn1_total_runs" not in vm.columns:
            return 1.0
        venue_avg = vm["inn1_total_runs"].mean()
        overall_avg = df["inn1_total_runs"].mean()
        if pd.isna(venue_avg) or pd.isna(overall_avg) or overall_avg == 0:
            return 1.0
        return venue_avg / overall_avg

    def _analyze_key_factors(
        self, team1, team2, venue, toss_winner, toss_decision,
        predictions, weather,
    ) -> list[str]:
        """Determine key factors influencing the prediction."""
        factors = []
        predicted_winner = team1 if np.mean(list(predictions.values())) > 0.5 else team2

        # Bayesian strength
        if self.bayesian.team_strengths:
            s1 = self.bayesian.team_strengths.get(team1, {}).get("mean_strength", 0.5)
            s2 = self.bayesian.team_strengths.get(team2, {}).get("mean_strength", 0.5)
            if abs(s1 - s2) > 0.05:
                stronger = team1 if s1 > s2 else team2
                factors.append(f"{stronger} has stronger historical record")

        # Toss
        if toss_winner:
            factors.append(f"Toss won by {toss_winner} (chose to {toss_decision or 'unknown'})")

        # Venue
        if venue:
            factors.append(f"Venue: {venue}")

        # Weather
        if weather:
            if weather.get("dew_probability", 0) > 0.6:
                factors.append("High dew probability favors chasing team")
            if weather.get("rain_probability", 0) > 0.3:
                factors.append("Rain risk may affect match outcome")

        # Model agreement
        pred_values = list(predictions.values())
        agree_count = sum(1 for p in pred_values if (p > 0.5) == (np.mean(pred_values) > 0.5))
        if agree_count == len(pred_values):
            factors.append(f"All {len(pred_values)} models agree on {predicted_winner}")
        else:
            factors.append(f"{agree_count}/{len(pred_values)} models favor {predicted_winner}")

        return factors

    def predict_today_matches(self, matches: list[dict]) -> list[dict]:
        """Predict all matches for today."""
        results = []
        for match in matches:
            pred = self.predict_match(
                team1=match.get("team1", ""),
                team2=match.get("team2", ""),
                venue=match.get("venue"),
                city=match.get("city"),
                toss_winner=match.get("toss_winner"),
                toss_decision=match.get("toss_decision"),
                weather=match.get("weather"),
            )
            pred["match_number"] = match.get("match_number")
            results.append(pred)
        return results

    def save_prediction(self, prediction: dict):
        """Save prediction to file for tracking."""
        pred_dir = settings.data_dir / "predictions"
        pred_dir.mkdir(exist_ok=True)

        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"{date_str}_{prediction['team1']}_vs_{prediction['team2']}.json"
        filepath = pred_dir / filename.replace(" ", "_")

        with open(filepath, "w") as f:
            json.dump(prediction, f, indent=2, default=str)

        logger.info(f"Prediction saved: {filepath}")
