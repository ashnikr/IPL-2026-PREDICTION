"""
DLS (Duckworth-Lewis-Stern) and Rain Impact Module.

Handles:
- Rain probability impact on match outcome predictions
- DLS par score estimation for rain-interrupted matches
- Reduced-overs match adjustments
- Toss advantage shift in rain-affected matches
"""

import numpy as np
from utils.logger import logger


class DLSRainAnalyzer:
    """Analyze rain and DLS impact on match predictions."""

    # DLS resource table (simplified) - percentage of resources remaining
    # Key: overs remaining, Value: % resources for 0 wickets lost
    RESOURCE_TABLE = {
        20: 100.0, 19: 96.5, 18: 92.8, 17: 89.0, 16: 85.1,
        15: 81.1, 14: 77.0, 13: 72.7, 12: 68.2, 11: 63.6,
        10: 58.9, 9: 54.0, 8: 49.0, 7: 43.8, 6: 38.5,
        5: 33.0, 4: 27.3, 3: 21.4, 2: 15.2, 1: 8.6, 0: 0.0,
    }

    # Average T20 par scores by overs (for reference)
    AVG_SCORES_BY_OVERS = {
        20: 165, 18: 150, 16: 135, 14: 118, 12: 100,
        10: 82, 8: 64, 6: 48, 5: 40,
    }

    def __init__(self):
        pass

    def estimate_rain_impact(
        self,
        rain_probability: float,
        weather: dict = None,
        venue: str = None,
    ) -> dict:
        """Estimate how rain probability affects match prediction."""
        if rain_probability <= 0.1:
            return {
                "rain_risk": "low",
                "match_reduction_prob": 0.0,
                "expected_overs": 20,
                "prediction_adjustment": 0.0,
                "toss_advantage_shift": 0.0,
                "description": "Clear conditions, full 20-over match expected",
            }

        # Estimate match reduction
        if rain_probability > 0.7:
            match_reduction_prob = 0.6
            expected_overs = 12
            risk = "very_high"
            toss_shift = 0.08  # Huge toss advantage in rain
        elif rain_probability > 0.5:
            match_reduction_prob = 0.35
            expected_overs = 15
            risk = "high"
            toss_shift = 0.05
        elif rain_probability > 0.3:
            match_reduction_prob = 0.15
            expected_overs = 18
            risk = "moderate"
            toss_shift = 0.03
        else:
            match_reduction_prob = 0.05
            expected_overs = 19
            risk = "low"
            toss_shift = 0.01

        # Rain favors team batting first (DLS can complicate chasing)
        # In reduced overs, team batting first has more clarity
        prediction_adj = rain_probability * 0.05  # Slight shift toward batting first team

        description_parts = []
        if rain_probability > 0.5:
            description_parts.append(f"High rain risk ({rain_probability*100:.0f}%)")
            description_parts.append(f"Match may be reduced to ~{expected_overs} overs")
            description_parts.append("DLS may come into play - favors team batting first")
        elif rain_probability > 0.3:
            description_parts.append(f"Moderate rain risk ({rain_probability*100:.0f}%)")
            description_parts.append("Brief interruptions possible")
        else:
            description_parts.append(f"Slight rain chance ({rain_probability*100:.0f}%)")

        return {
            "rain_risk": risk,
            "rain_probability": round(rain_probability, 3),
            "match_reduction_prob": round(match_reduction_prob, 3),
            "expected_overs": expected_overs,
            "prediction_adjustment": round(prediction_adj, 4),
            "toss_advantage_shift": round(toss_shift, 4),
            "abandon_probability": round(max(0, rain_probability - 0.6) * 0.5, 3),
            "description": ". ".join(description_parts),
        }

    def calculate_dls_par_score(
        self,
        first_innings_score: int,
        overs_available_second: int,
        wickets_lost_first: int = 10,
    ) -> int:
        """Calculate DLS par score for second innings."""
        # Resources used in first innings (always full 20 overs, wickets_lost)
        r1 = self.RESOURCE_TABLE.get(20, 100.0)

        # Resources available in second innings
        r2 = self.RESOURCE_TABLE.get(min(overs_available_second, 20), 58.9)

        # G50 (average score in full 20-over T20) = 165
        g50 = 165

        if r1 == 0:
            return first_innings_score

        # DLS formula (simplified)
        if r2 < r1:
            # Overs reduced: par = S1 * (R2/R1)
            par = first_innings_score * (r2 / r1)
        else:
            # Second team has more resources (unlikely in T20)
            par = first_innings_score + g50 * (r2 - r1) / 100

        return max(int(round(par)), 0)

    def get_reduced_overs_advantage(
        self,
        team1: str,
        team2: str,
        expected_overs: int,
        team1_powerplay_strength: float = 0.5,
        team2_powerplay_strength: float = 0.5,
    ) -> dict:
        """Analyze which team benefits from reduced overs."""
        if expected_overs >= 18:
            return {"advantage": "neutral", "shift": 0.0, "reason": "Near-full match expected"}

        # Reduced overs favor:
        # 1. Teams with explosive top-order batsmen
        # 2. Teams with strong powerplay bowling
        # The powerplay is proportionally larger in reduced matches

        pp_ratio_normal = 6 / 20  # 30% of normal match
        pp_ratio_reduced = 6 / max(expected_overs, 6)  # Higher % in reduced match

        # Team with better powerplay scores benefits more
        shift = (team1_powerplay_strength - team2_powerplay_strength) * (pp_ratio_reduced - pp_ratio_normal)

        if abs(shift) < 0.01:
            advantage = "neutral"
            reason = "Both teams equally suited to reduced overs"
        elif shift > 0:
            advantage = team1
            reason = f"{team1} has stronger powerplay game, benefits from {expected_overs}-over match"
        else:
            advantage = team2
            reason = f"{team2} has stronger powerplay game, benefits from {expected_overs}-over match"

        return {
            "advantage": advantage,
            "shift": round(shift, 4),
            "expected_overs": expected_overs,
            "reason": reason,
        }

    def should_bat_first_in_rain(self, rain_probability: float, dew_probability: float = 0.0) -> dict:
        """Advise on toss decision considering rain and dew."""
        bat_first_score = 0.5  # neutral

        # Rain favors batting first (DLS complexity, wet outfield in 2nd innings)
        bat_first_score += rain_probability * 0.2

        # But dew favors chasing
        bat_first_score -= dew_probability * 0.15

        decision = "bat" if bat_first_score > 0.5 else "field"
        confidence = abs(bat_first_score - 0.5) * 2

        reasons = []
        if rain_probability > 0.3:
            reasons.append(f"Rain risk ({rain_probability*100:.0f}%) favors batting first to set DLS par")
        if dew_probability > 0.5:
            reasons.append(f"Dew ({dew_probability*100:.0f}%) favors chasing")

        return {
            "recommended_decision": decision,
            "bat_first_preference": round(bat_first_score, 3),
            "confidence": round(confidence, 3),
            "reasons": reasons,
        }
