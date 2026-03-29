"""
IPL 2026 Prediction Telegram Bot — 2 Core Features.

1. PRE-MATCH PREDICTION — Before match starts (pitch, form, h2h, weather, all factors)
2. POST 1ST INNINGS — After 1st innings ends (who will win from current status)

Commands:
  /start        - Welcome + plan info
  /predict CSK MI  - Pre-match AI prediction (PAID)
  /innings CSK MI 185 4  - Post 1st innings prediction (PAID)
  /dream11 CSK MI  - Dream11 Fantasy XI (PAID)
  /form         - Team form (FREE)
  /news         - Cricket news (FREE)
  /teams        - IPL teams (FREE)
  /subscribe    - Plans & pricing
  /pay pro      - Pay via UPI
  /my_plan      - Check subscription
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
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")

# ── Premium User Management ─────────────────────────────────────────
import json

PREMIUM_FILE = Path(__file__).resolve().parent.parent / "data" / "premium" / "telegram_users.json"
PREMIUM_FILE.parent.mkdir(parents=True, exist_ok=True)

UPI_ID = "nikhil.rajak2106@oksbi"
UPI_NAME = "IPL2026 AI Predictions"

def _upi_link(amount, note):
    return f"upi://pay?pa={UPI_ID}&pn={UPI_NAME}&am={amount}&cu=INR&tn={note}"

def _load_premium_users():
    if PREMIUM_FILE.exists():
        return json.loads(PREMIUM_FILE.read_text())
    return {}

def _save_premium_users(data):
    PREMIUM_FILE.write_text(json.dumps(data, indent=2))

def is_premium(chat_id):
    users = _load_premium_users()
    user = users.get(str(chat_id), {})
    return user.get("plan", "free") in ("pro", "elite", "ultra_premium")

def get_user_plan(chat_id):
    users = _load_premium_users()
    return users.get(str(chat_id), {}).get("plan", "free")

def activate_premium(chat_id, plan="pro"):
    users = _load_premium_users()
    cid = str(chat_id)
    if cid not in users:
        users[cid] = {"usage": {}}
    users[cid]["plan"] = plan
    users[cid]["activated"] = __import__("datetime").datetime.now().isoformat()
    _save_premium_users(users)
    return True

def track_free_usage(chat_id):
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

# Team name shortcuts
TEAM_SHORTCUTS = {
    "CSK": "Chennai Super Kings", "MI": "Mumbai Indians",
    "RCB": "Royal Challengers Bengaluru", "KKR": "Kolkata Knight Riders",
    "SRH": "Sunrisers Hyderabad", "DC": "Delhi Capitals",
    "GT": "Gujarat Titans", "LSG": "Lucknow Super Giants",
    "RR": "Rajasthan Royals", "PBKS": "Punjab Kings",
}

def resolve_team(name):
    return TEAM_SHORTCUTS.get(name.upper(), name)

PAYWALL_MSG = """🔒 *This is a PAID feature!*

⭐ *PRO — ₹199/month*
✅ Pre-match AI predictions
✅ Post 1st innings predictions
✅ Dream11 Fantasy XI

💎 *ELITE — ₹499/month*
✅ Everything in Pro
✅ Auto Telegram alerts before every match

🚀 *ULTRA PREMIUM — ₹999/month*
✅ Everything in Elite
✅ Post-toss predictions (auto-sent)
✅ 1st innings predictions (auto-sent)

💳 /pay pro — Pay ₹199 via UPI
/subscribe for details"""


def api_get(endpoint, params=None):
    try:
        r = requests.get(f"{API_BASE}{endpoint}", params=params, timeout=60)
        return r.json() if r.ok else {"error": r.text}
    except Exception as e:
        return {"error": str(e)}

def api_post(endpoint, data):
    try:
        r = requests.post(f"{API_BASE}{endpoint}", json=data, timeout=60)
        return r.json() if r.ok else {"error": r.text}
    except Exception as e:
        return {"error": str(e)}


# ── Command Handlers ─────────────────────────────────────────────────

def handle_start():
    return """🏏 *IPL 2026 AI Prediction Bot*
