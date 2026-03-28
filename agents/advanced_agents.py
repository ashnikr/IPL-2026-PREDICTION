"""
Advanced AI Agent System for IPL Match Prediction.

10 specialized agents with LLM reasoning and debate system:
  1. DataAgent         - Collects live match data, schedule, squads
  2. PlayerFormAgent   - Analyzes player form & momentum with deep stats
  3. PitchAgent        - Venue/pitch analysis with historical data
  4. WeatherAgent      - Live weather + dew/rain/DLS analysis
  5. TossAgent         - Toss outcome prediction & strategy
  6. NewsAgent         - Scrapes live cricket news
  7. SentimentAgent    - Sentiment analysis from news & social signals
  8. StrategyAgent     - Tactical analysis (batting order, matchups, impact player)
  9. ModelAgent        - Runs 8 ML models with all adjustments
  10. DebateAgent      - Agents debate predictions, synthesizes final verdict

Uses LLM (Gemini/Groq/OpenAI) for intelligent reasoning at each agent step.
Falls back to structured analysis if no LLM available.
"""

import json
from datetime import date, datetime
from typing import Any

import numpy as np

from utils.logger import logger
from config.settings import settings
from agents.llm_provider import LLMChain


# ── Agent State ──────────────────────────────────────────────────────

class MatchState(dict):
    """State passed between all 10 agents."""
    pass


# ── Agent Base Class ─────────────────────────────────────────────────

class BaseAgent:
    """Base class for all prediction agents."""

    def __init__(self, llm: LLMChain = None):
        self.llm = llm

    @property
    def name(self) -> str:
        return self.__class__.__name__

    def think(self, task: str, context: dict) -> str:
        """Use LLM to reason about the task (if available)."""
        if self.llm:
            try:
                return self.llm.generate_agent_reasoning(self.name, task, context)
            except Exception as e:
                logger.warning(f"[{self.name}] LLM reasoning failed: {e}")
        return ""


# ── 1. DataAgent ─────────────────────────────────────────────────────

class DataAgent(BaseAgent):
    """Collects live match data from all sources."""

    def run(self, state: dict) -> dict:
        logger.info("[1/10 DataAgent] Collecting match data...")
        from scrapers.live_data_scraper import LiveDataScraper

        scraper = LiveDataScraper()
        team1 = state.get("team1", "")
        team2 = state.get("team2", "")

        if team1 and team2:
            match_info = scraper.get_match_info(team1, team2)
            state["match_info"] = match_info
            state["schedule"] = scraper.get_current_schedule()
            state["squads"] = scraper.get_team_squads()
            state["team1_xi"] = match_info["team1"]["playing_xi"]
            state["team2_xi"] = match_info["team2"]["playing_xi"]
            state["team1_captain"] = match_info["team1"]["captain"]
            state["team2_captain"] = match_info["team2"]["captain"]

            if not state.get("venue"):
                state["venue"] = match_info.get("venue", "")
            if not state.get("city"):
                state["city"] = match_info.get("city", "")
            state["time_ist"] = match_info.get("time_ist", "19:30")
            state["is_double_header"] = match_info.get("is_double_header", False)
            state["match_date"] = match_info.get("date")
            state["match_number"] = match_info.get("match_number")

        state["injuries"] = scraper.get_player_injuries()
        state["data_collected"] = True

        logger.info(f"[DataAgent] Venue: {state.get('venue', 'TBD')}, "
                     f"Time: {state.get('time_ist', '?')} IST, "
                     f"Match #{state.get('match_number', '?')}")
        return state


# ── 2. PlayerFormAgent ───────────────────────────────────────────────

class PlayerFormAgent(BaseAgent):
    """Deep player form analysis with momentum tracking."""

    def run(self, state: dict) -> dict:
        logger.info("[2/10 PlayerFormAgent] Analyzing player form & momentum...")
        team1 = state.get("team1", "")
        team2 = state.get("team2", "")

        # Form tracker
        from models.form_tracker import FormTracker
        tracker = FormTracker()

        form_data = tracker.get_matchup_form(team1, team2)
        state["form_data"] = form_data
        state["team1_form"] = form_data["team1_form"]
        state["team2_form"] = form_data["team2_form"]
        state["team1_key_players"] = form_data["team1_key_players"]
        state["team2_key_players"] = form_data["team2_key_players"]
        state["form_adjustment"] = form_data["prediction_adjustment"]

        # Impact player analysis
        try:
            from models.impact_player import ImpactPlayerAnalyzer
            impact = ImpactPlayerAnalyzer()
            state["team1_squad_strength"] = impact.get_team_squad_strength(team1)
            state["team2_squad_strength"] = impact.get_team_squad_strength(team2)
            state["impact_analysis"] = impact.estimate_impact_shift(
                team1, team2,
                venue=state.get("venue"),
                weather=state.get("weather"),
            )
        except Exception as e:
            logger.warning(f"[PlayerFormAgent] Impact analysis: {e}")
            state["impact_analysis"] = {"net_shift": 0, "scenarios": []}

        # LLM reasoning
        reasoning = self.think(
            "Analyze key player matchups and form for this IPL match",
            {
                "team1": team1, "team2": team2,
                "team1_form": form_data["team1_form"],
                "team2_form": form_data["team2_form"],
                "team1_key_players": [p["name"] for p in form_data.get("team1_key_players", [])[:4]],
                "team2_key_players": [p["name"] for p in form_data.get("team2_key_players", [])[:4]],
            }
        )
        if reasoning:
            state["player_reasoning"] = reasoning

        state["player_analysis_done"] = True
        logger.info(f"[PlayerFormAgent] {team1} form: {form_data['team1_form']['form_rating']:.3f}, "
                     f"{team2} form: {form_data['team2_form']['form_rating']:.3f}")
        return state


