// Description: course_id + section (CMSC 140 .01, from sections); credits; Capacity; Rooms;
// Labs; Faculty (null means "Any"); Conflicts; Modality (in_person / online / hybrid); Room features
// (required_room_features); Lab features (required_lab_features); Lab uses room
// (reserve_room_during_lab, true/false; only matters when the course has labs); Alternate faculty (alternate_faculty).

import { plural } from "../../../format.js";
import { MODALITY_NAMES } from "../labels.js";

/** A course section: identity, credits, capacity, resources, faculty, conflicts, and requirements. */
export default function CourseCard({ course, label, onEdit }) {
  const section = label.slice(course.course_id.length);
  const rooms = course.room.length > 0 ? course.room.join(", ") : "None";
  const labs = course.lab.length > 0 ? course.lab.join(", ") : "None"; // TODO: Do not display if empty
  const faculty = course.faculty ? course.faculty.join(", ") : "Any";
  const conflicts = course.conflicts.length > 0 ? plural(course.conflicts.length, "course") : "None";
  const modality = MODALITY_NAMES[course.modality];
  // alternate_faculty defaults to []. Each listed person must be a configured faculty member and must be available for every
  // assigned course meeting; alternates are not eligible assigned instructors unless they also appear in faculty.
  const alternateFaculty = course.alternate_faculty ? course.alternate_faculty.join(", ") : "None"; // TODO: Do not display if empty; has no dialog yet
  const requiredRoomFeatures = course.required_room_features ? course.required_room_features.join(", ") : "None"; // TODO: Do not display if empty; has no dialog yet
  const requiredLabFeatures = course.required_lab_features ? course.required_lab_features.join(", ") : "None"; // TODO: Do not display if empty; has no dialog yet
  const reserveRoomDuringLab = course.reserve_room_during_lab ? "Yes" : "No"; // TODO: Do not display if empty; has no dialog yet

  return (
    <article
      className="item-card"
      onClick={onEdit}
      onKeyDown={(e) => { if (e.key === "Enter") onEdit?.() }}
      tabIndex={0}
    >
      <div className="item-card__header">
        <h3 className="item-card__title">
          {course.course_id} <span className="item-card__section">{section}</span>
        </h3>
        <span className="item-card__credits">{course.credits} cr</span>
      </div>
      <dl className="item-card__facts">
        <dt>Capacity</dt>
        <dd>{course.capacity}</dd>
        <dt>Rooms</dt>
        <dd>{rooms}</dd>
        <dt>Labs</dt>
        <dd>{labs}</dd>
        <dt>Faculty</dt>
        <dd>{faculty}</dd>
        <dt>Conflicts</dt>
        <dd>{conflicts}</dd>
        <dt>Modality</dt>
        <dd>{modality}</dd>
        <dt>Alternate Faculty</dt>
        <dd>{alternateFaculty}</dd>
        <dt>Required Room Features</dt>
        <dd>{requiredRoomFeatures}</dd>
        <dt>Required Lab Features</dt>
        <dd>{requiredLabFeatures}</dd>
        <dt>Reserve Room During Lab</dt>
        <dd>{reserveRoomDuringLab}</dd>
      </dl>
    </article>
  );
}
