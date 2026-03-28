import { useState } from "react";
import { getDream11 } from "../api";
import TeamSelect from "../components/TeamSelect";
import Loading from "../components/Loading";

export default function Dream11() {
  const [team1, setTeam1] = useState("");
  const [team2, setTeam2] = useState("");
  const [contest, setContest] = useState("mega");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleGenerate = async () => {
    if (!team1 || !team2 || team1 === team2) return setError("Select two different teams");
    setError("");
    setLoading(true);
    setResult(null);
    try {
      const res = await getDream11({ team1, team2, contest_type: contest });
      setResult(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || "Failed to generate team.");
    }
    setLoading(false);
  };

  const roleColor = (role) => {
    const colors = { WK: "var(--yellow)", BAT: "var(--blue)", ALL: "var(--green)", BOWL: "var(--purple)" };
    return colors[role] || "var(--text-muted)";
  };

  return (
    <div>
      <div className="page-header">
        <h1>Dream11 Fantasy XI</h1>
        <p>AI-optimized team with Captain & Vice-Captain picks</p>
      </div>

      <div className="grid-2">
        <div className="card">
          <h3 className="card-title" style={{ marginBottom: 20 }}>Match Setup</h3>
          <TeamSelect label="Team 1" value={team1} onChange={setTeam1} />
          <TeamSelect label="Team 2" value={team2} onChange={setTeam2} />
          <div className="form-group">
            <label>Contest Type</label>
            <select className="form-control" value={contest} onChange={(e) => setContest(e.target.value)}>
              <option value="mega">Mega Contest (Safe picks)</option>
              <option value="h2h">Head to Head (High ceiling)</option>
              <option value="small">Small League (Balanced)</option>
            </select>
          </div>

          {error && <div className="error-box" style={{ marginBottom: 16 }}>{error}</div>}

          <button className="btn btn-primary" onClick={handleGenerate} disabled={loading} style={{ width: "100%" }}>
            {loading ? "Generating..." : "Generate Dream11 XI"}
          </button>
        </div>

        <div>
          {loading && <Loading text="Generating optimal Fantasy XI..." />}
          {result && (
            <div>
              {/* Summary */}
              <div className="grid-3" style={{ marginBottom: 20 }}>
                <div className="stat-card">
                  <div className="stat-value" style={{ color: "var(--accent)", fontSize: 22 }}>
                    {result.total_credits || "---"}
                  </div>
                  <div className="stat-label">Credits Used</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value" style={{ color: "var(--green)", fontSize: 22 }}>
                    {result.expected_points?.toFixed(1) || "---"}
                  </div>
                  <div className="stat-label">Expected Points</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value" style={{ color: "var(--blue)", fontSize: 22 }}>
                    {result.team?.length || 11}
                  </div>
                  <div className="stat-label">Players</div>
                </div>
              </div>

              {/* Captain & Vice-Captain */}
              {result.captain && (
                <div className="player-card captain" style={{ marginBottom: 12 }}>
                  <div>
                    <div className="player-name">{result.captain} (C)</div>
                    <div className="player-role">Captain - 2x Points</div>
                  </div>
                  <span className="badge badge-orange">CAPTAIN</span>
                </div>
              )}
              {result.vice_captain && (
                <div className="player-card vice-captain" style={{ marginBottom: 20 }}>
                  <div>
                    <div className="player-name">{result.vice_captain} (VC)</div>
                    <div className="player-role">Vice-Captain - 1.5x Points</div>
                  </div>
                  <span className="badge badge-blue">VICE-CAPTAIN</span>
                </div>
              )}

              {/* Full Team */}
              <div className="card">
                <h3 className="card-title" style={{ marginBottom: 16 }}>Full Squad</h3>
                {result.team?.map((p, i) => (
                  <div className="player-card" key={i} style={{ marginBottom: 8 }}>
                    <div>
                      <div className="player-name">{p.name}</div>
                      <div className="player-team">{p.team}</div>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <span className="badge" style={{ background: `${roleColor(p.role)}22`, color: roleColor(p.role) }}>
                        {p.role}
                      </span>
                      <div className="player-credits" style={{ marginTop: 4 }}>{p.credits} cr</div>
                    </div>
                  </div>
                ))}
              </div>

              {/* LLM Insight */}
              {result.llm_insight && (
                <div className="card" style={{ marginTop: 16 }}>
                  <h3 className="card-title">AI Insight</h3>
                  <div className="llm-box">{result.llm_insight}</div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
