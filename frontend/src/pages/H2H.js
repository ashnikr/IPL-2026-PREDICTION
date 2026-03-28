import { useState } from "react";
import { getHeadToHead } from "../api";
import TeamSelect from "../components/TeamSelect";
import Loading from "../components/Loading";

export default function H2H() {
  const [team1, setTeam1] = useState("");
  const [team2, setTeam2] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleFetch = async () => {
    if (!team1 || !team2 || team1 === team2) return setError("Select two different teams");
    setError("");
    setLoading(true);
    try {
      const res = await getHeadToHead(team1, team2);
      setResult(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || "Failed to fetch H2H data");
    }
    setLoading(false);
  };

  return (
    <div>
      <div className="page-header">
        <h1>Head to Head</h1>
        <p>Historical matchup statistics between any two IPL teams</p>
      </div>

      <div className="card" style={{ maxWidth: 600 }}>
        <TeamSelect label="Team 1" value={team1} onChange={setTeam1} />
        <TeamSelect label="Team 2" value={team2} onChange={setTeam2} />
        {error && <div className="error-box" style={{ marginBottom: 16 }}>{error}</div>}
        <button className="btn btn-primary" onClick={handleFetch} disabled={loading}>
          {loading ? "Loading..." : "Get H2H Stats"}
        </button>
      </div>

      {loading && <Loading />}
      {result && (
        <div className="grid-4" style={{ marginTop: 24 }}>
          <div className="stat-card">
            <div className="stat-value" style={{ color: "var(--accent)" }}>{result.total_matches}</div>
            <div className="stat-label">Total Matches</div>
          </div>
          <div className="stat-card">
            <div className="stat-value" style={{ color: "var(--green)" }}>{result.team1_wins}</div>
            <div className="stat-label">{team1.split(" ").pop()} Wins</div>
          </div>
          <div className="stat-card">
            <div className="stat-value" style={{ color: "var(--blue)" }}>{result.team2_wins}</div>
            <div className="stat-label">{team2.split(" ").pop()} Wins</div>
          </div>
          <div className="stat-card">
            <div className="stat-value" style={{ color: "var(--yellow)" }}>
              {Math.round((result.team1_win_pct || 0) * 100)}%
            </div>
            <div className="stat-label">{team1.split(" ").pop()} Win %</div>
          </div>
        </div>
      )}
    </div>
  );
}