# ── 3. PitchAgent ────────────────────────────────────────────────────

class PitchAgent(BaseAgent):
    """Advanced venue and pitch analysis."""

    def run(self, state: dict) -> dict:
        logger.info("[3/10 PitchAgent] Analyzing pitch & venue...")
        import pandas as pd

        venue = state.get("venue", "")
        team1 = state.get("team1", "")
        team2 = state.get("team2", "")

        try:
            matches = pd.read_csv(settings.processed_data_dir / "matches_processed.csv")
            vm = matches[matches["venue"].str.contains(
                str(venue)[:20], case=False, na=False
            )] if venue else pd.DataFrame()

            if not vm.empty and "winner" in vm.columns:
                total = len(vm)
                avg_score = vm.get("inn1_total_runs", pd.Series()).mean()
                avg_sc = float(avg_score) if pd.notna(avg_score) else 165

                # Chase analysis
                chase_wins = decided = 0
                for _, row in vm.iterrows():
                    if pd.notna(row.get("winner")) and pd.notna(row.get("toss_decision")):
                        decided += 1
                        if row["toss_decision"] == "field" and row.get("toss_winner") == row.get("winner"):
                            chase_wins += 1
                        elif row["toss_decision"] == "bat" and row.get("toss_winner") != row.get("winner"):
                            chase_wins += 1

                # Team records at venue
                t1_vm = vm[(vm["team1"] == team1) | (vm["team2"] == team1)]
                t2_vm = vm[(vm["team1"] == team2) | (vm["team2"] == team2)]
                t1_wins = len(t1_vm[t1_vm["winner"] == team1]) if not t1_vm.empty else 0
                t2_wins = len(t2_vm[t2_vm["winner"] == team2]) if not t2_vm.empty else 0

                if avg_sc > 175:
                    pitch_type = "Batting paradise"
                elif avg_sc > 160:
                    pitch_type = "Balanced"
                elif avg_sc > 145:
                    pitch_type = "Bowling-friendly"
                else:
                    pitch_type = "Spin-friendly (low & slow)"

                state["venue_stats"] = {
                    "total_matches": total,
                    "avg_first_innings_score": round(avg_sc, 1),
                    "chase_win_pct": round(chase_wins / decided, 3) if decided > 0 else 0.5,
                    "pitch_type": pitch_type,
                    "team1_venue_record": f"{t1_wins}/{len(t1_vm)}",
                    "team2_venue_record": f"{t2_wins}/{len(t2_vm)}",
                    "team1_venue_win_pct": round(t1_wins / len(t1_vm), 3) if len(t1_vm) > 0 else 0.5,
                    "team2_venue_win_pct": round(t2_wins / len(t2_vm), 3) if len(t2_vm) > 0 else 0.5,
                }
            else:
                state["venue_stats"] = self._default_stats()
        except Exception as e:
            logger.warning(f"[PitchAgent] Error: {e}")
            state["venue_stats"] = self._default_stats()

        # LLM reasoning about venue
        reasoning = self.think(
            "Analyze how this venue will affect the match outcome",
            {"venue": venue, "venue_stats": state["venue_stats"], "team1": team1, "team2": team2}
        )
        if reasoning:
            state["pitch_reasoning"] = reasoning

        state["pitch_analysis_done"] = True
        logger.info(f"[PitchAgent] {venue}: {state['venue_stats']['pitch_type']}, "
                     f"Avg: {state['venue_stats']['avg_first_innings_score']}")
        return state

    def _default_stats(self):
        return {
            "total_matches": 0, "avg_first_innings_score": 165,
            "chase_win_pct": 0.5, "pitch_type": "Unknown",
            "team1_venue_record": "0/0", "team2_venue_record": "0/0",
            "team1_venue_win_pct": 0.5, "team2_venue_win_pct": 0.5,
        }


# ── 4. WeatherAgent ─────────────────────────────────────────────────

