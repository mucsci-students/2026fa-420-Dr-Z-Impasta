// Description: Name; credits (12 cr, or 12–14 cr when minimum_credits ≠ maximum_credits); Mo–Fr
// availability chips; Mandatory; Limits (unique_course_limit, maximum_days);
// Prefers (course names).
//
// Missing From Mockup: Room prefs (room_preferences) and Lab prefs (lab_preferences). The
// preference scores: the mockup shows only names (CMSC 362, CMSC 476 +1), but each name has a
// score, e.g. CMSC 362 (5). Multiple ranges per day: a chip like 11–16 assumes one range, but a
// day can have several (9–12, 13–17).

import { plural } from "../../../format.js";
import AvailabilityChips from "../AvailabilityChips.jsx";

const WEEKDAYS = ["MON", "TUE", "WED", "THU", "FRI"];

/** { "CMSC 362": 5, "CMSC 161": 4 } → "CMSC 362 (5), CMSC 161 (4)", or "None". */
function preferenceText(prefs) {
  const entries = Object.entries(prefs);
  if (entries.length === 0) return "None";
  return entries.map(([name, score]) => `${name} (${score})`).join(", ");
}

/** A faculty member: credit range, weekly availability, mandatory days, limits, and preferences. */
export default function FacultyCard({ faculty, onEdit }) {
  const credits =
    faculty.minimum_credits === faculty.maximum_credits
      ? `${faculty.maximum_credits} cr`
      : `${faculty.minimum_credits}–${faculty.maximum_credits} cr`;
  const mandatoryDays = WEEKDAYS.filter((d) => faculty.mandatory_days.includes(d));
  const mandatory = mandatoryDays.length > 0 ? mandatoryDays.join(", ") : "None";
  const days = faculty.maximum_days < 5 ? ` · ${faculty.maximum_days} days max` : "";
  const limits = `${plural(faculty.unique_course_limit, "unique course")}${days}`;

  return (
    <article
      className="item-card"
      onClick={onEdit}
      onKeyDown={(e) => { if (e.key === "Enter") onEdit?.(); }}
      tabIndex={0}
    >
      <div className="item-card__header">
        <h3 className="item-card__title">{faculty.name}</h3>
        <span className="item-card__credits">{credits}</span>
      </div>
      <AvailabilityChips times={faculty.times} />
      <dl className="item-card__facts">
        <dt>Mandatory</dt>
        <dd>{mandatory}</dd>
        <dt>Limits</dt>
        <dd>{limits}</dd>
        <dt>Prefers</dt>
        <dd>{preferenceText(faculty.course_preferences)}</dd>
      </dl>
    </article>
  );
}
