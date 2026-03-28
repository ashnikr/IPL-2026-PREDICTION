"""
Daily Match Prediction Engine - Enhanced for IPL 2026.

Full pipeline:
1. Fetches today's IPL matches with dates, times, venues
2. Collects live weather (via WeatherAPI)
3. Gets squad info, playing XI, injuries, impact player analysis
4. Runs toss prediction + DLS/rain analysis
5. Generates ensemble prediction with 8 models
6. Outputs detailed predictions with explanations

Supports: match timings (IST), double headers, impact player,
          DLS/rain scenarios, live squad changes.
"""

import json
from datetime import datetime, date, timedelta
from pathlib import Path

import pandas as pd
import numpy as np

from utils.logger import logger
from config.settings import settings
from scrapers.live_data_scraper import LiveDataScraper
from scrapers.weather_scraper import WeatherCollector
from scrapers.cricbuzz_scraper import CricbuzzScraper
from models.ensemble import EnsemblePrediction
from models.explainability import PredictionExplainer
from models.impact_player import ImpactPlayerAnalyzer
from models.dls_rain import DLSRainAnalyzer
from models.toss_predictor import TossPredictor


class DailyPredictor:
    """Autonomous daily IPL match prediction engine with full live data."""

    def __init__(self):
        self.live_scraper = LiveDataScraper()
        self.weather = WeatherCollector()
        self.cricbuzz = CricbuzzScraper()
        self.ensemble = EnsemblePrediction()
        self.explainer = PredictionExplainer()
        self.impact_analyzer = ImpactPlayerAnalyzer()
        self.dls_analyzer = DLSRainAnalyzer()
        self.toss_predictor = TossPredictor()
        self.predictions_dir = settings.data_dir / "predictions"
        self.predictions_dir.mkdir(exist_ok=True)

    def run_daily_pipeline(self) -> list[dict]:
        """Run the full daily prediction pipeline."""
        logger.info("=" * 60)
        logger.info(f"DAILY PREDICTION PIPELINE - {date.today()}")
        logger.info("=" * 60)

        # Step 1: Get today's matches
        logger.info("Step 1: Fetching today's matches...")
        today_matches = self.live_scraper.get_today_matches()

        if not today_matches:
            # Check tomorrow
            tomorrow_matches = self.live_scraper.get_tomorrow_matches()
            if tomorrow_matches:
                logger.info(f"No matches today. Tomorrow has {len(tomorrow_matches)} match(es):")
                for m in tomorrow_matches:
                    print(f"  {m['team1']} vs {m['team2']} - {m.get('date')} at {m.get('time_ist', '19:30')} IST")
            else:
                logger.info("No matches scheduled for today or tomorrow.")
            return []

        is_double = len(today_matches) >= 2
        if is_double:
            logger.info(f"DOUBLE HEADER DAY! {len(today_matches)} matches today")

        # Step 2: Predict each match
        predictions = []
        for i, match in enumerate(today_matches):
            logger.info(f"\n{'='*50}")
            logger.info(f"Match {i+1}/{len(today_matches)}: {match['team1']} vs {match['team2']}")
            logger.info(f"Time: {match.get('time_ist', '19:30')} IST | Venue: {match.get('venue', 'TBD')}")
            logger.info(f"{'='*50}")

            pred = self._predict_single_match(match)
            predictions.append(pred)
            self._print_prediction(pred)

        # Save daily summary
        self._save_daily_summary(predictions)
        return predictions

    def _predict_single_match(self, match: dict) -> dict:
        """Generate a comprehensive prediction for one match."""
        team1 = match["team1"]
        team2 = match["team2"]
        venue = match.get("venue")
        city = match.get("city")
        time_ist = match.get("time_ist", "19:30")

        # ── 2a: Weather ─────────────────────────────────────────
        weather = self._get_match_weather(match)
        match["weather"] = weather

        # ── 2b: Squad / Playing XI ──────────────────────────────
        match_info = self.live_scraper.get_match_info(team1, team2)
        xi_team1 = match_info["team1"]["playing_xi"]
        xi_team2 = match_info["team2"]["playing_xi"]

        # ── 2c: Injuries ────────────────────────────────────────
        injuries = self._check_injuries()

        # ── 2d: Toss Prediction ──────────────────────────────────
        toss_pred = self.toss_predictor.predict_toss_decision(
            team1=team1, team2=team2,
            venue=venue, match_time=time_ist,
            weather=weather,
        )

        # ── 2e: DLS/Rain Analysis ────────────────────────────────
        rain_prob = weather.get("rain_probability", 0) if weather else 0
        rain_analysis = self.dls_analyzer.estimate_rain_impact(rain_prob, weather, venue)

        # ── 2f: Impact Player Analysis ───────────────────────────
        impact = self.impact_analyzer.estimate_impact_shift(
            team1, team2, venue, weather
        )

        # ── 2g: Squad Strength ───────────────────────────────────
        t1_strength = self.impact_analyzer.get_team_squad_strength(team1)
        t2_strength = self.impact_analyzer.get_team_squad_strength(team2)

        # ── 3: Run Ensemble Prediction ───────────────────────────
        pred = self.ensemble.predict_match(
            team1=team1,
            team2=team2,
            venue=venue,
            city=city,
            toss_winner=match.get("toss_winner"),
            toss_decision=match.get("toss_decision"),
            weather=weather,
            playing_xi_team1=[p["name"] for p in xi_team1] if xi_team1 else None,
            playing_xi_team2=[p["name"] for p in xi_team2] if xi_team2 else None,
        )

        # ── 4: Apply adjustments ─────────────────────────────────
        # Adjust for rain
        if rain_analysis["rain_risk"] in ("high", "very_high"):
            adj = rain_analysis["prediction_adjustment"]
            pred["team1_win_prob"] = round(np.clip(pred["team1_win_prob"] + adj, 0.02, 0.98), 4)
            pred["team2_win_prob"] = round(1 - pred["team1_win_prob"], 4)

        # Adjust for impact player
        if impact["net_shift"] != 0:
            pred["team1_win_prob"] = round(
                np.clip(pred["team1_win_prob"] + impact["net_shift"], 0.02, 0.98), 4
            )
            pred["team2_win_prob"] = round(1 - pred["team1_win_prob"], 4)

        # Re-determine winner after adjustments
        pred["predicted_winner"] = team1 if pred["team1_win_prob"] > 0.5 else team2

        # ── 5: Enrich prediction ─────────────────────────────────
        pred["match_number"] = match.get("match_number")
        pred["venue"] = venue or ""
        pred["city"] = city or ""
        pred["date"] = match.get("date", str(date.today()))
        pred["time_ist"] = time_ist
        pred["is_double_header"] = match.get("is_double_header", False)
        pred["weather"] = weather
        pred["toss_prediction"] = toss_pred
        pred["rain_analysis"] = rain_analysis
        pred["impact_player"] = impact
        pred["team1_squad"] = {
            "captain": t1_strength.get("captain"),
            "playing_xi": [p["name"] for p in xi_team1] if xi_team1 else [],
            "strength": t1_strength,
        }
        pred["team2_squad"] = {
            "captain": t2_strength.get("captain"),
            "playing_xi": [p["name"] for p in xi_team2] if xi_team2 else [],
            "strength": t2_strength,
        }
        pred["injuries"] = injuries[:5] if injuries else []

        # Add key factors from all analyses
        extra_factors = []
        if toss_pred["confidence"] > 0.2:
            extra_factors.append(
                f"Toss winner likely to {toss_pred['predicted_decision']} "
                f"({toss_pred['confidence']*100:.0f}% confidence)"
            )
        if rain_analysis["rain_risk"] in ("moderate", "high", "very_high"):
            extra_factors.append(rain_analysis["description"])
        for scenario in impact["scenarios"][:2]:
            extra_factors.append(f"Impact Player: {scenario}")
        if t1_strength.get("captain"):
            extra_factors.append(f"Captains: {t1_strength['captain']} vs {t2_strength.get('captain', 'Unknown')}")

        pred["key_factors"] = pred.get("key_factors", []) + extra_factors

        # Save
        self.ensemble.save_prediction(pred)
        return pred

    def predict_specific_match(
        self,
        team1: str,
        team2: str,
        venue: str = None,
        city: str = None,
        toss_winner: str = None,
        toss_decision: str = None,
    ) -> dict:
        """Predict a specific match on demand."""
        logger.info(f"Predicting: {team1} vs {team2}")

        # Build match dict
        match = {
            "team1": team1,
            "team2": team2,
            "venue": venue,
            "city": city or self._extract_city(venue),
            "toss_winner": toss_winner,
            "toss_decision": toss_decision,
            "time_ist": "19:30",
        }

        # Find in schedule for date/time
        schedule = self.live_scraper.get_current_schedule()
        for m in schedule:
            if (m.get("team1") == team1 and m.get("team2") == team2) or \
               (m.get("team1") == team2 and m.get("team2") == team1):
                match.update({
                    "date": m.get("date"),
                    "time_ist": m.get("time_ist", "19:30"),
                    "venue": match.get("venue") or m.get("venue"),
                    "city": match.get("city") or m.get("city"),
                    "match_number": m.get("match_number"),
                    "is_double_header": m.get("is_double_header", False),
                })
                break

        pred = self._predict_single_match(match)
        return pred

    def predict_tomorrow(self) -> list[dict]:
        """Predict all of tomorrow's matches."""
        tomorrow_matches = self.live_scraper.get_tomorrow_matches()
        if not tomorrow_matches:
            print("No matches scheduled for tomorrow.")
            return []

        predictions = []
        for match in tomorrow_matches:
            pred = self._predict_single_match(match)
            predictions.append(pred)
            self._print_prediction(pred)

        self._save_daily_summary(predictions, suffix="_tomorrow")
        return predictions

    def predict_upcoming(self, days: int = 7) -> list[dict]:
        """Predict all matches in the next N days."""
        upcoming = self.live_scraper.get_upcoming_matches(days)
        if not upcoming:
            print(f"No matches in the next {days} days.")
            return []

        predictions = []
        for match in upcoming:
            pred = self._predict_single_match(match)
            predictions.append(pred)

        return predictions

    def update_after_match(self, team1: str, team2: str, winner: str):
        """Update models after a completed match."""
        logger.info(f"Updating models: {winner} won ({team1} vs {team2})")
        self.ensemble.bayesian.update_with_result(team1, team2, winner)
        logger.info("Bayesian model updated with match result")

    # ── Private helpers ──────────────────────────────────────────────

    def _get_match_weather(self, match: dict) -> dict:
        """Get weather data for a match."""
        city = match.get("city", "")
        if not city:
            city = self._extract_city(match.get("venue", ""))

        if city:
            match_date = match.get("date", str(date.today()))
            try:
                weather = self.weather.get_weather(city, match_date)
                impact = self.weather.get_match_weather_impact(city, match_date)
                if impact:
                    weather.update(impact)
                return weather
            except Exception as e:
                logger.warning(f"Weather fetch failed: {e}")
        return {}

    def _extract_city(self, venue: str) -> str:
        """Extract city name from venue string."""
        if not venue:
            return ""
        city_map = {
            "Wankhede": "Mumbai", "Chinnaswamy": "Bengaluru",
            "Eden": "Kolkata", "Chidambaram": "Chennai",
            "Jaitley": "Delhi", "Rajiv Gandhi": "Hyderabad",
            "Mansingh": "Jaipur", "PCA": "Mohali",
            "Narendra Modi": "Ahmedabad", "Ekana": "Lucknow",
            "ACA": "Guwahati", "Barsapara": "Guwahati",
            "HPCA": "Dharamsala", "Dharamsala": "Dharamsala",
            "Nava Raipur": "Raipur", "Shaheed Veer": "Raipur",
            "Yadavindra": "Mullanpur", "Mullanpur": "Mullanpur",
        }
        for key, c in city_map.items():
            if key.lower() in venue.lower():
                return c
        return ""

    def _get_squads(self, match: dict) -> dict:
        """Get squad/playing XI information."""
        squads = self.live_scraper.get_team_squads()
        return {
            match["team1"]: squads.get(match["team1"], {}),
            match["team2"]: squads.get(match["team2"], {}),
        }

    def _check_injuries(self) -> list[dict]:
        """Check for injury updates."""
        try:
            return self.cricbuzz.get_injury_updates()
        except Exception:
            return []

    def _print_prediction(self, pred: dict):
        """Print detailed formatted prediction."""
        t1, t2 = pred["team1"], pred["team2"]
        p1, p2 = pred["team1_win_prob"], pred["team2_win_prob"]
        conf = pred["confidence"]
        winner = pred["predicted_winner"]

        print("\n" + "=" * 65)
        print(f"  MATCH {pred.get('match_number', '')}: {t1} vs {t2}")
        if pred.get("date"):
            print(f"  Date: {pred['date']} | Time: {pred.get('time_ist', '19:30')} IST")
        if pred.get("venue"):
            print(f"  Venue: {pred['venue']}, {pred.get('city', '')}")
        if pred.get("is_double_header"):
            print(f"  ** DOUBLE HEADER DAY **")
        print("-" * 65)

        # Captains
        t1_squad = pred.get("team1_squad", {})
        t2_squad = pred.get("team2_squad", {})
        if t1_squad.get("captain") or t2_squad.get("captain"):
            print(f"  Captains: {t1_squad.get('captain', '?')} vs {t2_squad.get('captain', '?')}")

        # Probabilities
        print(f"\n  {t1:35s}  {p1*100:5.1f}%")
        print(f"  {t2:35s}  {p2*100:5.1f}%")
        print(f"  Confidence: {conf*100:.1f}%")
        print(f"  PREDICTED WINNER: {winner}")
        print("-" * 65)

        # Weather
        weather = pred.get("weather", {})
        if weather:
            print(f"  Weather: {weather.get('condition', 'N/A')} | "
                  f"Temp: {weather.get('temperature', 'N/A')}C | "
                  f"Humidity: {weather.get('humidity', 'N/A')}%")
            if weather.get("dew_probability", 0) > 0.3:
                print(f"  Dew: {weather['dew_probability']*100:.0f}% (favors chasing)")
            if weather.get("rain_probability", 0) > 0.1:
                print(f"  Rain: {weather['rain_probability']*100:.0f}%")

        # Rain analysis
        rain = pred.get("rain_analysis", {})
        if rain.get("rain_risk") in ("moderate", "high", "very_high"):
            print(f"  RAIN ALERT: {rain.get('description', '')}")
            if rain.get("expected_overs", 20) < 20:
                print(f"  Expected overs: ~{rain['expected_overs']} (DLS likely)")

        # Toss prediction
        toss = pred.get("toss_prediction", {})
        if toss:
            print(f"  Toss: Winner likely to {toss.get('predicted_decision', '?')} "
                  f"({toss.get('confidence', 0)*100:.0f}% conf)")

        # Impact player
        impact = pred.get("impact_player", {})
        if impact and impact.get("scenarios"):
            print(f"  Impact Player: {impact['scenarios'][0]}")

        # Key factors
        if pred.get("key_factors"):
            print("\n  Key Factors:")
            for f in pred["key_factors"][:7]:
                print(f"    - {f}")

        print("=" * 65)

    def _save_daily_summary(self, predictions: list[dict], suffix: str = ""):
        """Save daily prediction summary."""
        summary = {
            "date": str(date.today()),
            "generated_at": datetime.now().isoformat(),
            "matches_predicted": len(predictions),
            "predictions": predictions,
        }

        filepath = self.predictions_dir / f"daily_{date.today()}{suffix}.json"
        with open(filepath, "w") as f:
            json.dump(summary, f, indent=2, default=str)

        logger.info(f"Daily summary saved: {filepath}")
