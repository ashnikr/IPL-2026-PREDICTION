"""
IPL 2026 Prediction API — Production Ready.

Endpoints:
  GET  /health               - Health check
  POST /predict              - Predict a specific match
  GET  /predict/today        - Predict today's matches
  POST /agents               - Run 10-agent AI system
  POST /dream11              - Generate Dream11 Fantasy XI
  POST /live                 - Mid-match prediction after 1st innings
  GET  /schedule             - Full IPL 2026 schedule
  GET  /squads               - All team squads
  GET  /squads/{team}        - Specific team squad
  GET  /news                 - Latest cricket news
  GET  /news/{team}          - Team-specific news & sentiment
  GET  /form                 - All teams form tracker
  GET  /teams                - List all teams
  GET  /team_strengths       - Bayesian team rankings
  GET  /head_to_head         - H2H stats
  POST /result               - Record match result (self-learning)
  GET  /accuracy             - Prediction accuracy report
"""

import sys
sys.path.insert(0, ".")

from datetime import date
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from utils.logger import logger
from config.settings import settings
from models.ensemble import EnsemblePrediction
from models.daily_predictor import DailyPredictor
from models.bayesian_model import BayesianPredictor
from models.explainability import PredictionExplainer


# ── Pydantic models ──────────────────────────────────────────────────

class MatchPredictionRequest(BaseModel):
    team1: str = Field(..., example="Chennai Super Kings")
    team2: str = Field(..., example="Mumbai Indians")
    venue: Optional[str] = Field(None, example="Wankhede Stadium")
    city: Optional[str] = Field(None, example="Mumbai")
    toss_winner: Optional[str] = None
    toss_decision: Optional[str] = None
    pitch_type: Optional[str] = None
    weather: Optional[dict] = None
    playing_xi_team1: Optional[list[str]] = None
    playing_xi_team2: Optional[list[str]] = None


class MatchResultUpdate(BaseModel):
    team1: str
    team2: str
    winner: str


class PredictionResponse(BaseModel):
    team1: str
    team2: str
    team1_win_prob: float
    team2_win_prob: float
    confidence: float
    predicted_winner: str
    key_factors: list[str]
    model_predictions: dict
    venue: Optional[str] = None
    date: Optional[str] = None


# ── App setup ────────────────────────────────────────────────────────

app = FastAPI(
    title="IPL 2026 AI Prediction API",
    description="10 AI Agents + 8 ML Models + LLM Analysis + Dream11 Fantasy + Live Mid-Match Predictions. Powered by Groq Llama 3.3 70B.",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazy-loaded singletons
_ensemble: EnsemblePrediction | None = None
_daily: DailyPredictor | None = None
_explainer: PredictionExplainer | None = None


def get_ensemble() -> EnsemblePrediction:
    global _ensemble
    if _ensemble is None:
        _ensemble = EnsemblePrediction()
        _ensemble.load_all_models()
    return _ensemble


def get_daily() -> DailyPredictor:
    global _daily
    if _daily is None:
        _daily = DailyPredictor()
    return _daily


def get_explainer() -> PredictionExplainer:
    global _explainer
    if _explainer is None:
        _explainer = PredictionExplainer()
        _explainer.load_model("catboost")
    return _explainer


# ── Endpoints ────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "version": "2.0.0",
        "date": str(date.today()),
        "models_loaded": bool(_ensemble and _ensemble.ml_trainer.models),
    }


@app.post("/predict_match", response_model=PredictionResponse)
def predict_match(req: MatchPredictionRequest):
    """Predict outcome of a specific IPL match."""
    ensemble = get_ensemble()

    pred = ensemble.predict_match(
        team1=req.team1,
        team2=req.team2,
        venue=req.venue,
        city=req.city,
        toss_winner=req.toss_winner,
        toss_decision=req.toss_decision,
        weather=req.weather,
        playing_xi_team1=req.playing_xi_team1,
        playing_xi_team2=req.playing_xi_team2,
    )

    return PredictionResponse(
        team1=pred["team1"],
        team2=pred["team2"],
        team1_win_prob=pred["team1_win_prob"],
        team2_win_prob=pred["team2_win_prob"],
        confidence=pred["confidence"],
        predicted_winner=pred["predicted_winner"],
        key_factors=pred["key_factors"],
        model_predictions=pred["model_predictions"],
        venue=req.venue,
        date=str(date.today()),
    )


