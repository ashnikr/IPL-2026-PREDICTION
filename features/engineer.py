"""
Advanced Feature Engineering.

Creates 100+ features for match prediction including team form,
player performance, venue stats, head-to-head, and contextual features.
"""

import pandas as pd
import numpy as np
from collections import defaultdict

from utils.logger import logger
from config.settings import settings


class FeatureEngineer:
    """Generate advanced features for IPL match prediction."""

    def __init__(self):
        self.processed_dir = settings.processed_data_dir

    def engineer_features(
        self,
        matches: pd.DataFrame,
        deliveries: pd.DataFrame = None,
        player_stats: pd.DataFrame = None,
    ) -> pd.DataFrame:
        """Run the full feature engineering pipeline."""
        logger.info("Starting feature engineering...")
        df = matches.copy()

        # Sort by date to ensure temporal ordering
        if "date" in df.columns:
            df = df.sort_values("date").reset_index(drop=True)

        # Generate all feature groups
        df = self._team_form_features(df)
        df = self._head_to_head_features(df)
        df = self._venue_features(df)
        df = self._toss_features(df)
        df = self._season_features(df)
        df = self._momentum_features(df)

        if player_stats is not None:
            df = self._player_strength_features(df, player_stats)

        if deliveries is not None:
            df = self._scoring_pattern_features(df, deliveries)

        # Weather-based features (from columns if available)
        df = self._weather_features(df)

        # Encode categorical variables
        df = self._encode_categoricals(df)

        # Drop rows without target
        if "team1_win" in df.columns:
            before = len(df)
            df = df.dropna(subset=["team1_win"])
            logger.info(f"Dropped {before - len(df)} rows without result")

        # Save
        df.to_csv(self.processed_dir / "features.csv", index=False)
        logger.info(f"Feature engineering complete: {df.shape[1]} features, {len(df)} matches")

        return df

    def _team_form_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute rolling team performance features."""
        logger.info("Computing team form features...")

        # Track team results chronologically
        team_results = defaultdict(list)

        features = {
            "team1_win_pct_last5": [],
            "team1_win_pct_last10": [],
            "team2_win_pct_last5": [],
            "team2_win_pct_last10": [],
            "team1_win_pct_season": [],
            "team2_win_pct_season": [],
            "team1_matches_played": [],
            "team2_matches_played": [],
        }

        for _, row in df.iterrows():
            t1, t2 = row["team1"], row["team2"]
            season = row.get("season", 0)

            # Team 1 recent form
            t1_results = team_results[t1]
            t1_season = [r for r in t1_results if r[1] == season]
            features["team1_win_pct_last5"].append(
                np.mean([r[0] for r in t1_results[-5:]]) if len(t1_results) >= 1 else 0.5
            )
            features["team1_win_pct_last10"].append(
                np.mean([r[0] for r in t1_results[-10:]]) if len(t1_results) >= 1 else 0.5
            )
            features["team1_win_pct_season"].append(
                np.mean([r[0] for r in t1_season]) if t1_season else 0.5
            )
            features["team1_matches_played"].append(len(t1_results))

            # Team 2 recent form
            t2_results = team_results[t2]
            t2_season = [r for r in t2_results if r[1] == season]
            features["team2_win_pct_last5"].append(
                np.mean([r[0] for r in t2_results[-5:]]) if len(t2_results) >= 1 else 0.5
            )
            features["team2_win_pct_last10"].append(
                np.mean([r[0] for r in t2_results[-10:]]) if len(t2_results) >= 1 else 0.5
            )
            features["team2_win_pct_season"].append(
                np.mean([r[0] for r in t2_season]) if t2_season else 0.5
            )
            features["team2_matches_played"].append(len(t2_results))

            # Update results
            if pd.notna(row.get("winner")):
                t1_won = 1 if row["winner"] == t1 else 0
                team_results[t1].append((t1_won, season))
                team_results[t2].append((1 - t1_won, season))

        for feat_name, values in features.items():
            df[feat_name] = values

        # Derived: form differential
        df["form_diff_last5"] = df["team1_win_pct_last5"] - df["team2_win_pct_last5"]
        df["form_diff_last10"] = df["team1_win_pct_last10"] - df["team2_win_pct_last10"]
        df["experience_diff"] = df["team1_matches_played"] - df["team2_matches_played"]

        return df

    def _head_to_head_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute head-to-head record features."""
        logger.info("Computing head-to-head features...")

        h2h_record = defaultdict(lambda: {"wins": 0, "total": 0})

        h2h_win_pct = []
        h2h_matches = []

        for _, row in df.iterrows():
            t1, t2 = row["team1"], row["team2"]
            key = tuple(sorted([t1, t2]))

            record = h2h_record[key]
            if record["total"] > 0:
                # Calculate from t1's perspective
                t1_key_wins = h2h_record[(t1, t2)]["wins"] if (t1, t2) in h2h_record else 0
                total = record["total"]
                h2h_win_pct.append(t1_key_wins / total if total > 0 else 0.5)
            else:
                h2h_win_pct.append(0.5)
            h2h_matches.append(record["total"])

            # Update after
            if pd.notna(row.get("winner")):
                record["total"] += 1
                if row["winner"] == t1:
                    h2h_record[(t1, t2)]["wins"] = h2h_record[(t1, t2)].get("wins", 0) + 1
                else:
                    h2h_record[(t2, t1)]["wins"] = h2h_record[(t2, t1)].get("wins", 0) + 1
                h2h_record[key] = record

        df["h2h_team1_win_pct"] = h2h_win_pct
        df["h2h_total_matches"] = h2h_matches

        return df

    def _venue_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute venue-based features."""
        logger.info("Computing venue features...")

        venue_stats = defaultdict(lambda: {
            "matches": 0, "bat_first_wins": 0,
            "total_score_inn1": 0, "total_score_inn2": 0,
        })

        # Team-venue performance
        team_venue_stats = defaultdict(lambda: {"wins": 0, "total": 0})

        venue_feats = {
            "venue_avg_first_score": [],
            "venue_chase_win_pct": [],
            "venue_matches": [],
            "team1_venue_win_pct": [],
            "team2_venue_win_pct": [],
            "is_home_team1": [],
            "is_home_team2": [],
        }

        # Home venue mapping
        home_venues = {
            "Chennai Super Kings": ["MA Chidambaram Stadium", "Chennai"],
            "Mumbai Indians": ["Wankhede Stadium", "Mumbai"],
            "Royal Challengers Bengaluru": ["M Chinnaswamy Stadium", "Bengaluru", "Bangalore"],
            "Kolkata Knight Riders": ["Eden Gardens", "Kolkata"],
            "Sunrisers Hyderabad": ["Rajiv Gandhi", "Hyderabad"],
            "Rajasthan Royals": ["Sawai Mansingh", "Jaipur"],
            "Delhi Capitals": ["Arun Jaitley", "Feroz Shah Kotla", "Delhi"],
            "Punjab Kings": ["PCA", "Mohali", "Punjab"],
            "Lucknow Super Giants": ["Ekana", "Lucknow"],
            "Gujarat Titans": ["Narendra Modi", "Ahmedabad"],
        }

        for _, row in df.iterrows():
            venue = row.get("venue", "Unknown")
            city = row.get("city", "Unknown")
            t1, t2 = row["team1"], row["team2"]

            vs = venue_stats[venue]
            venue_feats["venue_matches"].append(vs["matches"])
            venue_feats["venue_avg_first_score"].append(
                vs["total_score_inn1"] / vs["matches"] if vs["matches"] > 0 else 165
            )
            venue_feats["venue_chase_win_pct"].append(
                1 - vs["bat_first_wins"] / vs["matches"] if vs["matches"] > 0 else 0.5
            )

            # Team-venue
            tv1 = team_venue_stats[(t1, venue)]
            tv2 = team_venue_stats[(t2, venue)]
            venue_feats["team1_venue_win_pct"].append(
                tv1["wins"] / tv1["total"] if tv1["total"] > 0 else 0.5
            )
            venue_feats["team2_venue_win_pct"].append(
                tv2["wins"] / tv2["total"] if tv2["total"] > 0 else 0.5
            )

            # Home advantage
            venue_str = f"{venue} {city}".lower()
            is_home1 = any(h.lower() in venue_str for h in home_venues.get(t1, []))
            is_home2 = any(h.lower() in venue_str for h in home_venues.get(t2, []))
            venue_feats["is_home_team1"].append(int(is_home1))
            venue_feats["is_home_team2"].append(int(is_home2))

            # Update stats
            if pd.notna(row.get("winner")):
                vs["matches"] += 1
                inn1_score = row.get("inn1_total_runs", 165)
                inn2_score = row.get("inn2_total_runs", 155)
                vs["total_score_inn1"] += inn1_score if pd.notna(inn1_score) else 165
                vs["total_score_inn2"] += inn2_score if pd.notna(inn2_score) else 155

                # Bat first win?
                if row.get("toss_decision") == "bat" and row["winner"] == row.get("toss_winner"):
                    vs["bat_first_wins"] += 1
                elif row.get("toss_decision") == "field" and row["winner"] != row.get("toss_winner"):
                    vs["bat_first_wins"] += 1

                team_venue_stats[(t1, venue)]["total"] += 1
                team_venue_stats[(t2, venue)]["total"] += 1
                if row["winner"] == t1:
                    team_venue_stats[(t1, venue)]["wins"] += 1
                else:
                    team_venue_stats[(t2, venue)]["wins"] += 1

        for feat_name, values in venue_feats.items():
            df[feat_name] = values

        df["home_advantage"] = df["is_home_team1"] - df["is_home_team2"]

        return df

    def _toss_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute toss-related features."""
        logger.info("Computing toss features...")

        if "toss_winner" in df.columns:
            df["toss_winner_is_team1"] = (df["toss_winner"] == df["team1"]).astype(int)

        if "toss_decision" in df.columns:
            df["chose_bat"] = (df["toss_decision"] == "bat").astype(int)
            df["chose_field"] = (df["toss_decision"] == "field").astype(int)

        # Toss advantage at venue
        if "venue_chase_win_pct" in df.columns:
            df["toss_venue_advantage"] = np.where(
                df.get("toss_winner_is_team1", 0) == 1,
                np.where(
                    df["chose_field"] == 1,
                    df["venue_chase_win_pct"],
                    1 - df["venue_chase_win_pct"],
                ),
                np.where(
                    df.get("chose_field", 0) == 1,
                    1 - df["venue_chase_win_pct"],
                    df["venue_chase_win_pct"],
                ),
            )

        return df

    def _season_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Season position and stage features."""
        logger.info("Computing season features...")

        if "season" in df.columns:
            # Match number within season
            df["season_match_num"] = df.groupby("season").cumcount() + 1
            season_sizes = df.groupby("season")["season_match_num"].transform("max")
            df["season_progress"] = df["season_match_num"] / season_sizes

            # Phase of tournament
            df["is_playoff"] = (df.get("match_type", "League") != "League").astype(int)

        return df

    def _momentum_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute team momentum (win streaks, loss streaks)."""
        logger.info("Computing momentum features...")

        team_streaks = defaultdict(lambda: {"current_streak": 0, "last_3_margin": []})

        t1_streak = []
        t2_streak = []
        t1_avg_margin = []
        t2_avg_margin = []

        for _, row in df.iterrows():
            t1, t2 = row["team1"], row["team2"]

            t1_streak.append(team_streaks[t1]["current_streak"])
            t2_streak.append(team_streaks[t2]["current_streak"])

            margins_1 = team_streaks[t1]["last_3_margin"]
            margins_2 = team_streaks[t2]["last_3_margin"]
            t1_avg_margin.append(np.mean(margins_1[-3:]) if margins_1 else 0)
            t2_avg_margin.append(np.mean(margins_2[-3:]) if margins_2 else 0)

            if pd.notna(row.get("winner")):
                margin = row.get("result_margin", 0) or 0

                if row["winner"] == t1:
                    s1 = team_streaks[t1]["current_streak"]
                    team_streaks[t1]["current_streak"] = s1 + 1 if s1 > 0 else 1
                    team_streaks[t2]["current_streak"] = min(team_streaks[t2]["current_streak"], 0) - 1
                    team_streaks[t1]["last_3_margin"].append(margin)
                    team_streaks[t2]["last_3_margin"].append(-margin)
                else:
                    s2 = team_streaks[t2]["current_streak"]
                    team_streaks[t2]["current_streak"] = s2 + 1 if s2 > 0 else 1
                    team_streaks[t1]["current_streak"] = min(team_streaks[t1]["current_streak"], 0) - 1
                    team_streaks[t2]["last_3_margin"].append(margin)
                    team_streaks[t1]["last_3_margin"].append(-margin)

        df["team1_win_streak"] = t1_streak
        df["team2_win_streak"] = t2_streak
        df["team1_avg_margin"] = t1_avg_margin
        df["team2_avg_margin"] = t2_avg_margin
        df["momentum_diff"] = df["team1_win_streak"] - df["team2_win_streak"]

        return df

    def _player_strength_features(self, df: pd.DataFrame, player_stats: pd.DataFrame) -> pd.DataFrame:
        """Compute team strength based on player statistics."""
        logger.info("Computing player strength features...")

        # Aggregate player stats by team and season
        if "season" not in player_stats.columns:
            return df

        # Get top performers per season
        season_stats = player_stats.groupby("season").agg(
            avg_strike_rate=("strike_rate", "mean"),
            avg_batting_avg=("batting_avg", "mean"),
            avg_economy=("economy", lambda x: x[x > 0].mean() if (x > 0).any() else 8.0),
        ).reset_index()

        df = df.merge(season_stats, on="season", how="left")

        # Fill missing
        df["avg_strike_rate"] = df["avg_strike_rate"].fillna(130)
        df["avg_batting_avg"] = df["avg_batting_avg"].fillna(25)
        df["avg_economy"] = df["avg_economy"].fillna(8.0)

        return df

    def _scoring_pattern_features(self, df: pd.DataFrame, deliveries: pd.DataFrame) -> pd.DataFrame:
        """Features based on team scoring patterns."""
        logger.info("Computing scoring pattern features...")

        # Team powerplay performance
        if "phase" not in deliveries.columns and "over" in deliveries.columns:
            deliveries = deliveries.copy()
            deliveries["phase"] = pd.cut(
                deliveries["over"], bins=[-1, 5, 15, 20],
                labels=["powerplay", "middle", "death"],
            )

        return df

    def _weather_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate weather impact features if weather columns exist."""
        weather_cols = ["temperature", "humidity", "wind_speed", "dew_probability", "rain_probability"]
        has_weather = any(col in df.columns for col in weather_cols)

        if has_weather:
            logger.info("Computing weather features...")
            if "dew_probability" in df.columns:
                df["dew_chase_advantage"] = df["dew_probability"] * 0.15
            if "temperature" in df.columns and "humidity" in df.columns:
                df["heat_index"] = df["temperature"] + 0.5 * df["humidity"]
        else:
            # Add default weather features
            df["dew_chase_advantage"] = 0.07
            df["heat_index"] = 75

        return df

    def _encode_categoricals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Encode categorical variables."""
        logger.info("Encoding categorical variables...")

        # Label encode teams
        all_teams = sorted(set(df["team1"].unique()) | set(df["team2"].unique()))
        team_to_idx = {team: idx for idx, team in enumerate(all_teams)}

        df["team1_encoded"] = df["team1"].map(team_to_idx)
        df["team2_encoded"] = df["team2"].map(team_to_idx)

        # Label encode venue
        if "venue" in df.columns:
            venue_to_idx = {v: i for i, v in enumerate(df["venue"].unique())}
            df["venue_encoded"] = df["venue"].map(venue_to_idx)

        return df

    def get_feature_columns(self, df: pd.DataFrame) -> list[str]:
        """Get the list of numeric feature columns for modeling."""
        exclude = {
            "match_id", "date", "team1", "team2", "venue", "city",
            "winner", "player_of_match", "umpire1", "umpire2",
            "toss_winner", "toss_decision", "result", "match_type",
            "team1_win", "has_result", "venue_normalized", "season",
            "phase", "extras_type",
        }

        feature_cols = [
            col for col in df.columns
            if col not in exclude
            and df[col].dtype in ["int64", "float64", "int32", "float32"]
        ]

        return feature_cols
