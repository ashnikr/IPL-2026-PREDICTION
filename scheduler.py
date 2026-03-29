"""
Automated Pipeline Orchestration — Full IPL Season Engine.

Scheduled jobs:
  - Every 6 hours: refresh data (scrape schedule, squads, news)
  - Every day at 2 PM IST: generate daily match predictions
  - Every 12 hours: update RAG knowledge base
  - Every 30 min during match hours: check for completed matches → auto-train + RL
  - After toss (detected live): send predictions to premium Telegram users
  - After 1st innings: send chase predictions to ultra-premium users
  - Live ball-by-ball: continuous updates for ultra-premium during matches

Uses APScheduler for scheduling.
"""

import sys
sys.path.insert(0, ".")

import os
os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import json
import time
import requests
from pathlib import Path
from datetime import datetime, date, timedelta
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from utils.logger import logger
from config.settings import settings


# ── Telegram Alert Helpers ──────────────────────────────────────────

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
PREMIUM_FILE = Path("data/premium/telegram_users.json")


def _get_premium_users(tier: str = "pro") -> list:
    """Get chat IDs of users with given tier or higher."""
    if not PREMIUM_FILE.exists():
        return []
    users = json.loads(PREMIUM_FILE.read_text())
    tiers = {"free": 0, "pro": 1, "elite": 2, "ultra_premium": 3}
    min_level = tiers.get(tier, 1)
    return [
        cid for cid, data in users.items()
        if tiers.get(data.get("plan", "free"), 0) >= min_level
    ]


def _send_telegram(chat_id: str, text: str):
    """Send a Telegram message to a specific user."""
    if not BOT_TOKEN:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=10,
        )
    except Exception as e:
        logger.warning(f"Telegram send failed for {chat_id}: {e}")


def broadcast_to_tier(text: str, tier: str = "pro"):
    """Send message to all users of a tier or higher."""
    users = _get_premium_users(tier)
    for cid in users:
        _send_telegram(cid, text)
    logger.info(f"Broadcast to {len(users)} {tier}+ users")


# ── Core Jobs ───────────────────────────────────────────────────────

def refresh_data():
    """Refresh live data from web sources."""
    logger.info("=" * 50)
    logger.info("SCHEDULED: Refreshing data...")
    logger.info("=" * 50)

    try:
        from scrapers.live_data_scraper import LiveDataScraper
        scraper = LiveDataScraper()
        data = scraper.collect_all_live_data()
        logger.info(f"Data refreshed: season={data.get('season')}, "
                     f"schedule={len(data.get('schedule', []))} matches")
    except Exception as e:
        logger.error(f"Data refresh failed: {e}")


def daily_predictions():
    """Generate predictions for today's matches."""
    logger.info("=" * 50)
    logger.info(f"SCHEDULED: Daily predictions for {date.today()}")
    logger.info("=" * 50)

    try:
        from models.daily_predictor import DailyPredictor
        predictor = DailyPredictor()
        predictions = predictor.run_daily_pipeline()
        logger.info(f"Generated {len(predictions)} predictions")
    except Exception as e:
        logger.error(f"Daily prediction failed: {e}")


def update_rag_knowledge():
    """Update RAG knowledge base with latest info."""
    logger.info("SCHEDULED: Updating RAG knowledge base...")
    try:
        from rag.pipeline import IPLRAGPipeline
        rag = IPLRAGPipeline()
        rag.ingest_from_scrapers()
        logger.info("RAG knowledge base updated")
    except Exception as e:
        logger.error(f"RAG update failed: {e}")


# ── Match Completion Detection & Auto-Training ──────────────────────

COMPLETED_MATCHES_FILE = settings.data_dir / "rl" / "completed_matches.json"


def _load_completed_ids() -> set:
    if COMPLETED_MATCHES_FILE.exists():
        return set(json.loads(COMPLETED_MATCHES_FILE.read_text()))
    return set()


def _save_completed_ids(ids: set):
    COMPLETED_MATCHES_FILE.parent.mkdir(parents=True, exist_ok=True)
    COMPLETED_MATCHES_FILE.write_text(json.dumps(list(ids)))


