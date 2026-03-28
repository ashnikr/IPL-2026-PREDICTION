"""
IPL 2026 Prediction Telegram Bot — Monetization Engine.

Commands:
  /start        - Welcome + plan info
  /predict CSK MI  - Quick match prediction (FREE: 5/day)
  /dream11 CSK MI  - Dream11 Fantasy XI (PRO only)
  /live CSK MI 185 4  - Live mid-match prediction (PRO only)
  /agents CSK MI  - 10 AI Agents analysis (PRO only)
  /form         - All teams form
  /news         - Latest cricket news
  /subscribe    - Upgrade to Pro/Elite
  /my_plan      - Check your subscription

Setup:
  1. Create bot via @BotFather on Telegram → get BOT_TOKEN
  2. Add BOT_TOKEN to .env
  3. Run: python bot/telegram_bot.py
"""

import os
import sys
import asyncio
import logging
import requests
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, ".")
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("IPLBot")

API_BASE = os.getenv("API_URL", "https://ipl-2026-prediction-pxdp.onrender.com")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")  # Your Telegram chat ID

# ── Premium User Management ─────────────────────────────────────────
import json

PREMIUM_FILE = Path(__file__).resolve().parent.parent / "data" / "premium" / "telegram_users.json"
PREMIUM_FILE.parent.mkdir(parents=True, exist_ok=True)

FREE_DAILY_LIMIT = 0  # Free users get ZERO predictions — must pay
PREMIUM_COMMANDS = {"/predict", "/dream11", "/fantasy", "/live", "/agents"}  # ALL locked

def _load_premium_users():
    if PREMIUM_FILE.exists():
        return json.loads(PREMIUM_FILE.read_text())
    return {}

def _save_premium_users(data):
    PREMIUM_FILE.write_text(json.dumps(data, indent=2))

def is_premium(chat_id: str) -> bool:
    """Check if user has paid subscription."""
    users = _load_premium_users()
    user = users.get(str(chat_id), {})
    return user.get("plan", "free") in ("pro", "elite")

def get_user_plan(chat_id: str) -> str:
    users = _load_premium_users()
    return users.get(str(chat_id), {}).get("plan", "free")

def check_free_limit(chat_id: str) -> bool:
    """Check if free user has remaining daily predictions."""
    from datetime import date
    users = _load_premium_users()
    user = users.get(str(chat_id), {"usage": {}, "plan": "free"})
    if user.get("plan") in ("pro", "elite"):
        return True  # no limit for paid
    today = date.today().isoformat()
    daily_usage = user.get("usage", {}).get(today, 0)
    return daily_usage < FREE_DAILY_LIMIT

def track_free_usage(chat_id: str):
    """Increment daily usage for free user."""
    from datetime import date
    users = _load_premium_users()
    cid = str(chat_id)
    if cid not in users:
        users[cid] = {"plan": "free", "usage": {}}
    today = date.today().isoformat()
    if "usage" not in users[cid]:
        users[cid]["usage"] = {}
    users[cid]["usage"][today] = users[cid]["usage"].get(today, 0) + 1
    _save_premium_users(users)

def activate_premium(chat_id: str, plan: str = "pro"):
    """Activate premium for a user (called by admin)."""
    users = _load_premium_users()
    cid = str(chat_id)
    if cid not in users:
        users[cid] = {"usage": {}}
    users[cid]["plan"] = plan
    users[cid]["activated"] = __import__("datetime").datetime.now().isoformat()
    _save_premium_users(users)
    return True

PAYWALL_MSG = """🔒 *This is a PRO feature!*

You need a *Pro* or *Elite* subscription to access this.

⭐ *PRO — ₹299/month*
✅ Dream11 Fantasy XI
✅ Live mid-match predictor
✅ 10 AI Agents + LLM

💎 *ELITE — ₹799/month*
✅ Everything in Pro + Alerts

💳 *How to pay:*
1. Pay ₹299 via UPI
2. Send screenshot to @ashnikr
3. Get instant access!

/subscribe for details"""

FREE_LIMIT_MSG = """⚠️ *Daily limit reached!*

Free plan: {used}/{limit} predictions used today.

Upgrade to *Pro* for unlimited predictions!
/subscribe to upgrade."""

# Team name shortcuts
TEAM_SHORTCUTS = {
    "CSK": "Chennai Super Kings",
    "MI": "Mumbai Indians",
    "RCB": "Royal Challengers Bengaluru",
    "KKR": "Kolkata Knight Riders",
    "SRH": "Sunrisers Hyderabad",
    "DC": "Delhi Capitals",
    "GT": "Gujarat Titans",
    "LSG": "Lucknow Super Giants",
    "RR": "Rajasthan Royals",
    "PBKS": "Punjab Kings",
}


