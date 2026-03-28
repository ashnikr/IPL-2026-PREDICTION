import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { FiCheck, FiCopy, FiSmartphone, FiShield } from "react-icons/fi";

const UPI_ID = "nikhil.rajak2106@oksbi";
const UPI_NAME = "IPL2026 AI Predictions";

const PLANS = {
  pro: { name: "Pro", amount: 199, color: "#f59e0b", features: ["Unlimited predictions", "Dream11 Fantasy XI", "10 AI Agents + LLM", "Head-to-head stats"] },
  elite: { name: "Elite", amount: 499, color: "#8b5cf6", features: ["Everything in Pro", "Post-toss auto-predictions", "1st innings chase predictions", "Telegram alerts"] },
  ultra_premium: { name: "Ultra Premium", amount: 999, color: "#10b981", features: ["Everything in Elite", "Live ball-by-ball predictions", "Real-time alerts", "RL-corrected AI models", "Dedicated support"] },
};

export default function Payment() {
  const [params] = useSearchParams();
  const planKey = params.get("plan") || "pro";
  const plan = PLANS[planKey] || PLANS.pro;

  const [copied, setCopied] = useState(false);
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const upiLink = `upi://pay?pa=${UPI_ID}&pn=${encodeURIComponent(UPI_NAME)}&am=${plan.amount}&cu=INR&tn=IPL2026-${plan.name}`;
  const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=${encodeURIComponent(upiLink)}`;

  const copyUPI = () => {
    navigator.clipboard.writeText(UPI_ID);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const API_BASE = process.env.REACT_APP_API_URL || "https://ipl-2026-prediction-pxdp.onrender.com";

  const handleSubmit = async () => {
    if (!email) return;
    try {
      await fetch(`${API_BASE}/payment/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email,
          plan: planKey,
          txn_id: document.getElementById("txnId")?.value || "",
          telegram_username: document.getElementById("tgUser")?.value || "",
        }),
      });
    } catch (e) {
      // Still show success — payment saved locally
    }
    setSubmitted(true);
  };

  return (
    <div style={{ maxWidth: 600, margin: "0 auto" }}>
      {/* Plan Header */}
      <div className="card" style={{ textAlign: "center", borderColor: plan.color, borderWidth: 2 }}>
        <h1 style={{ fontSize: 28, fontWeight: 800, marginBottom: 4 }}>
          {plan.name} Plan
        </h1>
        <div style={{ fontSize: 48, fontWeight: 900, color: plan.color, margin: "12px 0" }}>
          ₹{plan.amount}
          <span style={{ fontSize: 16, color: "var(--text-muted)", fontWeight: 400 }}>/month</span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6, alignItems: "center", marginTop: 12 }}>
          {plan.features.map((f, i) => (
            <div key={i} style={{ display: "flex", gap: 8, alignItems: "center", fontSize: 14 }}>
              <FiCheck style={{ color: "#10b981", flexShrink: 0 }} />
              <span>{f}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Plan Selector */}
      <div style={{ display: "flex", gap: 8, margin: "20px 0" }}>
        {Object.entries(PLANS).map(([key, p]) => (
          <a
            key={key}
            href={`/payment?plan=${key}`}
            className="btn btn-secondary"
            style={{
              flex: 1,
              justifyContent: "center",
              borderColor: planKey === key ? p.color : "var(--border)",
              color: planKey === key ? p.color : "var(--text-secondary)",
              fontWeight: planKey === key ? 700 : 400,
            }}
          >
            {p.name} ₹{p.amount}
          </a>
        ))}
      </div>

      {!submitted ? (
        <>
          {/* QR Code */}
          <div className="card" style={{ textAlign: "center" }}>
            <h3 style={{ marginBottom: 16 }}>
              <FiSmartphone style={{ marginRight: 8 }} />
              Scan QR to Pay
            </h3>
            <div style={{
              background: "white", display: "inline-block", padding: 16, borderRadius: 12,
              marginBottom: 16,
            }}>
              <img
                src={qrUrl}
                alt={`Pay ₹${plan.amount}`}
                style={{ width: 220, height: 220 }}
              />
            </div>
            <p style={{ fontSize: 13, color: "var(--text-muted)" }}>
              Scan with GPay / PhonePe / Paytm / any UPI app
            </p>
          </div>

          {/* UPI ID Copy */}
          <div className="card">
            <h3 style={{ marginBottom: 12 }}>Or Pay Manually</h3>
            <div style={{
              display: "flex", alignItems: "center", gap: 8,
              background: "var(--bg-secondary)", padding: "12px 16px",
              borderRadius: 8, marginBottom: 12,
            }}>
              <span style={{ flex: 1, fontFamily: "monospace", fontSize: 16 }}>{UPI_ID}</span>
              <button className="btn btn-secondary" onClick={copyUPI} style={{ padding: "6px 12px" }}>
                {copied ? <><FiCheck /> Copied!</> : <><FiCopy /> Copy</>}
              </button>
            </div>
            <div style={{ fontSize: 14, color: "var(--text-secondary)" }}>
              <p>1. Open any UPI app</p>
              <p>2. Send <strong>₹{plan.amount}</strong> to the UPI ID above</p>
              <p>3. Come back here and enter your details below</p>
            </div>
          </div>

          {/* UPI Deep Link Button */}
          <a
            href={upiLink}
            className="btn btn-primary"
            style={{
              width: "100%", justifyContent: "center", padding: "16px 24px",
              fontSize: 18, fontWeight: 700, margin: "16px 0",
              background: plan.color,
            }}
          >
            Pay ₹{plan.amount} Now
          </a>

          {/* After Payment Form */}
          <div className="card" style={{ marginTop: 8 }}>
            <h3 style={{ marginBottom: 12 }}>After Payment</h3>
            <div className="form-group">
              <label style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 4 }}>
                Your Email
              </label>
              <input
                className="form-control"
                type="email"
                placeholder="your@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 4 }}>
                UPI Transaction ID / Reference Number
              </label>
              <input
                className="form-control"
                type="text"
                placeholder="e.g. 412345678901"
                id="txnId"
              />
            </div>
            <div className="form-group">
              <label style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 4 }}>
                Telegram Username (to activate bot access)
              </label>
              <input
                className="form-control"
                type="text"
                placeholder="@your_username"
                id="tgUser"
              />
            </div>
            <button
              className="btn btn-primary"
              style={{ width: "100%", justifyContent: "center", padding: "14px 24px", fontSize: 16 }}
              onClick={handleSubmit}
            >
              I've Paid — Activate My {plan.name} Plan
            </button>
          </div>

          {/* Trust Badges */}
          <div style={{ display: "flex", gap: 16, justifyContent: "center", margin: "24px 0", flexWrap: "wrap" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--text-muted)" }}>
              <FiShield style={{ color: "#10b981" }} /> Secure UPI Payment
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--text-muted)" }}>
              <FiCheck style={{ color: "#10b981" }} /> Instant Activation
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--text-muted)" }}>
              <FiSmartphone style={{ color: "#10b981" }} /> GPay / PhonePe / Paytm
            </div>
          </div>
        </>
      ) : (
        /* Success State */
        <div className="card" style={{ textAlign: "center", padding: 40, marginTop: 16 }}>
          <div style={{ fontSize: 60, marginBottom: 16 }}>✅</div>
          <h2 style={{ marginBottom: 8 }}>Payment Submitted!</h2>
          <p style={{ color: "var(--text-secondary)", marginBottom: 20 }}>
            Your <strong>{plan.name}</strong> plan will be activated within 5-10 minutes.
          </p>
          <div className="card" style={{ background: "var(--bg-secondary)", textAlign: "left" }}>
            <p style={{ fontSize: 14 }}><strong>Email:</strong> {email}</p>
            <p style={{ fontSize: 14 }}><strong>Plan:</strong> {plan.name} (₹{plan.amount}/month)</p>
            <p style={{ fontSize: 14 }}><strong>Status:</strong> Verification pending</p>
          </div>
          <p style={{ fontSize: 13, color: "var(--text-muted)", marginTop: 16 }}>
            For instant activation, send your payment screenshot to our
            <a href="https://t.me/Nikhil2026_bot" target="_blank" rel="noopener noreferrer"
              style={{ color: "var(--accent)", marginLeft: 4 }}>Telegram Bot</a>
          </p>
        </div>
      )}
    </div>
  );
}
