export default function ProbBar({ team1, team2, prob1, prob2 }) {
  const p1 = Math.round((prob1 || 0) * 100);
  const p2 = Math.round((prob2 || 0) * 100);

  return (
    <div className="prob-bar-container">
      <span className="prob-team-name" style={{ textAlign: "right" }}>{team1}</span>
      <div className="prob-bar">
        <div className="prob-bar-left" style={{ width: `${p1}%` }}>
          {p1}%
        </div>
        <div className="prob-bar-right" style={{ width: `${p2}%` }}>
          {p2}%
        </div>
      </div>
      <span className="prob-team-name">{team2}</span>
    </div>
  );
}
