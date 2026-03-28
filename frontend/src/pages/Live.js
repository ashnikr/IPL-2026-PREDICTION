import { useState } from "react";
import { getLivePrediction } from "../api";
import TeamSelect from "../components/TeamSelect";
import ProbBar from "../components/ProbBar";
import Loading from "../components/Loading";

export default function Live() {
  const [battingTeam, setBattingTeam] = useState("");
  const [bowlingTeam, setBowlingTeam] = useState("");
  const [score, setScore] = useState("");
  const [wickets, setWickets] = useState("");
  const [overs, setOvers] = useState("20");
  const [venue, setVenue] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handlePredict = async () => {
    if (!battingTeam || !bowlingTeam) return setError("Select both teams");
    if (!score) return setError("Enter the 1st innings score");
    setError("");
    setLoading(true);
    setResult(null);
    try {
      const res = await getLivePrediction({
        batting_team: battingTeam,
        bowling_team: bowlingTeam,
        score: parseInt(score),
        wickets: parseInt(wickets) || 0,
        overs: parseFloat(overs) || 20,
        venue: venue || undefined,
      });
      setResult(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || "Prediction failed.");
    }
    setLoading(false);
  };

  return (
    <div>
      <div className="page-header">
        <h1>Live Mid-Match Predictor</h1>
        <p>Predict outcome after 1st innings based on score, pitch, and team strengths</p>
      </div>

      <div className="grid-2">
        <div className="card">
          <h3 className="card-title" style={{ marginBottom: 20 }}>1st Innings Summary</h3>
          <TeamSelect label="Batting Team (1st Innings)" value={battingTeam} onChange={setBattingTeam} />
          <TeamSelect label="Bowling Team (Chasing)" value={bowlingTeam} onChange={setBowlingTeam} />
          <div className="grid-3">
            <div className="form-group">
              <label>Score</label>
              <input className="form-control" type="number" value={score} onChange={(e) => setScore(e.target.value)} placeholder="185" />
            </div>
            <div className="form-group">
              <label>Wickets</label>
              <input className="form-control" type="number" min="0" max="10" value={wickets} onChange={(e) => setWickets(e.target.value)} placeholder="4" />
            </div>
            <div className="form-group">
              <label>Overs</label>
              <input className="form-control" type="number" step="0.1" value={overs} onChange={(e) => setOvers(e.target.value)} placeholder="20" />
            </div>
          </div>
          <div className="form-group">
            <label>Venue (optional)</label>
            <input className="form-control" value={venue} onChange={(e) => setVenue(e.target.value)} placeholder="e.g. Wankhede Stadium" />
          </div>

          {error && <div className="error-box" style={{ marginBottom: 16 }}>{error}</div>}

          <button className="btn btn-primary" onClick={handlePredict} disabled={loading} style={{ width: "100%" }}>
            {loading ? "Analyzing..." : "Predict Chase"}
          </button>
        </div>

        <div>
          {loading && <Loading text="Analyzing pitch, team strengths, and dew factor..." />}
          {result && (
            <div className="prediction-result">
              <div style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 8 }}>CHASE PREDICTION</div>
              <div className="prediction-winner">{result.predicted_winner}</div>
              <div className="confidence-meter">
                Confidence: <strong>{Math.round((result.confidence || 0) * 100)}%</strong>
              </div>

              <ProbBar
                team1={result.batting_team || battingTeam}
                team2={result.bowling_team || bowlingTeam}
                prob1={result.defend_prob}
                prob2={result.chase_prob}
              />

              <div className="grid-2" style={{ marginTop: 20, textAlign: "left" }}>
                <div className="stat-card">
                  <div className="stat-value" style={{ fontSize: 22, color: "var(--green)" }}>
                    {result.par_score || "---"}
                  </div>
                  <div className="stat-label">Par Score</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value" style={{ fontSize: 22, color: "var(--accent)" }}>
                    {result.score_assessment || "---"}
                  </div>
                  <div className="stat-label">Assessment</div>
                </div>
              </div>

              {result.factors?.length > 0 && (
                <div className="key-factors" style={{ marginTop: 20 }}>
                  {result.factors.map((f, i) => <span className="factor-chip" key={i}>{f}</span>)}
                </div>
              )}

              {result.llm_analysis && (
                <div className="llm-box" style={{ textAlign: "left" }}>{result.llm_analysis}</div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
