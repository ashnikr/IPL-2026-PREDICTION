"""
Agentic AI System for IPL Match Prediction - Enhanced with LLM.

Autonomous agents that collaborate to generate predictions:
  - DataAgent: Collects live match data, schedule, squads
  - PlayerAnalysisAgent: Analyzes player form, impact player candidates
  - PitchAnalysisAgent: Analyzes venue conditions, historical stats
  - WeatherAgent: Fetches live weather, dew/rain analysis
  - TossAgent: Predicts toss outcome and its impact
  - ModelAgent: Runs all 8 prediction models + impact/DLS adjustments
  - ExplanationAgent: LLM-powered natural language explanation

Uses LangGraph for orchestration, falls back to sequential pipeline.
Optionally uses OpenAI/LLM for rich natural language insights.
"""

import json
from datetime import date, datetime
from typing import Any

from utils.logger import logger
from config.settings import settings

try:
    from langgraph.graph import StateGraph, END
    HAS_LANGGRAPH = True
except ImportError:
    HAS_LANGGRAPH = False
    logger.info("LangGraph not installed. Using pipeline-based agent system.")

try:
    import openai
    HAS_OPENAI = bool(settings.openai_api_key)
    if HAS_OPENAI:
        openai.api_key = settings.openai_api_key
except ImportError:
    HAS_OPENAI = False


# ── Agent State ──────────────────────────────────────────────────────

class MatchState(dict):
    """State passed between agents."""
    pass


# ── Individual Agents ────────────────────────────────────────────────

class DataAgent:
    """Collects live match data from web sources."""

    def run(self, state: dict) -> dict:
        logger.info("[DataAgent] Collecting match data...")
        from scrapers.live_data_scraper import LiveDataScraper

        scraper = LiveDataScraper()

        # Get full match info if teams specified
        team1 = state.get("team1", "")
        team2 = state.get("team2", "")

        if team1 and team2:
            match_info = scraper.get_match_info(team1, team2)
            state["match_info"] = match_info
            state["schedule"] = scraper.get_current_schedule()
            state["squads"] = scraper.get_team_squads()

            # Get squad details
            state["team1_xi"] = match_info["team1"]["playing_xi"]
            state["team2_xi"] = match_info["team2"]["playing_xi"]
            state["team1_captain"] = match_info["team1"]["captain"]
            state["team2_captain"] = match_info["team2"]["captain"]

            # Schedule context
            if not state.get("venue"):
                state["venue"] = match_info.get("venue", "")
            if not state.get("city"):
                state["city"] = match_info.get("city", "")
            state["time_ist"] = match_info.get("time_ist", "19:30")
            state["is_double_header"] = match_info.get("is_double_header", False)
            state["match_date"] = match_info.get("date")
        else:
            state["schedule"] = scraper.get_current_schedule()
            state["squads"] = scraper.get_team_squads()

        state["injuries"] = scraper.get_player_injuries()
        state["data_collected"] = True

        logger.info(f"[DataAgent] Done. Venue: {state.get('venue', 'TBD')}, "
                     f"Time: {state.get('time_ist', '?')} IST")
        return state


class PlayerAnalysisAgent:
    """Analyzes player form, squad strength, and impact player candidates."""

    def run(self, state: dict) -> dict:
        logger.info("[PlayerAnalysisAgent] Analyzing player form & impact players...")
        import pandas as pd

        team1 = state.get("team1", "")
        team2 = state.get("team2", "")

        # Player form from historical stats
        try:
            player_stats = pd.read_csv(settings.processed_data_dir / "player_stats.csv")
            t1_xi = state.get("team1_xi", [])
            t2_xi = state.get("team2_xi", [])

            def team_form_score(players):
                if not players:
                    return 0.5
                scores = []
                for p in players:
                    name = p if isinstance(p, str) else p.get("name", "")
                    ps = player_stats[player_stats["player_name"].str.contains(name, case=False, na=False)]
                    if not ps.empty:
                        latest = ps.sort_values("season").iloc[-1]
                        sr = latest.get("strike_rate", 130)
                        avg = latest.get("batting_avg", 25)
                        score = (sr / 200 + avg / 50) / 2
                        scores.append(min(score, 1.0))
                return sum(scores) / len(scores) if scores else 0.5

            state["team1_form_score"] = round(team_form_score(t1_xi), 4)
            state["team2_form_score"] = round(team_form_score(t2_xi), 4)
        except Exception as e:
            logger.warning(f"[PlayerAnalysisAgent] Form analysis: {e}")
            state["team1_form_score"] = 0.5
            state["team2_form_score"] = 0.5

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
            logger.warning(f"[PlayerAnalysisAgent] Impact analysis: {e}")

        state["player_analysis_done"] = True
        logger.info(f"[PlayerAnalysisAgent] Form: {team1}={state.get('team1_form_score', '?')}, "
                     f"{team2}={state.get('team2_form_score', '?')}")
        return state