━━━━━━━━━━━━━━━━━━━━━━

🤖 8 ML Models + Pitch/Form/H2H/Weather Analysis
🎯 Pre-Match & Post 1st Innings Predictions

*FREE Commands:*
/form — Team form & momentum
/news — Latest cricket news
/teams — All IPL teams
/subscribe — View plans

🔒 *PAID Features:*
/predict CSK MI — Pre-match AI prediction
/innings CSK MI 185 4 — After 1st innings prediction
/dream11 CSK MI — Dream11 Fantasy XI

💳 /pay pro — Pay ₹199 via UPI
/my\\_plan — Check your plan"""


def handle_predict(args):
    """Pre-match prediction based on pitch, form, h2h, weather, all factors."""
    if len(args) < 2:
        return "Usage: /predict CSK MI"
    team1 = resolve_team(args[0])
    team2 = resolve_team(args[1])

    result = api_post("/predict_match", {"team1": team1, "team2": team2})

    if "error" in result:
        return f"❌ Error: {result['error']}"

    p1 = round(result.get("team1_win_prob", 0) * 100)
    p2 = round(result.get("team2_win_prob", 0) * 100)
    conf = round(result.get("confidence", 0) * 100)
    winner = result.get("predicted_winner", "Unknown")

    factors = result.get("key_factors", [])
    factors_text = "\n".join(f"  • {f}" for f in factors[:6]) if factors else "  Analysis in progress"

    return f"""🏏 *PRE-MATCH PREDICTION*
*{team1} vs {team2}*
━━━━━━━━━━━━━━━━━━━━━━

🏆 *Predicted Winner: {winner}*

