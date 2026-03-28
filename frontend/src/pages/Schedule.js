import { useState, useEffect } from "react";
import { getSchedule } from "../api";
import Loading from "../components/Loading";

export default function Schedule() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getSchedule()
      .then((res) => setData(res.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loading text="Loading schedule..." />;

  return (
    <div>
      <div className="page-header">
        <h1>IPL 2026 Schedule</h1>
        <p>{data?.total_matches || 0} matches</p>
      </div>

      <div className="table-wrapper">
        <table>
          <thead>
            <tr><th>#</th><th>Date</th><th>Match</th><th>Venue</th></tr>
          </thead>
          <tbody>
            {(data?.schedule || []).map((m, i) => (
              <tr key={i}>
                <td>{m.match_no || i + 1}</td>
                <td>{m.date || "TBD"}</td>
                <td style={{ fontWeight: 600 }}>{m.team1} vs {m.team2}</td>
                <td style={{ color: "var(--text-secondary)" }}>{m.venue || "TBD"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
