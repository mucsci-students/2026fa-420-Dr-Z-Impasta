// Description: course_id + section (CMSC 140 .01, from sections); credits; Capacity; Rooms;
// Labs; Faculty (null means "Any"); Conflicts.
//
// Missing From Mockup: Modality (in_person / online / hybrid). Room features
// (required_room_features). Lab features (required_lab_features). Lab uses room
// (reserve_room_during_lab, true/false; only matters when the course has labs).

import { plural } from "../../../format.js";

const MODALITY_NAMES = { in_person: "In person", online: "Online", hybrid: "Hybrid" };

/** A course section: identity, credits, capacity, resources, faculty, conflicts, and requirements. */
export default function CourseCard({ course, label}) {
  const section = label.slice(course.course_id.length);   // "CMSC 140.01" → ".01"
const rooms = course.room.length > 0 ? course.room.join(", ") : "None";
const labs = course.lab.length > 0 ? course.lab.join(", ") : "None";
  const faculty = course.faculty ? course.faculty.join(", ") : "Any";
  const conflicts = course.conflicts.length > 0 ? plural(course.conflicts.length, "course") : "None";

  return (
    <article className="item-card">
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
      </dl>
    </article>
  );
}
