"""
IPL 2026 AI Prediction Bot — Payment & Group Access Only.

2 Plans:
  BASIC ₹199 — Pre-match + After 1st innings predictions
  PRO   ₹399 — Everything in Basic + Best Dream11 Playing XI

Flow:
  User /start → sees plans → /pay basic or /pay pro → UPI QR + link
  → sends screenshot → admin verifies → sends group invite link
  → user joins group → admin posts predictions manually in group

NO prediction commands in bot. Bot is only for payment collection.
"""

import os
import sys
import asyncio
import logging
import json
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, ".")
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("IPLBot")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")

UPI_ID = "nikhil.rajak2106@oksbi"
UPI_NAME = "IPL2026 Predictions"

# Telegram group invite links (set these after creating groups)
BASIC_GROUP_LINK = os.getenv("BASIC_GROUP_LINK", "")  # Set in .env
PRO_GROUP_LINK = os.getenv("PRO_GROUP_LINK", "")      # Set in .env

# ── Data Files ───────────────────────────────────────────────────
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "premium"
DATA_DIR.mkdir(parents=True, exist_ok=True)
PAYMENTS_FILE = DATA_DIR / "payments.json"


def _load_payments():
    if PAYMENTS_FILE.exists():
        return json.loads(PAYMENTS_FILE.read_text())
    return {}


def _save_payments(data):
    PAYMENTS_FILE.write_text(json.dumps(data, indent=2))


def _set_pending(chat_id, plan, amount):
    payments = _load_payments()
    payments[str(chat_id)] = {
        "plan": plan,
        "amount": amount,
        "status": "pending",
        "timestamp": datetime.now().isoformat(),
    }
    _save_payments(payments)


def _get_pending(chat_id):
    payments = _load_payments()
    return payments.get(str(chat_id), {})


def _upi_link(amount, note):
    return f"upi://pay?pa={UPI_ID}&pn={UPI_NAME}&am={amount}&cu=INR&tn={note}"


# ── Command Handlers ─────────────────────────────────────────────

def handle_start():
    return """🏏 *IPL 2026 AI Predictions*
━━━━━━━━━━━━━━━━━━━━━━

🤖 8 ML Models — Pitch, Form, H2H, Weather Analysis
🎯 Pre-Match & After 1st Innings Predictions

📋 *2 Plans:*

⭐ *BASIC — ₹199/month*
  ✅ Pre-match winner predictions
  ✅ After 1st innings predictions

💎 *PRO — ₹399/month*
  ✅ Everything in Basic
  ✅ Best Dream11 Playing XI

💳 *How to join:*
/pay basic — Pay ₹199
/pay pro — Pay ₹399

After payment → send screenshot here
→ You get group invite link instantly!

/plans — View plan details"""


def handle_plans():
    return """📋 *IPL 2026 Prediction Plans*
━━━━━━━━━━━━━━━━━━━━━━

⭐ *BASIC — ₹199/month*
━━━━━━━━━━━━━━━━━━━━━━
✅ Pre-match AI predictions before every match
  → Pitch analysis, player form, H2H stats
  → Weather, venue stats, team strength
  → Win probability with confidence %
✅ After 1st innings predictions
  → Who will win from current score
  → Chase probability, par score analysis

💎 *PRO — ₹399/month*
━━━━━━━━━━━━━━━━━━━━━━
✅ Everything in Basic
✅ Best Dream11 Playing XI
  → Captain & Vice-Captain picks
  → From actual Playing XI (auto-fetched)
  → Credit-optimized team

━━━━━━━━━━━━━━━━━━━━━━
📱 Predictions posted daily in private Telegram group
🔒 Only paid members get access

💳 /pay basic — ₹199
💳 /pay pro — ₹399"""