def check_completed_matches():
    """
    Check for newly completed matches via CricAPI.
    If a match just completed → auto-train + RL correction.
    """
    logger.info("SCHEDULED: Checking for completed matches...")

    cricapi_key = os.getenv("CRICAPI_KEY", "")
    if not cricapi_key:
        logger.warning("No CRICAPI_KEY set, skipping match completion check")
        return

    try:
        resp = requests.get(
            "https://api.cricapi.com/v1/currentMatches",
            params={"apikey": cricapi_key, "offset": 0},
            timeout=15,
        )
        if not resp.ok:
            logger.warning(f"CricAPI returned {resp.status_code}")
            return

        matches = resp.json().get("data", [])
        completed_ids = _load_completed_ids()
        newly_completed = []

        for match in matches:
            if not match.get("matchStarted") or not match.get("matchEnded"):
                continue
            match_id = match.get("id", "")
            if match_id in completed_ids:
                continue

            # Extract match details
            teams = match.get("teams", [])
            if len(teams) < 2:
                continue

            # Determine winner from status string
            status = match.get("status", "")
            winner = ""
            for team in teams:
                if team.lower() in status.lower() and "won" in status.lower():
                    winner = team
                    break

            if not winner:
                continue

            team1 = teams[0]
            team2 = teams[1]

            logger.info(f"COMPLETED MATCH: {team1} vs {team2} — Winner: {winner}")

            # Auto-train with RL
            try:
                _process_completed_match(team1, team2, winner, match)
            except Exception as e:
                logger.error(f"RL processing failed for {team1} vs {team2}: {e}")

            completed_ids.add(match_id)
            newly_completed.append(f"{team1} vs {team2} — {winner} won")

        _save_completed_ids(completed_ids)

        if newly_completed:
            # Notify admin
            admin_id = os.getenv("ADMIN_CHAT_ID", "")
            if admin_id:
                msg = "🔄 *Auto-Training Complete*\n\n"
                for m in newly_completed:
                    msg += f"✅ {m}\n"
                msg += f"\n🤖 Models retrained with RL correction"
                _send_telegram(admin_id, msg)

            logger.info(f"Processed {len(newly_completed)} newly completed matches")
        else:
            logger.info("No new completed matches found")

    except Exception as e:
        logger.error(f"Match completion check failed: {e}")


def _process_completed_match(team1: str, team2: str, winner: str, match_data: dict):
    """Process a completed match through RL trainer."""
    from models.rl_trainer import RLTrainer

    rl = RLTrainer()

    # Try to load our prediction for this match
    prediction_data = _find_our_prediction(team1, team2)

    match_record = {
        "team1": team1,
        "team2": team2,
        "winner": winner,
        "predicted_winner": prediction_data.get("predicted_winner", ""),
        "confidence": prediction_data.get("confidence", 0.5),
        "model_predictions": prediction_data.get("model_predictions", {}),
        "venue": match_data.get("venue", ""),
        "toss_winner": match_data.get("tossWinner", ""),
        "toss_decision": match_data.get("tossChoice", ""),
    }

    result = rl.process_match_result(match_record)
    logger.info(f"RL Result: correct={result['correct']}, reward={result['reward']:.2f}, "
                f"accuracy={result['rolling_accuracy']:.2%}")
    return result


def _find_our_prediction(team1: str, team2: str) -> dict:
    """Find our prediction for a match from saved predictions."""
    pred_dir = settings.data_dir / "predictions"
    today = date.today().isoformat()

    # Check daily predictions file
    pred_file = pred_dir / f"predictions_{today}.json"
    if pred_file.exists():
        try:
            preds = json.loads(pred_file.read_text())
            for p in preds if isinstance(preds, list) else [preds]:
                t1 = p.get("team1", "").lower()
                t2 = p.get("team2", "").lower()
                if (team1.lower() in t1 or t1 in team1.lower()) and \
                   (team2.lower() in t2 or t2 in team2.lower()):
                    return p
        except Exception:
            pass

    return {}


# ── Toss-Based Predictions (Premium) ───────────────────────────────

