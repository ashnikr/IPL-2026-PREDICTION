import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { healthCheck, predictToday, getTeams } from "../api";
import Loading from "../components/Loading";
import ProbBar from "../components/ProbBar";
import { FiZap, FiStar, FiRadio, FiUsers } from "react-icons/fi";

export default function Dashboard() {
  const [health, setHealth] = useState(null);
  const [todayPreds, setTodayPreds] = useState(null);
  const [teams, setTeams] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.allSettled([
      healthCheck(),
      predictToday(),
      getTeams(),
    ]).then(([h, p, t]) => {
      if (h.status === "fulfilled") setHealth(h.value.data);
      if (p.status === "fulfilled") setTodayPreds(p.value.data);
      if (t.status === "fulfilled") setTeams(t.value.data.teams || []);
      setLoading(false);
    });
  }, []);

  if (loading) return <Loading text="Loading dashboard..." />;

  return (
    <div>
      <div className="page-header">
        <h1>IPL 2026 AI Prediction Hub</h1>
        <p>10 AI Agents + 8 ML Models + LLM Analysis + Fantasy Cricket</p>
      </div>

      {/* Quick Stats */}
      <div className="grid-4" style={{ marginBottom: 28 }}>
        <div className="stat-card">
          <div className="stat-value" style={{ color: "var(--green)" }}>
            {health?.status === "healthy" ? "Live" : "---"}
          </div>
          <div className="stat-label">API Status</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: "var(--accent)" }}>10</div>
          <div className="stat-label">AI Agents</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: "var(--blue)" }}>8</div>
          <div className="stat-label">ML Models</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: "var(--purple)" }}>{teams.length}</div>
          <div className="stat-label">Teams</div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid-4" style={{ marginBottom: 28 }}>
        <Link to="/predict" className="card" style={{ textDecoration: "none", textAlign: "center" }}>
          <FiZap size={28} color="var(--accent)" />
          <h3 style={{ marginTop: 8, fontSize: 15 }}>Match Predictor</h3>
          <p style={{ fontSize: 12, color: "var(--text-muted)" }}>Predict any match</p>
        </Link>
        <Link to="/agents" className="card" style={{ textDecoration: "none", textAlign: "center" }}>
          <FiUsers size={28} color="var(--blue)" />
          <h3 style={{ marginTop: 8, fontSize: 15 }}>10 AI Agents</h3>
          <p style={{ fontSize: 12, color: "var(--text-muted)" }}>Deep analysis + LLM</p>
        </Link>
        <Link to="/dream11" className="card" style={{ textDecoration: "none", textAlign: "center" }}>
          <FiStar size={28} color="var(--yellow)" />
          <h3 style={{ marginTop: 8, fontSize: 15 }}>Dream11 XI</h3>
          <p style={{ fontSize: 12, color: "var(--text-muted)" }}>Fantasy team picks</p>
        </Link>
        <Link to="/live" className="card" style={{ textDecoration: "none", textAlign: "center" }}>
          <FiRadio size={28} color="var(--red)" />
          <h3 style={{ marginTop: 8, fontSize: 15 }}>Live Predictor</h3>
          <p style={{ fontSize: 12, color: "var(--text-muted)" }}>Mid-match prediction</p>
        </Link>
      </div>

      {/* Today's Predictions */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Today's Predictions</h2>
          <span className="badge badge-green">{todayPreds?.matches || 0} matches</span>
        </div>

        {todayPreds?.predictions?.length > 0 ? (
          todayPreds.predictions.map((p, i) => (
            <div key={i} style={{ marginBottom: 24, paddingBottom: 24, borderBottom: "1px solid var(--border)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                <span style={{ fontWeight: 600 }}>{p.team1} vs {p.team2}</span>
                <span className="badge badge-orange">{Math.round((p.confidence || 0) * 100)}% confidence</span>
              </div>
              <ProbBar
                team1={p.team1}
                team2={p.team2}
                prob1={p.team1_win_prob}
                prob2={p.team2_win_prob}
              />
              <div style={{ fontSize: 14, color: "var(--text-secondary)" }}>
                Predicted Winner: <strong style={{ color: "var(--accent)" }}>{p.predicted_winner}</strong>
              </div>
            </div>
          ))
        ) : (
          <p style={{ color: "var(--text-muted)", textAlign: "center", padding: 40 }}>
            No matches scheduled for today. Use the Match Predictor to predict any matchup!
          </p>
        )}
      </div>
    </div>
  );
}
