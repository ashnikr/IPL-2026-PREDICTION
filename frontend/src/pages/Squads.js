import { useState, useEffect } from "react";
import { getSquads } from "../api";
import Loading from "../components/Loading";

export default function Squads() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState("");

  useEffect(() => {
    getSquads()
      .then((res) => {
        setData(res.data);
        const teams = Object.keys(res.data || {});
        if (teams.length > 0) setSelected(teams[0]);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loading text="Loading squads..." />;

  const teams = Object.keys(data || {});

  return (
    <div>
      <div className="page-header">
        <h1>Team Squads</h1>
        <p>Full squad rosters for all IPL 2026 teams</p>
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 24 }}>
        {teams.map((t) => (
          <button
            key={t}
            className={`btn ${selected === t ? "btn-primary" : "btn-secondary"}`}
            style={{ fontSize: 13, padding: "6px 14px" }}
            onClick={() => setSelected(t)}
          >
            {t}
          </button>
        ))}
      </div>

      {selected && data[selected] && (
        <div className="card">
          <h3 className="card-title" style={{ marginBottom: 16 }}>{selected}</h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 8 }}>
            {(Array.isArray(data[selected]) ? data[selected] : []).map((player, i) => (
              <div className="player-card" key={i}>
                <div>
                  <div className="player-name">{typeof player === "string" ? player : player.name}</div>
                  {player.role && <div className="player-role">{player.role}</div>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
