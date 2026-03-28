import { useState, useEffect } from "react";
import { getForm } from "../api";
import Loading from "../components/Loading";

export default function Form() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getForm()
      .then((res) => setData(res.data))
      .catch((e) => setError(e.response?.data?.detail || "Failed to load form data"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loading text="Loading team form..." />;
  if (error) return <div className="error-box">{error}</div>;

  const teams = Object.entries(data || {}).sort(
    (a, b) => (b[1]?.rating || 0) - (a[1]?.rating || 0)
  );

  return (
    <div>
      <div className="page-header">
        <h1>Team Form & Momentum</h1>
        <p>Current form ratings, win streaks, and momentum for all teams</p>
      </div>

      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Team</th>
              <th>Rating</th>
              <th>Momentum</th>
              <th>Form</th>
              <th>Win Streak</th>
            </tr>
          </thead>
          <tbody>
            {teams.map(([team, info], i) => (
              <tr key={team}>
                <td>{i + 1}</td>
                <td style={{ fontWeight: 600 }}>{team}</td>
                <td>
                  <span style={{
                    fontWeight: 700,
                    color: (info?.rating || 0) > 0.6 ? "var(--green)" : (info?.rating || 0) > 0.5 ? "var(--yellow)" : "var(--red)"
                  }}>
                    {((info?.rating || 0) * 100).toFixed(1)}
                  </span>
                </td>
                <td>
                  <span className={`badge ${(info?.momentum || "") === "Rising" ? "badge-green" : (info?.momentum || "") === "Falling" ? "badge-red" : "badge-blue"}`}>
                    {info?.momentum || "Stable"}
                  </span>
                </td>
                <td style={{ fontFamily: "monospace", letterSpacing: 2 }}>
                  {(info?.recent_results || []).map((r, j) => (
                    <span key={j} style={{ color: r === "W" ? "var(--green)" : "var(--red)" }}>{r}</span>
                  ))}
                </td>
                <td>{info?.win_streak || 0}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
