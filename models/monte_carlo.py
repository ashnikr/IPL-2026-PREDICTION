"""
Monte Carlo Simulation for IPL Match Prediction.

Simulates matches thousands of times to estimate win probabilities.
"""

import numpy as np
import pandas as pd
from collections import defaultdict

from utils.logger import logger
from config.settings import settings


class MonteCarloSimulator:
    """Simulate IPL matches using Monte Carlo methods."""

    def __init__(self, n_simulations: int = None):
        self.n_sims = n_simulations or settings.n_monte_carlo_sims
        self.team_params = {}

    def fit(self, matches: pd.DataFrame, deliveries: pd.DataFrame = None):
        """Estimate team parameters from historical data."""
        logger.info("Fitting Monte Carlo simulation parameters...")

        for team in set(matches["team1"].unique()) | set(matches["team2"].unique()):
            team_matches = matches[
                (matches["team1"] == team) | (matches["team2"] == team)
            ]

            wins = team_matches[team_matches["winner"] == team]
            win_rate = len(wins) / len(team_matches) if len(team_matches) > 0 else 0.5

            # Estimate scoring parameters
            batting_scores = []
            bowling_scores = []

            for _, row in team_matches.iterrows():
                if row["team1"] == team:
                    if pd.notna(row.get("inn1_total_runs")):
                        batting_scores.append(row["inn1_total_runs"])
                    if pd.notna(row.get("inn2_total_runs")):
                        bowling_scores.append(row["inn2_total_runs"])
                else:
                    if pd.notna(row.get("inn2_total_runs")):
                        batting_scores.append(row["inn2_total_runs"])
                    if pd.notna(row.get("inn1_total_runs")):
                        bowling_scores.append(row["inn1_total_runs"])

            self.team_params[team] = {
                "win_rate": win_rate,
                "avg_score": np.mean(batting_scores) if batting_scores else 160,
                "std_score": np.std(batting_scores) if len(batting_scores) > 1 else 25,
                "avg_conceded": np.mean(bowling_scores) if bowling_scores else 155,
                "std_conceded": np.std(bowling_scores) if len(bowling_scores) > 1 else 25,
                "matches": len(team_matches),
            }

        logger.info(f"Monte Carlo params fitted for {len(self.team_params)} teams")

    def simulate_match(
        self,
        team1: str,
        team2: str,
        venue_factor: float = 1.0,
        toss_winner: str = None,
        toss_decision: str = None,
    ) -> dict:
        """Simulate a match n_sims times."""
        p1 = self.team_params.get(team1, {"avg_score": 160, "std_score": 25, "avg_conceded": 155, "std_conceded": 25})
        p2 = self.team_params.get(team2, {"avg_score": 160, "std_score": 25, "avg_conceded": 155, "std_conceded": 25})

        team1_wins = 0
        team2_wins = 0
        no_results = 0
        score_diffs = []

        for _ in range(self.n_sims):
            # Simulate team 1 batting score
            t1_bat = np.random.normal(p1["avg_score"], p1["std_score"]) * venue_factor
            # Adjusted by team 2's bowling
            t2_bowl_factor = p2["avg_conceded"] / 160
            t1_score = max(80, t1_bat * (t2_bowl_factor ** 0.3))

            # Simulate team 2 batting score
            t2_bat = np.random.normal(p2["avg_score"], p2["std_score"]) * venue_factor
            t1_bowl_factor = p1["avg_conceded"] / 160
            t2_score = max(80, t2_bat * (t1_bowl_factor ** 0.3))

            # Toss advantage
            if toss_winner and toss_decision:
                chase_bonus = np.random.normal(3, 2)  # Slight chase advantage
                if toss_winner == team2 and toss_decision == "field":
                    t2_score += chase_bonus
                elif toss_winner == team1 and toss_decision == "field":
                    t1_score += chase_bonus

            if t1_score > t2_score:
                team1_wins += 1
            elif t2_score > t1_score:
                team2_wins += 1
            else:
                no_results += 1

            score_diffs.append(t1_score - t2_score)

        t1_prob = team1_wins / self.n_sims
        t2_prob = team2_wins / self.n_sims

        return {
            "team1": team1,
            "team2": team2,
            "team1_win_prob": round(t1_prob, 4),
            "team2_win_prob": round(t2_prob, 4),
            "draw_prob": round(no_results / self.n_sims, 4),
            "avg_score_diff": round(np.mean(score_diffs), 2),
            "std_score_diff": round(np.std(score_diffs), 2),
            "simulations": self.n_sims,
            "model": "monte_carlo",
        }

    def simulate_tournament(self, schedule: list[dict]) -> pd.DataFrame:
        """Simulate an entire tournament."""
        logger.info(f"Simulating tournament with {len(schedule)} matches...")

        results = []
        for match in schedule:
            sim = self.simulate_match(
                match["team1"], match["team2"],
                venue_factor=match.get("venue_factor", 1.0),
            )
            sim["match_number"] = match.get("match_number", 0)
            results.append(sim)

        return pd.DataFrame(results)