class WeatherAgent(BaseAgent):
    """Live weather analysis with dew/rain/DLS impact."""

    def run(self, state: dict) -> dict:
        logger.info("[4/10 WeatherAgent] Fetching live weather...")
        from scrapers.weather_scraper import WeatherCollector

        collector = WeatherCollector()
        city = state.get("city", "")
        if not city:
            venue = state.get("venue", "")
            city_map = {
                "Wankhede": "Mumbai", "Chinnaswamy": "Bengaluru",
                "Eden": "Kolkata", "Chidambaram": "Chennai",
                "Jaitley": "Delhi", "Rajiv Gandhi": "Hyderabad",
                "Mansingh": "Jaipur", "Narendra Modi": "Ahmedabad",
                "Ekana": "Lucknow", "PCA": "Mohali",
                "ACA": "Guwahati", "Barsapara": "Guwahati",
                "HPCA": "Dharamsala", "Dharamsala": "Dharamsala",
                "Nava Raipur": "Raipur", "Yadavindra": "Mullanpur",
            }
            for key, c in city_map.items():
                if key.lower() in venue.lower():
                    city = c
                    break

        if city:
            match_date = state.get("match_date", str(date.today()))
            weather = collector.get_weather(city, match_date)
            try:
                impact = collector.get_match_weather_impact(city, match_date)
                if impact:
                    weather.update(impact)
            except Exception:
                pass
            state["weather"] = weather
        else:
            state["weather"] = {}

        # DLS/Rain analysis
        try:
            from models.dls_rain import DLSRainAnalyzer
            dls = DLSRainAnalyzer()
            rain_prob = state["weather"].get("rain_probability", 0)
            state["rain_analysis"] = dls.estimate_rain_impact(
                rain_prob, state["weather"], state.get("venue")
            )
        except Exception:
            state["rain_analysis"] = {"rain_risk": "low"}

        state["weather_done"] = True
        w = state["weather"]
        logger.info(f"[WeatherAgent] {city}: {w.get('condition', 'N/A')}, "
                     f"Temp: {w.get('temperature', '?')}C, "
                     f"Rain: {w.get('rain_probability', 0)*100:.0f}%")
        return state


# ── 5. TossAgent ─────────────────────────────────────────────────────

class TossAgent(BaseAgent):
    """Toss outcome prediction & strategy analysis."""

    def run(self, state: dict) -> dict:
        logger.info("[5/10 TossAgent] Analyzing toss strategy...")

        try:
            from models.toss_predictor import TossPredictor
            predictor = TossPredictor()
            toss_pred = predictor.predict_toss_decision(
                team1=state.get("team1", ""),
                team2=state.get("team2", ""),
                venue=state.get("venue"),
                match_time=state.get("time_ist"),
                weather=state.get("weather"),
            )
            state["toss_prediction"] = toss_pred
        except Exception as e:
            logger.warning(f"[TossAgent] Error: {e}")
            state["toss_prediction"] = {"predicted_decision": "field", "confidence": 0.5}

        state["toss_done"] = True
        logger.info(f"[TossAgent] Likely: {state['toss_prediction'].get('predicted_decision', '?')} "
                     f"({state['toss_prediction'].get('confidence', 0)*100:.0f}% conf)")
        return state


# ── 6. NewsAgent ─────────────────────────────────────────────────────

class NewsAgent(BaseAgent):
    """Scrapes live cricket news relevant to the match."""

    def run(self, state: dict) -> dict:
        logger.info("[6/10 NewsAgent] Scraping live cricket news...")

        try:
            from scrapers.news_scraper import CricketNewsScraper
            scraper = CricketNewsScraper()

            team1 = state.get("team1", "")
            team2 = state.get("team2", "")

            t1_news = scraper.get_team_news(team1)
            t2_news = scraper.get_team_news(team2)
            injury_news = scraper.get_injury_news()

            state["team1_news"] = [a["title"] for a in t1_news[:5]]
            state["team2_news"] = [a["title"] for a in t2_news[:5]]
            state["injury_news"] = [a["title"] for a in injury_news[:5]]
            state["total_news_articles"] = len(t1_news) + len(t2_news)

            logger.info(f"[NewsAgent] Found {len(t1_news)} articles for {team1}, "
                         f"{len(t2_news)} for {team2}")
        except Exception as e:
            logger.warning(f"[NewsAgent] Error: {e}")
            state["team1_news"] = []
            state["team2_news"] = []
            state["injury_news"] = []
            state["total_news_articles"] = 0

        state["news_done"] = True
        return state


# ── 7. SentimentAgent ────────────────────────────────────────────────

class SentimentAgent(BaseAgent):
    """Analyzes sentiment from news to gauge team confidence."""

    def run(self, state: dict) -> dict:
        logger.info("[7/10 SentimentAgent] Analyzing team sentiment...")

        try:
            from scrapers.news_scraper import CricketNewsScraper
            scraper = CricketNewsScraper()

            team1 = state.get("team1", "")
            team2 = state.get("team2", "")

            sentiment = scraper.get_match_sentiment(team1, team2)
            state["sentiment"] = sentiment
            state["sentiment_shift"] = sentiment.get("prediction_shift", 0)

            logger.info(f"[SentimentAgent] {team1}: {sentiment['team1']['sentiment_label']} "
                         f"({sentiment['team1']['sentiment_score']:.2f}), "
                         f"{team2}: {sentiment['team2']['sentiment_label']} "
                         f"({sentiment['team2']['sentiment_score']:.2f})")
        except Exception as e:
            logger.warning(f"[SentimentAgent] Error: {e}")
            state["sentiment"] = {"team1": {"sentiment_label": "neutral"}, "team2": {"sentiment_label": "neutral"}}
            state["sentiment_shift"] = 0

        state["sentiment_done"] = True
        return state


# ── 8. StrategyAgent ─────────────────────────────────────────────────

