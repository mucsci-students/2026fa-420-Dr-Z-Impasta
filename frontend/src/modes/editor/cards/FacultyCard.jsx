/**
 * One faculty member in the Faculty row. Its Edit button opens FacultyDialog.
 * Credits show as "12 cr", or "12–14 cr" when the minimum and maximum differ. Mandatory days
 * and each preference list are hidden when empty.
 */

import AvailabilityChips from "../AvailabilityChips.jsx";
import EditButton from "./EditButton.jsx";

const WEEKDAYS = ["MON", "TUE", "WED", "THU", "FRI"];

/**
 * { "CMSC 362": 5, "CMSC 161": 4 } → "CMSC 362 (5), CMSC 161 (4)", or "" when empty.
 * Spaces inside an entry are non-breaking, so the list wraps only between entries.
 */
function preferenceText(prefs) {
  return Object.entries(prefs).map(([name, score]) => `${name} (${score})`.replaceAll(" ", "\u00A0")).join(", ");
}

/** A faculty member: credit range, weekly availability, mandatory days, limits, and preferences. */
export default function FacultyCard({ faculty, onEdit }) {
  const credits =
    faculty.minimum_credits === faculty.maximum_credits
      ? `${faculty.maximum_credits} cr`
      : `${faculty.minimum_credits}–${faculty.maximum_credits} cr`;
  const mandatory = WEEKDAYS.filter((d) => faculty.mandatory_days.includes(d)).join(", ");
  const coursePreferences = preferenceText(faculty.course_preferences);
  const roomPreferences = preferenceText(faculty.room_preferences);
  const labPreferences = preferenceText(faculty.lab_preferences);
  const uniqueCourseLimit = faculty.unique_course_limit;
  const maximumDays = faculty.maximum_days;

  return (
    <article className="item-card">
      <div className="item-card__header">
        <h3 className="item-card__title">{faculty.name}</h3>
        <span className="item-card__credits">{credits}</span>
      </div>
      <AvailabilityChips times={faculty.times} />
      <dl className="item-card__facts">
        {mandatory && (
          <>
            <dt>Mandatory Days</dt>
            <dd>{mandatory}</dd>
          </>
        )}
        <dt>Unique Course Limit</dt>
        <dd>{uniqueCourseLimit}</dd>
        <dt>Maximum Days</dt>
        <dd>{maximumDays}</dd>
        {coursePreferences && (
          <>
            <dt>Course Preferences</dt>
            <dd>{coursePreferences}</dd>
          </>
        )}
        {roomPreferences && (
          <>
            <dt>Room Preferences</dt>
            <dd>{roomPreferences}</dd>
          </>
        )}
        {labPreferences && (
          <>
            <dt>Lab Preferences</dt>
            <dd>{labPreferences}</dd>
          </>
        )}
      </dl>
      <EditButton label={faculty.name} onEdit={onEdit} />
    </article>
  );
}