def resolve_team(name: str) -> str:
    """Resolve team shortcode to full name."""
    return TEAM_SHORTCUTS.get(name.upper(), name)


def api_get(endpoint: str, params=None):
    try:
        r = requests.get(f"{API_BASE}{endpoint}", params=params, timeout=60)
        return r.json() if r.ok else {"error": r.text}
    except Exception as e:
        return {"error": str(e)}


def api_post(endpoint: str, data: dict):
    try:
        r = requests.post(f"{API_BASE}{endpoint}", json=data, timeout=60)
        return r.json() if r.ok else {"error": r.text}
    except Exception as e:
        return {"error": str(e)}


# ── Bot Handlers ─────────────────────────────────────────────────────

def handle_start():
    return """🏏 *IPL 2026 AI Prediction Bot*
━━━━━━━━━━━━━━━━━━━━━━

🤖 10 AI Agents + 8 ML Models + LLM Analysis
🎯 85%+ Accuracy | Auto Playing XI

*FREE Commands:*
/form — Team form & momentum
/news — Latest cricket news
/teams — All IPL teams
/subscribe — View plans

🔒 *PAID Features (₹299/month):*
/predict CSK MI — AI Match Prediction
/dream11 CSK MI — Dream11 Fantasy XI
/live CSK MI 185 4 — Live Mid-Match
/agents CSK MI — 10 AI Agents + LLM

💳 *Pay ₹299 via UPI → Get instant access!*
Contact @ashnikr to subscribe

/subscribe — Plans & payment info
/my\\_plan — Check your plan"""


def handle_predict(args: list):
    if len(args) < 2:
        return "Usage: /predict CSK MI"
    team1 = resolve_team(args[0])
    team2 = resolve_team(args[1])

    result = api_post("/predict_match", {
        "team1": team1, "team2": team2
    })

    if "error" in result:
        return f"❌ Error: {result['error']}"

    p1 = round(result.get("team1_win_prob", 0) * 100)
    p2 = round(result.get("team2_win_prob", 0) * 100)
    conf = round(result.get("confidence", 0) * 100)
    winner = result.get("predicted_winner", "Unknown")

    factors = result.get("key_factors", [])
    factors_text = "\\n".join(f"  • {f}" for f in factors[:5]) if factors else "  No factors available"

    return f"""🏏 *{team1} vs {team2}*
━━━━━━━━━━━━━━━━━━━━━━

🏆 *Predicted Winner: {winner}*

📊 Win Probability:
  {team1}: {p1}%  {'█' * (p1 // 10)}
  {team2}: {p2}%  {'█' * (p2 // 10)}

🎯 Confidence: {conf}%

📋 Key Factors:
{factors_text}

━━━━━━━━━━━━━━━━━━━━━━
🌟 Want Dream11 XI? Try /dream11 {args[0]} {args[1]}
💰 Upgrade: /subscribe"""


def handle_dream11(args: list):
    if len(args) < 2:
        return "Usage: /dream11 RCB SRH"
    team1 = resolve_team(args[0])
    team2 = resolve_team(args[1])
    contest = args[2] if len(args) > 2 else "mega"

    result = api_post("/dream11", {
        "team1": team1, "team2": team2, "contest_type": contest
    })

    if "error" in result:
        return f"❌ Error: {result['error']}"

    captain = result.get("captain", "TBD")
    vc = result.get("vice_captain", "TBD")
    team = result.get("team", [])
    credits = result.get("total_credits", 0)
    points = result.get("expected_points", 0)

    players_text = ""
    for p in team:
        name = p.get("name", "Unknown")
        role = p.get("role", "")
        cr = p.get("credits", 0)
        tag = " 🏅(C)" if name == captain else (" ⭐(VC)" if name == vc else "")
        players_text += f"  {name}{tag} — {role} ({cr}cr)\\n"

    return f"""⭐ *Dream11 Fantasy XI*
*{team1} vs {team2}*
━━━━━━━━━━━━━━━━━━━━━━

🏅 Captain (2x): *{captain}*
⭐ Vice-Captain (1.5x): *{vc}*

👥 Team ({credits} credits):
{players_text}
📈 Expected Points: {points:.1f}

━━━━━━━━━━━━━━━━━━━━━━
🎰 Use this team on Dream11 & Win!
/predict {args[0]} {args[1]} — Match prediction"""