class StrategyAgent(BaseAgent):
    """Tactical analysis - batting order, matchups, impact player strategy."""

    def run(self, state: dict) -> dict:
        logger.info("[8/10 StrategyAgent] Analyzing match tactics...")

        team1 = state.get("team1", "")
        team2 = state.get("team2", "")
        venue_stats = state.get("venue_stats", {})
        weather = state.get("weather", {})
        toss = state.get("toss_prediction", {})
        impact = state.get("impact_analysis", {})
        form = state.get("form_data", {})

        # Build tactical analysis
        tactics = {
            "batting_first_advantage": self._batting_first_advantage(venue_stats, weather),
            "key_matchups": self._identify_matchups(state),
            "impact_player_strategy": self._impact_strategy(state),
            "powerplay_strategy": self._powerplay_analysis(state),
            "death_overs_edge": self._death_overs_analysis(state),
            "x_factor": self._identify_x_factor(state),
        }

        # LLM strategic reasoning
        reasoning = self.think(
            "Provide tactical analysis for this IPL match - batting order, key matchups, impact player strategy",
            {
                "team1": team1, "team2": team2,
                "venue": state.get("venue"),
                "pitch_type": venue_stats.get("pitch_type"),
                "weather_condition": weather.get("condition"),
                "dew_probability": weather.get("dew_probability", 0),
                "toss_likely": toss.get("predicted_decision"),
                "team1_captain": state.get("team1_captain"),
                "team2_captain": state.get("team2_captain"),
            }
        )
        if reasoning:
            tactics["llm_strategy"] = reasoning

        state["tactics"] = tactics
        state["strategy_done"] = True
        logger.info(f"[StrategyAgent] Bat-first advantage: {tactics['batting_first_advantage']:.2f}, "
                     f"X-factor: {tactics.get('x_factor', {}).get('player', 'N/A')}")
        return state

    def _batting_first_advantage(self, venue_stats: dict, weather: dict) -> float:
        """Calculate batting first advantage score (0-1)."""
        chase_pct = venue_stats.get("chase_win_pct", 0.5)
        dew = weather.get("dew_probability", 0.5)
        # High dew = chasing advantage, so batting first is disadvantaged
        bat_first = (1 - chase_pct) * 0.6 + (1 - dew) * 0.4
        return round(bat_first, 3)

    def _identify_matchups(self, state: dict) -> list[str]:
        """Identify key player matchups."""
        matchups = []
        t1_players = state.get("team1_key_players", [])
        t2_players = state.get("team2_key_players", [])

        # Find bat vs bowl matchups
        t1_bats = [p for p in t1_players if p.get("batting_rating", 0) > 70]
        t2_bowls = [p for p in t2_players if p.get("bowling_rating", 0) > 70]
        t2_bats = [p for p in t2_players if p.get("batting_rating", 0) > 70]
        t1_bowls = [p for p in t1_players if p.get("bowling_rating", 0) > 70]

        if t1_bats and t2_bowls:
            matchups.append(f"{t1_bats[0]['name']} vs {t2_bowls[0]['name']}")
        if t2_bats and t1_bowls:
            matchups.append(f"{t2_bats[0]['name']} vs {t1_bowls[0]['name']}")

        return matchups[:4]

    def _impact_strategy(self, state: dict) -> dict:
        """Analyze impact player strategy for both teams."""
        impact = state.get("impact_analysis", {})
        weather = state.get("weather", {})
        dew = weather.get("dew_probability", 0)

        if dew > 0.6:
            strategy = "Use impact batsman for chasing team to exploit dew conditions"
        elif state.get("venue_stats", {}).get("avg_first_innings_score", 165) < 155:
            strategy = "Use impact bowler on this bowling-friendly pitch"
        else:
            strategy = "Match-situation dependent - flexible impact player usage"

        return {
            "recommendation": strategy,
            "scenarios": impact.get("scenarios", []),
            "net_shift": impact.get("net_shift", 0),
        }

    def _powerplay_analysis(self, state: dict) -> dict:
        """Analyze powerplay strategy."""
        t1_players = state.get("team1_key_players", [])
        t2_players = state.get("team2_key_players", [])

        t1_openers = [p for p in t1_players if p.get("role") in ("opener", "keeper-bat")]
        t2_openers = [p for p in t2_players if p.get("role") in ("opener", "keeper-bat")]

        return {
            "team1_powerplay_strength": "strong" if len(t1_openers) >= 2 else "moderate",
            "team2_powerplay_strength": "strong" if len(t2_openers) >= 2 else "moderate",
        }

    def _death_overs_analysis(self, state: dict) -> dict:
        """Analyze death overs capabilities."""
        t1_players = state.get("team1_key_players", [])
        t2_players = state.get("team2_key_players", [])

        t1_finishers = [p for p in t1_players if p.get("role") in ("finisher", "allrounder")]
        t2_finishers = [p for p in t2_players if p.get("role") in ("finisher", "allrounder")]

        return {
            "team1_death_bowling": len([p for p in t1_players if p.get("role") == "pace"]),
            "team2_death_bowling": len([p for p in t2_players if p.get("role") == "pace"]),
            "team1_finishers": [p["name"] for p in t1_finishers[:2]],
            "team2_finishers": [p["name"] for p in t2_finishers[:2]],
        }

    def _identify_x_factor(self, state: dict) -> dict:
        """Identify the X-factor player for the match."""
        all_players = (
            state.get("team1_key_players", []) +
            state.get("team2_key_players", [])
        )
        if not all_players:
            return {"player": "Unknown", "reason": "No form data available"}

        # Highest impact in excellent form
        excellent = [p for p in all_players if p.get("recent_form") == "excellent"]
        if excellent:
            best = max(excellent, key=lambda p: p.get("impact_score", 0))
        else:
            best = max(all_players, key=lambda p: p.get("impact_score", 0))

        return {
            "player": best["name"],
            "impact_score": best.get("impact_score", 0),
            "reason": f"In {best.get('recent_form', 'good')} form with impact score {best.get('impact_score', 0):.0f}",
        }