def handle_pay(args, chat_id):
    """Send UPI QR + payment instructions."""
    plans = {
        "basic": {"amount": 199, "name": "Basic"},
        "pro": {"amount": 399, "name": "Pro"},
    }

    if not args:
        return "💳 /pay basic — ₹199\n💳 /pay pro — ₹399"

    plan_key = args[0].lower()
    plan = plans.get(plan_key)
    if not plan:
        return "❌ Use: /pay basic or /pay pro"

    amount = plan["amount"]
    name = plan["name"]
    note = f"IPL2026-{name}-{chat_id}"
    upi = _upi_link(amount, note)

    # Track pending payment
    _set_pending(chat_id, plan_key, amount)

    base = f"https://api.telegram.org/bot{BOT_TOKEN}"

    # Send QR code as image
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

    # Send instructions with inline UPI button
    text = f"""💳 *Pay ₹{amount} for {name} Plan*
━━━━━━━━━━━━━━━━━━━━━━

📱 *UPI ID:* `{UPI_ID}`
💰 *Amount:* ₹{amount}
📝 *Note:* `{note}`

👆 Tap UPI ID to copy

*How to pay:*
1️⃣ Open GPay / PhonePe / Paytm
2️⃣ Send ₹{amount} to `{UPI_ID}`
3️⃣ In remarks write: `{note}`

*After payment:*
📸 Send screenshot here → Get group invite link!

━━━━━━━━━━━━━━━━━━━━━━
✅ Instant verification → Group access within minutes!"""

    try:
        requests.post(f"{base}/sendMessage", json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": {
                "inline_keyboard": [
                    [{"text": f"💳 Pay ₹{amount} via UPI App", "url": upi}],
                ]
            }
        }, timeout=15)
    except Exception as e:
        logger.warning(f"Pay message failed: {e}")

    return None  # Already sent messages directly


def handle_screenshot(chat_id):
    """User sent payment screenshot → notify admin."""
    admin_id = ADMIN_CHAT_ID
    pending = _get_pending(chat_id)
    plan = pending.get("plan", "basic")
    amount = pending.get("amount", "199")
    plan_display = "Pro" if plan == "pro" else "Basic"

    base = f"https://api.telegram.org/bot{BOT_TOKEN}"

    if admin_id:
        try:
            requests.post(f"{base}/sendMessage", json={
                "chat_id": admin_id,
                "text": (
                    f"💰 *NEW PAYMENT!*\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"👤 User: `{chat_id}`\n"
                    f"📋 Plan: *{plan_display}* (₹{amount})\n"
                    f"⏰ {datetime.now().strftime('%d %b %I:%M %p')}\n\n"
                    f"_Screenshot below 👇_\n\n"
                    f"After verifying, tap button to send group link:"
                ),
                "parse_mode": "Markdown",
                "reply_markup": {
                    "inline_keyboard": [
                        [{"text": f"✅ Send {plan_display} Group Link", "callback_data": f"approve_{chat_id}_{plan}"}],
                        [{"text": "❌ Reject Payment", "callback_data": f"reject_{chat_id}"}],
                    ]
                }
            }, timeout=10)
        except Exception as e:
            logger.warning(f"Admin notify failed: {e}")

    return f"""📸 *Payment Screenshot Received!*
━━━━━━━━━━━━━━━━━━━━━━

✅ Your ₹{amount} payment for *{plan_display}* plan is being verified.

⏳ You'll receive the *group invite link* within 5 minutes.

_If not received in 10 min, contact @Nikhil2026_"""