class PitchAnalysisAgent:
    """Analyzes venue and pitch conditions with detailed stats."""

    def run(self, state: dict) -> dict:
        logger.info("[PitchAnalysisAgent] Analyzing pitch conditions...")
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

                # Chase analysis
                chase_wins = 0
                decided = 0
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
                t1_venue_wins = len(t1_vm[t1_vm["winner"] == team1]) if not t1_vm.empty else 0
                t2_venue_wins = len(t2_vm[t2_vm["winner"] == team2]) if not t2_vm.empty else 0

                # Pitch type classification
                avg_sc = float(avg_score) if pd.notna(avg_score) else 165
                if avg_sc > 175:
                    pitch_type = "Batting-friendly (high-scoring)"
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
                    "team1_venue_record": f"{t1_venue_wins}/{len(t1_vm)}",
                    "team2_venue_record": f"{t2_venue_wins}/{len(t2_vm)}",
                    "team1_venue_win_pct": round(t1_venue_wins / len(t1_vm), 3) if len(t1_vm) > 0 else 0.5,
                    "team2_venue_win_pct": round(t2_venue_wins / len(t2_vm), 3) if len(t2_vm) > 0 else 0.5,
                }
            else:
                state["venue_stats"] = self._default_stats()
        except Exception as e:
            logger.warning(f"[PitchAnalysisAgent] Error: {e}")
            state["venue_stats"] = self._default_stats()

        state["pitch_analysis_done"] = True
        logger.info(f"[PitchAnalysisAgent] Venue: {venue}, "
                     f"Avg score: {state['venue_stats']['avg_first_innings_score']}")
        return state

    def _default_stats(self):
        return {
            "total_matches": 0, "avg_first_innings_score": 165,
            "chase_win_pct": 0.5, "pitch_type": "Unknown",
            "team1_venue_record": "0/0", "team2_venue_record": "0/0",
        }


class WeatherAgent:
    """Fetches live weather data and analyzes conditions."""

    def run(self, state: dict) -> dict:
        logger.info("[WeatherAgent] Fetching weather data...")
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
            state["rain_analysis"] = dls.estimate_rain_impact(rain_prob, state["weather"])
        except Exception:
            state["rain_analysis"] = {"rain_risk": "low"}

        state["weather_done"] = True
        w = state["weather"]
        logger.info(f"[WeatherAgent] {city}: {w.get('condition', 'N/A')}, "
                     f"Temp: {w.get('temperature', '?')}C, "
                     f"Dew: {w.get('dew_probability', 0)*100:.0f}%, "
                     f"Rain: {w.get('rain_probability', 0)*100:.0f}%")
        return state


class TossAgent:
    """Predicts toss outcome and its strategic impact."""

    def run(self, state: dict) -> dict:
        logger.info("[TossAgent] Analyzing toss impact...")

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
            logger.info(f"[TossAgent] Likely decision: {toss_pred['predicted_decision']} "
                         f"({toss_pred['confidence']*100:.0f}% conf)")
        except Exception as e:
            logger.warning(f"[TossAgent] Error: {e}")
            state["toss_prediction"] = {"predicted_decision": "field", "confidence": 0.5}

        state["toss_done"] = True
        return state