# ── 9. ModelAgent ────────────────────────────────────────────────────

class ModelAgent(BaseAgent):
    """Runs all 8 prediction models with calibrated adjustments."""

    def run(self, state: dict) -> dict:
        logger.info("[9/10 ModelAgent] Running ensemble prediction models...")
        from models.ensemble import EnsemblePrediction

        ensemble = EnsemblePrediction()

        # Check for calibrated weights
        try:
            from models.calibration import PredictionCalibrator
            calibrator = PredictionCalibrator()
            calibrated_weights = calibrator.get_adjusted_weights()
            if calibrated_weights:
                logger.info(f"[ModelAgent] Using calibrated weights: {calibrated_weights}")
        except Exception:
            calibrated_weights = {}

        pred = ensemble.predict_match(
            team1=state.get("team1", ""),
            team2=state.get("team2", ""),
            venue=state.get("venue"),
            city=state.get("city"),
            toss_winner=state.get("toss_winner"),
            toss_decision=state.get("toss_decision"),
            weather=state.get("weather"),
        )

        # Apply adjustments
        total_adjustment = 0.0

        # 1. Impact player adjustment
        impact = state.get("impact_analysis", {})
        if impact and impact.get("net_shift", 0) != 0:
            total_adjustment += impact["net_shift"]

        # 2. Rain adjustment
        rain = state.get("rain_analysis", {})
        if rain.get("prediction_adjustment", 0) != 0:
            total_adjustment += rain["prediction_adjustment"]

        # 3. Form/momentum adjustment
        form_adj = state.get("form_adjustment", 0)
        total_adjustment += form_adj

        # 4. Sentiment adjustment
        sentiment_shift = state.get("sentiment_shift", 0)
        total_adjustment += sentiment_shift

        # Apply total adjustment
        if total_adjustment != 0:
            pred["team1_win_prob"] = round(
                float(np.clip(pred["team1_win_prob"] + total_adjustment, 0.02, 0.98)), 4
            )
            pred["team2_win_prob"] = round(1 - pred["team1_win_prob"], 4)

        pred["predicted_winner"] = state["team1"] if pred["team1_win_prob"] > 0.5 else state["team2"]
        pred["adjustments_applied"] = {
            "impact_player": impact.get("net_shift", 0),
            "rain": rain.get("prediction_adjustment", 0),
            "form_momentum": form_adj,
            "sentiment": sentiment_shift,
            "total": round(total_adjustment, 4),
        }

        state["prediction"] = pred
        state["model_done"] = True

        # Record for calibration
        try:
            from models.calibration import PredictionCalibrator
            calibrator = PredictionCalibrator()
            calibrator.record_prediction(pred)
        except Exception:
            pass

        logger.info(f"[ModelAgent] {pred['team1']}: {pred['team1_win_prob']:.1%} | "
                     f"{pred['team2']}: {pred['team2_win_prob']:.1%} | "
                     f"Adj: {total_adjustment:+.3f}")
        return state


# ── 10. DebateAgent ──────────────────────────────────────────────────

