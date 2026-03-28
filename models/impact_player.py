"""
Impact Player Analysis for IPL 2026.

The Impact Player rule allows teams to substitute one player between innings.
This module analyzes how impact player substitutions affect match predictions.
"""

import json
from pathlib import Path

import pandas as pd
import numpy as np

from utils.logger import logger
from config.settings import settings


class ImpactPlayerAnalyzer:
    """Analyze impact player substitution effects on match outcome."""

    # Role-based impact scores (how much a substitute of this role type shifts probabilities)
    ROLE_IMPACT = {
        "power_hitter": 0.04,      # Brings in an explosive batsman for death overs
        "spin_bowler": 0.03,       # Brings in a spinner on turning pitch
        "pace_bowler": 0.035,      # Brings in a fast bowler for swing/pace
        "all_rounder": 0.025,      # Flexible impact
        "wk_batsman": 0.02,        # Specialist WK-bat
    }

    # Typical impact player scenarios
    SCENARIOS = {
        "batting_first_low_score": {
            "description": "Team batting first scored low; bring in extra bowler to defend",
            "optimal_sub": "pace_bowler",
            "prob_shift": 0.03,
        },
        "batting_first_high_score": {
            "description": "Team batting first scored high; bring in extra batsman to chase",
            "optimal_sub": "power_hitter",
            "prob_shift": 0.04,
        },
        "chasing_high_target": {
            "description": "Chasing 180+; need extra batting firepower",
            "optimal_sub": "power_hitter",
            "prob_shift": 0.05,
        },
        "spin_friendly_pitch": {
            "description": "Pitch turning; bring in extra spinner",
            "optimal_sub": "spin_bowler",
            "prob_shift": 0.035,
        },
        "dew_factor": {
            "description": "Heavy dew expected; bring in extra batsman for chase",
            "optimal_sub": "power_hitter",
            "prob_shift": 0.03,
        },
    }

    def __init__(self):
        self.squads_path = settings.data_dir / "ipl2026_squads.json"
        self.squads = self._load_squads()

    def _load_squads(self) -> dict:
        """Load squad data with player roles."""
        if self.squads_path.exists():
            return json.loads(self.squads_path.read_text())
        return {}

    def get_impact_candidates(self, team: str) -> list[dict]:
        """Get potential impact player substitutes for a team."""
        team_data = self.squads.get(team, {})
        players = team_data.get("players", [])
        if not players:
            return []

        # Impact player candidates: typically bench players with specialist skills
        candidates = []
        for p in players:
            role = p.get("role", "")
            score = 0
            if "All-rounder" in role:
                score = 0.8  # Most versatile impact
            elif "Bowler" in role:
                score = 0.7
            elif "Batsman" in role and "WK" not in role:
                score = 0.6
            elif "WK" in role:
                score = 0.5

            candidates.append({
                "name": p["name"],
                "role": role,
                "overseas": p.get("overseas", False),
                "impact_score": score,
            })

        return sorted(candidates, key=lambda x: x["impact_score"], reverse=True)

    def estimate_impact_shift(
        self,
        team1: str,
        team2: str,
        venue: str = None,
        weather: dict = None,
        innings_score: int = None,
    ) -> dict:
        """Estimate how impact player usage shifts win probability."""
        shift_team1 = 0.0
        shift_team2 = 0.0
        scenarios_applied = []

        # Analyze squad depth
        t1_candidates = self.get_impact_candidates(team1)
        t2_candidates = self.get_impact_candidates(team2)

        # Team with more impact options has slight advantage
        t1_depth = len([c for c in t1_candidates if c["impact_score"] >= 0.7])
        t2_depth = len([c for c in t2_candidates if c["impact_score"] >= 0.7])

        if t1_depth > t2_depth:
            shift_team1 += 0.01
            scenarios_applied.append(f"{team1} has deeper impact player bench ({t1_depth} options)")
        elif t2_depth > t1_depth:
            shift_team2 += 0.01
            scenarios_applied.append(f"{team2} has deeper impact player bench ({t2_depth} options)")

        # Weather-based impact
        if weather and weather.get("dew_probability", 0) > 0.6:
            # Dew = chasing team benefits, both teams can use impact player to add batsman
            shift_team2 += 0.015  # Chasing team benefits more from impact batsman
            scenarios_applied.append("Dew factor: chasing team can use impact player as extra batsman")

        # Score-based impact (if known)
        if innings_score:
            if innings_score >= 180:
                scenarios_applied.append(f"High target ({innings_score}): impact player as extra batsman crucial")
                shift_team2 += 0.02
            elif innings_score <= 140:
                scenarios_applied.append(f"Low target ({innings_score}): impact player as extra bowler effective")
                shift_team1 += 0.02

        return {
            "team1_shift": round(shift_team1, 4),
            "team2_shift": round(shift_team2, 4),
            "net_shift": round(shift_team1 - shift_team2, 4),
            "scenarios": scenarios_applied,
            "team1_best_impact": t1_candidates[0] if t1_candidates else None,
            "team2_best_impact": t2_candidates[0] if t2_candidates else None,
        }

    def get_team_squad_strength(self, team: str) -> dict:
        """Analyze overall squad composition strength."""
        team_data = self.squads.get(team, {})
        players = team_data.get("players", [])
        if not players:
            return {"batting_depth": 0, "bowling_depth": 0, "all_rounder_count": 0, "overseas_count": 0}

        batting = len([p for p in players if "Batsman" in p.get("role", "") or "WK" in p.get("role", "")])
        bowling = len([p for p in players if "Bowler" in p.get("role", "")])
        ar = len([p for p in players if "All-rounder" in p.get("role", "")])
        overseas = len([p for p in players if p.get("overseas", False)])

        return {
            "captain": team_data.get("captain", "Unknown"),
            "coach": team_data.get("coach", "Unknown"),
            "total_players": len(players),
            "batting_depth": batting,
            "bowling_depth": bowling,
            "all_rounder_count": ar,
            "overseas_count": overseas,
            "strength_score": round((batting * 0.3 + bowling * 0.3 + ar * 0.4) / len(players), 3),
        }
