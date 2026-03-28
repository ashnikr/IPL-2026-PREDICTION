import { useState, useEffect } from "react";
import { getTeamStrengths } from "../api";
import Loading from "../components/Loading";

export default function Strengths() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getTeamStrengths()
      .then((res) => setData(res.data))
      .catch((e) => setError(e.response?.data?.detail || "Failed to load rankings"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loading text="Loading Bayesian rankings..." />;
  if (error) return <div className="error-box">{error}</div>;

  return (
    <div>
      <div className="page-header">
        <h1>Bayesian Team Rankings</h1>
        <p>Dynamic team strength ratings updated with every match result</p>
      </div>

      <div className="table-wrapper">
        <table>
          <thead>
            <tr><th>Rank</th><th>Team</th><th>Strength</th><th>Wins</th><th>Losses</th></tr>
          </thead>
          <tbody>
            {(data?.rankings || []).map((t) => (
              <tr key={t.team}>
                <td><strong>#{t.rank}</strong></td>
                <td style={{ fontWeight: 600 }}>{t.team}</td>
                <td>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <div style={{
                      width: `${Math.round(t.strength * 100)}%`,
                      maxWidth: 120,
                      height: 8,
                      borderRadius: 4,
                      background: t.strength > 0.6 ? "var(--green)" : t.strength > 0.45 ? "var(--yellow)" : "var(--red)",
                    }} />
                    <span style={{ fontWeight: 700 }}>{(t.strength * 100).toFixed(1)}</span>
                  </div>
                </td>
                <td style={{ color: "var(--green)" }}>{t.wins}</td>
                <td style={{ color: "var(--red)" }}>{t.losses}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
