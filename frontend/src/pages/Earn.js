import { useState } from "react";
import { FiDollarSign, FiShare2, FiStar, FiCopy, FiCheck } from "react-icons/fi";

const API_BASE = process.env.REACT_APP_API_URL || "https://ipl-2026-prediction-pxdp.onrender.com";

/*
  REPLACE THESE WITH YOUR ACTUAL REFERRAL LINKS:
  1. Dream11: https://affiliate.dream11.com → Sign up → Get link
  2. MPL: https://www.mpl.live/affiliate → Sign up → Get link
  3. My11Circle: https://my11circle.com/affiliate → Sign up → Get link
*/
const AFFILIATE_PLATFORMS = [
  {
    name: "Dream11",
    logo: "https://upload.wikimedia.org/wikipedia/en/thumb/a/a1/Dream11_logo.png/220px-Dream11_logo.png",
    referralLink: "https://dream11.com",  // REPLACE with your referral link
    commission: "₹100-₹500 per signup",
    description: "India's #1 Fantasy Sports App — 20 Cr+ users",
    color: "#e4002b",
    cta: "Join & Get ₹100 Bonus",
  },
  {
    name: "MPL",
    logo: "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0e/MPL_Logo.svg/220px-MPL_Logo.svg.png",
    referralLink: "https://mpl.live",  // REPLACE with your referral link
    commission: "₹75 per referral",
    description: "Play Fantasy Cricket & Win Real Cash",
    color: "#ff6b00",
    cta: "Download MPL & Win",
  },
  {
    name: "My11Circle",
    logo: "https://play-lh.googleusercontent.com/F-WkMGIm4K7CRfKBMmm_RnOEdm6h2-qPWc-X35sgRNc7gXAGt-Yx8aSgZQbVr_UM7A=w240-h480",
    referralLink: "https://my11circle.com",  // REPLACE with your referral link
    commission: "₹500 signup bonus",
    description: "Fantasy Cricket by Games24x7 — Sourav Ganguly",
    color: "#1a237e",
    cta: "Get ₹500 Free",
  },
  {
    name: "Paytm First Games",
    logo: "https://play-lh.googleusercontent.com/FRpUuEO_oJQQKEHzDB4r5JOv_PKplGc5rhYbPyX1e1hEVBBzONu6ZD4lRmmCNw-gUg=w240-h480",
    referralLink: "https://paytmfirstgames.com",  // REPLACE with your referral link
    commission: "₹50 per referral",
    description: "Fantasy Cricket on Paytm",
    color: "#00b9f5",
    cta: "Play Now",
  },
];

const SUBSCRIPTION_PLANS = [
  {
    name: "Free",
    price: "₹0",
    features: ["Form & news only", "No predictions", "Schedule & teams"],
    recommended: false,
  },
  {
    name: "Pro",
    price: "₹199/mo",
    priceUSD: "$2.49/mo",
    features: [
      "Unlimited predictions",
      "Dream11 Fantasy XI",
      "10 AI Agents + LLM",
      "News & sentiment analysis",
      "Head-to-head stats",
    ],
    recommended: true,
    upiId: "nikhil.rajak2106@oksbi",  // REPLACE with your UPI ID
  },
  {
    name: "Elite",
    price: "₹499/mo",
    priceUSD: "$5.99/mo",
    features: [
      "Everything in Pro",
      "Post-toss auto-predictions",
      "1st innings chase predictions",
      "Telegram match alerts",
    ],
    recommended: false,
    upiId: "nikhil.rajak2106@oksbi",  // REPLACE with your UPI ID
  },
  {
    name: "Ultra Premium",
    price: "₹999/mo",
    priceUSD: "$11.99/mo",
    features: [
      "Everything in Elite",
      "Live ball-by-ball predictions",
      "Real-time Telegram alerts",
      "RL-corrected AI models",
      "Dedicated support",
    ],
    recommended: false,
    upiId: "nikhil.rajak2106@oksbi",  // REPLACE with your UPI ID
  },
];

