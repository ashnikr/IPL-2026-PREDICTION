import { useState } from "react";
import { getDream11 } from "../api";
import TeamSelect from "../components/TeamSelect";
import Loading from "../components/Loading";

export default function Dream11() {
  const [team1, setTeam1] = useState("");
  const [team2, setTeam2] = useState("");
  const [contest, setContest] = useState("mega");
  const [xi1, setXi1] = useState("");
  const [xi2, setXi2] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const parseNames = (text) => {
    if (!text.trim()) return null;
    return text.split(/[,\n]+/).map((n) => n.trim()).filter(Boolean);
  };

  const handleGenerate = async () => {
    if (!team1 || !team2 || team1 === team2) return setError("Select two different teams");
    setError("");
    setLoading(true);
    setResult(null);
    try {
      const payload = { team1, team2, contest_type: contest };
      const xi1List = parseNames(xi1);
      const xi2List = parseNames(xi2);
      if (xi1List && xi1List.length >= 11) payload.playing_xi_team1 = xi1List;
      if (xi2List && xi2List.length >= 11) payload.playing_xi_team2 = xi2List;
      const res = await getDream11(payload);
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
        <p>AI-optimized team — only picks from actual Playing XI, not benched players</p>
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

          {/* Playing XI Input */}
          <div className="form-group">
            <label>{team1 ? `${team1} — Playing XI` : "Team 1 Playing XI"} (paste 11 names, comma or newline separated)</label>
            <textarea
              className="form-control"
              rows={4}
              value={xi1}
              onChange={(e) => setXi1(e.target.value)}
              placeholder="e.g. Ruturaj Gaikwad, Devon Conway, Ravindra Jadeja, ..."
              style={{ resize: "vertical", fontSize: 13 }}
            />
            <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
              {parseNames(xi1)?.length || 0}/11 players entered {parseNames(xi1)?.length >= 11 ? " — Using your XI" : " — Leave empty to auto-detect"}
            </span>
          </div>

          <div className="form-group">
            <label>{team2 ? `${team2} — Playing XI` : "Team 2 Playing XI"} (paste 11 names)</label>
            <textarea
              className="form-control"
              rows={4}
              value={xi2}
              onChange={(e) => setXi2(e.target.value)}
              placeholder="e.g. Travis Head, Abhishek Sharma, Heinrich Klaasen, ..."
              style={{ resize: "vertical", fontSize: 13 }}
            />
            <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
              {parseNames(xi2)?.length || 0}/11 players entered {parseNames(xi2)?.length >= 11 ? " — Using your XI" : " — Leave empty to auto-detect"}
            </span>
          </div>

          {error && <div className="error-box" style={{ marginBottom: 16 }}>{error}</div>}

          <button className="btn btn-primary" onClick={handleGenerate} disabled={loading} style={{ width: "100%" }}>
            {loading ? "Generating..." : "Generate Dream11 XI"}
          </button>
        </div>

        <div>
          {loading && <Loading text="Picking best 11 from actual Playing XI..." />}
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
                <h3 className="card-title" style={{ marginBottom: 16 }}>Fantasy XI (from Playing XI only)</h3>
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
