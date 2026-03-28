import { useState, useEffect } from "react";
import { getNews, getTeamNews } from "../api";
import { TEAMS } from "../components/TeamSelect";
import Loading from "../components/Loading";

export default function News() {
  const [articles, setArticles] = useState([]);
  const [teamNews, setTeamNews] = useState(null);
  const [selectedTeam, setSelectedTeam] = useState("");
  const [loading, setLoading] = useState(true);
  const [teamLoading, setTeamLoading] = useState(false);

  useEffect(() => {
    getNews()
      .then((res) => setArticles(res.data.articles || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleTeamSelect = async (team) => {
    setSelectedTeam(team);
    if (!team) { setTeamNews(null); return; }
    setTeamLoading(true);
    try {
      const res = await getTeamNews(team);
      setTeamNews(res.data);
    } catch { setTeamNews(null); }
    setTeamLoading(false);
  };

  return (
    <div>
      <div className="page-header">
        <h1>News & Sentiment</h1>
        <p>Latest cricket news with AI sentiment analysis</p>
      </div>

      <div className="form-group" style={{ maxWidth: 400, marginBottom: 24 }}>
        <label>Filter by Team</label>
        <select className="form-control" value={selectedTeam} onChange={(e) => handleTeamSelect(e.target.value)}>
          <option value="">All News</option>
          {TEAMS.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
      </div>

      {/* Team Sentiment */}
      {teamLoading && <Loading text="Analyzing sentiment..." />}
      {teamNews?.sentiment && (
        <div className="card" style={{ marginBottom: 24 }}>
          <h3 className="card-title">Sentiment Analysis: {selectedTeam}</h3>
          <div className="grid-3" style={{ marginTop: 16 }}>
            <div className="stat-card">
              <div className="stat-value" style={{
                fontSize: 22,
                color: (teamNews.sentiment.overall || "") === "Positive" ? "var(--green)" : (teamNews.sentiment.overall || "") === "Negative" ? "var(--red)" : "var(--yellow)"
              }}>
                {teamNews.sentiment.overall || "Neutral"}
              </div>
              <div className="stat-label">Overall</div>
            </div>
            <div className="stat-card">
              <div className="stat-value" style={{ fontSize: 22, color: "var(--green)" }}>
                {teamNews.sentiment.positive_count || 0}
              </div>
              <div className="stat-label">Positive</div>
            </div>
            <div className="stat-card">
              <div className="stat-value" style={{ fontSize: 22, color: "var(--red)" }}>
                {teamNews.sentiment.negative_count || 0}
              </div>
              <div className="stat-label">Negative</div>
            </div>
          </div>
        </div>
      )}

      {/* News Articles */}
      {loading ? (
        <Loading text="Fetching latest news..." />
      ) : (
        <div>
          {(teamNews?.news || articles).length === 0 ? (
            <p style={{ color: "var(--text-muted)", textAlign: "center", padding: 40 }}>No news articles found.</p>
          ) : (
            (teamNews?.news || articles).map((a, i) => (
              <div className="card" key={i} style={{ marginBottom: 12 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start" }}>
                  <div>
                    <h4 style={{ fontSize: 15, marginBottom: 4 }}>{a.title}</h4>
                    <p style={{ fontSize: 13, color: "var(--text-muted)" }}>
                      {a.source} {a.date ? `| ${a.date}` : ""}
                    </p>
                  </div>
                  {a.sentiment && (
                    <span className={`badge ${a.sentiment === "positive" ? "badge-green" : a.sentiment === "negative" ? "badge-red" : "badge-blue"}`}>
                      {a.sentiment}
                    </span>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
