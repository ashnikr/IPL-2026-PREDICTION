import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { healthCheck, predictToday, getTeams } from "../api";
import Loading from "../components/Loading";
import ProbBar from "../components/ProbBar";
import { FiZap, FiStar, FiRadio } from "react-icons/fi";

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
        <p>8 ML Models — Pre-Match & Post 1st Innings Predictions + Dream11 XI</p>
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
          <div className="stat-value" style={{ color: "var(--accent)" }}>8</div>
          <div className="stat-label">ML Models</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: "var(--blue)" }}>{teams.length}</div>
          <div className="stat-label">IPL Teams</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: "var(--purple)" }}>2</div>
          <div className="stat-label">Prediction Modes</div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid-3" style={{ marginBottom: 28 }}>
        <Link to="/predict" className="card" style={{ textDecoration: "none", textAlign: "center" }}>
          <FiZap size={28} color="var(--accent)" />
          <h3 style={{ marginTop: 8, fontSize: 15 }}>Pre-Match Prediction</h3>
          <p style={{ fontSize: 12, color: "var(--text-muted)" }}>Pitch, form, H2H, weather, toss</p>
        </Link>
        <Link to="/innings" className="card" style={{ textDecoration: "none", textAlign: "center" }}>
          <FiRadio size={28} color="var(--blue)" />
          <h3 style={{ marginTop: 8, fontSize: 15 }}>After 1st Innings</h3>
          <p style={{ fontSize: 12, color: "var(--text-muted)" }}>Who wins from current score?</p>
        </Link>
        <Link to="/dream11" className="card" style={{ textDecoration: "none", textAlign: "center" }}>
          <FiStar size={28} color="var(--yellow)" />
          <h3 style={{ marginTop: 8, fontSize: 15 }}>Dream11 Fantasy XI</h3>
          <p style={{ fontSize: 12, color: "var(--text-muted)" }}>Best 11 from actual Playing XI</p>
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
            No matches scheduled for today. Use Pre-Match Prediction to predict any matchup!
          </p>
        )}
      </div>
    </div>
  );
}
