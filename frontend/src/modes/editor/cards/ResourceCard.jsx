/**
 * One room or lab; the Rooms and Labs rows both use this card. Its Edit button opens ResourceDialog.
 * `times` null means always available, so "Unrestricted" replaces the availability chips.
 */

import { plural } from "../../../format.js";
import AvailabilityChips from "../AvailabilityChips.jsx";
import EditButton from "./EditButton.jsx";

/** A room or lab: its name, capacity, how many sections use it, features, and availability. */
export default function ResourceCard({ resource, usedBy, onEdit }) {
  const features = resource.features?.join(", ");

  return (
    <article className="item-card">
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
      <EditButton label={resource.name} onEdit={onEdit} />
    </article>
  );
}
