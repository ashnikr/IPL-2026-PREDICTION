import { useState } from "react";
import { predictMatch } from "../api";
import TeamSelect from "../components/TeamSelect";
import ProbBar from "../components/ProbBar";
import Loading from "../components/Loading";

const VENUES = [
  "Wankhede Stadium", "M. A. Chidambaram Stadium", "Eden Gardens",
  "M. Chinnaswamy Stadium", "Rajiv Gandhi Intl Stadium",
  "Arun Jaitley Stadium", "Narendra Modi Stadium",
  "Sawai Mansingh Stadium", "Punjab Cricket Association Stadium",
  "Bharat Ratna Shri Atal Bihari Vajpayee Ekana Stadium",
];

export default function Predict() {
  const [team1, setTeam1] = useState("");
  const [team2, setTeam2] = useState("");
  const [venue, setVenue] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handlePredict = async () => {
    if (!team1 || !team2) return setError("Select both teams");
    if (team1 === team2) return setError("Select different teams");
    setError("");
    setLoading(true);
    setResult(null);
    try {
      const res = await predictMatch({ team1, team2, venue: venue || undefined });
      setResult(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || "Prediction failed. Try again.");
    }
    setLoading(false);
  };

  return (
    <div>
      <div className="page-header">
        <h1>Match Predictor</h1>
        <p>Ensemble of 8 ML models for any IPL matchup</p>
      </div>

      <div className="grid-2">
        <div className="card">
          <h3 className="card-title" style={{ marginBottom: 20 }}>Setup Match</h3>
          <TeamSelect label="Team 1" value={team1} onChange={setTeam1} />
          <TeamSelect label="Team 2" value={team2} onChange={setTeam2} />
          <div className="form-group">
            <label>Venue (optional)</label>
            <select className="form-control" value={venue} onChange={(e) => setVenue(e.target.value)}>
              <option value="">Auto-detect</option>
              {VENUES.map((v) => <option key={v} value={v}>{v}</option>)}
            </select>
          </div>

          {error && <div className="error-box" style={{ marginBottom: 16 }}>{error}</div>}

          <button className="btn btn-primary" onClick={handlePredict} disabled={loading} style={{ width: "100%" }}>
            {loading ? "Predicting..." : "Predict Match"}
          </button>
        </div>

        <div>
          {loading && <Loading text="Running 8 ML models..." />}
          {result && (
            <div className="prediction-result">
              <div style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 8 }}>PREDICTED WINNER</div>
              <div className="prediction-winner">{result.predicted_winner}</div>
              <div className="confidence-meter">
                Confidence: <strong>{Math.round(result.confidence * 100)}%</strong>
              </div>

              <ProbBar
                team1={result.team1}
                team2={result.team2}
                prob1={result.team1_win_prob}
                prob2={result.team2_win_prob}
              />

              {result.key_factors?.length > 0 && (
                <>
                  <div style={{ fontSize: 13, color: "var(--text-muted)", marginTop: 20, marginBottom: 8 }}>KEY FACTORS</div>
                  <div className="key-factors">
                    {result.key_factors.map((f, i) => (
                      <span className="factor-chip" key={i}>{f}</span>
                    ))}
                  </div>
                </>
              )}

              {result.model_predictions && (
                <div style={{ marginTop: 20, textAlign: "left" }}>
                  <div style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 8 }}>MODEL BREAKDOWN</div>
                  <div className="table-wrapper">
                    <table>
                      <thead><tr><th>Model</th><th>Prediction</th></tr></thead>
                      <tbody>
                        {Object.entries(result.model_predictions).map(([model, pred]) => (
                          <tr key={model}>
                            <td style={{ textTransform: "capitalize" }}>{model}</td>
                            <td>{typeof pred === "object" ? JSON.stringify(pred) : String(pred)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