def check_toss_and_predict():
    """
    Check if toss has happened for today's match.
    If yes → generate prediction → send to premium users.
    """
    logger.info("SCHEDULED: Checking for toss results...")

    cricapi_key = os.getenv("CRICAPI_KEY", "")
    if not cricapi_key:
        return

    try:
        resp = requests.get(
            "https://api.cricapi.com/v1/currentMatches",
            params={"apikey": cricapi_key, "offset": 0},
            timeout=15,
        )
        if not resp.ok:
            return

        matches = resp.json().get("data", [])
        toss_sent_file = settings.data_dir / "rl" / "toss_sent_today.json"
        toss_sent_file.parent.mkdir(parents=True, exist_ok=True)

        sent_today = set()
        if toss_sent_file.exists():
            try:
                data = json.loads(toss_sent_file.read_text())
                if data.get("date") == date.today().isoformat():
                    sent_today = set(data.get("ids", []))
            except Exception:
                pass

        for match in matches:
            match_id = match.get("id", "")
            if match_id in sent_today:
                continue

            # Match must be started but not ended, and toss must be decided
            toss_winner = match.get("tossWinner", "")
            toss_choice = match.get("tossChoice", "")
            if not toss_winner or match.get("matchEnded"):
                continue

            teams = match.get("teams", [])
            if len(teams) < 2:
                continue

            team1, team2 = teams[0], teams[1]
            venue = match.get("venue", "")

            logger.info(f"TOSS: {team1} vs {team2} — {toss_winner} won toss, chose to {toss_choice}")

            # Generate prediction
            try:
                from models.ensemble_predictor import EnsemblePredictor
                predictor = EnsemblePredictor()
                result = predictor.predict(team1, team2, venue=venue,
                                           toss_winner=toss_winner, toss_decision=toss_choice)

                winner = result.get("predicted_winner", "Unknown")
                p1 = round(result.get("team1_win_prob", 0.5) * 100)
                p2 = 100 - p1
                conf = round(result.get("confidence", 0.5) * 100)

                factors = result.get("key_factors", [])
                factors_text = "\n".join(f"  • {f}" for f in factors[:5])

                msg = f"""🏏 *POST-TOSS PREDICTION*
━━━━━━━━━━━━━━━━━━━━━━
*{team1} vs {team2}*
📍 {venue}

🪙 Toss: *{toss_winner}* won → chose to *{toss_choice}*

🏆 *Predicted Winner: {winner}*

📊 Win Probability:
  {team1}: {p1}% {'█' * (p1 // 10)}
  {team2}: {p2}% {'█' * (p2 // 10)}

🎯 Confidence: {conf}%

📋 Key Factors:
{factors_text}

━━━━━━━━━━━━━━━━━━━━━━
🤖 _AI Prediction by IPL 2026 Bot_"""

                # Send to all PRO+ users
                broadcast_to_tier(msg, tier="pro")

                # Save prediction for later RL comparison
                pred_dir = settings.data_dir / "predictions"
                pred_dir.mkdir(parents=True, exist_ok=True)
                pred_file = pred_dir / f"predictions_{date.today().isoformat()}.json"
                preds = []
                if pred_file.exists():
                    try:
                        preds = json.loads(pred_file.read_text())
                        if not isinstance(preds, list):
                            preds = [preds]
                    except Exception:
                        pass
                preds.append({
                    "team1": team1, "team2": team2,
                    "predicted_winner": winner,
                    "confidence": result.get("confidence", 0.5),
                    "team1_win_prob": result.get("team1_win_prob", 0.5),
                    "model_predictions": result.get("model_predictions", {}),
                    "toss_winner": toss_winner, "toss_choice": toss_choice,
                    "venue": venue, "timestamp": datetime.now().isoformat(),
                })
                pred_file.write_text(json.dumps(preds, indent=2, default=str))

                sent_today.add(match_id)
                logger.info(f"Toss prediction sent for {team1} vs {team2}")

            except Exception as e:
                logger.error(f"Toss prediction failed for {team1} vs {team2}: {e}")

        # Save sent IDs
        toss_sent_file.write_text(json.dumps({
            "date": date.today().isoformat(),
            "ids": list(sent_today),
        }))

    except Exception as e:
        logger.error(f"Toss check failed: {e}")


# ── 1st Innings Prediction (Ultra-Premium) ─────────────────────────