class DebateAgent(BaseAgent):
    """Agents debate the prediction - bull vs bear case, then final verdict."""

    def run(self, state: dict) -> dict:
        logger.info("[10/10 DebateAgent] Generating debate & final analysis...")

        pred = state.get("prediction", {})
        team1 = state.get("team1", "?")
        team2 = state.get("team2", "?")
        winner = pred.get("predicted_winner", team1)
        loser = team2 if winner == team1 else team1

        # Collect all agent analyses
        agent_analyses = {
            "player_form": {
                "team1_form": state.get("team1_form", {}),
                "team2_form": state.get("team2_form", {}),
                "form_advantage": state.get("form_data", {}).get("form_advantage", "even"),
            },
            "venue": state.get("venue_stats", {}),
            "weather": {
                "condition": state.get("weather", {}).get("condition"),
                "rain_risk": state.get("rain_analysis", {}).get("rain_risk"),
                "dew": state.get("weather", {}).get("dew_probability", 0),
            },
            "toss": state.get("toss_prediction", {}),
            "sentiment": {
                "team1": state.get("sentiment", {}).get("team1", {}).get("sentiment_label"),
                "team2": state.get("sentiment", {}).get("team2", {}).get("sentiment_label"),
            },
            "tactics": {
                "x_factor": state.get("tactics", {}).get("x_factor", {}),
                "batting_first_adv": state.get("tactics", {}).get("batting_first_advantage", 0.5),
            },
        }

        # Try LLM debate
        debate_text = ""
        if self.llm:
            try:
                debate_text = self.llm.generate_debate(pred, [agent_analyses])
            except Exception as e:
                logger.warning(f"[DebateAgent] LLM debate failed: {e}")

        # Build comprehensive report
        report = self._build_full_report(state, debate_text)
        state["explanation"] = report
        state["debate"] = debate_text

        # Try LLM for final match analysis
        if self.llm:
            try:
                match_context = self._build_llm_context(state)
                llm_analysis = self.llm.generate_match_analysis(match_context)
                state["llm_analysis"] = llm_analysis
                state["explanation_source"] = "llm"
            except Exception:
                state["explanation_source"] = "structured"
        else:
            state["explanation_source"] = "structured"

        state["explanation_done"] = True
        return state

    def _build_llm_context(self, state: dict) -> dict:
        """Build context dict for LLM analysis."""
        pred = state.get("prediction", {})
        return {
            "team1": state.get("team1"),
            "team2": state.get("team2"),
            "venue": state.get("venue"),
            "city": state.get("city"),
            "date": state.get("match_date"),
            "time_ist": state.get("time_ist"),
            "match_number": state.get("match_number"),
            "team1_captain": state.get("team1_captain"),
            "team2_captain": state.get("team2_captain"),
            "team1_xi": [p["name"] if isinstance(p, dict) else p for p in state.get("team1_xi", [])[:11]],
            "team2_xi": [p["name"] if isinstance(p, dict) else p for p in state.get("team2_xi", [])[:11]],
            "team1_strength": state.get("team1_squad_strength", {}),
            "team2_strength": state.get("team2_squad_strength", {}),
            "weather": state.get("weather", {}),
            "toss_prediction": state.get("toss_prediction", {}),
            "rain_analysis": state.get("rain_analysis", {}),
            "impact_player": state.get("impact_analysis", {}),
            "team1_prob": round(pred.get("team1_win_prob", 0.5) * 100, 1),
            "team2_prob": round(pred.get("team2_win_prob", 0.5) * 100, 1),
            "predicted_winner": pred.get("predicted_winner"),
            "confidence": round(pred.get("confidence", 0) * 100, 1),
            "key_factors": pred.get("key_factors", []),
            "news_sentiment": state.get("sentiment", {}),
            "form_data": {
                "team1": state.get("team1_form", {}),
                "team2": state.get("team2_form", {}),
            },
            "h2h": state.get("h2h", {}),
        }

    def _build_full_report(self, state: dict, debate: str) -> str:
        """Build the comprehensive prediction report."""
        pred = state.get("prediction", {})
        t1 = state.get("team1", "?")
        t2 = state.get("team2", "?")
        p1 = pred.get("team1_win_prob", 0.5)
        winner = pred.get("predicted_winner", t1)
        conf = pred.get("confidence", 0) * 100

        lines = [
            "",
            "=" * 70,
            f"   IPL 2026 MATCH PREDICTION — AI AGENT SYSTEM (10 Agents)",
            "=" * 70,
            f"",
            f"  MATCH {state.get('match_number', '')}: {t1} vs {t2}",
            f"  Date: {state.get('match_date', 'TBD')} | Time: {state.get('time_ist', '19:30')} IST",
            f"  Venue: {state.get('venue', 'TBD')}, {state.get('city', '')}",
        ]

        if state.get("is_double_header"):
            lines.append(f"  ** DOUBLE HEADER DAY **")

        lines.extend([
            f"  Captains: {state.get('team1_captain', '?')} vs {state.get('team2_captain', '?')}",
            "",
            "-" * 70,
            f"  PREDICTION",
            "-" * 70,
            f"  {t1:40s}  {p1*100:5.1f}%",
            f"  {t2:40s}  {(1-p1)*100:5.1f}%",
            f"  Confidence: {conf:.0f}%",
            f"  PREDICTED WINNER: >>> {winner} <<<",
            "",
        ])

        # Adjustments applied
        adj = pred.get("adjustments_applied", {})
        if adj and adj.get("total", 0) != 0:
            lines.extend([
                "-" * 70,
                f"  ADJUSTMENTS APPLIED",
                "-" * 70,
            ])
            if adj.get("impact_player", 0) != 0:
                lines.append(f"    Impact Player:   {adj['impact_player']:+.3f}")
            if adj.get("rain", 0) != 0:
                lines.append(f"    Rain/DLS:        {adj['rain']:+.3f}")
            if adj.get("form_momentum", 0) != 0:
                lines.append(f"    Form/Momentum:   {adj['form_momentum']:+.3f}")
            if adj.get("sentiment", 0) != 0:
                lines.append(f"    News Sentiment:  {adj['sentiment']:+.3f}")
            lines.append(f"    TOTAL:           {adj['total']:+.3f}")
            lines.append("")

        # Team Form
        t1_form = state.get("team1_form", {})
        t2_form = state.get("team2_form", {})
        lines.extend([
            "-" * 70,
            f"  TEAM FORM & MOMENTUM",
            "-" * 70,
        ])
        if t1_form.get("matches_played", 0) > 0:
            lines.append(f"  {t1}: {t1_form.get('form_string', 'N/A')} | "
                        f"Streak: {t1_form.get('streak', '?')} | "
                        f"Momentum: {t1_form.get('momentum', '?')}")
        else:
            lines.append(f"  {t1}: Season start — Base rating: {t1_form.get('base_rating', 0):.0%}")
        if t2_form.get("matches_played", 0) > 0:
            lines.append(f"  {t2}: {t2_form.get('form_string', 'N/A')} | "
                        f"Streak: {t2_form.get('streak', '?')} | "
                        f"Momentum: {t2_form.get('momentum', '?')}")
        else:
            lines.append(f"  {t2}: Season start — Base rating: {t2_form.get('base_rating', 0):.0%}")
        lines.append("")

        # Key Players
        t1_kp = state.get("team1_key_players", [])
        t2_kp = state.get("team2_key_players", [])
        if t1_kp or t2_kp:
            lines.extend([
                "-" * 70,
                f"  KEY PLAYERS",
                "-" * 70,
            ])
            if t1_kp:
                lines.append(f"  {t1}:")
                for p in t1_kp[:4]:
                    lines.append(f"    {p['name']:25s} Form: {p.get('recent_form', '?'):10s} "
                                f"Impact: {p.get('impact_score', 0):.0f}")
            if t2_kp:
                lines.append(f"  {t2}:")
                for p in t2_kp[:4]:
                    lines.append(f"    {p['name']:25s} Form: {p.get('recent_form', '?'):10s} "
                                f"Impact: {p.get('impact_score', 0):.0f}")
            lines.append("")

        # Venue
        vs = state.get("venue_stats", {})
        if vs.get("total_matches", 0) > 0:
            lines.extend([
                "-" * 70,
                f"  VENUE ANALYSIS",
                "-" * 70,
                f"  Pitch: {vs.get('pitch_type', 'Unknown')} | "
                f"Avg Score: {vs['avg_first_innings_score']} | "
                f"Chase Win: {vs['chase_win_pct']*100:.0f}%",
                f"  {t1} record: {vs.get('team1_venue_record', 'N/A')} | "
                f"{t2} record: {vs.get('team2_venue_record', 'N/A')}",
                "",
            ])

        # Weather
        weather = state.get("weather", {})
        if weather:
            lines.extend([
                "-" * 70,
                f"  WEATHER & CONDITIONS",
                "-" * 70,
                f"  {weather.get('condition', 'N/A')} | "
                f"Temp: {weather.get('temperature', '?')}C | "
                f"Humidity: {weather.get('humidity', '?')}% | "
                f"Wind: {weather.get('wind_speed', '?')} kph",
                f"  Dew: {weather.get('dew_probability', 0)*100:.0f}% | "
                f"Rain: {weather.get('rain_probability', 0)*100:.0f}%",
            ])
            rain = state.get("rain_analysis", {})
            if rain.get("rain_risk") in ("moderate", "high", "very_high"):
                lines.append(f"  RAIN ALERT: {rain.get('description', '')}")
                if rain.get("expected_overs", 20) < 20:
                    lines.append(f"  Expected overs: ~{rain['expected_overs']} (DLS may apply)")
            lines.append("")

        # Toss
        toss = state.get("toss_prediction", {})
        if toss:
            lines.extend([
                "-" * 70,
                f"  TOSS STRATEGY",
                "-" * 70,
                f"  Likely decision: {toss.get('predicted_decision', '?').upper()} "
                f"({toss.get('confidence', 0)*100:.0f}% confidence)",
            ])
            lines.append("")

        # Tactics
        tactics = state.get("tactics", {})
        if tactics:
            lines.extend([
                "-" * 70,
                f"  TACTICAL ANALYSIS",
                "-" * 70,
                f"  Bat-first advantage: {tactics.get('batting_first_advantage', 0.5):.0%}",
                f"  Impact strategy: {tactics.get('impact_player_strategy', {}).get('recommendation', 'N/A')}",
            ])
            matchups = tactics.get("key_matchups", [])
            if matchups:
                lines.append(f"  Key matchups:")
                for m in matchups:
                    lines.append(f"    vs {m}")
            xf = tactics.get("x_factor", {})
            if xf.get("player"):
                lines.append(f"  X-Factor: {xf['player']} — {xf.get('reason', '')}")
            lines.append("")

        # News & Sentiment
        sentiment = state.get("sentiment", {})
        if sentiment.get("team1") or sentiment.get("team2"):
            lines.extend([
                "-" * 70,
                f"  NEWS & SENTIMENT",
                "-" * 70,
            ])
            t1_sent = sentiment.get("team1", {})
            t2_sent = sentiment.get("team2", {})
            lines.append(f"  {t1}: {t1_sent.get('sentiment_label', 'neutral').upper()} "
                        f"(score: {t1_sent.get('sentiment_score', 0):.2f}, "
                        f"{t1_sent.get('news_count', 0)} articles)")
            lines.append(f"  {t2}: {t2_sent.get('sentiment_label', 'neutral').upper()} "
                        f"(score: {t2_sent.get('sentiment_score', 0):.2f}, "
                        f"{t2_sent.get('news_count', 0)} articles)")
            adv = sentiment.get("sentiment_advantage", "neutral")
            if adv != "neutral":
                lines.append(f"  Sentiment edge: {adv} ({sentiment.get('advantage_level', '')})")

            # Headlines
            headlines = sentiment.get("headlines", {})
            for team, hdls in headlines.items():
                if hdls:
                    lines.append(f"  {team} headlines:")
                    for h in hdls[:2]:
                        lines.append(f"    - {h[:80]}")
            lines.append("")

        # Model breakdown
        model_preds = pred.get("model_predictions", {})
        if model_preds:
            lines.extend([
                "-" * 70,
                f"  MODEL BREAKDOWN (8 models)",
                "-" * 70,
            ])
            for model, prob in sorted(model_preds.items(), key=lambda x: x[1], reverse=True):
                favors = t1 if prob > 0.5 else t2
                bar_len = int(prob * 30)
                bar = "█" * bar_len + "░" * (30 - bar_len)
                lines.append(f"  {model:22s} {bar} {prob*100:5.1f}% ({favors})")
            lines.append("")

        # Key factors
        factors = pred.get("key_factors", [])
        if factors:
            lines.extend([
                "-" * 70,
                f"  KEY FACTORS",
                "-" * 70,
            ])
            for f in factors[:8]:
                lines.append(f"    ▸ {f}")
            lines.append("")

        # Agent Debate
        if debate:
            lines.extend([
                "-" * 70,
                f"  AGENT DEBATE",
                "-" * 70,
                debate,
                "",
            ])

        # Agent reasoning snippets
        for key in ["player_reasoning", "pitch_reasoning"]:
            reasoning = state.get(key, "")
            if reasoning:
                label = key.replace("_reasoning", "").title()
                lines.extend([
                    "-" * 70,
                    f"  {label.upper()} AGENT INSIGHT",
                    "-" * 70,
                    reasoning[:500],
                    "",
                ])

        lines.extend([
            "=" * 70,
            f"  Powered by: 10-Agent AI System | "
            f"LLM: {state.get('explanation_source', 'structured')} | "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M')} IST",
            "=" * 70,
        ])

        return "\n".join(lines)


