import { FiCheck, FiStar, FiZap } from "react-icons/fi";

const UPI_ID = "nikhil.rajak2106@oksbi";
const TELEGRAM_BOT = "https://t.me/Nikhil2026_bot";

const PLANS = [
  {
    key: "basic",
    name: "Basic",
    price: 199,
    icon: <FiZap size={28} />,
    color: "var(--accent)",
    popular: false,
    features: [
      "Pre-match AI predictions",
      "After 1st innings predictions",
      "Pitch, form, H2H, weather analysis",
      "Win probability with confidence %",
      "Private Telegram group access",
    ],
  },
  {
    key: "pro",
    name: "Pro",
    price: 399,
    icon: <FiStar size={28} />,
    color: "var(--purple)",
    popular: true,
    features: [
      "Everything in Basic",
      "Best Dream11 Playing XI",
      "Captain & Vice-Captain picks",
      "Credit-optimized team from actual Playing XI",
      "Private Telegram group access",
    ],
  },
];

export default function Pricing() {
  const handlePay = (plan) => {
    const note = `IPL2026-${plan.name}`;
    const upi = `upi://pay?pa=${UPI_ID}&pn=IPL2026+Predictions&am=${plan.price}&cu=INR&tn=${note}`;
    window.open(upi, "_blank");
  };

  return (
    <div>
      <div className="page-header" style={{ textAlign: "center" }}>
        <h1>IPL 2026 AI Predictions</h1>
        <p>Join our private Telegram group for daily match predictions</p>
      </div>

      <div className="grid-2" style={{ maxWidth: 700, margin: "0 auto" }}>
        {PLANS.map((plan) => (
          <div
            className="card"
            key={plan.key}
            style={{
              borderColor: plan.popular ? plan.color : "var(--border)",
              position: "relative",
              overflow: "hidden",
            }}
          >
            {plan.popular && (
              <div style={{
                position: "absolute", top: 12, right: -30,
                background: "var(--gradient-1)", color: "white",
                padding: "2px 40px", fontSize: 11, fontWeight: 700,
                transform: "rotate(45deg)",
              }}>
                BEST VALUE
              </div>
            )}

            <div style={{ textAlign: "center", marginBottom: 20 }}>
              <div style={{ color: plan.color, marginBottom: 8 }}>{plan.icon}</div>
              <h3 style={{ fontSize: 20, fontWeight: 800 }}>{plan.name}</h3>
              <div style={{ marginTop: 8 }}>
                <span style={{ fontSize: 32, fontWeight: 800, color: plan.color }}>
                  ₹{plan.price}
                </span>
                <span style={{ color: "var(--text-muted)", fontSize: 14 }}>/month</span>
              </div>
            </div>

            <div style={{ marginBottom: 20 }}>
              {plan.features.map((f, i) => (
                <div key={i} style={{ display: "flex", gap: 8, alignItems: "start", marginBottom: 8, fontSize: 13 }}>
                  <FiCheck style={{ color: "var(--green)", flexShrink: 0, marginTop: 2 }} />
                  <span>{f}</span>
                </div>
              ))}
            </div>

            <button
              className={plan.popular ? "btn btn-primary" : "btn btn-secondary"}
              style={{ width: "100%", marginBottom: 8 }}
              onClick={() => handlePay(plan)}
            >
              Pay ₹{plan.price} via UPI
            </button>

            <a
              href={TELEGRAM_BOT}
              target="_blank"
              rel="noreferrer"
              className="btn btn-secondary"
              style={{ width: "100%", display: "block", textAlign: "center", textDecoration: "none" }}
            >
              Or Pay via Telegram Bot
            </a>
          </div>
        ))}
      </div>

      {/* How it works */}
      <div className="card" style={{ maxWidth: 700, margin: "28px auto 0" }}>
        <h3 style={{ marginBottom: 16, fontSize: 16 }}>How It Works</h3>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {[
            { step: "1", text: "Choose Basic (₹199) or Pro (₹399) plan" },
            { step: "2", text: `Pay via UPI to ${UPI_ID}` },
            { step: "3", text: "Send payment screenshot on Telegram bot" },
            { step: "4", text: "Get private group invite link within minutes" },
            { step: "5", text: "Receive daily predictions in the group!" },
          ].map((s) => (
            <div key={s.step} style={{ display: "flex", gap: 12, alignItems: "center" }}>
              <div style={{
                width: 28, height: 28, borderRadius: "50%",
                background: "var(--gradient-1)", color: "white",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontWeight: 700, fontSize: 13, flexShrink: 0,
              }}>
                {s.step}
              </div>
              <span style={{ fontSize: 14 }}>{s.text}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
