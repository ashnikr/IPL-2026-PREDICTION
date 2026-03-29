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
  const [selectedPlan, setSelectedPlan] = useState("");

  useEffect(() => {
    fetch(`${API_BASE}/plans`)
      .then((r) => r.json())
      .then((d) => setPlans(d.plans || {}))
      .catch(() => {});
  }, []);

  const handleSubscribe = (planKey) => {
    setSelectedPlan(planKey);
    if (planKey === "free") return;
    window.location.href = `/payment?plan=${planKey}`;
  };

  return (
    <div>
      <div className="page-header" style={{ textAlign: "center" }}>
        <h1>Choose Your Plan</h1>
        <p>Pre-match predictions + After 1st innings predictions + Dream11 XI</p>
      </div>

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

            <button
              className={key === "pro" ? "btn btn-primary" : "btn btn-secondary"}
              style={{ width: "100%" }}
              onClick={() => handleSubscribe(key)}
            >
              {key === "free" ? "Free Access" : `Pay ₹${plan.price_inr} via UPI`}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
