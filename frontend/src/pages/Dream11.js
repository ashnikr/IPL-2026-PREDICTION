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

  const sourceLabel = (src) => {
    const labels = {
      "playing_xi_announced": "Live Playing XI (from Cricbuzz/ESPN)",
      "cricapi": "Live Playing XI (CricAPI)",
      "cricbuzz": "Live Playing XI (Cricbuzz)",
      "espn": "Live Playing XI (ESPNCricinfo)",
      "likely_xi": "Predicted Likely XI (from squads)",
      "squad_prediction": "Predicted Likely XI (from squads)",
      "manual": "User Provided XI",
    };
    return labels[src] || src || "Auto-detected";
  };

  return (
    <div>
      <div className="page-header">
        <h1>Dream11 Fantasy XI</h1>
        <p>Auto-fetches actual Playing XI from Cricbuzz/ESPN — picks only from players on the field</p>
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

          <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 16, padding: "8px 12px", background: "var(--bg-secondary)", borderRadius: 8 }}>
            Playing XI is auto-fetched from Cricbuzz / ESPNCricinfo / CricAPI. If match hasn't started, it uses the predicted likely XI from squad data.
          </div>

          {error && <div className="error-box" style={{ marginBottom: 16 }}>{error}</div>}

          <button className="btn btn-primary" onClick={handleGenerate} disabled={loading} style={{ width: "100%" }}>
            {loading ? "Fetching Playing XI & Generating..." : "Generate Dream11 XI"}
          </button>
        </div>

        <div>
          {loading && <Loading text="Auto-fetching Playing XI from live sources & generating best 11..." />}
          {result && (
            <div>
              {/* XI Source */}
              <div className="card" style={{ marginBottom: 16, padding: 16 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>Data Source:</span>
                  <span className={`badge ${result.xi_source === "playing_xi_announced" || result.xi_source === "cricbuzz" || result.xi_source === "espn" ? "badge-green" : "badge-orange"}`}>
                    {sourceLabel(result.xi_source)}
                  </span>
                </div>
              </div>

              {/* Playing XI from both teams */}
              {(result.playing_xi_team1?.length > 0 || result.playing_xi_team2?.length > 0) && (
                <div className="grid-2" style={{ marginBottom: 16 }}>
                  <div className="card" style={{ padding: 16 }}>
                    <h4 style={{ fontSize: 14, marginBottom: 8, color: "var(--accent)" }}>{team1} — Playing XI</h4>
                    {result.playing_xi_team1?.map((name, i) => (
                      <div key={i} style={{ fontSize: 13, padding: "3px 0", color: "var(--text-secondary)" }}>
                        {i + 1}. {name}
                      </div>
                    ))}
                  </div>
                  <div className="card" style={{ padding: 16 }}>
                    <h4 style={{ fontSize: 14, marginBottom: 8, color: "var(--blue)" }}>{team2} — Playing XI</h4>
                    {result.playing_xi_team2?.map((name, i) => (
                      <div key={i} style={{ fontSize: 13, padding: "3px 0", color: "var(--text-secondary)" }}>
                        {i + 1}. {name}
                      </div>
                    ))}
                  </div>
                </div>
              )}

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
                <h3 className="card-title" style={{ marginBottom: 16 }}>Best Fantasy XI (from actual Playing XI)</h3>
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
                      <div className="player-credits" style={{ marginTop: 4 }}>{p.credit} cr</div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Team split */}
              <div className="grid-2" style={{ marginTop: 16 }}>
                <div className="stat-card">
                  <div className="stat-value" style={{ fontSize: 18, color: "var(--accent)" }}>{result.team1_count}</div>
                  <div className="stat-label">From {team1?.split(" ").pop()}</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value" style={{ fontSize: 18, color: "var(--blue)" }}>{result.team2_count}</div>
                  <div className="stat-label">From {team2?.split(" ").pop()}</div>
                </div>
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
