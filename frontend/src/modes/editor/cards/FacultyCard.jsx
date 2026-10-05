// Description: Name; credits (12 cr, or 12–14 cr when minimum_credits ≠ maximum_credits); Mo–Fr
// availability chips; Mandatory; Limits (unique_course_limit, maximum_days);
// Prefers (course names); Room prefs (room_preferences); Lab prefs (lab_preferences).

// TODO: Remove more than 1 time slot in availability chips. No "add hours" for an already existing availability.

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
  const coursePreferences = preferenceText(faculty.course_preferences);
  const roomPreferences = preferenceText(faculty.room_preferences);
  const labPreferences = preferenceText(faculty.lab_preferences);
  const uniqueCourseLimit = faculty.unique_course_limit;
  const maximumDays = faculty.maximum_days;

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
        <dt>Mandatory Days</dt>
        <dd>{mandatory}</dd>
        <dt>Unique Course Limit</dt>
        <dd>{uniqueCourseLimit}</dd>
        <dt>Maximum Days</dt>
        <dd>{maximumDays}</dd>
        <dt>Course Preferences</dt>
        <dd>{coursePreferences}</dd>
        <dt>Room Preferences</dt>
        <dd>{roomPreferences}</dd>
        <dt>Lab Preferences</dt>
        <dd>{labPreferences}</dd>
      </dl>
    </article>
  );
}
