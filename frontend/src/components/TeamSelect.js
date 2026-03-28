const TEAMS = [
  "Chennai Super Kings",
  "Delhi Capitals",
  "Gujarat Titans",
  "Kolkata Knight Riders",
  "Lucknow Super Giants",
  "Mumbai Indians",
  "Punjab Kings",
  "Rajasthan Royals",
  "Royal Challengers Bengaluru",
  "Sunrisers Hyderabad",
];

export default function TeamSelect({ label, value, onChange, name }) {
  return (
    <div className="form-group">
      <label>{label}</label>
      <select
        className="form-control"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        name={name}
      >
        <option value="">Select Team</option>
        {TEAMS.map((t) => (
          <option key={t} value={t}>{t}</option>
        ))}
      </select>
    </div>
  );
}

export { TEAMS };
