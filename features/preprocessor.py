"""
Data Preprocessing Pipeline.

Cleans, normalizes, and prepares raw IPL data for feature engineering.
"""

import re
from datetime import datetime

import pandas as pd
import numpy as np

from utils.logger import logger
from config.settings import settings


class DataPreprocessor:
    """Clean and preprocess IPL data."""

    # Team name normalization mapping
    TEAM_NAME_MAP = {
        "Delhi Daredevils": "Delhi Capitals",
        "Deccan Chargers": "Sunrisers Hyderabad",
        "Kings XI Punjab": "Punjab Kings",
        "Rising Pune Supergiant": "Rising Pune Supergiants",
        "Rising Pune Supergiants": "Rising Pune Supergiants",
        "Royal Challengers Bangalore": "Royal Challengers Bengaluru",
        "Pune Warriors India": "Pune Warriors India",
        "Pune Warriors": "Pune Warriors India",
        "Gujarat Lions": "Gujarat Lions",
        "Kochi Tuskers Kerala": "Kochi Tuskers Kerala",
    }

    # Player name normalization
    PLAYER_NAME_MAP = {
        "V Kohli": "Virat Kohli",
        "RG Sharma": "Rohit Sharma",
        "MS Dhoni": "MS Dhoni",
        "AB de Villiers": "AB de Villiers",
        "CH Gayle": "Chris Gayle",
        "DA Warner": "David Warner",
        "KL Rahul": "KL Rahul",
        "JC Buttler": "Jos Buttler",
        "RA Jadeja": "Ravindra Jadeja",
    }

    def __init__(self):
        self.processed_dir = settings.processed_data_dir

    def preprocess_matches(self, matches_df: pd.DataFrame) -> pd.DataFrame:
        """Full preprocessing pipeline for match data."""
        logger.info(f"Preprocessing {len(matches_df)} matches...")
        df = matches_df.copy()

        # 1. Clean column names (strip whitespace, lowercase, underscores)
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
        # Also strip whitespace from all string columns
        for col in df.select_dtypes(include=["object"]).columns:
            df[col] = df[col].astype(str).str.strip().replace("nan", pd.NA).replace("NA", pd.NA)

        # 2. Ensure required columns exist
        required = ["team1", "team2"]
        for col in required:
            if col not in df.columns:
                logger.error(f"Missing required column: {col}")
                return df

        # 3. Handle match_id
        if "match_id" not in df.columns:
            if "id" in df.columns:
                df["match_id"] = df["id"]
            else:
                df["match_id"] = range(1, len(df) + 1)

        # 4. Normalize team names
        for col in ["team1", "team2", "toss_winner", "winner"]:
            if col in df.columns:
                df[col] = df[col].map(lambda x: self.TEAM_NAME_MAP.get(x, x) if pd.notna(x) else x)

        # 5. Parse dates
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df["year"] = df["date"].dt.year
            df["month"] = df["date"].dt.month
            df["day_of_week"] = df["date"].dt.dayofweek

        # 6. Handle season
        if "season" not in df.columns:
            if "year" in df.columns:
                df["season"] = df["year"]
            elif "date" in df.columns:
                df["season"] = df["date"].dt.year

        # 7. Clean venue names
        if "venue" in df.columns:
            df["venue"] = df["venue"].str.strip()
            df["venue_normalized"] = df["venue"].apply(self._normalize_venue)

        # 8. Clean city names
        if "city" in df.columns:
            df["city"] = df["city"].fillna("Unknown").str.strip()

        # 9. Handle toss decision
        if "toss_decision" in df.columns:
            df["toss_decision"] = df["toss_decision"].str.lower().str.strip()
            df["toss_decision"] = df["toss_decision"].replace({"batting": "bat", "fielding": "field"})

        # 10. Create target variable
        if "winner" in df.columns:
            df["team1_win"] = (df["winner"] == df["team1"]).astype(int)
            # Handle no results / ties
            df.loc[df["winner"].isna(), "team1_win"] = np.nan

        # 11. Create derived columns
        if "toss_winner" in df.columns:
            df["toss_winner_is_team1"] = (df["toss_winner"] == df["team1"]).astype(int)

        # 12. Handle DL method
        if "dl_applied" not in df.columns:
            df["dl_applied"] = 0
        df["dl_applied"] = df["dl_applied"].fillna(0).astype(int)

        # 13. Remove duplicates
        if "match_id" in df.columns:
            before = len(df)
            df = df.drop_duplicates(subset=["match_id"], keep="first")
            removed = before - len(df)
            if removed > 0:
                logger.info(f"Removed {removed} duplicate matches")

        # 14. Sort by date
        if "date" in df.columns:
            df = df.sort_values("date").reset_index(drop=True)

        # 15. Drop matches with no result (optional - keep for analysis)
        df["has_result"] = df["winner"].notna().astype(int)

        logger.info(f"Preprocessing complete: {len(df)} matches")
        return df

    def preprocess_deliveries(self, deliveries_df: pd.DataFrame) -> pd.DataFrame:
        """Preprocess ball-by-ball data."""
        logger.info(f"Preprocessing {len(deliveries_df)} deliveries...")
        df = deliveries_df.copy()

        # Clean column names (strip whitespace - critical for real data)
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
        # Strip whitespace from string columns
        for col in df.select_dtypes(include=["object"]).columns:
            df[col] = df[col].astype(str).str.strip().replace("nan", pd.NA).replace("NA", pd.NA)

        # Ensure numeric columns
        for col in ["batsman_runs", "extra_runs", "total_runs", "is_wicket"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

        # Handle alternative column names
        col_renames = {
            "batting_team": "batting_team",
            "batsman": "batter",
            "non_striker": "non_striker",
            "bowler": "bowler",
        }
        for old, new in col_renames.items():
            if old in df.columns and new not in df.columns:
                df[new] = df[old]

        # Create ball number within over (1-6)
        if "ball" in df.columns:
            df["ball"] = df["ball"].clip(1, 7)

        # Create over phase
        if "over" in df.columns:
            df["phase"] = pd.cut(
                df["over"],
                bins=[-1, 5, 15, 20],
                labels=["powerplay", "middle", "death"],
            )

        # Is boundary
        if "batsman_runs" in df.columns:
            df["is_four"] = (df["batsman_runs"] == 4).astype(int)
            df["is_six"] = (df["batsman_runs"] == 6).astype(int)
            df["is_dot"] = (df["total_runs"] == 0).astype(int)

        logger.info(f"Deliveries preprocessing complete: {len(df)} rows")
        return df

    def compute_match_aggregates(self, matches_df: pd.DataFrame, deliveries_df: pd.DataFrame) -> pd.DataFrame:
        """Compute aggregate stats per match from ball-by-ball data."""
        logger.info("Computing match aggregates from ball-by-ball data...")

        aggs = []
        for match_id in matches_df["match_id"].unique():
            match_del = deliveries_df[deliveries_df["match_id"] == match_id]

            for inning in [1, 2]:
                inn_del = match_del[match_del["inning"] == inning]
                if inn_del.empty:
                    continue

                total_runs = inn_del["total_runs"].sum()
                wickets = inn_del["is_wicket"].sum() if "is_wicket" in inn_del.columns else 0
                balls = len(inn_del)
                fours = inn_del["is_four"].sum() if "is_four" in inn_del.columns else 0
                sixes = inn_del["is_six"].sum() if "is_six" in inn_del.columns else 0
                dots = inn_del["is_dot"].sum() if "is_dot" in inn_del.columns else 0
                extras = inn_del["extra_runs"].sum()

                # Phase-wise runs
                if "phase" in inn_del.columns:
                    pp_runs = inn_del[inn_del["phase"] == "powerplay"]["total_runs"].sum()
                    mid_runs = inn_del[inn_del["phase"] == "middle"]["total_runs"].sum()
                    death_runs = inn_del[inn_del["phase"] == "death"]["total_runs"].sum()
                else:
                    pp_runs = inn_del[inn_del["over"] < 6]["total_runs"].sum()
                    mid_runs = inn_del[(inn_del["over"] >= 6) & (inn_del["over"] < 16)]["total_runs"].sum()
                    death_runs = inn_del[inn_del["over"] >= 16]["total_runs"].sum()

                run_rate = total_runs / (balls / 6) if balls > 0 else 0

                aggs.append({
                    "match_id": match_id,
                    "inning": inning,
                    "total_runs": total_runs,
                    "wickets": wickets,
                    "balls": balls,
                    "fours": fours,
                    "sixes": sixes,
                    "dots": dots,
                    "extras": extras,
                    "run_rate": round(run_rate, 2),
                    "powerplay_runs": pp_runs,
                    "middle_overs_runs": mid_runs,
                    "death_overs_runs": death_runs,
                })

        agg_df = pd.DataFrame(aggs)

        if not agg_df.empty:
            # Pivot so each match has innings 1 and 2 side by side
            inn1 = agg_df[agg_df["inning"] == 1].add_prefix("inn1_").rename(columns={"inn1_match_id": "match_id"})
            inn2 = agg_df[agg_df["inning"] == 2].add_prefix("inn2_").rename(columns={"inn2_match_id": "match_id"})

            merged = matches_df.merge(inn1.drop(columns=["inn1_inning"], errors="ignore"), on="match_id", how="left")
            merged = merged.merge(inn2.drop(columns=["inn2_inning"], errors="ignore"), on="match_id", how="left")

            logger.info(f"Match aggregates computed: {len(merged)} matches")
            return merged

        return matches_df

    def compute_player_stats(self, deliveries_df: pd.DataFrame, matches_df: pd.DataFrame) -> pd.DataFrame:
        """Compute per-player per-season statistics."""
        logger.info("Computing player statistics...")

        # Merge season info
        if "season" in matches_df.columns:
            del_with_season = deliveries_df.merge(
                matches_df[["match_id", "season"]].drop_duplicates(),
                on="match_id",
                how="left",
            )
        else:
            del_with_season = deliveries_df.copy()
            del_with_season["season"] = 2024  # fallback

        # Batting stats
        batting = del_with_season.groupby(["batter", "season"]).agg(
            runs_scored=("batsman_runs", "sum"),
            balls_faced=("batsman_runs", "count"),
            fours=("is_four", "sum") if "is_four" in del_with_season.columns else ("batsman_runs", lambda x: (x == 4).sum()),
            sixes=("is_six", "sum") if "is_six" in del_with_season.columns else ("batsman_runs", lambda x: (x == 6).sum()),
            dismissals=("is_wicket", "sum") if "is_wicket" in del_with_season.columns else ("batsman_runs", lambda x: 0),
        ).reset_index()

        batting["strike_rate"] = np.where(
            batting["balls_faced"] > 0,
            batting["runs_scored"] / batting["balls_faced"] * 100,
            0,
        )
        batting["batting_avg"] = np.where(
            batting["dismissals"] > 0,
            batting["runs_scored"] / batting["dismissals"],
            batting["runs_scored"],
        )
        batting = batting.rename(columns={"batter": "player_name"})

        # Bowling stats
        bowling = del_with_season.groupby(["bowler", "season"]).agg(
            balls_bowled=("bowler", "count"),
            runs_conceded=("total_runs", "sum"),
            wickets=("is_wicket", "sum") if "is_wicket" in del_with_season.columns else ("total_runs", lambda x: 0),
        ).reset_index()

        bowling["economy"] = np.where(
            bowling["balls_bowled"] > 0,
            bowling["runs_conceded"] / (bowling["balls_bowled"] / 6),
            0,
        )
        bowling["bowling_avg"] = np.where(
            bowling["wickets"] > 0,
            bowling["runs_conceded"] / bowling["wickets"],
            999,
        )
        bowling["bowling_sr"] = np.where(
            bowling["wickets"] > 0,
            bowling["balls_bowled"] / bowling["wickets"],
            999,
        )
        bowling = bowling.rename(columns={"bowler": "player_name"})

        # Merge batting and bowling
        player_stats = batting.merge(
            bowling[["player_name", "season", "balls_bowled", "runs_conceded", "wickets", "economy", "bowling_avg", "bowling_sr"]],
            on=["player_name", "season"],
            how="outer",
        )
        player_stats = player_stats.fillna(0)

        logger.info(f"Computed stats for {player_stats['player_name'].nunique()} players")
        return player_stats

    def _normalize_venue(self, venue: str) -> str:
        """Normalize venue names."""
        if pd.isna(venue):
            return "Unknown"

        venue = venue.strip()
        venue_map = {
            "M Chinnaswamy Stadium": "M Chinnaswamy Stadium, Bengaluru",
            "Wankhede Stadium": "Wankhede Stadium, Mumbai",
            "Eden Gardens": "Eden Gardens, Kolkata",
            "MA Chidambaram Stadium": "MA Chidambaram Stadium, Chennai",
            "Feroz Shah Kotla": "Arun Jaitley Stadium, Delhi",
            "Arun Jaitley Stadium": "Arun Jaitley Stadium, Delhi",
            "Rajiv Gandhi International Stadium": "Rajiv Gandhi Intl Stadium, Hyderabad",
        }

        for key, val in venue_map.items():
            if key.lower() in venue.lower():
                return val

        return venue

    def run_full_pipeline(self, matches_df: pd.DataFrame, deliveries_df: pd.DataFrame) -> dict:
        """Run the complete preprocessing pipeline."""
        logger.info("=" * 60)
        logger.info("STARTING FULL PREPROCESSING PIPELINE")
        logger.info("=" * 60)

        # Preprocess
        matches_clean = self.preprocess_matches(matches_df)
        deliveries_clean = self.preprocess_deliveries(deliveries_df)

        # Compute aggregates
        matches_with_agg = self.compute_match_aggregates(matches_clean, deliveries_clean)

        # Compute player stats
        player_stats = self.compute_player_stats(deliveries_clean, matches_clean)

        # Save processed data
        matches_with_agg.to_csv(self.processed_dir / "matches_processed.csv", index=False)
        deliveries_clean.to_csv(self.processed_dir / "deliveries_processed.csv", index=False)
        player_stats.to_csv(self.processed_dir / "player_stats.csv", index=False)

        logger.info("Preprocessing pipeline complete. Files saved.")

        return {
            "matches": matches_with_agg,
            "deliveries": deliveries_clean,
            "player_stats": player_stats,
        }
