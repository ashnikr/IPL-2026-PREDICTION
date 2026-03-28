import { useState } from "react";
import { predictMatch } from "../api";
import TeamSelect, { TEAMS } from "../components/TeamSelect";
import ProbBar from "../components/ProbBar";
import Loading from "../components/Loading";

const VENUES = [
  "Wankhede Stadium", "M. A. Chidambaram Stadium", "Eden Gardens",
  "M. Chinnaswamy Stadium", "Rajiv Gandhi Intl Stadium",
  "Arun Jaitley Stadium", "Narendra Modi Stadium",
  "Sawai Mansingh Stadium", "Punjab Cricket Association Stadium",
  "Bharat Ratna Shri Atal Bihari Vajpayee Ekana Stadium",
  "Dr. Y.S. Rajasekhara Reddy ACA-VDCA Cricket Stadium",
  "Barsapara Cricket Stadium",
  "Himachal Pradesh Cricket Association Stadium",
  "Maharashtra Cricket Association Stadium",
];

export default function Predict() {
  const [team1, setTeam1] = useState("");
  const [team2, setTeam2] = useState("");
  const [venue, setVenue] = useState("");
  const [tossWinner, setTossWinner] = useState("");
  const [tossDecision, setTossDecision] = useState("");
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
      const payload = { team1, team2 };
      if (venue) payload.venue = venue;
      if (tossWinner) payload.toss_winner = tossWinner;
      if (tossDecision) payload.toss_decision = tossDecision;
      const res = await predictMatch(payload);
      setResult(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || "Prediction failed. Try again.");
    }
    setLoading(false);
  };

  // Only show selected teams in toss dropdown
  const tossOptions = [team1, team2].filter(Boolean);

  return (
    <div>
      <div className="page-header">
        <h1>Match Predictor</h1>
        <p>Ensemble of 8 ML models + toss analysis for any IPL matchup</p>
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

          {/* Toss Section */}
          <div style={{
            background: "var(--bg-secondary)", borderRadius: 10, padding: 16, marginBottom: 16,
            border: "1px solid var(--border)",
          }}>
            <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, color: "var(--accent)" }}>
              🪙 Toss Details (for post-toss prediction)
            </div>
            <div className="form-group" style={{ marginBottom: 12 }}>
              <label>Toss Winner</label>
              <select className="form-control" value={tossWinner} onChange={(e) => setTossWinner(e.target.value)}>
                <option value="">Not decided yet</option>
                {tossOptions.length > 0
                  ? tossOptions.map((t) => <option key={t} value={t}>{t}</option>)
                  : TEAMS.map((t) => <option key={t} value={t}>{t}</option>)
                }
              </select>
            </div>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label>Toss Decision</label>
              <select className="form-control" value={tossDecision} onChange={(e) => setTossDecision(e.target.value)}>
                <option value="">Select decision</option>
                <option value="bat">Bat First</option>
                <option value="field">Field First (Bowl)</option>
              </select>
            </div>
            {!tossWinner && (
              <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 8 }}>
                Leave blank for pre-toss prediction. Fill after toss for more accurate results.
              </div>
            )}
          </div>

          {error && <div className="error-box" style={{ marginBottom: 16 }}>{error}</div>}

          <button className="btn btn-primary" onClick={handlePredict} disabled={loading} style={{ width: "100%" }}>
            {loading ? "Predicting..." : tossWinner ? "Predict (Post-Toss)" : "Predict Match"}
          </button>
        </div>

        <div>
          {loading && <Loading text="Running 8 ML models..." />}
          {result && (
            <div className="prediction-result">
              {/* Toss info if available */}
              {result.toss_winner && (
                <div style={{
                  background: "var(--bg-secondary)", borderRadius: 8, padding: "10px 16px",
                  marginBottom: 16, fontSize: 14, display: "flex", justifyContent: "space-between",
                }}>
                  <span>🪙 Toss: <strong>{result.toss_winner}</strong></span>
                  <span>Decision: <strong>{result.toss_decision === "bat" ? "Bat First" : "Bowl First"}</strong></span>
                </div>
              )}

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
