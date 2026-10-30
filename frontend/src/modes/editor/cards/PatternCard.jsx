/**
 * One class pattern in the Class Patterns row. Its Edit button opens PatternDialog; the On/Off
 * switch saves right away through `onToggle`.
 * A meeting's own start_time overrides the pattern's.
 */

import Badge from "../../../components/Badge.jsx";
import EditButton from "./EditButton.jsx";

/** A class pattern: credits, on/off, its meetings (day, length, lab, delivery, start), and start time. */
export default function PatternCard({ pattern, onEdit, onToggle }) {
  const startText = pattern.disabled
    ? "Disabled"
    : pattern.start_time
      ? `Starts at ${pattern.start_time}`
      : "Any start time";

  return (
    <article className={`item-card ${pattern.disabled ? "item-card--disabled" : ""}`}>
      <div className="item-card__header">
        <h3 className="item-card__title">{pattern.credits} credits</h3>
        <label className="toggle">
          <span>{pattern.disabled ? "Off" : "On"}</span>
          <input
            type="checkbox"
            role="switch"
            aria-label="Pattern enabled"
            checked={!pattern.disabled}
            onChange={onToggle}
            readOnly={!onToggle}
          />
        </label>
      </div>
      <ul className="pattern-meetings">
        {pattern.meetings.map((m, i) => (
          <li key={i}>
            <span className="pattern-meetings__day">{m.day}</span>
            <span>{m.duration} min</span>
            {m.lab && <Badge tone="success">Lab</Badge>}
            {m.delivery === "online" && <Badge tone="info">Online</Badge>}
            {m.start_time && <span>at {m.start_time}</span>}
          </li>
        ))}
      </ul>
      <p className="item-card__note">{startText}</p>
      <EditButton label={`${pattern.credits}-credit pattern`} onEdit={onEdit} />
    </article>
  );
}
