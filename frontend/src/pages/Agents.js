import { useState } from "react";
import { runAgents } from "../api";
import TeamSelect from "../components/TeamSelect";
import ProbBar from "../components/ProbBar";
import Loading from "../components/Loading";

export default function Agents() {
  const [team1, setTeam1] = useState("");
  const [team2, setTeam2] = useState("");
  const [venue, setVenue] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleRun = async () => {
    if (!team1 || !team2 || team1 === team2) return setError("Select two different teams");
    setError("");
    setLoading(true);
    setResult(null);
    try {
      const res = await runAgents({ team1, team2, venue });
      setResult(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || "Agent system failed. Try again.");
    }
    setLoading(false);
  };

  return (
    <div>
      <div className="page-header">
        <h1>10 AI Agents System</h1>
        <p>DataAgent, PlayerForm, Pitch, Weather, Toss, News, Sentiment, Strategy, Model, Debate</p>
      </div>

      <div className="grid-2">
        <div className="card">
          <h3 className="card-title" style={{ marginBottom: 20 }}>Configure</h3>
          <TeamSelect label="Team 1" value={team1} onChange={setTeam1} />
          <TeamSelect label="Team 2" value={team2} onChange={setTeam2} />
          <div className="form-group">
            <label>Venue (optional)</label>
            <input className="form-control" value={venue} onChange={(e) => setVenue(e.target.value)} placeholder="e.g. Wankhede Stadium" />
          </div>

          {error && <div className="error-box" style={{ marginBottom: 16 }}>{error}</div>}

          <button className="btn btn-primary" onClick={handleRun} disabled={loading} style={{ width: "100%" }}>
            {loading ? "Running 10 Agents..." : "Run AI Agents"}
          </button>
        </div>

        <div>
          {loading && <Loading text="Running 10 AI agents with LLM analysis... This may take 30-60 seconds." />}
          {result && (
            <div>
              <div className="prediction-result">
                <div style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 8 }}>AI AGENTS PREDICTION</div>
                <div className="prediction-winner">{result.predicted_winner}</div>
                <div className="confidence-meter">
                  Confidence: <strong>{Math.round((result.confidence || 0) * 100)}%</strong>
                </div>
                <ProbBar
                  team1={result.team1}
                  team2={result.team2}
                  prob1={result.team1_win_prob}
                  prob2={result.team2_win_prob}
                />
              </div>

              {result.explanation && (
                <div className="card" style={{ marginTop: 16 }}>
                  <h3 className="card-title">Agent Explanation</h3>
                  <div className="llm-box">{result.explanation}</div>
                </div>
              )}

              {result.llm_analysis && (
                <div className="card" style={{ marginTop: 16 }}>
                  <h3 className="card-title">LLM Analysis (Groq Llama 3.3 70B)</h3>
                  <div className="llm-box">{result.llm_analysis}</div>
                </div>
              )}

              {result.debate && (
                <div className="card" style={{ marginTop: 16 }}>
                  <h3 className="card-title">Agent Debate</h3>
                  <div className="llm-box">{result.debate}</div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
