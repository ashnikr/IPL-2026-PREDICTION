"""
Bayesian Model for IPL Match Prediction.

Uses PyMC for Bayesian inference to estimate team strength parameters
and update win probabilities dynamically.
"""

import pickle
import numpy as np
import pandas as pd
from collections import defaultdict

from utils.logger import logger
from config.settings import settings

try:
    import pymc as pm
    import arviz as az
    HAS_PYMC = True
except ImportError:
    HAS_PYMC = False
    logger.warning("PyMC not available. Bayesian model will use analytical approximation.")


class BayesianPredictor:
    """Bayesian model for team strength estimation and match prediction."""

    def __init__(self):
        self.team_strengths = {}
        self.trace = None
        self.model_path = settings.model_dir / "bayesian_strengths.pkl"

    def fit_analytical(self, matches: pd.DataFrame) -> dict:
        """
        Analytical Bayesian approach using Beta-Binomial conjugate prior.
        Each team's win probability is modeled with Beta(alpha, beta).
        """
        logger.info("Fitting analytical Bayesian model...")

        team_wins = defaultdict(int)
        team_losses = defaultdict(int)

        for _, row in matches.iterrows():
            if pd.isna(row.get("winner")):
                continue
            t1, t2 = row["team1"], row["team2"]
            if row["winner"] == t1:
                team_wins[t1] += 1
                team_losses[t2] += 1
            else:
                team_wins[t2] += 1
                team_losses[t1] += 1

        # Beta prior: alpha=2, beta=2 (mildly informative, centered at 0.5)
        prior_alpha, prior_beta = 2, 2

        self.team_strengths = {}
        for team in set(list(team_wins.keys()) + list(team_losses.keys())):
            alpha = prior_alpha + team_wins[team]
            beta = prior_beta + team_losses[team]
            mean = alpha / (alpha + beta)
            var = (alpha * beta) / ((alpha + beta) ** 2 * (alpha + beta + 1))

            self.team_strengths[team] = {
                "alpha": alpha,
                "beta": beta,
                "mean_strength": round(mean, 4),
                "std": round(np.sqrt(var), 4),
                "wins": team_wins[team],
                "losses": team_losses[team],
                "total": team_wins[team] + team_losses[team],
            }

        # Save
        with open(self.model_path, "wb") as f:
            pickle.dump(self.team_strengths, f)

        logger.info(f"Bayesian model fitted for {len(self.team_strengths)} teams")
        return self.team_strengths

    def fit_pymc(self, matches: pd.DataFrame) -> dict:
        """Full Bayesian inference using PyMC (Bradley-Terry model)."""
        if not HAS_PYMC:
            logger.warning("PyMC not available, falling back to analytical")
            return self.fit_analytical(matches)

        logger.info("Fitting PyMC Bayesian model (Bradley-Terry)...")

        # Prepare data
        valid = matches.dropna(subset=["winner"]).copy()
        teams = sorted(set(valid["team1"].unique()) | set(valid["team2"].unique()))
        team_idx = {t: i for i, t in enumerate(teams)}
        n_teams = len(teams)

        team1_idx = valid["team1"].map(team_idx).values
        team2_idx = valid["team2"].map(team_idx).values
        team1_won = (valid["winner"] == valid["team1"]).astype(int).values

        with pm.Model() as bt_model:
            # Team strength parameters (sum-to-zero constraint)
            raw_strength = pm.Normal("raw_strength", mu=0, sigma=1, shape=n_teams - 1)
            strength = pm.Deterministic(
                "strength",
                pm.math.concatenate([raw_strength, [-pm.math.sum(raw_strength)]]),
            )

            # Home advantage
            home_adv = pm.Normal("home_advantage", mu=0, sigma=0.5)

            # Win probability via logistic function
            logit_p = strength[team1_idx] - strength[team2_idx] + home_adv
            p = pm.Deterministic("p", pm.math.sigmoid(logit_p))

            # Likelihood
            outcome = pm.Bernoulli("outcome", p=p, observed=team1_won)

            # Sample
            self.trace = pm.sample(
                1000, tune=500, cores=1, random_seed=settings.random_state,
                progressbar=True, return_inferencedata=True,
            )

        # Extract posterior means
        posterior_strength = self.trace.posterior["strength"].mean(dim=["chain", "draw"]).values
        self.team_strengths = {}
        for team, idx in team_idx.items():
            s = posterior_strength[idx]
            self.team_strengths[team] = {
                "mean_strength": round(float(s), 4),
                "logit_strength": round(float(s), 4),
            }

        with open(self.model_path, "wb") as f:
            pickle.dump(self.team_strengths, f)

        logger.info(f"PyMC model fitted for {n_teams} teams")
        return self.team_strengths

    def predict_match(self, team1: str, team2: str) -> dict:
        """Predict match outcome using Bayesian team strengths."""
        if not self.team_strengths:
            self.load()

        s1 = self.team_strengths.get(team1, {})
        s2 = self.team_strengths.get(team2, {})

        if "logit_strength" in s1 and "logit_strength" in s2:
            # Bradley-Terry prediction
            logit_diff = s1["logit_strength"] - s2["logit_strength"]
            p1 = 1 / (1 + np.exp(-logit_diff))
        elif "alpha" in s1 and "alpha" in s2:
            # Beta-Binomial prediction
            m1 = s1["mean_strength"]
            m2 = s2["mean_strength"]
            # Normalize
            p1 = m1 / (m1 + m2) if (m1 + m2) > 0 else 0.5
        else:
            p1 = 0.5

        return {
            "team1": team1,
            "team2": team2,
            "team1_win_prob": round(float(p1), 4),
            "team2_win_prob": round(float(1 - p1), 4),
            "team1_strength": s1.get("mean_strength", 0.5),
            "team2_strength": s2.get("mean_strength", 0.5),
            "model": "bayesian",
        }

    def update_with_result(self, team1: str, team2: str, winner: str):
        """Update team strengths with a new match result (online learning)."""
        if not self.team_strengths:
            self.load()

        for team in [team1, team2]:
            if team not in self.team_strengths:
                self.team_strengths[team] = {"alpha": 2, "beta": 2, "mean_strength": 0.5}

        won = winner == team1
        # Update Beta parameters
        if "alpha" in self.team_strengths[team1]:
            if won:
                self.team_strengths[team1]["alpha"] += 1
                self.team_strengths[team2]["beta"] += 1
            else:
                self.team_strengths[team1]["beta"] += 1
                self.team_strengths[team2]["alpha"] += 1

            # Recalculate means
            for t in [team1, team2]:
                a = self.team_strengths[t]["alpha"]
                b = self.team_strengths[t]["beta"]
                self.team_strengths[t]["mean_strength"] = round(a / (a + b), 4)

        # Save updated strengths
        with open(self.model_path, "wb") as f:
            pickle.dump(self.team_strengths, f)

    def load(self):
        """Load saved team strengths."""
        try:
            with open(self.model_path, "rb") as f:
                self.team_strengths = pickle.load(f)
            logger.info(f"Loaded Bayesian strengths for {len(self.team_strengths)} teams")
        except FileNotFoundError:
            logger.warning("No saved Bayesian model found")
            self.team_strengths = {}