📊 Win Probability:
  {team1}: {p1}%  {'█' * (p1 // 10)}
  {team2}: {p2}%  {'█' * (p2 // 10)}

🎯 Confidence: {conf}%

📋 *Key Factors (Pitch/Form/H2H/Weather):*
{factors_text}

━━━━━━━━━━━━━━━━━━━━━━
_Based on: Pitch analysis, Player form, Head-to-head, Weather, Venue stats, Team strength_

🏏 Want Dream11 XI? /dream11 {args[0]} {args[1]}"""


def handle_innings(args):
    """Post 1st innings — who will win from current match status."""
    if len(args) < 4:
        return """Usage: /innings CSK MI 185 4
_(batting\\_team bowling\\_team score wickets)_

Example: After CSK scores 185/4 in 20 overs
/innings CSK MI 185 4"""
    batting = resolve_team(args[0])
    bowling = resolve_team(args[1])
    try:
        score = int(args[2])
        wickets = int(args[3])
    except ValueError:
        return "❌ Score and wickets must be numbers.\nUsage: /innings CSK MI 185 4"

    result = api_post("/live", {
        "batting_team": batting, "bowling_team": bowling,
        "score": score, "wickets": wickets,
    })

    if "error" in result:
        return f"❌ Error: {result['error']}"

    winner = result.get("predicted_winner", "Unknown")
    chase = round(result.get("chase_prob", 0) * 100)
    defend = 100 - chase
    par = result.get("par_score", "N/A")
    target = score + 1
    rr = round(target / 20, 2)
    assessment = result.get("score_assessment", "")

    factors = result.get("factors", [])
    if isinstance(factors, dict):
        factors_list = [f"{k}: {v}" for k, v in factors.items()]
    elif isinstance(factors, list):
        factors_list = factors
    else:
        factors_list = []
    factors_text = "\n".join(f"  • {f}" for f in factors_list[:5])

    insights = result.get("insights", [])
    insights_text = "\n".join(f"  💡 {i}" for i in insights[:4]) if insights else ""

    return f"""📻 *AFTER 1ST INNINGS PREDICTION*
━━━━━━━━━━━━━━━━━━━━━━
*{batting} {score}/{wickets} (20 ov)*
🎯 Target: *{target}* | RRR: *{rr}*

🏆 *Predicted Winner: {winner}*

📊 Probabilities:
  Defend ({batting}): {defend}% {'█' * (defend // 10)}
  Chase ({bowling}): {chase}% {'█' * (chase // 10)}

📏 Par Score: {par}
📝 Assessment: {assessment}

{insights_text}

━━━━━━━━━━━━━━━━━━━━━━
_Based on: Score vs par, Venue chase rate, Team chase ability, Dew factor_"""


def handle_dream11(args):
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
    source = result.get("xi_source", "auto")

    players_text = ""
    for p in team:
        name = p.get("name", "Unknown")
        role = p.get("role", "")
        cr = p.get("credit", p.get("credits", 0))
        tag = " 🏅(C)" if name == captain else (" ⭐(VC)" if name == vc else "")
        players_text += f"  {name}{tag} — {role} ({cr}cr)\n"

    return f"""⭐ *Dream11 Fantasy XI*
*{team1} vs {team2}*
━━━━━━━━━━━━━━━━━━━━━━
📋 Source: {source}

🏅 Captain (2x): *{captain}*
⭐ Vice-Captain (1.5x): *{vc}*

👥 Team ({credits} credits):
{players_text}
📈 Expected Points: {points:.1f}

━━━━━━━━━━━━━━━━━━━━━━
_Only from actual Playing XI — auto-fetched_"""


def handle_form():
    result = api_get("/form")
    if "error" in result:
        return f"❌ Error: {result['error']}"

    text = "📊 *Team Form & Momentum*\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
    teams = sorted(result.items(), key=lambda x: x[1].get("rating", 0) if isinstance(x[1], dict) else 0, reverse=True)
    for i, (team, info) in enumerate(teams):
        if not isinstance(info, dict):
            continue
        rating = round((info.get("rating", 0)) * 100, 1)
        momentum = info.get("momentum", "Stable")
        emoji = "🟢" if momentum == "Rising" else ("🔴" if momentum == "Falling" else "🟡")
        text += f"{i+1}. {team} — {rating} {emoji}\n"
    return text


def handle_news():
    result = api_get("/news")
    if "error" in result:
        return f"❌ Error: {result['error']}"
    articles = result.get("articles", [])[:5]
    text = "📰 *Latest Cricket News*\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
    for a in articles:
        text += f"• {a.get('title', 'No title')}\n  _{a.get('source', 'Unknown')}_\n\n"
    return text if articles else "No news available right now."


def handle_teams():
    shortcuts = "\n".join(f"  {v} → {k}" for k, v in sorted(TEAM_SHORTCUTS.items(), key=lambda x: x[1]))
    return f"""🏏 *IPL 2026 Teams*
━━━━━━━━━━━━━━━━━━━━━━

{shortcuts}

Use shortcuts:
/predict CSK MI
/innings CSK MI 185 4
/dream11 RCB SRH"""


def handle_subscribe():
    return f"""💎 *Upgrade Your Plan*
━━━━━━━━━━━━━━━━━━━━━━

🆓 *FREE* — Form, news, teams only
  ❌ No predictions

⭐ *PRO — ₹199/month*
  ✅ Pre-match AI predictions (all factors)
  ✅ Post 1st innings predictions
  ✅ Dream11 Fantasy XI (auto Playing XI)

💎 *ELITE — ₹499/month*
  ✅ Everything in Pro
  ✅ Auto predictions sent before every match

🚀 *ULTRA PREMIUM — ₹999/month*
  ✅ Everything in Elite
  ✅ Post-toss auto-predictions
  ✅ 1st innings auto-predictions

💳 *How to pay:*
/pay pro — Pay ₹199
/pay elite — Pay ₹499
/pay ultra — Pay ₹999

After payment → send screenshot here → instant access!"""


# ── Pending Payments Tracker ──────────────────────────────────────
PENDING_PAYMENTS_FILE = Path(__file__).resolve().parent.parent / "data" / "premium" / "pending_payments.json"

def _load_pending_payments():
    if PENDING_PAYMENTS_FILE.exists():
        return json.loads(PENDING_PAYMENTS_FILE.read_text())
    return {}

def _save_pending_payments(data):
    PENDING_PAYMENTS_FILE.write_text(json.dumps(data, indent=2))

def _set_pending_payment(chat_id, plan, amount):
    pending = _load_pending_payments()
    pending[str(chat_id)] = {
        "plan": plan,
        "amount": amount,
        "timestamp": __import__("datetime").datetime.now().isoformat(),
    }
    _save_pending_payments(pending)

def _get_pending_payment(chat_id):
    pending = _load_pending_payments()
    return pending.get(str(chat_id), {})


def handle_pay(args, chat_id):
    """Send UPI QR code as image + inline pay button + track plan selection."""
    plans_info = {
        "pro": {"amount": 199, "name": "Pro"},
        "elite": {"amount": 499, "name": "Elite"},
        "ultra": {"amount": 999, "name": "Ultra Premium"},
        "ultra_premium": {"amount": 999, "name": "Ultra Premium"},
    }
    if not args:
        return "💳 /pay pro — ₹199\n/pay elite — ₹499\n/pay ultra — ₹999"

    plan = plans_info.get(args[0].lower())
    if not plan:
        return "❌ Use: /pay pro, /pay elite, or /pay ultra"

    amount = plan["amount"]
    name = plan["name"]
    plan_key = args[0].lower()
    if plan_key == "ultra":
        plan_key = "ultra_premium"
    note = f"IPL2026-{name}-{chat_id}"
    upi = _upi_link(amount, note)

    # Track which plan this user wants to pay for
    _set_pending_payment(chat_id, plan_key, amount)

    base = f"https://api.telegram.org/bot{BOT_TOKEN}"

    # Step 1: Send QR code as actual image
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&data={requests.utils.quote(upi)}"
    try:
        requests.post(f"{base}/sendPhoto", json={
            "chat_id": chat_id,
            "photo": qr_url,
            "caption": f"📱 *Scan QR to Pay ₹{amount}*\nPlan: {name}\nUPI: `{UPI_ID}`",
            "parse_mode": "Markdown",
        }, timeout=15)
    except Exception as e:
        logger.warning(f"QR send failed: {e}")

    # Step 2: Send payment instructions with UPI button
    text = f"""💳 *Pay for {name} Plan — ₹{amount}*
━━━━━━━━━━━━━━━━━━━━━━

*Step 1:* Pay using any of these methods:

📱 *UPI ID:* `{UPI_ID}`
💰 *Amount:* ₹{amount}
📝 *Note:* `{note}`

👆 Tap the UPI ID above to copy it

*How to pay:*
1️⃣ Open GPay / PhonePe / Paytm
2️⃣ Go to "Pay to UPI ID"
3️⃣ Paste: `{UPI_ID}`
4️⃣ Enter ₹{amount}
5️⃣ In remarks/note write: `{note}`
6️⃣ Complete payment

*Step 2:* After payment done 👇
📸 *Send payment screenshot here*

━━━━━━━━━━━━━━━━━━━━━━
✅ Screenshot → Instant verification → Plan activated!"""

    # Send with inline keyboard: UPI deep link button + copy button
    try:
        requests.post(f"{base}/sendMessage", json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": {
                "inline_keyboard": [
                    [{"text": f"💳 Pay ₹{amount} via UPI App", "url": upi}],
                    [{"text": "📋 Copy UPI ID", "callback_data": "copy_upi"}],
                ]
            }
        }, timeout=15)
    except Exception as e:
        logger.warning(f"Pay message send failed: {e}")

    # Return None so the main loop doesn't send duplicate
    return None


def handle_payment_screenshot(chat_id):
    """User sent screenshot → forward to admin with plan info + quick activate buttons."""
    admin_id = os.getenv("ADMIN_CHAT_ID", "")
    pending = _get_pending_payment(chat_id)
    plan_name = pending.get("plan", "unknown")
    amount = pending.get("amount", "?")

    base = f"https://api.telegram.org/bot{BOT_TOKEN}"

    if admin_id:
        try:
            # Send alert to admin with plan details and quick activate buttons
            requests.post(f"{base}/sendMessage", json={
                "chat_id": admin_id,
                "text": (
                    f"💰 *NEW PAYMENT SCREENSHOT!*\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"👤 User: `{chat_id}`\n"
                    f"📋 Plan requested: *{plan_name.upper()}*\n"
                    f"💰 Amount: *₹{amount}*\n"
                    f"⏰ Time: {__import__('datetime').datetime.now().strftime('%I:%M %p')}\n\n"
                    f"*Quick Activate:*\n"
                    f"/activate {chat_id} {plan_name}\n\n"
                    f"_Screenshot forwarded below 👇_"
                ),
                "parse_mode": "Markdown",
                "reply_markup": {
                    "inline_keyboard": [
                        [
                            {"text": f"✅ Activate {plan_name.upper()}", "callback_data": f"activate_{chat_id}_{plan_name}"},
                            {"text": "❌ Reject", "callback_data": f"reject_{chat_id}"},
                        ]
                    ]
                }
            }, timeout=10)
        except Exception as e:
            logger.warning(f"Admin notification failed: {e}")

    plan_display = plan_name.replace("_", " ").title() if plan_name != "unknown" else "Selected"
    return f"""📸 *Payment Screenshot Received!*
━━━━━━━━━━━━━━━━━━━━━━

✅ Your ₹{amount} payment for *{plan_display}* plan is being verified.

⏳ Your plan will be activated within *2-5 minutes*.
📱 You'll receive a confirmation message here.

Your Chat ID: `{chat_id}`

_If not activated in 10 minutes, contact @Nikhil2026_"""


def handle_callback_query(callback_data, from_chat_id):
    """Handle inline keyboard button presses."""
    base = f"https://api.telegram.org/bot{BOT_TOKEN}"

    if callback_data == "copy_upi":
        return f"📋 UPI ID: `{UPI_ID}`\n\nTap to copy 👆"

    if callback_data.startswith("activate_") and str(from_chat_id) == str(ADMIN_CHAT_ID):
        parts = callback_data.split("_", 2)
        if len(parts) >= 3:
            target_id = parts[1]
            plan = parts[2]
            activate_premium(target_id, plan)

            # Notify the user their plan is activated
            plan_display = plan.replace("_", " ").title()
            try:
                requests.post(f"{base}/sendMessage", json={
                    "chat_id": target_id,
                    "text": (
                        f"🎉 *PLAN ACTIVATED!*\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"✅ Your *{plan_display}* plan is now active!\n\n"
                        f"🏏 You can now use:\n"
                        f"  /predict CSK MI — Pre-match prediction\n"
                        f"  /innings CSK MI 185 4 — After 1st innings\n"
                        f"  /dream11 CSK MI — Dream11 Fantasy XI\n\n"
                        f"Enjoy your predictions! 🚀"
                    ),
                    "parse_mode": "Markdown",
                }, timeout=10)
            except Exception:
                pass

            return f"✅ Activated *{plan_display}* for `{target_id}`\nUser has been notified!"

    if callback_data.startswith("reject_") and str(from_chat_id) == str(ADMIN_CHAT_ID):
        target_id = callback_data.split("_", 1)[1]
        try:
            requests.post(f"{base}/sendMessage", json={
                "chat_id": target_id,
                "text": (
                    "❌ *Payment could not be verified.*\n\n"
                    "Please ensure you paid to the correct UPI ID:\n"
                    f"`{UPI_ID}`\n\n"
                    "Try again: /pay pro or /pay elite or /pay ultra\n"
                    "Issue? Contact @Nikhil2026"
                ),
                "parse_mode": "Markdown",
            }, timeout=10)
        except Exception:
            pass
        return "❌ Payment rejected. User notified."

    return None


def handle_rl_status():
    try:
        from models.rl_trainer import RLTrainer
        rl = RLTrainer()
        r = rl.get_rl_report()
        if r.get("total_matches", 0) == 0:
            return "🤖 No matches processed yet."
        return f"""🤖 *RL Status*
Matches: {r['total_matches']} | Correct: {r['correct_predictions']}
Accuracy: {r['overall_accuracy']:.1%} | Trend: {r['improvement_trend']}"""
    except Exception as e:
        return f"❌ {str(e)[:100]}"


def handle_result(args):
    """Admin command: /result RCB CSK RCB  →  process match result through RL."""
    if len(args) < 3:
        return """Usage: /result TEAM1 TEAM2 WINNER

Example: /result RCB CSK RCB
(RCB vs CSK, RCB won)

This triggers RL auto-training immediately."""

    team1 = resolve_team(args[0])
    team2 = resolve_team(args[1])
    winner = resolve_team(args[2])

    try:
        from scheduler import manual_process_result
        result = manual_process_result(team1, team2, winner)
        correct = result.get("correct", False)
        reward = result.get("reward", 0)
        accuracy = result.get("rolling_accuracy", 0)
        corrected = result.get("models_corrected", [])

        return f"""🔄 *RL Training Complete*
━━━━━━━━━━━━━━━━━━━━━━
*{team1} vs {team2}*
Winner: *{winner}*

{'✅ Prediction was CORRECT' if correct else '❌ Prediction was WRONG'}
Reward: {reward:.2f}
Models corrected: {', '.join(corrected) if corrected else 'None'}
Rolling accuracy: {accuracy:.1%}
Total matches: {result.get('total_matches', 0)}

🤖 Weights updated automatically!"""
    except Exception as e:
        return f"❌ RL processing failed: {str(e)[:200]}"


# ── Main Message Router ──────────────────────────────────────────────

def process_message(text, chat_id=""):
    if not text:
        return handle_start()

    parts = text.strip().split()
    cmd = parts[0].lower().split("@")[0]
    args = parts[1:]

    # Admin commands
    if cmd == "/activate" and str(chat_id) == str(ADMIN_CHAT_ID):
        if len(args) >= 1:
            target_id = args[0]
            plan = args[1] if len(args) > 1 else "pro"
            activate_premium(target_id, plan)
            return f"✅ Activated *{plan}* for `{target_id}`"
        return "Usage: /activate <chat_id> <pro|elite|ultra_premium>"

    if cmd == "/users" and str(chat_id) == str(ADMIN_CHAT_ID):
        users = _load_premium_users()
        paid = {k: v for k, v in users.items() if v.get("plan") in ("pro", "elite", "ultra_premium")}
        return f"Total: {len(users)} | Paid: {len(paid)}\n\n" + "\n".join(
            f"`{k}` — {v.get('plan')}" for k, v in paid.items()
        ) if paid else f"Total: {len(users)} | No paid users yet."

    if cmd == "/rl_status" and str(chat_id) == str(ADMIN_CHAT_ID):
        return handle_rl_status()

    if cmd == "/result" and str(chat_id) == str(ADMIN_CHAT_ID):
        return handle_result(args)

    # Payment command
    if cmd == "/pay":
        return handle_pay(args, str(chat_id))

    # Free commands
    free_cmds = {
        "/start": lambda: handle_start(),
        "/help": lambda: handle_start(),
        "/subscribe": lambda: handle_subscribe(),
        "/upgrade": lambda: handle_subscribe(),
        "/teams": lambda: handle_teams(),
        "/my_plan": lambda: f"Your plan: *{get_user_plan(chat_id).upper()}*\n\n" + (
            "✅ Full access!" if is_premium(chat_id)
            else "🔒 FREE plan — no predictions.\n/subscribe to unlock!"
        ),
        "/form": lambda: handle_form(),
        "/news": lambda: handle_news(),
    }

    if cmd in free_cmds:
        try:
            return free_cmds[cmd]()
        except Exception as e:
            return f"❌ Error: {str(e)[:100]}"

    # Paid commands
    paid_cmds = {
        "/predict": lambda: handle_predict(args),
        "/innings": lambda: handle_innings(args),
        "/dream11": lambda: handle_dream11(args),
        "/fantasy": lambda: handle_dream11(args),
        "/live": lambda: handle_innings(args),  # /live also works as /innings
    }

    if cmd in paid_cmds:
        if not is_premium(chat_id) and str(chat_id) != str(ADMIN_CHAT_ID):
            track_free_usage(chat_id)
            return PAYWALL_MSG
        try:
            track_free_usage(chat_id)
            return paid_cmds[cmd]()
        except Exception as e:
            return f"❌ Error: {str(e)[:100]}"

    return "Unknown command. /start to see all commands."


# ── Bot Polling Loop ─────────────────────────────────────────────────

async def run_polling():
    if not BOT_TOKEN:
        print("No TELEGRAM_BOT_TOKEN set. Add it to .env")
        return

    base = f"https://api.telegram.org/bot{BOT_TOKEN}"
    offset = 0
    logger.info("🏏 IPL Bot started!")

    while True:
        try:
            r = requests.get(f"{base}/getUpdates", params={"offset": offset, "timeout": 30}, timeout=35)
            updates = r.json().get("result", [])

            for update in updates:
                offset = update["update_id"] + 1

                # ── Handle inline button presses (callback queries) ──
                callback = update.get("callback_query")
                if callback:
                    cb_data = callback.get("data", "")
                    cb_chat_id = callback.get("from", {}).get("id", "")
                    cb_id = callback.get("id", "")

                    logger.info(f"Callback: {cb_data} from {cb_chat_id}")
                    reply = handle_callback_query(cb_data, str(cb_chat_id))

                    # Answer the callback to remove loading spinner
                    try:
                        requests.post(f"{base}/answerCallbackQuery", json={
                            "callback_query_id": cb_id,
                            "text": "Processing..." if reply else "Done",
                        }, timeout=5)
                    except Exception:
                        pass

                    if reply:
                        requests.post(f"{base}/sendMessage", json={
                            "chat_id": cb_chat_id, "text": reply, "parse_mode": "Markdown",
                        }, timeout=10)
                    continue

                # ── Handle messages ──
                msg = update.get("message", {})
                chat_id = msg.get("chat", {}).get("id")
                text = msg.get("text", "")

                if not chat_id:
                    continue

                # Photo/document = payment screenshot
                if msg.get("photo") or msg.get("document"):
                    logger.info(f"Payment screenshot from {chat_id}")
                    reply = handle_payment_screenshot(str(chat_id))

                    # Forward the actual screenshot to admin
                    admin_id = os.getenv("ADMIN_CHAT_ID", "")
                    if admin_id:
                        try:
                            requests.post(f"{base}/forwardMessage", json={
                                "chat_id": admin_id, "from_chat_id": chat_id,
                                "message_id": msg["message_id"],
                            }, timeout=10)
                        except Exception:
                            pass

                    requests.post(f"{base}/sendMessage", json={
                        "chat_id": chat_id, "text": reply, "parse_mode": "Markdown",
                    })
                    continue

                if text:
                    logger.info(f"[{chat_id}] {text[:50]}")
                    reply = process_message(text, chat_id=str(chat_id))

                    # handle_pay returns None (it sends messages directly)
                    if reply is not None:
                        requests.post(f"{base}/sendMessage", json={
                            "chat_id": chat_id, "text": reply, "parse_mode": "Markdown",
                        })

        except Exception as e:
            logger.error(f"Poll error: {e}")
            await asyncio.sleep(5)

        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(run_polling())