def handle_callback(callback_data, from_chat_id):
    """Handle admin button presses."""
    base = f"https://api.telegram.org/bot{BOT_TOKEN}"

    # Admin approves payment → send group link to user
    if callback_data.startswith("approve_") and str(from_chat_id) == str(ADMIN_CHAT_ID):
        parts = callback_data.split("_", 2)
        if len(parts) >= 3:
            target_id = parts[1]
            plan = parts[2]

            # Determine group link
            if plan == "pro":
                group_link = PRO_GROUP_LINK or BASIC_GROUP_LINK
                plan_display = "Pro"
                features = (
                    "✅ Pre-match predictions\n"
                    "✅ After 1st innings predictions\n"
                    "✅ Dream11 Best Playing XI"
                )
            else:
                group_link = BASIC_GROUP_LINK
                plan_display = "Basic"
                features = (
                    "✅ Pre-match predictions\n"
                    "✅ After 1st innings predictions"
                )

            # Update payment status
            payments = _load_payments()
            if str(target_id) in payments:
                payments[str(target_id)]["status"] = "approved"
                payments[str(target_id)]["approved_at"] = datetime.now().isoformat()
                _save_payments(payments)

            if group_link:
                # Send group invite link to user
                try:
                    requests.post(f"{base}/sendMessage", json={
                        "chat_id": target_id,
                        "text": (
                            f"🎉 *PAYMENT VERIFIED!*\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
                            f"✅ Your *{plan_display}* plan is active!\n\n"
                            f"📋 *Your features:*\n{features}\n\n"
                            f"👇 *Join the prediction group:*"
                        ),
                        "parse_mode": "Markdown",
                        "reply_markup": {
                            "inline_keyboard": [
                                [{"text": f"🏏 Join {plan_display} Predictions Group", "url": group_link}],
                            ]
                        }
                    }, timeout=10)
                except Exception as e:
                    logger.warning(f"Group link send failed: {e}")

                return f"✅ Group link sent to `{target_id}` ({plan_display})"
            else:
                # No group link set — tell admin to set it
                try:
                    requests.post(f"{base}/sendMessage", json={
                        "chat_id": target_id,
                        "text": (
                            f"🎉 *PAYMENT VERIFIED!*\n\n"
                            f"✅ *{plan_display}* plan active!\n\n"
                            f"⏳ Admin will add you to the group shortly.\n"
                            f"_Contact @Nikhil2026 if not added in 10 min._"
                        ),
                        "parse_mode": "Markdown",
                    }, timeout=10)
                except Exception:
                    pass

                return (
                    f"⚠️ No group link set for {plan_display}!\n"
                    f"User `{target_id}` notified to wait.\n\n"
                    f"Set group links in .env:\n"
                    f"`BASIC_GROUP_LINK=https://t.me/+xxxxx`\n"
                    f"`PRO_GROUP_LINK=https://t.me/+xxxxx`\n\n"
                    f"Or use /setgroup basic <link> or /setgroup pro <link>"
                )

    # Admin rejects payment
    if callback_data.startswith("reject_") and str(from_chat_id) == str(ADMIN_CHAT_ID):
        target_id = callback_data.split("_", 1)[1]

        payments = _load_payments()
        if str(target_id) in payments:
            payments[str(target_id)]["status"] = "rejected"
            _save_payments(payments)

        try:
            requests.post(f"{base}/sendMessage", json={
                "chat_id": target_id,
                "text": (
                    "❌ *Payment could not be verified.*\n\n"
                    f"Please pay to correct UPI ID: `{UPI_ID}`\n\n"
                    "Try again: /pay basic or /pay pro\n"
                    "Issue? Contact @Nikhil2026"
                ),
                "parse_mode": "Markdown",
            }, timeout=10)
        except Exception:
            pass

        return "❌ Rejected. User notified to retry."

    return None


# ── Message Router ───────────────────────────────────────────────

def process_message(text, chat_id=""):
    if not text:
        return handle_start()

    parts = text.strip().split()
    cmd = parts[0].lower().split("@")[0]
    args = parts[1:]

    # ── Admin commands ──
    if str(chat_id) == str(ADMIN_CHAT_ID):
        if cmd == "/users":
            payments = _load_payments()
            approved = {k: v for k, v in payments.items() if v.get("status") == "approved"}
            pending = {k: v for k, v in payments.items() if v.get("status") == "pending"}
            text = f"👥 *Users*\nApproved: {len(approved)} | Pending: {len(pending)}\n\n"
            for uid, info in approved.items():
                plan = info.get('plan', 'basic').title()
                text += f"✅ `{uid}` — {plan} (₹{info.get('amount', '?')})\n"
            for uid, info in pending.items():
                plan = info.get('plan', 'basic').title()
                text += f"⏳ `{uid}` — {plan} (₹{info.get('amount', '?')})\n"
            return text if approved or pending else "No users yet."

        if cmd == "/setgroup" and len(args) >= 2:
            plan_type = args[0].lower()
            link = args[1]
            # Save to a config file
            config_file = DATA_DIR / "group_links.json"
            config = {}
            if config_file.exists():
                config = json.loads(config_file.read_text())
            config[plan_type] = link
            config_file.write_text(json.dumps(config, indent=2))
            # Also update global vars
            global BASIC_GROUP_LINK, PRO_GROUP_LINK
            if plan_type == "basic":
                BASIC_GROUP_LINK = link
            elif plan_type == "pro":
                PRO_GROUP_LINK = link
            return f"✅ {plan_type.title()} group link set!\n`{link}`"

        if cmd == "/revenue":
            payments = _load_payments()
            approved = [v for v in payments.values() if v.get("status") == "approved"]
            total = sum(v.get("amount", 0) for v in approved)
            basic_count = sum(1 for v in approved if v.get("plan") == "basic")
            pro_count = sum(1 for v in approved if v.get("plan") == "pro")
            return (
                f"💰 *Revenue*\n━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Basic: {basic_count} × ₹199 = ₹{basic_count * 199}\n"
                f"Pro: {pro_count} × ₹399 = ₹{pro_count * 399}\n"
                f"*Total: ₹{total}*"
            )

        if cmd == "/rl_status":
            try:
                from models.rl_trainer import RLTrainer
                rl = RLTrainer()
                r = rl.get_rl_report()
                if r.get("total_matches", 0) == 0:
                    return "🤖 No matches processed yet."
                return (
                    f"🤖 *RL Status*\n"
                    f"Matches: {r['total_matches']} | Correct: {r['correct_predictions']}\n"
                    f"Accuracy: {r['overall_accuracy']:.1%} | Trend: {r['improvement_trend']}"
                )
            except Exception as e:
                return f"❌ {str(e)[:100]}"

        if cmd == "/result" and len(args) >= 3:
            from bot.telegram_bot import TEAM_SHORTCUTS
            team1 = TEAM_SHORTCUTS.get(args[0].upper(), args[0])
            team2 = TEAM_SHORTCUTS.get(args[1].upper(), args[1])
            winner = TEAM_SHORTCUTS.get(args[2].upper(), args[2])
            try:
                from scheduler import manual_process_result
                result = manual_process_result(team1, team2, winner)
                return (
                    f"🔄 *RL Training Done*\n"
                    f"{team1} vs {team2} → {winner} won\n"
                    f"{'✅ Correct' if result.get('correct') else '❌ Wrong'} | "
                    f"Reward: {result.get('reward', 0):.2f}"
                )
            except Exception as e:
                return f"❌ {str(e)[:150]}"

    # ── User commands ──
    if cmd in ("/start", "/help"):
        return handle_start()

    if cmd in ("/plans", "/subscribe", "/pricing"):
        return handle_plans()

    if cmd == "/pay":
        return handle_pay(args, str(chat_id))

    return """🏏 *IPL 2026 AI Predictions*

/plans — View prediction plans
/pay basic — Pay ₹199 (Predictions)
/pay pro — Pay ₹399 (Predictions + Dream11 XI)

After payment → send screenshot → get group access!"""