export default function Earn() {
  const [copied, setCopied] = useState("");
  const [email, setEmail] = useState("");
  const [subMsg, setSubMsg] = useState("");

  const copyLink = (link, name) => {
    navigator.clipboard.writeText(link);
    setCopied(name);
    setTimeout(() => setCopied(""), 2000);
  };

  const handleSubscribe = (plan) => {
    if (plan.name === "Free") {
      if (!email) return setSubMsg("Enter your email first");
      fetch(`${API_BASE}/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, name: "" }),
      }).then(() => setSubMsg("Registered on Free plan!")).catch(() => setSubMsg("Try again."));
      return;
    }
    // Redirect to payment page
    const planKey = plan.name === "Pro" ? "pro" : plan.name === "Elite" ? "elite" : "ultra_premium";
    window.location.href = `/payment?plan=${planKey}`;
  };

  return (
    <div>
      <div className="page-header">
        <h1>Start Earning</h1>
        <p>Multiple revenue streams — affiliates, subscriptions, ads, Telegram bot</p>
      </div>

      {/* Revenue Overview */}
      <div className="grid-4" style={{ marginBottom: 32 }}>
        <div className="stat-card">
          <div className="stat-value" style={{ fontSize: 20, color: "var(--green)" }}>₹15K-₹50K</div>
          <div className="stat-label">Monthly Potential</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ fontSize: 20, color: "var(--accent)" }}>5</div>
          <div className="stat-label">Revenue Streams</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ fontSize: 20, color: "var(--blue)" }}>₹0</div>
          <div className="stat-label">Setup Cost</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ fontSize: 20, color: "var(--purple)" }}>IPL Season</div>
          <div className="stat-label">Peak Earning</div>
        </div>
      </div>

      {/* STREAM 1: Fantasy Affiliates */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-header">
          <h2 className="card-title"><FiDollarSign style={{ marginRight: 8 }} />Stream 1: Fantasy Affiliates (Fastest Money)</h2>
          <span className="badge badge-green">₹100-₹500 per signup</span>
        </div>
        <p style={{ color: "var(--text-secondary)", marginBottom: 20, fontSize: 14 }}>
          Share these links after every prediction. When users sign up through your link, you earn commission instantly.
        </p>

        <div className="grid-2">
          {AFFILIATE_PLATFORMS.map((p) => (
            <div key={p.name} className="card" style={{ borderColor: p.color + "44" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                <div>
                  <h3 style={{ fontSize: 16, fontWeight: 700 }}>{p.name}</h3>
                  <p style={{ fontSize: 12, color: "var(--text-muted)" }}>{p.description}</p>
                </div>
                <span className="badge badge-green">{p.commission}</span>
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <a
                  href={p.referralLink}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-primary"
                  style={{ flex: 1, justifyContent: "center", background: p.color }}
                >
                  {p.cta}
                </a>
                <button
                  className="btn btn-secondary"
                  onClick={() => copyLink(p.referralLink, p.name)}
                  title="Copy referral link"
                >
                  {copied === p.name ? <FiCheck /> : <FiCopy />}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* STREAM 2: Subscriptions */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-header">
          <h2 className="card-title"><FiStar style={{ marginRight: 8 }} />Stream 2: Premium Subscriptions</h2>
          <span className="badge badge-orange">₹199-₹999/month per user</span>
        </div>

        <div className="form-group" style={{ maxWidth: 400, marginBottom: 20 }}>
          <input
            className="form-control"
            type="email"
            placeholder="Enter email to subscribe"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>

        {subMsg && (
          <div className="card" style={{ marginBottom: 16, padding: 16, background: "var(--bg-secondary)" }}>
            <p style={{ fontSize: 14, color: "var(--green)" }}>{subMsg}</p>
          </div>
        )}

        <div className="grid-4">
          {SUBSCRIPTION_PLANS.map((plan) => (
            <div
              key={plan.name}
              className="card"
              style={{
                borderColor: plan.recommended ? "var(--accent)" : "var(--border)",
                position: "relative",
              }}
            >
              {plan.recommended && (
                <div style={{
                  position: "absolute", top: -12, left: "50%", transform: "translateX(-50%)",
                  background: "var(--accent)", color: "white", padding: "2px 16px",
                  borderRadius: 12, fontSize: 11, fontWeight: 700,
                }}>
                  MOST POPULAR
                </div>
              )}
              <div style={{ textAlign: "center", padding: "16px 0" }}>
                <h3 style={{ fontSize: 18, fontWeight: 700, marginBottom: 4 }}>{plan.name}</h3>
                <div style={{ fontSize: 28, fontWeight: 800, color: plan.recommended ? "var(--accent)" : "var(--text-primary)" }}>
                  {plan.price}
                </div>
                {plan.priceUSD && <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{plan.priceUSD}</div>}
              </div>
              <div style={{ marginBottom: 16 }}>
                {plan.features.map((f, i) => (
                  <div key={i} style={{ fontSize: 13, padding: "4px 0", color: "var(--text-secondary)" }}>
                    ✓ {f}
                  </div>
                ))}
              </div>
              <button
                className={plan.recommended ? "btn btn-primary" : "btn btn-secondary"}
                style={{ width: "100%" }}
                onClick={() => handleSubscribe(plan)}
              >
                {plan.name === "Free" ? "Get Started" : `Pay ${plan.price} via UPI`}
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* STREAM 3: Telegram Bot */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-header">
          <h2 className="card-title">Stream 3: Telegram Bot</h2>
          <span className="badge badge-blue">t.me/Nikhil2026_bot</span>
        </div>
        <p style={{ color: "var(--text-secondary)", fontSize: 14, marginBottom: 16 }}>
          Share your bot in WhatsApp cricket groups, Instagram stories, and Twitter. Free commands bring users in, premium commands convert them to paid.
        </p>
        <div className="grid-3">
          <div className="stat-card">
            <div className="stat-value" style={{ fontSize: 16, color: "var(--green)" }}>Free</div>
            <div className="stat-label">/form /news /teams</div>
          </div>
          <div className="stat-card">
            <div className="stat-value" style={{ fontSize: 16, color: "var(--accent)" }}>₹199 Pro</div>
            <div className="stat-label">/predict /dream11 /agents</div>
          </div>
          <div className="stat-card">
            <div className="stat-value" style={{ fontSize: 16, color: "var(--purple)" }}>₹499 Elite</div>
            <div className="stat-label">Post-toss + 1st innings</div>
          </div>
        </div>
        <div style={{ marginTop: 16, display: "flex", gap: 8 }}>
          <button className="btn btn-primary" onClick={() => copyLink("https://t.me/Nikhil2026_bot", "telegram")}>
            {copied === "telegram" ? <><FiCheck /> Copied!</> : <><FiCopy /> Copy Bot Link</>}
          </button>
          <a href="https://t.me/Nikhil2026_bot" target="_blank" rel="noopener noreferrer" className="btn btn-secondary">
            Open Bot
          </a>
        </div>
      </div>

      {/* STREAM 4 & 5 */}
      <div className="grid-2" style={{ marginBottom: 24 }}>
        <div className="card">
          <h3 className="card-title">Stream 4: Google AdSense</h3>
          <p style={{ color: "var(--text-secondary)", fontSize: 14, marginBottom: 12 }}>
            Passive income from ads on your website. ₹15 CPM average during IPL season.
          </p>
          <div className="stat-card" style={{ marginBottom: 12 }}>
            <div className="stat-value" style={{ fontSize: 18, color: "var(--green)" }}>₹750-₹3K/mo</div>
            <div className="stat-label">With 50K pageviews</div>
          </div>
          <p style={{ fontSize: 12, color: "var(--text-muted)" }}>
            Steps: Apply at adsense.google.com → Get approved → Ads auto-show on your site
          </p>
        </div>

        <div className="card">
          <h3 className="card-title">Stream 5: Telegram Bot Growth</h3>
          <p style={{ color: "var(--text-secondary)", fontSize: 14, marginBottom: 12 }}>
            Share your bot in WhatsApp cricket groups, Instagram stories, and Twitter during IPL season.
          </p>
          <div className="stat-card" style={{ marginBottom: 12 }}>
            <div className="stat-value" style={{ fontSize: 18, color: "var(--accent)" }}>₹199-₹999</div>
            <div className="stat-label">Per subscriber/month</div>
          </div>
          <p style={{ fontSize: 12, color: "var(--text-muted)" }}>
            100 Pro users = ₹19,900/month | 20 Ultra Premium = ₹19,980/month
          </p>
        </div>
      </div>

      {/* Share for Growth */}
      <div className="card" style={{ textAlign: "center", padding: 32 }}>
        <FiShare2 size={32} color="var(--accent)" />
        <h2 style={{ marginTop: 12, marginBottom: 8 }}>Share & Grow</h2>
        <p style={{ color: "var(--text-secondary)", marginBottom: 20 }}>
          More users = More affiliate earnings + More subscribers
        </p>
        <div style={{ display: "flex", gap: 8, justifyContent: "center", flexWrap: "wrap" }}>
          <a
            href={`https://api.whatsapp.com/send?text=${encodeURIComponent("🏏 Free IPL 2026 AI Predictions! 10 AI Agents + Dream11 XI + Live Mid-Match 🔥\n\n🤖 Telegram Bot: https://t.me/Nikhil2026_bot\n🌐 Website: https://ipl-2026-prediction.vercel.app\n\nTry /predict CSK MI on the bot!")}`}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-primary"
            style={{ background: "#25D366" }}
          >
            Share on WhatsApp
          </a>
          <a
            href={`https://twitter.com/intent/tweet?text=${encodeURIComponent("🏏 Built an AI system that predicts IPL matches with 10 AI Agents + 8 ML Models!\n\n🤖 Free Telegram Bot: https://t.me/Nikhil2026_bot\n🌐 Website: https://ipl-2026-prediction.vercel.app\n\n#IPL2026 #Cricket #AI #Dream11")}`}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-primary"
            style={{ background: "#1DA1F2" }}
          >
            Share on Twitter/X
          </a>
          <button
            className="btn btn-secondary"
            onClick={() => copyLink("https://ipl-2026-prediction.vercel.app", "site")}
          >
            {copied === "site" ? <><FiCheck /> Copied!</> : <><FiCopy /> Copy Website Link</>}
          </button>
        </div>
      </div>
    </div>
  );
}
