import { useState, useEffect } from "react";
import { FiCheck, FiStar, FiZap, FiAward } from "react-icons/fi";

const API_BASE = process.env.REACT_APP_API_URL || "https://ipl-2026-prediction-pxdp.onrender.com";

const PLAN_ICONS = {
  free: <FiZap size={28} />,
  pro: <FiStar size={28} />,
  elite: <FiAward size={28} />,
  ultra_premium: <FiAward size={28} />,
};

const PLAN_COLORS = {
  free: "var(--text-muted)",
  pro: "var(--accent)",
  elite: "var(--purple)",
  ultra_premium: "var(--green)",
};

export default function Pricing() {
  const [plans, setPlans] = useState({});
  const [email, setEmail] = useState("");
  const [selectedPlan, setSelectedPlan] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    fetch(`${API_BASE}/plans`)
      .then((r) => r.json())
      .then((d) => setPlans(d.plans || {}))
      .catch(() => {});
  }, []);

  const handleSubscribe = async (planKey) => {
    setSelectedPlan(planKey);

    if (planKey === "free") {
      if (!email) return setMessage("Enter your email first");
      await fetch(`${API_BASE}/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, name: "" }),
      });
      setMessage("You're registered on the Free plan! Start predicting now.");
      return;
    }

    // Redirect to payment page
    window.location.href = `/payment?plan=${planKey}`;
  };

  return (
    <div>
      <div className="page-header" style={{ textAlign: "center" }}>
        <h1>Choose Your Plan</h1>
        <p>Unlock the full power of AI-driven cricket predictions</p>
      </div>

      <div className="form-group" style={{ maxWidth: 400, margin: "0 auto 32px" }}>
        <input
          className="form-control"
          type="email"
          placeholder="Enter your email to get started"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          style={{ textAlign: "center", fontSize: 16 }}
        />
      </div>

      {message && (
        <div className="card" style={{ maxWidth: 600, margin: "0 auto 24px", textAlign: "center" }}>
          <p style={{ color: "var(--green)" }}>{message}</p>
        </div>
      )}

      <div className="grid-4">
        {Object.entries(plans).map(([key, plan]) => (
          <div
            className="card"
            key={key}
            style={{
              borderColor: selectedPlan === key ? PLAN_COLORS[key] : "var(--border)",
              position: "relative",
              overflow: "hidden",
            }}
          >
            {key === "ultra_premium" && (
              <div style={{
                position: "absolute", top: 12, right: -30,
                background: "linear-gradient(135deg, #00c853, #00e676)", color: "white",
                padding: "2px 40px", fontSize: 11, fontWeight: 700,
                transform: "rotate(45deg)",
              }}>
                BEST VALUE
              </div>
            )}
            {key === "pro" && (
              <div style={{
                position: "absolute", top: 12, right: -30,
                background: "var(--gradient-1)", color: "white",
                padding: "2px 40px", fontSize: 11, fontWeight: 700,
                transform: "rotate(45deg)",
              }}>
                POPULAR
              </div>
            )}

            <div style={{ textAlign: "center", marginBottom: 20 }}>
              <div style={{ color: PLAN_COLORS[key], marginBottom: 8 }}>{PLAN_ICONS[key]}</div>
              <h3 style={{ fontSize: 20, fontWeight: 800 }}>{plan.name}</h3>
              <div style={{ marginTop: 8 }}>
                {plan.price_inr > 0 ? (
                  <>
                    <span style={{ fontSize: 32, fontWeight: 800, color: PLAN_COLORS[key] }}>
                      ₹{plan.price_inr}
                    </span>
                    <span style={{ color: "var(--text-muted)", fontSize: 14 }}>/month</span>
                    <div style={{ fontSize: 12, color: "var(--text-muted)" }}>(${plan.price_usd}/mo)</div>
                  </>
                ) : (
                  <span style={{ fontSize: 32, fontWeight: 800, color: "var(--green)" }}>FREE</span>
                )}
              </div>
            </div>

            <div style={{ marginBottom: 20 }}>
              {plan.features?.map((f, i) => (
                <div key={i} style={{ display: "flex", gap: 8, alignItems: "start", marginBottom: 8, fontSize: 13 }}>
                  <FiCheck style={{ color: "var(--green)", flexShrink: 0, marginTop: 2 }} />
                  <span>{f}</span>
                </div>
              ))}
            </div>

            <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 16 }}>
              {plan.predictions_per_day === -1
                ? "Unlimited predictions"
                : `${plan.predictions_per_day} predictions/day`}
            </div>

            <button
              className={key === "pro" ? "btn btn-primary" : "btn btn-secondary"}
              style={{ width: "100%" }}
              onClick={() => handleSubscribe(key)}
            >
              {key === "free" ? "Get Started" : "Subscribe"}
            </button>
          </div>
        ))}
      </div>

      {/* Revenue info for owner */}
      <div className="card" style={{ marginTop: 40, textAlign: "center" }}>
        <h3 className="card-title" style={{ marginBottom: 8 }}>Revenue Streams</h3>
        <p style={{ color: "var(--text-secondary)", fontSize: 14 }}>
          Subscriptions + Fantasy Affiliates + Google AdSense + API-as-a-Service + Telegram Bot
        </p>
        <div className="grid-4" style={{ marginTop: 20 }}>
          <div className="stat-card">
            <div className="stat-value" style={{ fontSize: 20, color: "var(--accent)" }}>₹199-₹999</div>
            <div className="stat-label">Subscriptions</div>
          </div>
          <div className="stat-card">
            <div className="stat-value" style={{ fontSize: 20, color: "var(--green)" }}>₹50-₹500</div>
            <div className="stat-label">Per Referral</div>
          </div>
          <div className="stat-card">
            <div className="stat-value" style={{ fontSize: 20, color: "var(--blue)" }}>₹15 CPM</div>
            <div className="stat-label">Ad Revenue</div>
          </div>
          <div className="stat-card">
            <div className="stat-value" style={{ fontSize: 20, color: "var(--purple)" }}>5+</div>
            <div className="stat-label">Revenue Streams</div>
          </div>
        </div>
      </div>
    </div>
  );
}