class ModelAgent:
    """Runs all prediction models with full adjustments."""

    def run(self, state: dict) -> dict:
        logger.info("[ModelAgent] Running ensemble prediction models...")
        from models.ensemble import EnsemblePrediction

        ensemble = EnsemblePrediction()
        pred = ensemble.predict_match(
            team1=state.get("team1", ""),
            team2=state.get("team2", ""),
            venue=state.get("venue"),
            city=state.get("city"),
            toss_winner=state.get("toss_winner"),
            toss_decision=state.get("toss_decision"),
            weather=state.get("weather"),
        )

        # Apply impact player adjustment
        impact = state.get("impact_analysis", {})
        if impact and impact.get("net_shift", 0) != 0:
            import numpy as np
            pred["team1_win_prob"] = round(
                float(np.clip(pred["team1_win_prob"] + impact["net_shift"], 0.02, 0.98)), 4
            )
            pred["team2_win_prob"] = round(1 - pred["team1_win_prob"], 4)

        # Apply rain adjustment
        rain = state.get("rain_analysis", {})
        if rain.get("prediction_adjustment", 0) != 0:
            import numpy as np
            pred["team1_win_prob"] = round(
                float(np.clip(pred["team1_win_prob"] + rain["prediction_adjustment"], 0.02, 0.98)), 4
            )
            pred["team2_win_prob"] = round(1 - pred["team1_win_prob"], 4)

        pred["predicted_winner"] = state["team1"] if pred["team1_win_prob"] > 0.5 else state["team2"]

        state["prediction"] = pred
        state["model_done"] = True

        logger.info(f"[ModelAgent] {pred['team1']}: {pred['team1_win_prob']:.1%} | "
                     f"{pred['team2']}: {pred['team2_win_prob']:.1%}")
        return state


