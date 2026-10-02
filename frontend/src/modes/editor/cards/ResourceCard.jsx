// Description: Name; Capacity; Used by N sections (For rooms and labs).
//
// Missing From Mockup: Features (features tags). Availability (times): show "Always" when it's
// null, or Mo–Fr chips like the faculty card.

import { plural } from "../../../format.js";

/** A room or lab: its name, capacity, how many sections use it, features, and availability. */
export default function ResourceCard({ resource, usedBy, onEdit }) {

  return (
    <article
      className="item-card"
      onClick={onEdit}
      onKeyDown={(e) => { if (e.key === "Enter") onEdit?.() }}
      tabIndex={0}
    >
      <h3 className="item-card__title">{resource.name}</h3>
      <dl className="item-card__facts">
        <dt>Capacity</dt>
        <dd>{resource.capacity}</dd>
        <dt>Used by</dt>
        <dd>{plural(usedBy, "section")}</dd>
      </dl>
    </article>
  );
}