def handle_live(args: list):
    if len(args) < 4:
        return "Usage: /live CSK MI 185 4\\n(batting\\_team bowling\\_team score wickets)"
    batting = resolve_team(args[0])
    bowling = resolve_team(args[1])
    score = int(args[2])
    wickets = int(args[3])

    result = api_post("/live", {
        "batting_team": batting,
        "bowling_team": bowling,
        "score": score,
        "wickets": wickets,
    })

    if "error" in result:
        return f"❌ Error: {result['error']}"

    winner = result.get("predicted_winner", "Unknown")
    chase = round(result.get("chase_prob", 0) * 100)
    defend = round(result.get("defend_prob", 0) * 100)
    par = result.get("par_score", "N/A")

    return f"""📻 *Live Mid-Match Prediction*
*{batting} {score}/{wickets} (20 ov)*
━━━━━━━━━━━━━━━━━━━━━━

🏆 Predicted Winner: *{winner}*

📊 Probabilities:
  Defend ({batting}): {defend}%
  Chase ({bowling}): {chase}%

📏 Par Score: {par}
📝 Assessment: {result.get('score_assessment', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━━"""


def handle_agents(args: list):
    if len(args) < 2:
        return "Usage: /agents RCB SRH"
    team1 = resolve_team(args[0])
    team2 = resolve_team(args[1])

    result = api_post("/agents", {
        "team1": team1, "team2": team2
    })

    if "error" in result:
        return f"❌ Error: {result['error']}"

    winner = result.get("predicted_winner", "Unknown")
    p1 = round((result.get("team1_win_prob", 0) or 0) * 100)
    p2 = round((result.get("team2_win_prob", 0) or 0) * 100)
    conf = round((result.get("confidence", 0) or 0) * 100)

    text = f"""🤖 *10 AI Agents Analysis*
*{team1} vs {team2}*
━━━━━━━━━━━━━━━━━━━━━━

🏆 Winner: *{winner}*
📊 {team1}: {p1}% | {team2}: {p2}%
🎯 Confidence: {conf}%

"""
    if result.get("explanation"):
        text += f"📋 *Explanation:*\\n{result['explanation'][:500]}\\n\\n"
    if result.get("llm_analysis"):
        text += f"🧠 *LLM Analysis:*\\n{result['llm_analysis'][:500]}"

    return text


def handle_form():
    result = api_get("/form")
    if "error" in result:
        return f"❌ Error: {result['error']}"

    text = "📊 *Team Form & Momentum*\\n━━━━━━━━━━━━━━━━━━━━━━\\n\\n"
    teams = sorted(result.items(), key=lambda x: x[1].get("rating", 0) if isinstance(x[1], dict) else 0, reverse=True)
    for i, (team, info) in enumerate(teams):
        if not isinstance(info, dict):
            continue
        rating = round((info.get("rating", 0)) * 100, 1)
        momentum = info.get("momentum", "Stable")
        emoji = "🟢" if momentum == "Rising" else ("🔴" if momentum == "Falling" else "🟡")
        text += f"{i+1}. {team} — {rating} {emoji}\\n"

    return text


def handle_news():
    result = api_get("/news")
    if "error" in result:
        return f"❌ Error: {result['error']}"

    articles = result.get("articles", [])[:5]
    text = "📰 *Latest Cricket News*\\n━━━━━━━━━━━━━━━━━━━━━━\\n\\n"
    for a in articles:
        text += f"• {a.get('title', 'No title')}\\n  _{a.get('source', 'Unknown')}_\\n\\n"

    return text if articles else "No news available right now."


def handle_subscribe():
    return """💎 *Upgrade Your Plan*
━━━━━━━━━━━━━━━━━━━━━━

🆓 *FREE* — 5 predictions/day
  Basic match predictor, schedule, news

⭐ *PRO — ₹299/month ($3.99)*
  ✅ Unlimited predictions
  ✅ Dream11 Fantasy XI
  ✅ Live mid-match predictor
  ✅ 10 AI Agents + LLM analysis
  ✅ News & sentiment tracker

💎 *ELITE — ₹799/month ($9.99)*
  ✅ Everything in Pro
  ✅ Telegram match alerts
  ✅ Priority API access
  ✅ Accuracy reports
  ✅ Early predictions

🔗 *Subscribe now:*
Contact @ashnikr to upgrade your plan!

💳 Payment: UPI / Razorpay / PayPal"""


def handle_teams():
    result = api_get("/teams")
    teams = result.get("teams", [])
    shortcuts = "\\n".join(f"  {v} → {k}" for k, v in sorted(TEAM_SHORTCUTS.items(), key=lambda x: x[1]))
    return f"""🏏 *IPL 2026 Teams*
━━━━━━━━━━━━━━━━━━━━━━

{shortcuts}

Use shortcuts in commands:
/predict CSK MI
/dream11 RCB SRH"""