class ExplanationAgent:
    """Generates rich, human-readable match predictions.
    Uses OpenAI LLM if available, otherwise generates structured analysis."""

    def run(self, state: dict) -> dict:
        logger.info("[ExplanationAgent] Generating match analysis...")

        if HAS_OPENAI:
            return self._llm_explanation(state)
        return self._structured_explanation(state)

    def _llm_explanation(self, state: dict) -> dict:
        """Generate LLM-powered natural language explanation."""
        pred = state.get("prediction", {})
        t1, t2 = state.get("team1", "?"), state.get("team2", "?")

        # Build context for LLM
        context = {
            "match": f"{t1} vs {t2}",
            "venue": state.get("venue", "TBD"),
            "date": state.get("match_date", str(date.today())),
            "time": state.get("time_ist", "19:30 IST"),
            "prediction": {
                "team1_prob": pred.get("team1_win_prob", 0.5),
                "team2_prob": pred.get("team2_win_prob", 0.5),
                "winner": pred.get("predicted_winner"),
                "confidence": pred.get("confidence"),
            },
            "venue_stats": state.get("venue_stats", {}),
            "weather": state.get("weather", {}),
            "toss": state.get("toss_prediction", {}),
            "rain": state.get("rain_analysis", {}),
            "impact_player": state.get("impact_analysis", {}),
            "team1_captain": state.get("team1_captain", "?"),
            "team2_captain": state.get("team2_captain", "?"),
            "team1_form": state.get("team1_form_score", 0.5),
            "team2_form": state.get("team2_form_score", 0.5),
            "key_factors": pred.get("key_factors", []),
        }

        prompt = f"""You are an expert IPL cricket analyst. Generate a detailed match prediction report.

Match Data:
{json.dumps(context, indent=2, default=str)}

Write a detailed, engaging prediction analysis (300-400 words) covering:
1. Match overview and context
2. Key matchups and team strengths
3. Venue and conditions analysis
4. Weather and dew factor
5. Toss strategy recommendation
6. Impact player considerations
7. Final prediction with reasoning

Keep it conversational but data-driven. Use specific numbers from the data."""

        try:
            client = openai.OpenAI(api_key=settings.openai_api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert IPL cricket analyst providing match predictions."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=800,
                temperature=0.7,
            )
            explanation = response.choices[0].message.content
            state["explanation"] = explanation
            state["explanation_source"] = "llm"
        except Exception as e:
            logger.warning(f"[ExplanationAgent] LLM failed: {e}. Using structured explanation.")
            return self._structured_explanation(state)

        state["explanation_done"] = True
        return state

    def _structured_explanation(self, state: dict) -> dict:
        """Generate structured explanation without LLM."""
        pred = state.get("prediction", {})
        t1, t2 = state.get("team1", "?"), state.get("team2", "?")
        p1 = pred.get("team1_win_prob", 0.5)
        winner = pred.get("predicted_winner", t1 if p1 > 0.5 else t2)
        win_pct = max(p1, 1 - p1) * 100
        conf = pred.get("confidence", 0) * 100

        lines = [
            "=" * 60,
            f"  MATCH PREDICTION REPORT",
            "=" * 60,
            f"",
            f"  {t1} vs {t2}",
            f"  Date: {state.get('match_date', 'TBD')} | Time: {state.get('time_ist', '19:30')} IST",
            f"  Venue: {state.get('venue', 'TBD')}",
        ]

        if state.get("is_double_header"):
            lines.append(f"  ** DOUBLE HEADER DAY **")

        lines.extend([
            f"",
            f"  Captains: {state.get('team1_captain', '?')} vs {state.get('team2_captain', '?')}",
            "-" * 60,
            f"",
            f"  PREDICTION: {winner} ({win_pct:.1f}%) | Confidence: {conf:.0f}%",
            f"  {t1}: {p1*100:.1f}%  |  {t2}: {(1-p1)*100:.1f}%",
            "",
        ])

        # Venue analysis
        vs = state.get("venue_stats", {})
        if vs.get("total_matches", 0) > 0:
            lines.extend([
                f"  VENUE ANALYSIS:",
                f"    Matches played: {vs['total_matches']}",
                f"    Avg 1st innings: {vs['avg_first_innings_score']}",
                f"    Chase success: {vs['chase_win_pct']*100:.0f}%",
                f"    Pitch type: {vs.get('pitch_type', 'Unknown')}",
                f"    {t1} record: {vs.get('team1_venue_record', 'N/A')}",
                f"    {t2} record: {vs.get('team2_venue_record', 'N/A')}",
                "",
            ])

        # Weather
        weather = state.get("weather", {})
        if weather:
            lines.extend([
                f"  WEATHER:",
                f"    Condition: {weather.get('condition', 'N/A')}",
                f"    Temperature: {weather.get('temperature', '?')}C",
                f"    Humidity: {weather.get('humidity', '?')}%",
                f"    Dew: {weather.get('dew_probability', 0)*100:.0f}%",
                f"    Rain: {weather.get('rain_probability', 0)*100:.0f}%",
                "",
            ])

        # Rain
        rain = state.get("rain_analysis", {})
        if rain.get("rain_risk") in ("moderate", "high", "very_high"):
            lines.extend([
                f"  RAIN ALERT: {rain.get('description', '')}",
                f"    Expected overs: ~{rain.get('expected_overs', 20)}",
                "",
            ])

        # Toss
        toss = state.get("toss_prediction", {})
        if toss:
            lines.extend([
                f"  TOSS STRATEGY:",
                f"    Likely decision: {toss.get('predicted_decision', '?').upper()}",
                f"    Confidence: {toss.get('confidence', 0)*100:.0f}%",
            ])
            for f in toss.get("factors", []):
                lines.append(f"    - {f}")
            lines.append("")

        # Impact player
        impact = state.get("impact_analysis", {})
        if impact and impact.get("scenarios"):
            lines.append(f"  IMPACT PLAYER:")
            for s in impact["scenarios"][:3]:
                lines.append(f"    - {s}")
            lines.append("")

        # Form
        f1 = state.get("team1_form_score", 0.5)
        f2 = state.get("team2_form_score", 0.5)
        lines.extend([
            f"  TEAM FORM: {t1}={f1:.3f} | {t2}={f2:.3f}",
            "",
        ])

        # Model breakdown
        model_preds = pred.get("model_predictions", {})
        if model_preds:
            lines.append(f"  MODEL BREAKDOWN:")
            for model, prob in sorted(model_preds.items(), key=lambda x: x[1], reverse=True):
                favors = t1 if prob > 0.5 else t2
                lines.append(f"    {model:25s}  {prob*100:5.1f}% ({favors})")
            lines.append("")

        # Key factors
        factors = pred.get("key_factors", [])
        if factors:
            lines.append(f"  KEY FACTORS:")
            for f in factors[:8]:
                lines.append(f"    - {f}")

        lines.extend(["", "=" * 60])

        explanation = "\n".join(lines)
        state["explanation"] = explanation
        state["explanation_source"] = "structured"
        state["explanation_done"] = True

        return state


