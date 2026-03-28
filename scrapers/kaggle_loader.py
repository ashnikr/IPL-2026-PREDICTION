"""
Kaggle IPL Dataset Loader.

Downloads and loads IPL datasets from Kaggle.
Primary source for historical match and ball-by-ball data (2008-2024).
"""

import os
import zipfile
import subprocess
from pathlib import Path

import pandas as pd
from utils.logger import logger
from config.settings import settings


class KaggleDataLoader:
    """Load IPL data from Kaggle datasets."""

    KAGGLE_DATASETS = [
        "patrickb1912/ipl-complete-dataset-20082020",
        "ramjidoolla/ipl-data-set",
    ]

    # Real IPL data URLs (2008-2024, ~1094 matches)
    REAL_DATA_URLS = [
        {
            "matches": "https://raw.githubusercontent.com/avinashyadav16/ipl-analytics/main/matches_2008-2024.csv",
            "deliveries": "https://raw.githubusercontent.com/avinashyadav16/ipl-analytics/main/deliveries_2008-2024.csv",
        },
        {
            "matches": "https://raw.githubusercontent.com/rpkar/ipl-data-analysis/master/ipl/matches.csv",
            "deliveries": "https://raw.githubusercontent.com/rpkar/ipl-data-analysis/master/ipl/deliveries.csv",
        },
    ]

    # Legacy fallback
    FALLBACK_MATCHES_URL = "https://raw.githubusercontent.com/dsrscientist/dataset1/master/matches.csv"
    FALLBACK_DELIVERIES_URL = "https://raw.githubusercontent.com/dsrscientist/dataset1/master/deliveries.csv"

    def __init__(self):
        self.raw_dir = settings.raw_data_dir
        self.matches_path = self.raw_dir / "matches.csv"
        self.deliveries_path = self.raw_dir / "deliveries.csv"

    def download_from_kaggle(self, dataset: str = None) -> bool:
        """Download dataset using kaggle CLI."""
        dataset = dataset or self.KAGGLE_DATASETS[0]
        try:
            logger.info(f"Downloading Kaggle dataset: {dataset}")
            subprocess.run(
                [
                    "kaggle", "datasets", "download",
                    "-d", dataset,
                    "-p", str(self.raw_dir),
                    "--unzip",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info("Kaggle download successful")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.warning(f"Kaggle CLI failed: {e}. Trying fallback...")
            return False

    def download_real_data(self) -> bool:
        """Download real IPL data from GitHub mirrors."""
        import requests

        for source in self.REAL_DATA_URLS:
            try:
                logger.info(f"Downloading real IPL data from: {source['matches']}")
                matches_resp = requests.get(source["matches"], timeout=120)
                matches_resp.raise_for_status()

                logger.info(f"Downloading deliveries from: {source['deliveries']}")
                deliveries_resp = requests.get(source["deliveries"], timeout=120)
                deliveries_resp.raise_for_status()

                self.matches_path.write_text(matches_resp.text, encoding="utf-8")
                self.deliveries_path.write_text(deliveries_resp.text, encoding="utf-8")

                # Verify data
                matches = pd.read_csv(self.matches_path)
                deliveries = pd.read_csv(self.deliveries_path)
                logger.info(f"Real data downloaded: {len(matches)} matches, {len(deliveries)} deliveries")
                return True
            except Exception as e:
                logger.warning(f"Source failed: {e}. Trying next...")
                continue

        return False

    def download_fallback(self) -> bool:
        """Download from public GitHub mirrors as legacy fallback."""
        import requests

        try:
            for url, path in [
                (self.FALLBACK_MATCHES_URL, self.matches_path),
                (self.FALLBACK_DELIVERIES_URL, self.deliveries_path),
            ]:
                logger.info(f"Downloading from fallback: {url}")
                resp = requests.get(url, timeout=60)
                resp.raise_for_status()
                path.write_text(resp.text, encoding="utf-8")

            logger.info("Fallback download successful")
            return True
        except Exception as e:
            logger.error(f"Fallback download failed: {e}")
            return False

    def generate_synthetic_data(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Generate realistic synthetic IPL data for development/testing."""
        import numpy as np

        logger.info("Generating synthetic IPL data for development...")
        np.random.seed(settings.random_state)

        teams = settings.current_teams
        venues = [
            "Wankhede Stadium, Mumbai",
            "M Chinnaswamy Stadium, Bengaluru",
            "Eden Gardens, Kolkata",
            "MA Chidambaram Stadium, Chennai",
            "Arun Jaitley Stadium, Delhi",
            "Rajiv Gandhi Intl Stadium, Hyderabad",
            "Sawai Mansingh Stadium, Jaipur",
            "Punjab Cricket Association Stadium, Mohali",
            "Narendra Modi Stadium, Ahmedabad",
            "Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium, Lucknow",
        ]
        cities = [
            "Mumbai", "Bengaluru", "Kolkata", "Chennai", "Delhi",
            "Hyderabad", "Jaipur", "Mohali", "Ahmedabad", "Lucknow",
        ]

        batters = [
            "V Kohli", "R Sharma", "S Dhawan", "KL Rahul", "D Warner",
            "AB de Villiers", "MS Dhoni", "S Iyer", "R Pant", "H Pandya",
            "J Buttler", "F du Plessis", "S Gill", "RV Uthappa", "Q de Kock",
            "S Yadav", "R Jadeja", "A Russell", "K Pollard", "M Agarwal",
            "Y Jaiswal", "T Head", "P Shaw", "SA Yadav", "R Gaikwad",
        ]
        bowlers = [
            "J Bumrah", "R Ashwin", "Y Chahal", "B Kumar", "T Boult",
            "K Rabada", "R Jadeja", "A Patel", "M Shami", "S Thakur",
            "P Krishna", "D Chahar", "Rashid Khan", "W Sundar", "A Nortje",
            "U Malik", "M Siraj", "A Zampa", "S Curran", "P Chawla",
        ]

        all_players = list(set(batters + bowlers))
        matches_data = []
        deliveries_data = []
        match_id = 1

        for season in range(2008, 2027):
            season_teams = list(np.random.choice(teams, size=min(len(teams), 8 if season < 2022 else 10), replace=False))
            n_matches = np.random.randint(56, 76)

            for _ in range(n_matches):
                t1, t2 = np.random.choice(season_teams, size=2, replace=False)
                venue_idx = np.random.randint(0, len(venues))
                toss_winner = np.random.choice([t1, t2])
                toss_decision = np.random.choice(["bat", "field"])

                # Simulate win probability based on simple factors
                team_strength = {t: np.random.uniform(0.3, 0.7) for t in season_teams}
                p1 = team_strength.get(t1, 0.5)
                p2 = team_strength.get(t2, 0.5)
                toss_bonus = 0.05 if toss_winner == t1 else -0.05
                win_prob = p1 / (p1 + p2) + toss_bonus

                winner = t1 if np.random.random() < win_prob else t2
                result = np.random.choice(["runs", "wickets"])
                margin = (
                    np.random.randint(1, 120) if result == "runs"
                    else np.random.randint(1, 10)
                )
                pom = np.random.choice(all_players)
                match_date = f"{season}-{np.random.randint(3,6):02d}-{np.random.randint(1,29):02d}"

                matches_data.append({
                    "match_id": match_id,
                    "season": season,
                    "date": match_date,
                    "venue": venues[venue_idx],
                    "city": cities[venue_idx],
                    "team1": t1,
                    "team2": t2,
                    "toss_winner": toss_winner,
                    "toss_decision": toss_decision,
                    "winner": winner,
                    "result": result,
                    "result_margin": margin,
                    "player_of_match": pom,
                    "umpire1": f"Umpire_{np.random.randint(1,20)}",
                    "umpire2": f"Umpire_{np.random.randint(1,20)}",
                    "match_type": "League",
                    "dl_applied": 0,
                })

                # Generate ball-by-ball for this match
                for inning in [1, 2]:
                    batting_team = t1 if inning == 1 else t2
                    team_batters = list(np.random.choice(batters, size=11, replace=False))
                    team_bowlers = list(np.random.choice(bowlers, size=6, replace=False))
                    wickets = 0
                    batter_idx = 0

                    for over in range(20):
                        bowler = team_bowlers[over % len(team_bowlers)]
                        for ball in range(1, 7):
                            if wickets >= 10:
                                break

                            batter = team_batters[batter_idx % len(team_batters)]
                            non_striker = team_batters[(batter_idx + 1) % len(team_batters)]

                            # Simulate ball outcome
                            rand = np.random.random()
                            if rand < 0.02:  # Wicket
                                runs = 0
                                is_wicket = True
                                dismissal = np.random.choice([
                                    "caught", "bowled", "lbw", "run out",
                                    "stumped", "caught and bowled",
                                ])
                                wickets += 1
                                batter_idx += 1
                            elif rand < 0.05:  # Extra
                                runs = np.random.choice([1, 2, 4, 5])
                                is_wicket = False
                                dismissal = None
                            elif rand < 0.20:  # Boundary
                                runs = np.random.choice([4, 6], p=[0.65, 0.35])
                                is_wicket = False
                                dismissal = None
                            else:
                                runs = np.random.choice([0, 1, 2, 3], p=[0.35, 0.40, 0.20, 0.05])
                                is_wicket = False
                                dismissal = None

                            extra = np.random.choice([0, 1], p=[0.95, 0.05])

                            deliveries_data.append({
                                "match_id": match_id,
                                "inning": inning,
                                "over": over,
                                "ball": ball,
                                "batter": batter,
                                "bowler": bowler,
                                "non_striker": non_striker,
                                "batsman_runs": runs,
                                "extra_runs": extra,
                                "total_runs": runs + extra,
                                "extras_type": "wides" if extra > 0 else None,
                                "is_wicket": is_wicket,
                                "dismissal_kind": dismissal,
                                "player_dismissed": batter if is_wicket else None,
                                "fielder": np.random.choice(team_bowlers) if is_wicket and dismissal == "caught" else None,
                            })

                match_id += 1

        matches_df = pd.DataFrame(matches_data)
        deliveries_df = pd.DataFrame(deliveries_data)

        # Save to CSV
        matches_df.to_csv(self.matches_path, index=False)
        deliveries_df.to_csv(self.deliveries_path, index=False)

        logger.info(f"Generated {len(matches_df)} matches and {len(deliveries_df)} deliveries")
        return matches_df, deliveries_df

    def load_data(self, force_download: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Load match and delivery data. Download if not present."""

        if not force_download and self.matches_path.exists() and self.deliveries_path.exists():
            matches = pd.read_csv(self.matches_path)
            # Check if it's real data (real data has 1000+ matches for 2008-2024)
            if len(matches) > 500:
                deliveries = pd.read_csv(self.deliveries_path)
                logger.info(f"Loaded existing real data: {len(matches)} matches, {len(deliveries)} deliveries")
                return matches, deliveries
            else:
                logger.info("Existing data looks synthetic. Re-downloading real data...")

        # Priority 1: Download real data from GitHub
        success = self.download_real_data()

        # Priority 2: Kaggle CLI
        if not success:
            success = self.download_from_kaggle()

        # Priority 3: Legacy fallback
        if not success:
            success = self.download_fallback()

        if success and self.matches_path.exists():
            matches = pd.read_csv(self.matches_path)
            deliveries = pd.read_csv(self.deliveries_path)
            logger.info(f"Loaded {len(matches)} matches, {len(deliveries)} deliveries")
            return matches, deliveries

        # Last resort: synthetic data
        logger.warning("All download sources failed. Using synthetic data.")
        return self.generate_synthetic_data()

    def load_to_database(self, engine=None):
        """Load data into the database."""
        from models.database import create_tables, get_engine, Match, Delivery, get_session

        if engine is None:
            engine = get_engine()
        create_tables(engine)
        session = get_session(engine)

        matches_df, deliveries_df = self.load_data()

        # Check if data already loaded
        existing = session.query(Match).count()
        if existing > 0:
            logger.info(f"Database already has {existing} matches. Skipping bulk load.")
            session.close()
            return matches_df, deliveries_df

        logger.info("Loading data into database...")

        # Bulk insert matches
        matches_df.to_sql("matches", engine, if_exists="append", index=False, method="multi")
        logger.info(f"Loaded {len(matches_df)} matches into database")

        # Bulk insert deliveries in chunks
        chunk_size = 50000
        for i in range(0, len(deliveries_df), chunk_size):
            chunk = deliveries_df.iloc[i:i + chunk_size]
            chunk.to_sql("deliveries", engine, if_exists="append", index=False, method="multi")
            logger.info(f"Loaded deliveries chunk {i // chunk_size + 1}")

        session.close()
        logger.info("Database loading complete")
        return matches_df, deliveries_df