def check_innings_break():
    """
    Detect innings break → generate chase prediction → send to ultra-premium users.
    """
    logger.info("SCHEDULED: Checking for innings break...")

    cricapi_key = os.getenv("CRICAPI_KEY", "")
    if not cricapi_key:
        return

    try:
        resp = requests.get(
            "https://api.cricapi.com/v1/currentMatches",
            params={"apikey": cricapi_key, "offset": 0},
            timeout=15,
        )
        if not resp.ok:
            return

        matches = resp.json().get("data", [])
        innings_sent_file = settings.data_dir / "rl" / "innings_sent_today.json"
        innings_sent_file.parent.mkdir(parents=True, exist_ok=True)

        sent_today = set()
        if innings_sent_file.exists():
            try:
                data = json.loads(innings_sent_file.read_text())
                if data.get("date") == date.today().isoformat():
                    sent_today = set(data.get("ids", []))
            except Exception:
                pass

        for match in matches:
            match_id = match.get("id", "")
            if match_id in sent_today or match.get("matchEnded"):
                continue

            # Check if match is in innings break (score available for 1st innings)
            scores = match.get("score", [])
            if not scores or len(scores) < 1:
                continue

            # First innings must be complete (20 overs or all out)
            first_innings = scores[0]
            overs = first_innings.get("o", 0)
            wickets = first_innings.get("w", 0)
            runs = first_innings.get("r", 0)

            # Innings complete if 20 overs bowled or all out
            innings_complete = (overs >= 19.5 or wickets >= 10) and runs > 0

            # If 2nd innings already started (2+ score entries with runs), skip
            if len(scores) >= 2 and scores[1].get("r", 0) > 30:
                continue

            if not innings_complete:
                continue

            teams = match.get("teams", [])
            if len(teams) < 2:
                continue

            batting_team = first_innings.get("inning", "").replace(" Inning 1", "").strip()
            bowling_team = teams[1] if batting_team == teams[0] else teams[0]
            venue = match.get("venue", "")

            logger.info(f"INNINGS BREAK: {batting_team} scored {runs}/{wickets} in {overs} overs")

            try:
                from models.live_predictor import LivePredictor
                predictor = LivePredictor()
                result = predictor.predict_after_first_innings(
                    batting_team=batting_team,
                    bowling_team=bowling_team,
                    score=runs,
                    wickets=wickets,
                    overs=float(overs),
                    venue=venue,
                )

                winner = result.get("predictions", {}).get("predicted_winner", "Unknown")
                chase_prob = round(result.get("predictions", {}).get("chasing_win_prob", 0.5) * 100)
                defend_prob = 100 - chase_prob
                par = result.get("par_score", "N/A")
                target = result.get("target", runs + 1)

                insights = result.get("insights", [])
                insights_text = "\n".join(f"  💡 {i}" for i in insights[:4])

                msg = f"""📻 *1ST INNINGS PREDICTION*
━━━━━━━━━━━━━━━━━━━━━━
*{batting_team} vs {bowling_team}*
📍 {venue}

🏏 *{batting_team}: {runs}/{wickets} ({overs} ov)*
🎯 Target: *{target}*

📊 Probabilities:
  Defend ({batting_team}): {defend_prob}% {'█' * (defend_prob // 10)}
  Chase ({bowling_team}): {chase_prob}% {'█' * (chase_prob // 10)}

📏 Par Score: {par}
🏆 *Predicted Winner: {winner}*

{insights_text}

━━━━━━━━━━━━━━━━━━━━━━
💎 _Ultra-Premium exclusive — IPL 2026 AI Bot_"""

                # Send to ELITE+ users (ultra_premium and elite)
                broadcast_to_tier(msg, tier="elite")

                sent_today.add(match_id)
                logger.info(f"Innings prediction sent for {batting_team} vs {bowling_team}")

            except Exception as e:
                logger.error(f"Innings prediction failed: {e}")

        innings_sent_file.write_text(json.dumps({
            "date": date.today().isoformat(),
            "ids": list(sent_today),
        }))

    except Exception as e:
        logger.error(f"Innings break check failed: {e}")


# ── Live Ball-by-Ball Updates (Ultra-Premium) ──────────────────────

_last_live_score = {}


