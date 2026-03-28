"""
Toss Decision Predictor.

Predicts the likely toss decision (bat/field) based on:
- Venue history (how often teams choose to bat/field)
- Weather conditions (dew, rain)
- Time of match (day/night, evening matches favor chasing due to dew)
- Team preference patterns
"""

import numpy as np
import pandas as pd

from utils.logger import logger
from config.settings import settings


class TossPredictor:
    """Predict toss decision and its impact."""

    # Historical team toss preferences (approximate from 2020-2024 data)
    TEAM_FIELD_PREFERENCE = {
        "Chennai Super Kings": 0.55,     # Slight field preference under Dhoni
        "Mumbai Indians": 0.60,          # MI loves chasing
        "Royal Challengers Bengaluru": 0.65,  # Strong chase preference (Chinnaswamy dew)
        "Kolkata Knight Riders": 0.55,
        "Sunrisers Hyderabad": 0.50,     # Balanced
        "Rajasthan Royals": 0.55,
        "Delhi Capitals": 0.60,
        "Punjab Kings": 0.50,
        "Lucknow Super Giants": 0.55,
        "Gujarat Titans": 0.50,          # GT often bats first
    }

    # Venue toss decision patterns (field first %)
    VENUE_FIELD_PCT = {
        "MA Chidambaram Stadium": 0.45,      # Chennai: batting first works (slow pitch)
        "Wankhede Stadium": 0.65,            # Mumbai: dew, chase
        "M Chinnaswamy Stadium": 0.70,       # Bengaluru: heavy dew, always chase
        "Eden Gardens": 0.60,                # Kolkata: dew factor
        "Rajiv Gandhi Intl Stadium": 0.55,   # Hyderabad: balanced
        "Sawai Mansingh Stadium": 0.50,      # Jaipur: balanced
        "Arun Jaitley Stadium": 0.60,        # Delhi: dew in evenings
        "PCA Stadium": 0.55,                 # Mohali: slight dew
        "BRSABV Ekana Stadium": 0.55,        # Lucknow: balanced
        "Narendra Modi Stadium": 0.50,       # Ahmedabad: balanced (huge ground)
    }

    def __init__(self):
        self._matches_df = None
        self._load_historical_data()

    def _load_historical_data(self):
        """Load historical match data for toss analysis."""
        try:
            path = settings.processed_data_dir / "matches_processed.csv"
            if path.exists():
                self._matches_df = pd.read_csv(path)
        except Exception:
            pass

    def predict_toss_decision(
        self,
        team1: str,
        team2: str,
        venue: str = None,
        match_time: str = None,
        weather: dict = None,
    ) -> dict:
        """Predict what the toss winner will likely choose."""

        # Base: venue historical preference
        venue_field_pct = 0.55  # Default slight preference for fielding
        for v_name, pct in self.VENUE_FIELD_PCT.items():
            if venue and v_name.lower() in venue.lower():
                venue_field_pct = pct
                break

        # Team preferences
        t1_field_pref = self.TEAM_FIELD_PREFERENCE.get(team1, 0.55)
        t2_field_pref = self.TEAM_FIELD_PREFERENCE.get(team2, 0.55)
        avg_team_pref = (t1_field_pref + t2_field_pref) / 2

        # Time of match effect
        time_factor = 0.0
        if match_time:
            hour = int(match_time.split(":")[0])
            if hour >= 19:  # Evening match (7:30 PM)
                time_factor = 0.05  # More dew = more chasing
            elif hour >= 15:  # Afternoon (3:30 PM)
                time_factor = -0.03  # Less dew in afternoon

        # Weather effect
        weather_factor = 0.0
        if weather:
            dew = weather.get("dew_probability", 0)
            rain = weather.get("rain_probability", 0)
            weather_factor += dew * 0.1   # Dew -> chase
            weather_factor -= rain * 0.15  # Rain -> bat first

        # Combined field probability
        field_prob = (
            venue_field_pct * 0.4 +
            avg_team_pref * 0.3 +
            0.55 * 0.3  # Base rate
        ) + time_factor + weather_factor

        field_prob = np.clip(field_prob, 0.2, 0.85)

        # Historical venue data
        venue_history = {}
        if self._matches_df is not None and venue:
            vm = self._matches_df[
                self._matches_df["venue"].str.contains(str(venue)[:20], case=False, na=False)
            ]
            if not vm.empty and "toss_decision" in vm.columns:
                field_count = len(vm[vm["toss_decision"] == "field"])
                total = len(vm[vm["toss_decision"].notna()])
                if total > 5:
                    venue_history = {
                        "total_matches": total,
                        "field_first_pct": round(field_count / total, 3),
                        "bat_first_pct": round(1 - field_count / total, 3),
                    }
                    # Weight real data more
                    field_prob = field_prob * 0.5 + (field_count / total) * 0.5

        predicted_decision = "field" if field_prob > 0.5 else "bat"
        confidence = abs(field_prob - 0.5) * 2

        factors = []
        if venue_field_pct > 0.6:
            factors.append(f"Venue historically favors chasing ({venue_field_pct*100:.0f}% field first)")
        elif venue_field_pct < 0.45:
            factors.append(f"Venue historically favors batting first ({(1-venue_field_pct)*100:.0f}% bat first)")

        if weather and weather.get("dew_probability", 0) > 0.5:
            factors.append(f"Dew factor ({weather['dew_probability']*100:.0f}%) favors chasing")

        if weather and weather.get("rain_probability", 0) > 0.3:
            factors.append(f"Rain risk ({weather['rain_probability']*100:.0f}%) favors batting first")

        if match_time and int(match_time.split(":")[0]) >= 19:
            factors.append("Evening match: dew likely in second innings")

        # Toss win probability impact
        toss_impact = self._calculate_toss_impact(venue, predicted_decision)

        return {
            "predicted_decision": predicted_decision,
            "field_probability": round(float(field_prob), 3),
            "bat_probability": round(float(1 - field_prob), 3),
            "confidence": round(float(confidence), 3),
            "toss_win_advantage": round(toss_impact, 3),
            "factors": factors,
            "venue_history": venue_history,
        }

    def _calculate_toss_impact(self, venue: str, decision: str) -> float:
        """Calculate how much winning the toss impacts win probability at this venue."""
        if self._matches_df is None or not venue:
            return 0.03  # Default small toss advantage

        df = self._matches_df
        vm = df[df["venue"].str.contains(str(venue)[:20], case=False, na=False)]

        if len(vm) < 10:
            return 0.03

        # How often does toss winner win the match?
        toss_match_wins = len(vm[vm.get("toss_winner", "") == vm.get("winner", "")])
        toss_win_rate = toss_match_wins / len(vm) if len(vm) > 0 else 0.5

        return round(toss_win_rate - 0.5, 3)  # Shift from 50-50

    def get_toss_recommendation(
        self, team: str, venue: str, weather: dict = None, match_time: str = None
    ) -> dict:
        """Get toss recommendation for a specific team."""
        pred = self.predict_toss_decision(
            team1=team, team2="Opponent",
            venue=venue, match_time=match_time, weather=weather,
        )

        return {
            "team": team,
            "recommendation": pred["predicted_decision"],
            "confidence": pred["confidence"],
            "reason": pred["factors"],
        }