# ── Advanced Agent Orchestration ─────────────────────────────────────

class AdvancedIPLAgentSystem:
    """Orchestrate all 10 agents with LLM reasoning for comprehensive prediction."""

    def __init__(self):
        self.llm = LLMChain()
        logger.info(f"Advanced Agent System initialized | LLM: {self.llm.active_provider_name}")

        self.data_agent = DataAgent(self.llm)
        self.player_agent = PlayerFormAgent(self.llm)
        self.pitch_agent = PitchAgent(self.llm)
        self.weather_agent = WeatherAgent(self.llm)
        self.toss_agent = TossAgent(self.llm)
        self.news_agent = NewsAgent(self.llm)
        self.sentiment_agent = SentimentAgent(self.llm)
        self.strategy_agent = StrategyAgent(self.llm)
        self.model_agent = ModelAgent(self.llm)
        self.debate_agent = DebateAgent(self.llm)

    def predict_match(
        self,
        team1: str,
        team2: str,
        venue: str = "",
        city: str = "",
        toss_winner: str = None,
        toss_decision: str = None,
    ) -> dict:
        """Run all 10 agents to predict a match."""
        logger.info(f"\n{'='*60}")
        logger.info(f"ADVANCED 10-AGENT PIPELINE: {team1} vs {team2}")
        logger.info(f"LLM Provider: {self.llm.active_provider_name}")
        logger.info(f"{'='*60}")

        state = {
            "team1": team1, "team2": team2,
            "venue": venue, "city": city,
            "toss_winner": toss_winner, "toss_decision": toss_decision,
        }

        # Phase 1: Data Collection (parallel in concept)
        state = self.data_agent.run(state)

        # Phase 2: Analysis (can run in parallel)
        state = self.player_agent.run(state)
        state = self.pitch_agent.run(state)
        state = self.weather_agent.run(state)

        # Phase 3: Dependent analysis
        state = self.toss_agent.run(state)
        state = self.news_agent.run(state)
        state = self.sentiment_agent.run(state)

        # Phase 4: Strategy
        state = self.strategy_agent.run(state)

        # Phase 5: Model prediction
        state = self.model_agent.run(state)

        # Phase 6: Debate & Final Report
        state = self.debate_agent.run(state)

        logger.info(f"\nAll 10 agents completed. Winner: {state.get('prediction', {}).get('predicted_winner')}")

        return state

    def predict_today(self) -> list[dict]:
        """Run agents for all today's matches."""
        from scrapers.live_data_scraper import LiveDataScraper
        scraper = LiveDataScraper()
        matches = scraper.get_today_matches()

        if not matches:
            tomorrow = scraper.get_tomorrow_matches()
            if tomorrow:
                print(f"\nNo matches today. Tomorrow:")
                for m in tomorrow:
                    print(f"  {m['team1']} vs {m['team2']} at {m.get('time_ist', '19:30')} IST")
            return []

        results = []
        for match in matches:
            result = self.predict_match(
                team1=match["team1"], team2=match["team2"],
                venue=match.get("venue", ""), city=match.get("city", ""),
            )
            results.append(result)

        return results

    def record_result(self, team1: str, team2: str, winner: str):
        """Record a match result for self-learning."""
        from models.calibration import PredictionCalibrator
        from models.form_tracker import FormTracker

        calibrator = PredictionCalibrator()
        tracker = FormTracker()

        calibrator.record_result(team1, team2, winner)
        tracker.record_result(team1, team2, winner)

        report = calibrator.get_calibration_report()
        logger.info(f"Result recorded. Overall accuracy: {report['overall_accuracy']:.1%} "
                     f"({report['total_predictions']} predictions)")

    def get_accuracy_report(self) -> dict:
        """Get prediction accuracy report."""
        from models.calibration import PredictionCalibrator
        calibrator = PredictionCalibrator()
        return calibrator.get_calibration_report()