# ── Polling Loop ─────────────────────────────────────────────────

def _load_group_links():
    """Load group links from config file."""
    global BASIC_GROUP_LINK, PRO_GROUP_LINK
    config_file = DATA_DIR / "group_links.json"
    if config_file.exists():
        config = json.loads(config_file.read_text())
        BASIC_GROUP_LINK = config.get("basic", BASIC_GROUP_LINK)
        PRO_GROUP_LINK = config.get("pro", PRO_GROUP_LINK)


TEAM_SHORTCUTS = {
    "CSK": "Chennai Super Kings", "MI": "Mumbai Indians",
    "RCB": "Royal Challengers Bengaluru", "KKR": "Kolkata Knight Riders",
    "SRH": "Sunrisers Hyderabad", "DC": "Delhi Capitals",
    "GT": "Gujarat Titans", "LSG": "Lucknow Super Giants",
    "RR": "Rajasthan Royals", "PBKS": "Punjab Kings",
}


async def run_polling():
    if not BOT_TOKEN:
        print("No TELEGRAM_BOT_TOKEN set. Add it to .env")
        return

    _load_group_links()

    base = f"https://api.telegram.org/bot{BOT_TOKEN}"
    offset = 0
    logger.info("🏏 IPL Payment Bot started!")

    while True:
        try:
            r = requests.get(f"{base}/getUpdates", params={"offset": offset, "timeout": 30}, timeout=35)
            updates = r.json().get("result", [])

            for update in updates:
                offset = update["update_id"] + 1

                # ── Inline button presses ──
                callback = update.get("callback_query")
                if callback:
                    cb_data = callback.get("data", "")
                    cb_chat_id = callback.get("from", {}).get("id", "")
                    cb_id = callback.get("id", "")

                    logger.info(f"Callback: {cb_data} from {cb_chat_id}")
                    reply = handle_callback(cb_data, str(cb_chat_id))

                    try:
                        requests.post(f"{base}/answerCallbackQuery", json={
                            "callback_query_id": cb_id,
                            "text": "Done!" if reply else "OK",
                        }, timeout=5)
                    except Exception:
                        pass

                    if reply:
                        requests.post(f"{base}/sendMessage", json={
                            "chat_id": cb_chat_id, "text": reply, "parse_mode": "Markdown",
                        }, timeout=10)
                    continue

                # ── Messages ──
                msg = update.get("message", {})
                chat_id = msg.get("chat", {}).get("id")
                text = msg.get("text", "")

                if not chat_id:
                    continue

                # Photo/doc = payment screenshot
                if msg.get("photo") or msg.get("document"):
                    logger.info(f"Screenshot from {chat_id}")
                    reply = handle_screenshot(str(chat_id))

                    # Forward screenshot to admin
                    if ADMIN_CHAT_ID:
                        try:
                            requests.post(f"{base}/forwardMessage", json={
                                "chat_id": ADMIN_CHAT_ID, "from_chat_id": chat_id,
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
