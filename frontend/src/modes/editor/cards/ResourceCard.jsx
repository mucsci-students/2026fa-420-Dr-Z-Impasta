// Description: Name; Capacity; Used by N sections (For rooms and labs); Features (features tags, hidden when empty);
// Availability (times): Mo–Fr availability chips, or "Unrestricted" when it's null.

import { plural } from "../../../format.js";
import AvailabilityChips from "../AvailabilityChips.jsx";

/** A room or lab: its name, capacity, how many sections use it, features, and availability. */
export default function ResourceCard({ resource, usedBy, onEdit }) {
  const features = resource.features?.join(", ");

  return (
    <article
      className="item-card"
      onClick={onEdit}
      onKeyDown={(e) => { if (e.key === "Enter") onEdit?.() }}
      tabIndex={0}
    >
      <h3 className="item-card__title">{resource.name}</h3>
      {resource.times && <AvailabilityChips times={resource.times} />}
      <dl className="item-card__facts">
        <dt>Capacity</dt>
        <dd>{resource.capacity}</dd>
        <dt>Used by</dt>
        <dd>{plural(usedBy, "section")}</dd>
        {features && (
          <>
            <dt>Features</dt>
            <dd>{features}</dd>
          </>
        )}
        {!resource.times && (
          <>
            <dt>Availability</dt>
            <dd>Unrestricted</dd>
          </>
        )}
      </dl>
    </article>
  );
}
