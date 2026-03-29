import { NavLink } from "react-router-dom";
import {
  FiHome, FiZap, FiStar,
  FiTrendingUp, FiCalendar, FiTarget,
  FiRadio, FiFileText, FiDollarSign
} from "react-icons/fi";

const sections = [
  {
    title: "Predictions",
    links: [
      { to: "/", icon: <FiHome />, label: "Dashboard" },
      { to: "/predict", icon: <FiZap />, label: "Pre-Match Prediction" },
      { to: "/innings", icon: <FiRadio />, label: "After 1st Innings" },
      { to: "/dream11", icon: <FiStar />, label: "Dream11 Fantasy XI" },
    ],
  },
  {
    title: "Intelligence",
    links: [
      { to: "/form", icon: <FiTrendingUp />, label: "Team Form" },
      { to: "/h2h", icon: <FiTarget />, label: "Head to Head" },
      { to: "/news", icon: <FiFileText />, label: "News & Sentiment" },
    ],
  },
  {
    title: "Data",
    links: [
      { to: "/schedule", icon: <FiCalendar />, label: "Schedule" },
    ],
  },
  {
    title: "Subscribe",
    links: [
      { to: "/pricing", icon: <FiStar />, label: "Plans & Pricing" },
      { to: "/payment?plan=basic", icon: <FiDollarSign />, label: "Pay via UPI" },
    ],
  },
];

export default function Sidebar({ open, onClose }) {
  return (
    <aside className={`sidebar${open ? " open" : ""}`} onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()}>
        <div className="sidebar-logo">IPL 2026 AI</div>
        <div className="sidebar-subtitle">8 ML Models + Cricket AI</div>
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
