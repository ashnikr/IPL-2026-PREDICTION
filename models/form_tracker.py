"""
Team & Player Form Momentum Tracker.

Tracks recent performance trends, momentum shifts, and form scores
to provide real-time form assessment for prediction adjustments.
"""

import json
from datetime import datetime, date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from utils.logger import logger
from config.settings import settings


class FormTracker:
    """Track team and player form with momentum scoring."""

    # IPL historical form indicators (based on last 3 seasons)
    TEAM_BASE_RATINGS = {
        "Kolkata Knight Riders": 0.72,  # Won IPL 2024
        "Chennai Super Kings": 0.68,    # Won IPL 2023, consistent
        "Rajasthan Royals": 0.65,       # Strong recent seasons
        "Sunrisers Hyderabad": 0.67,    # Finalist 2024
        "Mumbai Indians": 0.60,         # Rebuilding
        "Royal Challengers Bengaluru": 0.62,  # New captain era
        "Delhi Capitals": 0.58,         # Rebuilding
        "Gujarat Titans": 0.63,         # Won 2022, decent 2023
        "Lucknow Super Giants": 0.61,   # Consistent mid-table
        "Punjab Kings": 0.55,           # Historically inconsistent
    }

    # Player form ratings (key players, scale 0-100)
    PLAYER_FORM = {
        # CSK
        "Ruturaj Gaikwad": {"batting": 82, "recent_form": "good", "role": "opener"},
        "Sanju Samson": {"batting": 78, "recent_form": "excellent", "role": "keeper-bat"},
        "Ravindra Jadeja": {"batting": 70, "bowling": 75, "recent_form": "good", "role": "allrounder"},
        # MI
        "Jasprit Bumrah": {"bowling": 95, "recent_form": "excellent", "role": "pace"},
        "Hardik Pandya": {"batting": 72, "bowling": 65, "recent_form": "moderate", "role": "allrounder"},
        "Suryakumar Yadav": {"batting": 85, "recent_form": "good", "role": "middle-order"},
        "Trent Boult": {"bowling": 82, "recent_form": "good", "role": "pace"},
        "Rohit Sharma": {"batting": 80, "recent_form": "moderate", "role": "opener"},
        # RCB
        "Virat Kohli": {"batting": 88, "recent_form": "good", "role": "top-order"},
        "Rajat Patidar": {"batting": 75, "recent_form": "good", "role": "middle-order"},
        "Phil Salt": {"batting": 83, "recent_form": "excellent", "role": "opener"},
        "Josh Hazlewood": {"bowling": 84, "recent_form": "good", "role": "pace"},
        # KKR
        "Ajinkya Rahane": {"batting": 68, "recent_form": "moderate", "role": "opener"},
        "Sunil Narine": {"batting": 72, "bowling": 80, "recent_form": "good", "role": "allrounder"},
        "Andre Russell": {"batting": 80, "bowling": 65, "recent_form": "moderate", "role": "allrounder"},
        "Rinku Singh": {"batting": 76, "recent_form": "good", "role": "finisher"},
        "Varun Chakravarthy": {"bowling": 82, "recent_form": "excellent", "role": "spin"},
        # SRH
        "Pat Cummins": {"bowling": 85, "batting": 55, "recent_form": "good", "role": "pace"},
        "Travis Head": {"batting": 86, "recent_form": "excellent", "role": "opener"},
        "Heinrich Klaasen": {"batting": 84, "recent_form": "excellent", "role": "middle-order"},
        "Abhishek Sharma": {"batting": 74, "recent_form": "good", "role": "opener"},
        "Ishan Kishan": {"batting": 72, "recent_form": "moderate", "role": "keeper-bat"},
        # RR
        "Riyan Parag": {"batting": 73, "recent_form": "good", "role": "middle-order"},
        "Sanju Samson (RR)": {"batting": 78, "recent_form": "good", "role": "keeper-bat"},
        "Jofra Archer": {"bowling": 88, "recent_form": "moderate", "role": "pace"},
        "Yuzvendra Chahal": {"bowling": 80, "recent_form": "good", "role": "spin"},
        "Yashasvi Jaiswal": {"batting": 85, "recent_form": "excellent", "role": "opener"},
        # DC
        "KL Rahul": {"batting": 80, "recent_form": "good", "role": "opener"},
        "Mitchell Starc": {"bowling": 87, "recent_form": "good", "role": "pace"},
        "David Miller": {"batting": 75, "recent_form": "moderate", "role": "finisher"},
        "Axar Patel": {"batting": 65, "bowling": 76, "recent_form": "good", "role": "allrounder"},
        # PBKS
        "Shreyas Iyer": {"batting": 78, "recent_form": "good", "role": "middle-order"},
        "Marcus Stoinis": {"batting": 74, "bowling": 62, "recent_form": "moderate", "role": "allrounder"},
        "Marco Jansen": {"bowling": 80, "batting": 55, "recent_form": "good", "role": "pace"},
        "Lockie Ferguson": {"bowling": 83, "recent_form": "good", "role": "pace"},
        "Yuzvendra Chahal": {"bowling": 80, "recent_form": "good", "role": "spin"},
        # LSG
        "Rishabh Pant": {"batting": 82, "recent_form": "excellent", "role": "keeper-bat"},
        "Mitchell Marsh": {"batting": 73, "bowling": 60, "recent_form": "moderate", "role": "allrounder"},
        "Mohammed Shami": {"bowling": 85, "recent_form": "moderate", "role": "pace"},
        "Nicholas Pooran": {"batting": 77, "recent_form": "good", "role": "middle-order"},
        # GT
        "Jos Buttler": {"batting": 84, "recent_form": "good", "role": "opener"},
        "Shubman Gill": {"batting": 83, "recent_form": "excellent", "role": "opener"},
        "Kagiso Rabada": {"bowling": 86, "recent_form": "good", "role": "pace"},
        "Rashid Khan": {"bowling": 88, "recent_form": "excellent", "role": "spin"},
    }

    def __init__(self):
        self.results_file = settings.data_dir / "match_results.json"
        self.form_file = settings.data_dir / "team_form.json"
        self._match_results = self._load_results()

    def _load_results(self) -> list[dict]:
        """Load completed match results."""
        if self.results_file.exists():
            return json.loads(self.results_file.read_text())
        return []

    def record_result(self, team1: str, team2: str, winner: str,
                      margin: str = "", motm: str = ""):
        """Record a completed match result."""
        result = {
            "date": str(date.today()),
            "team1": team1,
            "team2": team2,
            "winner": winner,
            "loser": team2 if winner == team1 else team1,
            "margin": margin,
            "motm": motm,
        }
        self._match_results.append(result)
        self.results_file.write_text(json.dumps(self._match_results, indent=2))
        logger.info(f"Recorded result: {winner} won ({team1} vs {team2})")

    def get_team_form(self, team: str, last_n: int = 5) -> dict:
        """Get a team's recent form analysis."""
        # Get results involving this team
        team_results = [
            r for r in self._match_results
            if r["team1"] == team or r["team2"] == team
        ][-last_n:]

        if not team_results:
            # Use base rating for season start
            base = self.TEAM_BASE_RATINGS.get(team, 0.55)
            return {
                "team": team,
                "matches_played": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": base,
                "form_string": "N/A (Season Start)",
                "momentum": "neutral",
                "momentum_score": 0.0,
                "form_rating": base,
                "streak": "No matches yet",
                "base_rating": base,
            }

        wins = sum(1 for r in team_results if r["winner"] == team)
        losses = len(team_results) - wins
        win_rate = wins / len(team_results)

        # Form string (W/L sequence)
        form_chars = []
        for r in team_results:
            form_chars.append("W" if r["winner"] == team else "L")
        form_string = "".join(form_chars)

        # Momentum: weighted recent results (more recent = more weight)
        weights = np.array([0.1, 0.15, 0.2, 0.25, 0.3])[:len(team_results)]
        weights = weights / weights.sum()
        results_binary = np.array([1 if r["winner"] == team else 0 for r in team_results])
        momentum_score = float(np.dot(results_binary, weights))

        # Streak
        streak_count = 0
        streak_type = "W" if team_results[-1]["winner"] == team else "L"
        for r in reversed(team_results):
            if (r["winner"] == team and streak_type == "W") or \
               (r["winner"] != team and streak_type == "L"):
                streak_count += 1
            else:
                break
        streak = f"{streak_count}{streak_type}"

        # Momentum label
        if momentum_score > 0.65:
            momentum = "hot"
        elif momentum_score > 0.45:
            momentum = "good"
        elif momentum_score > 0.3:
            momentum = "average"
        else:
            momentum = "cold"

        # Overall form rating (blend base + recent)
        base = self.TEAM_BASE_RATINGS.get(team, 0.55)
        if len(team_results) >= 3:
            form_rating = 0.4 * base + 0.6 * win_rate
        else:
            form_rating = 0.7 * base + 0.3 * win_rate

        return {
            "team": team,
            "matches_played": len(team_results),
            "wins": wins,
            "losses": losses,
            "win_rate": round(win_rate, 3),
            "form_string": form_string,
            "momentum": momentum,
            "momentum_score": round(momentum_score, 3),
            "form_rating": round(form_rating, 3),
            "streak": streak,
            "base_rating": base,
        }

    def get_player_form(self, player_name: str) -> dict:
        """Get a player's current form assessment."""
        form = self.PLAYER_FORM.get(player_name)
        if not form:
            return {"name": player_name, "form": "unknown", "impact_score": 50}

        # Calculate impact score
        bat = form.get("batting", 0)
        bowl = form.get("bowling", 0)
        impact = max(bat, bowl)

        # Adjust for recent form
        form_multiplier = {
            "excellent": 1.15,
            "good": 1.0,
            "moderate": 0.85,
            "poor": 0.7,
        }.get(form.get("recent_form", "moderate"), 0.85)

        return {
            "name": player_name,
            "batting_rating": bat,
            "bowling_rating": bowl,
            "recent_form": form.get("recent_form", "unknown"),
            "role": form.get("role", "unknown"),
            "impact_score": round(impact * form_multiplier, 1),
            "form_multiplier": form_multiplier,
        }

    def get_key_players_form(self, team: str) -> list[dict]:
        """Get form data for key players of a team."""
        key_players = [
            name for name, data in self.PLAYER_FORM.items()
            if data.get("batting", 0) > 70 or data.get("bowling", 0) > 75
        ]

        # Filter by team context (this is approximate - checks if player
        # is associated with team based on squad data)
        from scrapers.live_data_scraper import LiveDataScraper
        try:
            scraper = LiveDataScraper()
            squads = scraper.get_team_squads()
            team_squad = squads.get(team, {}).get("players", [])
            team_player_names = {p["name"] for p in team_squad}

            team_key = [
                self.get_player_form(name)
                for name in key_players
                if name in team_player_names
            ]

            if not team_key:
                # Fallback: return all known key players
                team_key = [self.get_player_form(name) for name in team_player_names
                           if name in self.PLAYER_FORM]

            return sorted(team_key, key=lambda x: x["impact_score"], reverse=True)[:6]
        except Exception:
            return []

    def get_matchup_form(self, team1: str, team2: str) -> dict:
        """Get comparative form analysis for a matchup."""
        t1_form = self.get_team_form(team1)
        t2_form = self.get_team_form(team2)

        t1_players = self.get_key_players_form(team1)
        t2_players = self.get_key_players_form(team2)

        # Form-based prediction adjustment
        form_diff = t1_form["form_rating"] - t2_form["form_rating"]
        adjustment = round(max(-0.05, min(0.05, form_diff * 0.15)), 4)

        # Momentum comparison
        if t1_form["momentum"] == "hot" and t2_form["momentum"] in ("cold", "average"):
            momentum_edge = team1
        elif t2_form["momentum"] == "hot" and t1_form["momentum"] in ("cold", "average"):
            momentum_edge = team2
        else:
            momentum_edge = "even"

        return {
            "team1_form": t1_form,
            "team2_form": t2_form,
            "team1_key_players": t1_players,
            "team2_key_players": t2_players,
            "form_advantage": team1 if form_diff > 0.05 else (team2 if form_diff < -0.05 else "even"),
            "momentum_edge": momentum_edge,
            "prediction_adjustment": adjustment,
            "summary": self._generate_form_summary(t1_form, t2_form, momentum_edge),
        }

    def get_head_to_head(self, team1: str, team2: str) -> dict:
        """Get head-to-head record from this season."""
        h2h = [
            r for r in self._match_results
            if (r["team1"] == team1 and r["team2"] == team2) or
               (r["team1"] == team2 and r["team2"] == team1)
        ]

        t1_wins = sum(1 for r in h2h if r["winner"] == team1)
        t2_wins = sum(1 for r in h2h if r["winner"] == team2)

        return {
            "total_matches": len(h2h),
            "team1_wins": t1_wins,
            "team2_wins": t2_wins,
            "last_winner": h2h[-1]["winner"] if h2h else None,
            "results": h2h,
        }

    def _generate_form_summary(self, t1: dict, t2: dict, momentum: str) -> str:
        """Generate a human-readable form summary."""
        parts = []

        if t1["matches_played"] == 0 and t2["matches_played"] == 0:
            parts.append("Season opener - no current form data. Using historical base ratings.")
            if t1["base_rating"] > t2["base_rating"] + 0.05:
                parts.append(f"{t1['team']} has a stronger historical pedigree ({t1['base_rating']:.0%} vs {t2['base_rating']:.0%}).")
            elif t2["base_rating"] > t1["base_rating"] + 0.05:
                parts.append(f"{t2['team']} has a stronger historical pedigree ({t2['base_rating']:.0%} vs {t1['base_rating']:.0%}).")
            else:
                parts.append("Both teams are evenly matched historically.")
        else:
            if t1["matches_played"] > 0:
                parts.append(f"{t1['team']}: {t1['form_string']} (streak: {t1['streak']}, momentum: {t1['momentum']})")
            if t2["matches_played"] > 0:
                parts.append(f"{t2['team']}: {t2['form_string']} (streak: {t2['streak']}, momentum: {t2['momentum']})")

            if momentum != "even":
                parts.append(f"{momentum} has the momentum advantage.")

        return " | ".join(parts)
