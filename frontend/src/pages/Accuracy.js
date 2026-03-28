import { useState, useEffect } from "react";
import { getAccuracy } from "../api";
import Loading from "../components/Loading";

export default function Accuracy() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getAccuracy()
      .then((res) => setData(res.data))
      .catch((e) => setError(e.response?.data?.detail || "Failed to load accuracy data"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loading text="Loading accuracy report..." />;
  if (error) return <div className="error-box">{error}</div>;

  return (
    <div>
      <div className="page-header">
        <h1>Prediction Accuracy</h1>
        <p>Self-learning calibration report</p>
      </div>

      <div className="grid-3" style={{ marginBottom: 24 }}>
        <div className="stat-card">
          <div className="stat-value" style={{ color: "var(--green)" }}>
            {data?.overall_accuracy != null ? `${Math.round(data.overall_accuracy * 100)}%` : "N/A"}
          </div>
          <div className="stat-label">Overall Accuracy</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: "var(--accent)" }}>
            {data?.total_predictions || 0}
          </div>
          <div className="stat-label">Predictions Made</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: "var(--blue)" }}>
            {data?.brier_score != null ? data.brier_score.toFixed(4) : "N/A"}
          </div>
          <div className="stat-label">Brier Score</div>
        </div>
      </div>

      {data?.model_leaderboard && (
        <div className="card">
          <h3 className="card-title" style={{ marginBottom: 16 }}>Model Leaderboard</h3>
          <div className="table-wrapper">
            <table>
              <thead><tr><th>Model</th><th>Accuracy</th><th>Predictions</th></tr></thead>
              <tbody>
                {Object.entries(data.model_leaderboard).map(([model, stats]) => (
                  <tr key={model}>
                    <td style={{ fontWeight: 600, textTransform: "capitalize" }}>{model}</td>
                    <td style={{ color: "var(--green)" }}>
                      {stats?.accuracy != null ? `${Math.round(stats.accuracy * 100)}%` : "N/A"}
                    </td>
                    <td>{stats?.count || 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {data?.confidence_calibration && (
        <div className="card" style={{ marginTop: 20 }}>
          <h3 className="card-title" style={{ marginBottom: 16 }}>Confidence Calibration</h3>
          <div className="table-wrapper">
            <table>
              <thead><tr><th>Confidence Range</th><th>Actual Win %</th><th>Count</th></tr></thead>
              <tbody>
                {Object.entries(data.confidence_calibration).map(([range, stats]) => (
                  <tr key={range}>
                    <td>{range}</td>
                    <td>{stats?.actual_pct != null ? `${Math.round(stats.actual_pct * 100)}%` : "N/A"}</td>
                    <td>{stats?.count || 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
