"""
Premium Subscription & Monetization System.

Tiers:
  FREE   — 5 predictions/day, basic match predictor, no agents
  PRO    — ₹299/month — Unlimited predictions, Dream11, Live, Agents, News
  ELITE  — ₹799/month — Everything + priority API, Telegram alerts, accuracy reports

Revenue Streams:
  1. Web SaaS subscriptions (Razorpay/Stripe)
  2. Telegram Premium Bot (@IPL2026PredBot)
  3. Affiliate links (Dream11, MPL, My11Circle referral codes)
  4. Ad revenue on website (Google AdSense)
  5. API-as-a-Service for developers (₹1999/month)
"""

import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from fastapi import HTTPException, Request

DATA_DIR = Path("data/premium")
DATA_DIR.mkdir(parents=True, exist_ok=True)

USERS_FILE = DATA_DIR / "users.json"
USAGE_FILE = DATA_DIR / "usage.json"

# ── Subscription Plans ───────────────────────────────────────────────
PLANS = {
    "basic": {
        "name": "Basic",
        "price_inr": 199,
        "price_usd": 2.49,
        "predictions_per_day": -1,
        "features": [
            "Pre-match AI predictions (all cricket factors)",
            "After 1st innings predictions",
            "Pitch, form, H2H, weather analysis",
            "Win probability with confidence %",
            "Private Telegram group access",
        ],
        "dream11": False,
        "live": True,
        "news": False,
        "telegram_group": True,
    },
    "pro": {
        "name": "Pro",
        "price_inr": 399,
        "price_usd": 4.99,
        "predictions_per_day": -1,
        "features": [
            "Everything in Basic",
            "Best Dream11 Playing XI",
            "Captain & Vice-Captain picks",
            "Credit-optimized team from actual Playing XI",
            "Private Telegram group access",
        ],
        "dream11": True,
        "live": True,
        "news": False,
        "telegram_group": True,
    },
}


# ── User Management ──────────────────────────────────────────────────

def _load_users():
    if USERS_FILE.exists():
        return json.loads(USERS_FILE.read_text())
    return {}


def _save_users(users):
    USERS_FILE.write_text(json.dumps(users, indent=2))


def _load_usage():
    if USAGE_FILE.exists():
        return json.loads(USAGE_FILE.read_text())
    return {}


def _save_usage(usage):
    USAGE_FILE.write_text(json.dumps(usage, indent=2))


def register_user(email: str, name: str = ""):
    users = _load_users()
    if email in users:
        return users[email]
    users[email] = {
        "email": email,
        "name": name,
        "plan": "free",
        "created": datetime.now().isoformat(),
        "expires": None,
        "api_key": f"ipl_{hash(email + str(time.time())) & 0xFFFFFFFF:08x}",
    }
    _save_users(users)
    return users[email]


def upgrade_user(email: str, plan: str, payment_id: str = ""):
    users = _load_users()
    if email not in users:
        register_user(email)
        users = _load_users()
    users[email]["plan"] = plan
    users[email]["payment_id"] = payment_id
    users[email]["upgraded"] = datetime.now().isoformat()
    users[email]["expires"] = (datetime.now() + timedelta(days=30)).isoformat()
    _save_users(users)
    return users[email]


def check_access(api_key: str, feature: str) -> bool:
    users = _load_users()
    user = None
    for u in users.values():
        if u.get("api_key") == api_key:
            user = u
            break
    if not user:
        return False
    plan = PLANS.get(user["plan"], PLANS["free"])
    return plan.get(feature, False)


def track_usage(api_key: str):
    usage = _load_usage()
    today = datetime.now().strftime("%Y-%m-%d")
    key = f"{api_key}:{today}"
    usage[key] = usage.get(key, 0) + 1
    _save_usage(usage)
    return usage[key]


def check_rate_limit(api_key: str) -> bool:
    users = _load_users()
    user = None
    for u in users.values():
        if u.get("api_key") == api_key:
            user = u
            break
    if not user:
        return False
    plan = PLANS.get(user["plan"], PLANS["free"])
    limit = plan["predictions_per_day"]
    if limit == -1:
        return True
    usage = _load_usage()
    today = datetime.now().strftime("%Y-%m-%d")
    key = f"{api_key}:{today}"
    return usage.get(key, 0) < limit


# ── Affiliate Links (Dream11, MPL, My11Circle) ──────────────────────

AFFILIATE_LINKS = {
    "dream11": {
        "name": "Dream11",
        "url": "https://dream11.com",  # Replace with your referral link
        "commission": "Up to ₹100 per referral",
        "description": "India's #1 Fantasy Sports Platform",
    },
    "mpl": {
        "name": "MPL (Mobile Premier League)",
        "url": "https://mpl.live",  # Replace with your referral link
        "commission": "Up to ₹75 per referral",
        "description": "Play Fantasy Cricket & Win Real Cash",
    },
    "my11circle": {
        "name": "My11Circle",
        "url": "https://my11circle.com",  # Replace with your referral link
        "commission": "Up to ₹500 signup bonus",
        "description": "Fantasy Cricket by Games24x7",
    },
    "paytm_first": {
        "name": "Paytm First Games",
        "url": "https://paytmfirstgames.com",
        "commission": "₹50 per referral",
        "description": "Fantasy Cricket on Paytm",
    },
}


def get_affiliate_banner(team1: str, team2: str):
    """Generate contextual affiliate recommendations after predictions."""
    return {
        "message": f"🏏 Use our AI-picked Dream11 team for {team1} vs {team2} and win big!",
        "platforms": AFFILIATE_LINKS,
        "cta": "Create your fantasy team with our AI picks →",
    }


# ── Revenue Calculator ───────────────────────────────────────────────

def estimate_monthly_revenue(
    free_users: int = 1000,
    pro_users: int = 50,
    elite_users: int = 10,
    ultra_users: int = 5,
    affiliate_clicks: int = 500,
    ad_pageviews: int = 50000,
):
    """Estimate monthly revenue from all streams."""
    sub_revenue = (
        pro_users * 199 +
        elite_users * 499 +
        ultra_users * 999
    )
    affiliate_revenue = affiliate_clicks * 5  # avg ₹5 per click conversion
    ad_revenue = (ad_pageviews / 1000) * 15  # ₹15 CPM average

    return {
        "subscription_revenue": sub_revenue,
        "affiliate_revenue": affiliate_revenue,
        "ad_revenue": round(ad_revenue),
        "total_monthly_inr": round(sub_revenue + affiliate_revenue + ad_revenue),
        "total_monthly_usd": round((sub_revenue + affiliate_revenue + ad_revenue) / 83, 2),
        "breakdown": {
            f"Pro ({pro_users} users × ₹199)": pro_users * 199,
            f"Elite ({elite_users} users × ₹499)": elite_users * 499,
            f"Ultra Premium ({ultra_users} users × ₹999)": ultra_users * 999,
            f"Affiliates ({affiliate_clicks} clicks)": affiliate_clicks * 5,
            f"Ads ({ad_pageviews} pageviews)": round(ad_revenue),
        },
    }
