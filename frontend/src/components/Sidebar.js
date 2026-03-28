import { NavLink } from "react-router-dom";
import {
  FiHome, FiZap, FiUsers, FiStar,
  FiTrendingUp, FiCalendar, FiBarChart2, FiTarget,
  FiRadio, FiAward, FiFileText, FiDollarSign
} from "react-icons/fi";

const sections = [
  {
    title: "Predictions",
    links: [
      { to: "/", icon: <FiHome />, label: "Dashboard" },
      { to: "/predict", icon: <FiZap />, label: "Match Predictor" },
      { to: "/agents", icon: <FiUsers />, label: "AI Agents (10)" },
      { to: "/live", icon: <FiRadio />, label: "Live Mid-Match" },
    ],
  },
  {
    title: "Fantasy",
    links: [
      { to: "/dream11", icon: <FiStar />, label: "Dream11 Fantasy XI" },
    ],
  },
  {
    title: "Intelligence",
    links: [
      { to: "/form", icon: <FiTrendingUp />, label: "Team Form" },
      { to: "/news", icon: <FiFileText />, label: "News & Sentiment" },
      { to: "/h2h", icon: <FiTarget />, label: "Head to Head" },
      { to: "/strengths", icon: <FiBarChart2 />, label: "Team Rankings" },
    ],
  },
  {
    title: "Data",
    links: [
      { to: "/schedule", icon: <FiCalendar />, label: "Schedule" },
      { to: "/squads", icon: <FiUsers />, label: "Squads" },
      { to: "/accuracy", icon: <FiAward />, label: "Accuracy" },
    ],
  },
  {
    title: "Subscribe",
    links: [
      { to: "/pricing", icon: <FiStar />, label: "Plans & Pricing" },
      { to: "/payment?plan=pro", icon: <FiDollarSign />, label: "Pay via UPI" },
      { to: "/earn", icon: <FiDollarSign />, label: "Earn Money" },
    ],
  },
];

export default function Sidebar({ open, onClose }) {
  return (
    <aside className={`sidebar${open ? " open" : ""}`} onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()}>
        <div className="sidebar-logo">IPL 2026 AI</div>
        <div className="sidebar-subtitle">10 Agents + 8 ML Models</div>
        {sections.map((s) => (
          <div className="nav-section" key={s.title}>
            <div className="nav-section-title">{s.title}</div>
            {s.links.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                end={l.to === "/"}
                className={({ isActive }) =>
                  `nav-link${isActive ? " active" : ""}`
                }
                onClick={onClose}
              >
                {l.icon}
                {l.label}
              </NavLink>
            ))}
          </div>
        ))}
      </div>
    </aside>
  );
}