@app.get("/predict_today")
def predict_today():
    """Predict all of today's IPL matches automatically."""
    daily = get_daily()
    predictions = daily.run_daily_pipeline()

    return {
        "date": str(date.today()),
        "matches": len(predictions),
        "predictions": predictions,
    }


@app.get("/team_strengths")
def team_strengths():
    """Get Bayesian team strength rankings."""
    ensemble = get_ensemble()
    strengths = ensemble.bayesian.team_strengths

    if not strengths:
        raise HTTPException(404, "No team strengths available")

    ranked = sorted(strengths.items(), key=lambda x: x[1].get("mean_strength", 0), reverse=True)

    return {
        "rankings": [
            {
                "rank": i + 1,
                "team": team,
                "strength": stats.get("mean_strength", 0.5),
                "wins": stats.get("wins", 0),
                "losses": stats.get("losses", 0),
            }
            for i, (team, stats) in enumerate(ranked)
        ]
    }


@app.get("/head_to_head")
def head_to_head(team1: str, team2: str):
    """Get head-to-head record between two teams."""
    try:
        import pandas as pd
        matches = pd.read_csv(settings.processed_data_dir / "matches_processed.csv")

        h2h = matches[
            ((matches["team1"] == team1) & (matches["team2"] == team2)) |
            ((matches["team1"] == team2) & (matches["team2"] == team1))
        ]

        t1_wins = len(h2h[h2h["winner"] == team1])
        t2_wins = len(h2h[h2h["winner"] == team2])
        no_result = len(h2h) - t1_wins - t2_wins

        return {
            "team1": team1,
            "team2": team2,
            "total_matches": len(h2h),
            "team1_wins": t1_wins,
            "team2_wins": t2_wins,
            "no_result": no_result,
            "team1_win_pct": round(t1_wins / len(h2h), 4) if len(h2h) > 0 else 0.5,
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/update_result")
def update_result(req: MatchResultUpdate):
    """Update models with a completed match result."""
    ensemble = get_ensemble()
    ensemble.bayesian.update_with_result(req.team1, req.team2, req.winner)

    return {
        "status": "updated",
        "team1": req.team1,
        "team2": req.team2,
        "winner": req.winner,
    }


@app.get("/explain/{team1}/{team2}")
def explain_prediction(team1: str, team2: str):
    """Get detailed SHAP explanation for a prediction."""
    ensemble = get_ensemble()
    explainer = get_explainer()

    # Build minimal features
    features = ensemble._build_minimal_features(team1, team2, None, None, None, None)
    if features is None:
        raise HTTPException(400, "Could not build features")

    explanation = explainer.explain_prediction(features, team1, team2)
    return explanation


@app.get("/teams")
def list_teams():
    """List all current IPL teams."""
    return {"teams": settings.current_teams}


# ── NEW: Dream11 Fantasy Team ─────────────────────────────────────────

class Dream11Request(BaseModel):
    team1: str = Field(..., example="Royal Challengers Bengaluru")
    team2: str = Field(..., example="Sunrisers Hyderabad")
    contest_type: str = Field(default="mega", example="mega")
    playing_xi_team1: Optional[list[str]] = None
    playing_xi_team2: Optional[list[str]] = None


@app.post("/dream11")
def dream11_team(req: Dream11Request):
    """Generate Dream11 Fantasy XI — only picks from actual Playing XI."""
    from models.fantasy_team import FantasyTeamGenerator
    gen = FantasyTeamGenerator()
    result = gen.generate_team(
        req.team1, req.team2,
        contest_type=req.contest_type,
        playing_xi_team1=req.playing_xi_team1,
        playing_xi_team2=req.playing_xi_team2,
    )
    return result


@app.get("/playing_xi/{team1}/{team2}")
def get_playing_xi(team1: str, team2: str):
    """Auto-fetch Playing XI from Cricbuzz/ESPN/CricAPI."""
    from scrapers.playing_xi_scraper import fetch_playing_xi
    result = fetch_playing_xi(team1, team2)
    return result


# ── NEW: Live Mid-Match Prediction ────────────────────────────────────

class LiveRequest(BaseModel):
    batting_team: str = Field(..., example="Royal Challengers Bengaluru")
    bowling_team: str = Field(..., example="Sunrisers Hyderabad")
    score: int = Field(..., example=185)
    wickets: int = Field(..., example=4)
    overs: float = Field(default=20.0, example=20.0)
    venue: Optional[str] = None


@app.post("/live")
def live_prediction(req: LiveRequest):
    """Predict match outcome after 1st innings."""
    from models.live_predictor import LiveMatchPredictor
    predictor = LiveMatchPredictor()
    result = predictor.predict_after_first_innings(
        batting_team=req.batting_team,
        bowling_team=req.bowling_team,
        score=req.score,
        wickets=req.wickets,
        overs=req.overs,
        venue=req.venue or "",
    )
    return result


# ── NEW: 10-Agent AI System ───────────────────────────────────────────

class AgentRequest(BaseModel):
    team1: str = Field(..., example="Royal Challengers Bengaluru")
    team2: str = Field(..., example="Sunrisers Hyderabad")
    venue: Optional[str] = ""


@app.post("/agents")
def run_agents(req: AgentRequest):
    """Run the 10-agent AI system with LLM for a match."""
    from agents.advanced_agents import AdvancedIPLAgentSystem
    system = AdvancedIPLAgentSystem()
    result = system.predict_match(req.team1, req.team2, venue=req.venue or "")
    pred = result.get("prediction", {})
    return {
        "team1": req.team1,
        "team2": req.team2,
        "predicted_winner": pred.get("predicted_winner"),
        "team1_win_prob": pred.get("team1_win_prob"),
        "team2_win_prob": pred.get("team2_win_prob"),
        "confidence": pred.get("confidence"),
        "explanation": result.get("explanation", ""),
        "llm_analysis": result.get("llm_analysis", ""),
        "debate": result.get("debate", ""),
    }


# ── NEW: Schedule & Squads ────────────────────────────────────────────

@app.get("/schedule")
def get_schedule():
    """Get full IPL 2026 schedule."""
    from scrapers.live_data_scraper import LiveDataScraper
    scraper = LiveDataScraper()
    return {"schedule": scraper.get_current_schedule(), "total_matches": len(scraper.get_current_schedule())}


@app.get("/squads")
def get_all_squads():
    """Get all team squads."""
    from scrapers.live_data_scraper import LiveDataScraper
    scraper = LiveDataScraper()
    return scraper.get_team_squads()


@app.get("/squads/{team}")
def get_team_squad(team: str):
    """Get a specific team's squad."""
    from scrapers.live_data_scraper import LiveDataScraper
    scraper = LiveDataScraper()
    squads = scraper.get_team_squads()
    if team not in squads:
        raise HTTPException(404, f"Team not found: {team}")
    return {team: squads[team]}


# ── NEW: News & Sentiment ─────────────────────────────────────────────

@app.get("/news")
def get_news():
    """Get latest cricket news."""
    from scrapers.news_scraper import CricketNewsScraper
    scraper = CricketNewsScraper()
    return {"articles": scraper.get_latest_news()}


@app.get("/news/{team}")
def get_team_news(team: str):
    """Get team-specific news and sentiment analysis."""
    from scrapers.news_scraper import CricketNewsScraper
    scraper = CricketNewsScraper()
    news = scraper.get_team_news(team)
    sentiment = scraper.analyze_sentiment(team, news)
    return {"news": news, "sentiment": sentiment}


# ── NEW: Form Tracker ─────────────────────────────────────────────────

@app.get("/form")
def get_all_form():
    """Get all teams form and momentum."""
    from models.form_tracker import FormTracker
    tracker = FormTracker()
    return {team: tracker.get_team_form(team) for team in settings.current_teams}


@app.get("/form/{team}")
def get_team_form(team: str):
    """Get a specific team's form and key players."""
    from models.form_tracker import FormTracker
    tracker = FormTracker()
    return {
        "form": tracker.get_team_form(team),
        "key_players": tracker.get_key_players_form(team),
    }


# ── NEW: Self-Learning ────────────────────────────────────────────────

@app.post("/result")
def record_result(req: MatchResultUpdate):
    """Record match result for self-learning calibration."""
    from agents.advanced_agents import AdvancedIPLAgentSystem
    system = AdvancedIPLAgentSystem()
    system.record_result(req.team1, req.team2, req.winner)
    report = system.get_accuracy_report()
    return {"status": "recorded", "winner": req.winner, "accuracy_report": report}


@app.get("/accuracy")
def get_accuracy():
    """Get prediction accuracy report."""
    from models.calibration import PredictionCalibrator
    return PredictionCalibrator().get_calibration_report()


# ── Premium & Monetization ───────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str
    name: str = ""


class UpgradeRequest(BaseModel):
    email: str
    plan: str = Field(..., example="pro")
    payment_id: str = ""


@app.get("/plans")
def get_plans():
    """Get all subscription plans and pricing."""
    from api.premium import PLANS
    return {"plans": PLANS}


@app.post("/register")
def register(req: RegisterRequest):
    """Register a new free user."""
    from api.premium import register_user
    user = register_user(req.email, req.name)
    return {"status": "registered", "user": user}


@app.post("/upgrade")
def upgrade(req: UpgradeRequest):
    """Upgrade user to a paid plan."""
    from api.premium import upgrade_user, PLANS
    if req.plan not in PLANS:
        raise HTTPException(400, f"Invalid plan. Choose from: {list(PLANS.keys())}")
    user = upgrade_user(req.email, req.plan, req.payment_id)
    return {"status": "upgraded", "user": user}


@app.get("/affiliates")
def get_affiliates():
    """Get fantasy cricket affiliate links."""
    from api.premium import AFFILIATE_LINKS, get_affiliate_banner
    return {"platforms": AFFILIATE_LINKS}


@app.get("/affiliates/{team1}/{team2}")
def get_match_affiliates(team1: str, team2: str):
    """Get contextual affiliate recommendations for a match."""
    from api.premium import get_affiliate_banner
    return get_affiliate_banner(team1, team2)


@app.get("/revenue_estimate")
def revenue_estimate():
    """Estimate monthly revenue from all streams."""
    from api.premium import estimate_monthly_revenue
    return estimate_monthly_revenue()


class PaymentRequest(BaseModel):
    email: str
    plan: str = Field(..., example="pro")
    txn_id: str = ""
    telegram_username: str = ""


@app.post("/payment/submit")
def submit_payment(req: PaymentRequest):
    """Submit payment details for verification."""
    from api.premium import PLANS
    import json
    from pathlib import Path
    from datetime import datetime

    if req.plan not in PLANS:
        raise HTTPException(400, f"Invalid plan. Choose from: {list(PLANS.keys())}")

    # Save payment for admin review
    payments_file = Path("data/premium/pending_payments.json")
    payments_file.parent.mkdir(parents=True, exist_ok=True)

    pending = []
    if payments_file.exists():
        try:
            pending = json.loads(payments_file.read_text())
        except Exception:
            pass

    pending.append({
        "email": req.email,
        "plan": req.plan,
        "amount": PLANS[req.plan]["price_inr"],
        "txn_id": req.txn_id,
        "telegram_username": req.telegram_username,
        "submitted_at": datetime.now().isoformat(),
        "status": "pending",
    })
    payments_file.write_text(json.dumps(pending, indent=2))

    return {
        "status": "submitted",
        "message": f"Payment for {PLANS[req.plan]['name']} (₹{PLANS[req.plan]['price_inr']}) submitted. Will be activated within 5-10 minutes.",
        "plan": req.plan,
        "amount": PLANS[req.plan]["price_inr"],
    }


@app.get("/payment/pending")
def get_pending_payments():
    """Get pending payments (admin only)."""
    import json
    from pathlib import Path

    payments_file = Path("data/premium/pending_payments.json")
    if not payments_file.exists():
        return {"pending": []}
    try:
        return {"pending": json.loads(payments_file.read_text())}
    except Exception:
        return {"pending": []}


@app.get("/upi_info")
def get_upi_info():
    """Get UPI payment details for frontend."""
    return {
        "upi_id": "nikhil.rajak2106@oksbi",
        "name": "IPL2026 AI Predictions",
        "plans": {
            "pro": {"amount": 199, "name": "Pro"},
            "elite": {"amount": 499, "name": "Elite"},
            "ultra_premium": {"amount": 999, "name": "Ultra Premium"},
        },
    }


# ── Run ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.app:app", host="0.0.0.0", port=8000, reload=True)