# ── Agent Orchestration ──────────────────────────────────────────────

class IPLAgentSystem:
    """Orchestrate all 7 agents for comprehensive match prediction."""

    def __init__(self):
        self.data_agent = DataAgent()
        self.player_agent = PlayerAnalysisAgent()
        self.pitch_agent = PitchAnalysisAgent()
        self.weather_agent = WeatherAgent()
        self.toss_agent = TossAgent()
        self.model_agent = ModelAgent()
        self.explanation_agent = ExplanationAgent()

    def predict_match(
        self,
        team1: str,
        team2: str,
        venue: str = "",
        city: str = "",
        toss_winner: str = None,
        toss_decision: str = None,
    ) -> dict:
        """Run all agents to predict a match."""
        if HAS_LANGGRAPH:
            return self._run_langgraph(team1, team2, venue, city, toss_winner, toss_decision)
        return self._run_pipeline(team1, team2, venue, city, toss_winner, toss_decision)

    def _run_langgraph(self, team1, team2, venue, city, toss_winner, toss_decision) -> dict:
        """Run agents using LangGraph state machine."""
        logger.info("Running LangGraph agent pipeline (7 agents)...")

        workflow = StateGraph(dict)

        workflow.add_node("data", lambda s: self.data_agent.run(s))
        workflow.add_node("player_analysis", lambda s: self.player_agent.run(s))
        workflow.add_node("pitch_analysis", lambda s: self.pitch_agent.run(s))
        workflow.add_node("weather", lambda s: self.weather_agent.run(s))
        workflow.add_node("toss", lambda s: self.toss_agent.run(s))
        workflow.add_node("model", lambda s: self.model_agent.run(s))
        workflow.add_node("explanation", lambda s: self.explanation_agent.run(s))

        workflow.set_entry_point("data")
        workflow.add_edge("data", "player_analysis")
        workflow.add_edge("data", "pitch_analysis")
        workflow.add_edge("data", "weather")
        workflow.add_edge("weather", "toss")
        workflow.add_edge("player_analysis", "model")
        workflow.add_edge("pitch_analysis", "model")
        workflow.add_edge("toss", "model")
        workflow.add_edge("model", "explanation")
        workflow.add_edge("explanation", END)

        graph = workflow.compile()

        initial_state = {
            "team1": team1, "team2": team2,
            "venue": venue, "city": city,
            "toss_winner": toss_winner, "toss_decision": toss_decision,
        }

        return graph.invoke(initial_state)

    def _run_pipeline(self, team1, team2, venue, city, toss_winner, toss_decision) -> dict:
        """Run agents as sequential pipeline (fallback)."""
        logger.info("Running sequential agent pipeline (7 agents)...")

        state = {
            "team1": team1, "team2": team2,
            "venue": venue, "city": city,
            "toss_winner": toss_winner, "toss_decision": toss_decision,
        }

        state = self.data_agent.run(state)
        state = self.player_agent.run(state)
        state = self.pitch_agent.run(state)
        state = self.weather_agent.run(state)
        state = self.toss_agent.run(state)
        state = self.model_agent.run(state)
        state = self.explanation_agent.run(state)

        return state

    def predict_today(self) -> list[dict]:
        """Run agents for all today's matches."""
        from scrapers.live_data_scraper import LiveDataScraper
        scraper = LiveDataScraper()
        today_matches = scraper.get_today_matches()

        if not today_matches:
            tomorrow = scraper.get_tomorrow_matches()
            if tomorrow:
                print(f"\nNo matches today. Tomorrow ({tomorrow[0].get('date', '?')}):")
                for m in tomorrow:
                    print(f"  {m['team1']} vs {m['team2']} at {m.get('time_ist', '19:30')} IST")
            return []

        results = []
        for match in today_matches:
            result = self.predict_match(
                team1=match["team1"], team2=match["team2"],
                venue=match.get("venue", ""), city=match.get("city", ""),
            )
            results.append(result)

        return results
