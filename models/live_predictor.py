"""
Live Mid-Match Predictor — After 1st Innings.

Predicts match winner based on:
  - 1st innings score
  - Venue par scores
  - Pitch behavior
  - Dew factor
  - Chasing team strength
  - Historical chase success rates
  - Current momentum & key batsmen remaining
"""

import json
from datetime import datetime

import numpy as np

from utils.logger import logger
from config.settings import settings


class LiveMatchPredictor:
    """Predict match outcome after 1st innings completion."""

    # Venue par scores (average successful chase at each venue)
    VENUE_PAR_SCORES = {
        "M Chinnaswamy Stadium": {"par": 175, "high": 195, "low": 155, "chase_rate": 0.56},
        "Wankhede Stadium": {"par": 172, "high": 190, "low": 150, "chase_rate": 0.54},
        "Eden Gardens": {"par": 168, "high": 185, "low": 148, "chase_rate": 0.52},
        "MA Chidambaram Stadium": {"par": 158, "high": 175, "low": 140, "chase_rate": 0.48},
        "Arun Jaitley Stadium": {"par": 170, "high": 188, "low": 150, "chase_rate": 0.53},
        "Rajiv Gandhi Intl Cricket Stadium": {"par": 162, "high": 180, "low": 145, "chase_rate": 0.50},
        "Sawai Mansingh Stadium": {"par": 165, "high": 182, "low": 148, "chase_rate": 0.51},
        "Narendra Modi Stadium": {"par": 170, "high": 190, "low": 150, "chase_rate": 0.52},
        "BRSABV Ekana Stadium": {"par": 160, "high": 178, "low": 142, "chase_rate": 0.49},
        "Maharaja Yadavindra Singh International Cricket Stadium": {"par": 165, "high": 180, "low": 148, "chase_rate": 0.50},
        "ACA Cricket Stadium": {"par": 168, "high": 185, "low": 148, "chase_rate": 0.51},
        "HPCA Stadium": {"par": 170, "high": 190, "low": 150, "chase_rate": 0.53},
        "Shaheed Veer Narayan Singh Intl Stadium": {"par": 162, "high": 178, "low": 145, "chase_rate": 0.50},
        "IS Bindra Stadium": {"par": 165, "high": 182, "low": 148, "chase_rate": 0.51},
    }

    # Team chasing ability ratings (0-1)
    CHASE_RATINGS = {
        "Chennai Super Kings": 0.68,   # Elite chasers under pressure
        "Mumbai Indians": 0.62,
        "Royal Challengers Bengaluru": 0.58,
        "Kolkata Knight Riders": 0.65,
        "Sunrisers Hyderabad": 0.70,   # Aggressive chasing lineup
        "Rajasthan Royals": 0.60,
        "Delhi Capitals": 0.57,
        "Punjab Kings": 0.55,
        "Lucknow Super Giants": 0.59,
        "Gujarat Titans": 0.63,
    }

    # Team defending ability ratings (0-1)
    DEFEND_RATINGS = {
        "Chennai Super Kings": 0.65,
        "Mumbai Indians": 0.60,
        "Royal Challengers Bengaluru": 0.55,
        "Kolkata Knight Riders": 0.62,
        "Sunrisers Hyderabad": 0.58,
        "Rajasthan Royals": 0.60,
        "Delhi Capitals": 0.62,
        "Punjab Kings": 0.52,
        "Lucknow Super Giants": 0.58,
        "Gujarat Titans": 0.64,
    }

    def __init__(self):
        self.llm = None
        try:
            from agents.llm_provider import LLMChain
            self.llm = LLMChain()
        except Exception:
            pass

    def predict_after_first_innings(
        self,
        batting_team: str,
        bowling_team: str,
        score: int,
        wickets: int,
        overs: float = 20.0,
        venue: str = "",
        weather: dict = None,
        key_wickets_fallen: list[str] = None,
    ) -> dict:
        """
        Predict match outcome after 1st innings.

        Args:
            batting_team: Team that batted first
            bowling_team: Team that will chase
            score: 1st innings total
            wickets: Wickets fallen
            overs: Overs bowled (default 20)
            venue: Match venue
            weather: Weather conditions
            key_wickets_fallen: List of key batsmen already out
        """
        logger.info(f"Live prediction: {batting_team} {score}/{wickets} ({overs} ov) | "
                     f"Chasing: {bowling_team}")

        # 1. Get venue par score
        venue_data = self._get_venue_data(venue)
        par_score = venue_data["par"]

        # 2. Score analysis
        score_factor = self._analyze_score(score, wickets, overs, par_score, venue_data)

        # 3. Chase probability
        chase_prob = self._calculate_chase_probability(
            score, bowling_team, batting_team, venue_data, weather
        )

        # 4. Dew factor
        dew_adjustment = self._dew_factor(weather)

        # 5. Team strength adjustment
        chase_rating = self.CHASE_RATINGS.get(bowling_team, 0.55)
        defend_rating = self.DEFEND_RATINGS.get(batting_team, 0.55)

        # 6. Calculate final probabilities
        # Base: chase probability adjusted for team strengths
        chasing_win_prob = chase_prob

        # Adjust for team chase/defend ability
        chasing_win_prob += (chase_rating - 0.6) * 0.15
        chasing_win_prob -= (defend_rating - 0.6) * 0.12

        # Dew adjustment (favors chasing)
        chasing_win_prob += dew_adjustment

        # Reduced overs adjustment
        if overs < 20:
            # Reduced overs slightly favor batting first (DLS)
            chasing_win_prob -= (20 - overs) * 0.01

        # Clamp
        chasing_win_prob = round(np.clip(chasing_win_prob, 0.05, 0.95), 4)
        batting_win_prob = round(1 - chasing_win_prob, 4)

        # 7. Confidence
        confidence = min(0.85, 0.5 + abs(chasing_win_prob - 0.5) * 0.8)

        # 8. Required run rate
        target = score + 1
        rrr = target / 20 if overs == 20 else target / 20

        # 9. Key insights
        insights = self._generate_insights(
            batting_team, bowling_team, score, wickets, overs,
            par_score, venue_data, weather, chasing_win_prob
        )

        # 10. LLM analysis
        llm_analysis = ""
        if self.llm:
            try:
                llm_analysis = self.llm.generate(
                    f"""IPL match: {batting_team} scored {score}/{wickets} in {overs} overs.
                    {bowling_team} needs {score + 1} to win at {venue}.
                    Par score: {par_score}, Chase win rate at venue: {venue_data['chase_rate']*100:.0f}%
                    Dew probability: {weather.get('dew_probability', 0)*100:.0f}% if weather else 'Unknown'

                    Win probability: {bowling_team} {chasing_win_prob*100:.1f}% vs {batting_team} {batting_win_prob*100:.1f}%

                    In 150 words, give a mid-match analysis. Who wins and why?
                    Mention required rate, key phases, and which players can be game-changers.""",
                    max_tokens=400, temperature=0.7,
                )
            except Exception:
                pass

        result = {
            "match": f"{batting_team} vs {bowling_team}",
            "innings_1": {
                "team": batting_team,
                "score": score,
                "wickets": wickets,
                "overs": overs,
                "run_rate": round(score / max(overs, 1), 2),
            },
            "target": target,
            "required_run_rate": round(rrr, 2),
            "par_score": par_score,
            "score_vs_par": f"{'Above' if score > par_score else 'Below'} par by {abs(score - par_score)}",
            "venue": venue,
            "predictions": {
                "chasing_team": bowling_team,
                "chasing_win_prob": chasing_win_prob,
                "batting_team": batting_team,
                "batting_win_prob": batting_win_prob,
                "predicted_winner": bowling_team if chasing_win_prob > 0.5 else batting_team,
                "confidence": round(confidence, 3),
            },
            "factors": {
                "venue_chase_rate": venue_data["chase_rate"],
                "chase_rating": chase_rating,
                "defend_rating": defend_rating,
                "dew_adjustment": dew_adjustment,
                "score_factor": score_factor,
            },
            "insights": insights,
            "llm_analysis": llm_analysis,
            "timestamp": datetime.now().isoformat(),
        }

        return result

    def _get_venue_data(self, venue: str) -> dict:
        """Get venue-specific data."""
        for venue_name, data in self.VENUE_PAR_SCORES.items():
            if venue and venue_name.lower() in venue.lower() or \
               (venue and any(word in venue.lower() for word in venue_name.lower().split()[:2])):
                return {**data, "name": venue_name}
        return {"par": 165, "high": 185, "low": 148, "chase_rate": 0.50, "name": venue or "Unknown"}

    def _analyze_score(self, score: int, wickets: int, overs: float,
                       par: int, venue_data: dict) -> str:
        """Analyze the 1st innings score."""
        if score >= venue_data["high"]:
            return "well_above_par"
        elif score >= par + 10:
            return "above_par"
        elif score >= par - 10:
            return "par"
        elif score >= venue_data["low"]:
            return "below_par"
        else:
            return "well_below_par"

    def _calculate_chase_probability(self, score: int, chasing_team: str,
                                      batting_team: str, venue_data: dict,
                                      weather: dict = None) -> float:
        """Calculate base chase probability from score and venue."""
        par = venue_data["par"]
        base_chase = venue_data["chase_rate"]

        # Score relative to par
        diff = score - par
        # Every 10 runs above par reduces chase prob by ~8%
        score_adjustment = -diff * 0.008

        chase_prob = base_chase + score_adjustment

        # Very low scores are almost always chased
        if score < 130:
            chase_prob = max(chase_prob, 0.82)
        elif score < 150:
            chase_prob = max(chase_prob, 0.65)

        # Very high scores are hard to chase
        if score > 200:
            chase_prob = min(chase_prob, 0.25)
        elif score > 190:
            chase_prob = min(chase_prob, 0.35)

        return chase_prob

    def _dew_factor(self, weather: dict = None) -> float:
        """Calculate dew advantage for chasing team."""
        if not weather:
            return 0.03  # Default slight dew advantage for evening matches

        dew = weather.get("dew_probability", 0.3)
        humidity = weather.get("humidity", 50)

        # High dew helps chasing team (wet ball = harder to bowl)
        if dew > 0.7:
            return 0.08
        elif dew > 0.5:
            return 0.05
        elif dew > 0.3:
            return 0.03
        return 0.01

    def _generate_insights(self, batting_team, bowling_team, score, wickets,
                           overs, par, venue_data, weather, chase_prob) -> list[str]:
        """Generate key match insights."""
        insights = []

        # Score context
        diff = score - par
        if diff > 15:
            insights.append(f"{batting_team} posted {score}, {diff} above par ({par}). Challenging target.")
        elif diff > 0:
            insights.append(f"{batting_team}'s {score} is slightly above par ({par}). Competitive total.")
        elif diff > -15:
            insights.append(f"{batting_team}'s {score} is around par ({par}). Balanced match ahead.")
        else:
            insights.append(f"{batting_team}'s {score} is {abs(diff)} below par ({par}). {bowling_team} favorites.")

        # Run rate
        rrr = (score + 1) / 20
        if rrr > 10:
            insights.append(f"Required rate of {rrr:.1f} is very demanding. {batting_team} in control.")
        elif rrr > 8.5:
            insights.append(f"Required rate of {rrr:.1f} is challenging but achievable with a fast start.")
        else:
            insights.append(f"Required rate of {rrr:.1f} is manageable. {bowling_team} should back themselves.")

        # Venue chase history
        cr = venue_data["chase_rate"]
        if cr > 0.55:
            insights.append(f"Venue favors chasing ({cr*100:.0f}% chase win rate). Good for {bowling_team}.")
        elif cr < 0.45:
            insights.append(f"Venue favors defending ({(1-cr)*100:.0f}% defend rate). {batting_team} advantage.")

        # Dew
        if weather and weather.get("dew_probability", 0) > 0.5:
            insights.append(f"High dew expected ({weather['dew_probability']*100:.0f}%) — "
                          f"bowling will be harder in 2nd innings. Favors {bowling_team}.")

        # Prediction
        winner = bowling_team if chase_prob > 0.5 else batting_team
        insights.append(f"PREDICTION: {winner} ({max(chase_prob, 1-chase_prob)*100:.0f}% probability)")

        return insights

    def print_prediction(self, result: dict):
        """Print formatted mid-match prediction."""
        inn = result["innings_1"]
        pred = result["predictions"]

        print(f"\n{'='*65}")
        print(f"   LIVE MATCH PREDICTION — After 1st Innings")
        print(f"{'='*65}")
        print(f"   {inn['team']}: {inn['score']}/{inn['wickets']} ({inn['overs']} overs)")
        print(f"   Run Rate: {inn['run_rate']}")
        print(f"   Target: {result['target']} | Required Rate: {result['required_run_rate']}")
        print(f"   {result['score_vs_par']} (Par: {result['par_score']})")
        print(f"-" * 65)

        chasing = pred["chasing_team"]
        batting = pred["batting_team"]
        print(f"\n   {chasing} (chasing):  {pred['chasing_win_prob']*100:5.1f}%")
        print(f"   {batting} (defending): {pred['batting_win_prob']*100:5.1f}%")
        print(f"   Confidence: {pred['confidence']*100:.0f}%")
        print(f"   PREDICTED WINNER: >>> {pred['predicted_winner']} <<<")

        print(f"\n   Factors:")
        f = result["factors"]
        print(f"     Venue chase rate: {f['venue_chase_rate']*100:.0f}%")
        print(f"     {chasing} chase rating: {f['chase_rating']:.2f}")
        print(f"     {batting} defend rating: {f['defend_rating']:.2f}")
        print(f"     Dew advantage: +{f['dew_adjustment']*100:.1f}% to chasing team")

        print(f"\n   Key Insights:")
        for insight in result["insights"]:
            print(f"     > {insight}")

        if result.get("llm_analysis"):
            print(f"\n   AI Analysis:")
            for line in result["llm_analysis"].split("\n"):
                if line.strip():
                    print(f"     {line.strip()}")

        print(f"{'='*65}")
