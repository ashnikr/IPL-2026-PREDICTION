import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { FiCheck, FiCopy, FiSmartphone, FiShield } from "react-icons/fi";

const UPI_ID = "nikhil.rajak2106@oksbi";
const UPI_NAME = "IPL2026 Predictions";
const TELEGRAM_BOT = "https://t.me/Nikhil2026_bot";

const PLANS = {
  basic: {
    name: "Basic", amount: 199, color: "#f59e0b",
    features: [
      "Pre-match AI predictions",
      "After 1st innings predictions",
      "Pitch, form, H2H, weather analysis",
      "Private Telegram group access",
    ],
  },
  pro: {
    name: "Pro", amount: 399, color: "#8b5cf6",
    features: [
      "Everything in Basic",
      "Best Dream11 Playing XI",
      "Captain & Vice-Captain picks",
      "Credit-optimized team",
      "Private Telegram group access",
    ],
  },
};

export default function Payment() {
  const [params] = useSearchParams();
  const planKey = params.get("plan") || "basic";
  const plan = PLANS[planKey] || PLANS.basic;

  const [copied, setCopied] = useState(false);

  const upiLink = `upi://pay?pa=${UPI_ID}&pn=${encodeURIComponent(UPI_NAME)}&am=${plan.amount}&cu=INR&tn=IPL2026-${plan.name}`;
  const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=${encodeURIComponent(upiLink)}`;

  const copyUPI = () => {
    navigator.clipboard.writeText(UPI_ID);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div style={{ maxWidth: 600, margin: "0 auto" }}>
      {/* Plan Header */}
      <div className="card" style={{ textAlign: "center", borderColor: plan.color, borderWidth: 2 }}>
        <h1 style={{ fontSize: 28, fontWeight: 800, marginBottom: 4 }}>{plan.name} Plan</h1>
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
              flex: 1, justifyContent: "center",
              borderColor: planKey === key ? p.color : "var(--border)",
              color: planKey === key ? p.color : "var(--text-secondary)",
              fontWeight: planKey === key ? 700 : 400,
              textDecoration: "none",
            }}
          >
            {p.name} ₹{p.amount}
          </a>
        ))}
      </div>

      {/* QR Code */}
        <>
          <div className="card" style={{ textAlign: "center" }}>
            <h3 style={{ marginBottom: 16 }}>
              <FiSmartphone style={{ marginRight: 8 }} />
              Scan QR to Pay
            </h3>
            <div style={{
              background: "white", display: "inline-block", padding: 16, borderRadius: 12, marginBottom: 16,
            }}>
              <img src={qrUrl} alt={`Pay ₹${plan.amount}`} style={{ width: 220, height: 220 }} />
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
              background: "var(--bg-secondary)", padding: "12px 16px", borderRadius: 8, marginBottom: 12,
            }}>
              <span style={{ flex: 1, fontFamily: "monospace", fontSize: 16 }}>{UPI_ID}</span>
              <button className="btn btn-secondary" onClick={copyUPI} style={{ padding: "6px 12px" }}>
                {copied ? <><FiCheck /> Copied!</> : <><FiCopy /> Copy</>}
              </button>
            </div>
            <div style={{ fontSize: 14, color: "var(--text-secondary)" }}>
              <p>1. Open any UPI app</p>
              <p>2. Send <strong>₹{plan.amount}</strong> to the UPI ID above</p>
              <p>3. Send screenshot on Telegram bot</p>
            </div>
          </div>

          {/* UPI Deep Link */}
          <a
            href={upiLink}
            className="btn btn-primary"
            style={{
              width: "100%", justifyContent: "center", padding: "16px 24px",
              fontSize: 18, fontWeight: 700, margin: "16px 0", background: plan.color,
              display: "flex", textDecoration: "none",
            }}
          >
            Pay ₹{plan.amount} Now
          </a>

          {/* After Payment */}
          <div className="card" style={{ marginTop: 8 }}>
            <h3 style={{ marginBottom: 12 }}>After Payment</h3>
            <p style={{ fontSize: 14, color: "var(--text-secondary)", marginBottom: 16 }}>
              Send your payment screenshot to our Telegram bot to get your group invite link.
            </p>
            <a
              href={TELEGRAM_BOT}
              target="_blank"
              rel="noreferrer"
              className="btn btn-primary"
              style={{
                width: "100%", justifyContent: "center", padding: "14px 24px",
                fontSize: 16, display: "flex", textDecoration: "none",
              }}
            >
              Send Screenshot on Telegram Bot
            </a>
            <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 12, textAlign: "center" }}>
              Or send directly to @Nikhil2026 on Telegram
            </p>
          </div>

          {/* Trust */}
          <div style={{ display: "flex", gap: 16, justifyContent: "center", margin: "24px 0", flexWrap: "wrap" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--text-muted)" }}>
              <FiShield style={{ color: "#10b981" }} /> Secure UPI Payment
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--text-muted)" }}>
              <FiCheck style={{ color: "#10b981" }} /> Group Access in Minutes
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--text-muted)" }}>
              <FiSmartphone style={{ color: "#10b981" }} /> GPay / PhonePe / Paytm
            </div>
          </div>
        </>
    </div>
  );
}