# ── Main Bot Loop (polling) ──────────────────────────────────────────

def process_message(text: str, chat_id: str = "") -> str:
    """Process incoming message and return response."""
    if not text:
        return handle_start()

    parts = text.strip().split()
    cmd = parts[0].lower().split("@")[0]  # handle @botname suffix
    args = parts[1:]

    # Admin commands (only you can use these)
    if cmd == "/activate" and str(chat_id) == str(ADMIN_CHAT_ID):
        # /activate 123456789 pro
        if len(args) >= 1:
            target_id = args[0]
            plan = args[1] if len(args) > 1 else "pro"
            activate_premium(target_id, plan)
            return f"✅ Activated *{plan}* plan for user `{target_id}`"
        return "Usage: /activate <chat_id> <pro|elite>"

    if cmd == "/users" and str(chat_id) == str(ADMIN_CHAT_ID):
        users = _load_premium_users()
        paid = {k: v for k, v in users.items() if v.get("plan") in ("pro", "elite")}
        return f"Total users: {len(users)}\nPaid users: {len(paid)}\n\n" + "\n".join(
            f"  `{k}` — {v.get('plan', 'free')}" for k, v in paid.items()
        ) if paid else f"Total users: {len(users)}\nNo paid users yet."

    # Free commands (no payment needed)
    free_handlers = {
        "/start": lambda: handle_start(),
        "/help": lambda: handle_start(),
        "/subscribe": lambda: handle_subscribe(),
        "/upgrade": lambda: handle_subscribe(),
        "/teams": lambda: handle_teams(),
        "/my_plan": lambda: f"Your plan: *{get_user_plan(chat_id).upper()}*\n\n" + (
            "✅ You have full access to all features!" if is_premium(chat_id)
            else "🔒 You're on FREE plan. No predictions available.\n\n/subscribe to unlock everything!"
        ),
        "/form": lambda: handle_form(),
        "/news": lambda: handle_news(),
    }

    if cmd in free_handlers:
        try:
            return free_handlers[cmd]()
        except Exception as e:
            logger.error(f"Error handling {cmd}: {e}")
            return f"❌ Something went wrong: {str(e)[:100]}"

    # PAID commands — check subscription
    paid_handlers = {
        "/predict": lambda: handle_predict(args),
        "/dream11": lambda: handle_dream11(args),
        "/fantasy": lambda: handle_dream11(args),
        "/live": lambda: handle_live(args),
        "/agents": lambda: handle_agents(args),
    }

    if cmd in paid_handlers:
        if not is_premium(chat_id):
            # Show teaser but lock the actual result
            track_free_usage(chat_id)
            return PAYWALL_MSG
        try:
            track_free_usage(chat_id)
            return paid_handlers[cmd]()
        except Exception as e:
            logger.error(f"Error handling {cmd}: {e}")
            return f"❌ Something went wrong: {str(e)[:100]}"

    return "Unknown command. Type /start to see all commands."


async def run_polling():
    """Simple polling-based Telegram bot."""
    if not BOT_TOKEN:
        print("=" * 60)
        print("TELEGRAM BOT SETUP INSTRUCTIONS")
        print("=" * 60)
        print()
        print("1. Open Telegram and search for @BotFather")
        print("2. Send: /newbot")
        print("3. Name it: IPL 2026 Prediction Bot")
        print("4. Username: IPL2026PredBot (or your choice)")
        print("5. Copy the BOT TOKEN")
        print("6. Add to .env: TELEGRAM_BOT_TOKEN=your-token-here")
        print("7. Run again: python bot/telegram_bot.py")
        print()
        print("=" * 60)
        return

    base = f"https://api.telegram.org/bot{BOT_TOKEN}"
    offset = 0
    logger.info("🤖 IPL 2026 Telegram Bot started! Listening for messages...")

    while True:
        try:
            r = requests.get(f"{base}/getUpdates", params={"offset": offset, "timeout": 30}, timeout=35)
            updates = r.json().get("result", [])

            for update in updates:
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                chat_id = msg.get("chat", {}).get("id")
                text = msg.get("text", "")

                if chat_id and text:
                    reply = process_message(text, chat_id=str(chat_id))
                    requests.post(f"{base}/sendMessage", json={
                        "chat_id": chat_id,
                        "text": reply,
                        "parse_mode": "Markdown",
                    })

        except Exception as e:
            logger.error(f"Polling error: {e}")
            await asyncio.sleep(5)

        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(run_polling())