def live_ball_by_ball():
    """
    Fetch live score and send updates to ultra-premium users
    every significant event (wicket, boundary, milestone).
    """
    cricapi_key = os.getenv("CRICAPI_KEY", "")
    if not cricapi_key:
        return

    try:
        resp = requests.get(
            "https://api.cricapi.com/v1/currentMatches",
            params={"apikey": cricapi_key, "offset": 0},
            timeout=15,
        )
        if not resp.ok:
            return

        matches = resp.json().get("data", [])

        for match in matches:
            if not match.get("matchStarted") or match.get("matchEnded"):
                continue

            match_id = match.get("id", "")
            scores = match.get("score", [])
            if not scores:
                continue

            current = scores[-1]  # Latest innings
            runs = current.get("r", 0)
            wickets = current.get("w", 0)
            overs = current.get("o", 0)
            inning_name = current.get("inning", "")

            # Build score key
            score_key = f"{match_id}_{runs}_{wickets}_{overs}"
            if score_key == _last_live_score.get(match_id):
                continue  # No change

            prev = _last_live_score.get(match_id, "")
            _last_live_score[match_id] = score_key

            # Determine if this is a significant event
            significant = False
            event_type = ""

            if prev:
                prev_parts = prev.split("_")
                if len(prev_parts) >= 4:
                    prev_wickets = int(prev_parts[2])
                    prev_runs = int(prev_parts[1])

                    if wickets > prev_wickets:
                        significant = True
                        event_type = "🔴 WICKET"
                    elif runs - prev_runs >= 6:
                        significant = True
                        event_type = "💥 BOUNDARY"
                    elif runs in [50, 100, 150, 200, 250] or (runs % 50 < 3 and runs > 0):
                        significant = True
                        event_type = f"🎯 MILESTONE ({runs} runs)"
            else:
                # First update for this match
                significant = True
                event_type = "🏏 MATCH LIVE"

            if not significant:
                # Send update every 2 overs at minimum
                if prev:
                    prev_overs = float(prev.split("_")[3]) if len(prev.split("_")) >= 4 else 0
                    if overs - prev_overs >= 2:
                        significant = True
                        event_type = "📊 SCORE UPDATE"

            if significant:
                teams = match.get("teams", [])
                team_info = inning_name.replace(" Inning 1", "").replace(" Inning 2", "").strip()
                status = match.get("status", "")

                msg = f"""{event_type}
*{teams[0] if teams else ''} vs {teams[1] if len(teams) > 1 else ''}*

🏏 *{team_info}: {runs}/{wickets} ({overs} ov)*
{f'📝 {status}' if status else ''}

_Live update — Ultra-Premium_"""

                broadcast_to_tier(msg, tier="ultra_premium")

    except Exception as e:
        logger.error(f"Live ball-by-ball failed: {e}")


# ── Scheduler ──────────────────────────────────────────────────────

def run_scheduler():
    """Start the automated scheduler with all jobs."""
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
        from apscheduler.triggers.interval import IntervalTrigger

        scheduler = BlockingScheduler()

        # Refresh data every 6 hours
        scheduler.add_job(
            refresh_data,
            IntervalTrigger(hours=6),
            id="refresh_data",
            name="Refresh live data",
        )

        # Daily predictions at 2 PM IST (8:30 UTC)
        scheduler.add_job(
            daily_predictions,
            CronTrigger(hour=8, minute=30),
            id="daily_predictions",
            name="Daily match predictions",
        )

        # Update RAG every 12 hours
        scheduler.add_job(
            update_rag_knowledge,
            IntervalTrigger(hours=12),
            id="update_rag",
            name="Update RAG knowledge",
        )

        # Check for completed matches every 30 min (auto-train + RL)
        scheduler.add_job(
            check_completed_matches,
            IntervalTrigger(minutes=30),
            id="check_completed",
            name="Check completed matches + auto-train",
        )

        # Check for toss every 5 min during match hours (2 PM - 11 PM IST = 8:30 - 17:30 UTC)
        scheduler.add_job(
            check_toss_and_predict,
            IntervalTrigger(minutes=5),
            id="check_toss",
            name="Check toss + predict for premium",
        )

        # Check for innings break every 3 min during match hours
        scheduler.add_job(
            check_innings_break,
            IntervalTrigger(minutes=3),
            id="check_innings",
            name="Check innings break for ultra-premium",
        )

        logger.info("=" * 60)
        logger.info("IPL 2026 SCHEDULER STARTED")
        logger.info("=" * 60)
        for job in scheduler.get_jobs():
            logger.info(f"  ✅ {job.name} ({job.trigger})")

        print("\nScheduler running. Press Ctrl+C to stop.\n")
        scheduler.start()

    except ImportError:
        logger.warning("APScheduler not installed. Running once...")
        refresh_data()
        daily_predictions()
        update_rag_knowledge()
        check_completed_matches()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="IPL Prediction Scheduler")
    parser.add_argument("--once", action="store_true", help="Run pipeline once and exit")
    parser.add_argument("--predict", action="store_true", help="Run daily prediction only")
    parser.add_argument("--refresh", action="store_true", help="Refresh data only")
    parser.add_argument("--check-matches", action="store_true", help="Check completed matches + auto-train")
    parser.add_argument("--toss", action="store_true", help="Check toss and predict")
    parser.add_argument("--innings", action="store_true", help="Check innings break")
    args = parser.parse_args()

    if args.once:
        refresh_data()
        daily_predictions()
        check_completed_matches()
    elif args.predict:
        daily_predictions()
    elif args.refresh:
        refresh_data()
    elif args.check_matches:
        check_completed_matches()
    elif args.toss:
        check_toss_and_predict()
    elif args.innings:
        check_innings_break()
    else:
        run_scheduler()
