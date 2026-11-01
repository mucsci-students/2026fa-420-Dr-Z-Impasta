/**
 * The Time Slots card. A day tile's Edit button opens DayBlocksDialog for that day;
 * "Advanced timing options…" opens TimeSlotsDialog.
 */

import Button from "../../../components/Button.jsx";
import { DAY_NAMES } from "../labels.js";
import CardRow from "./CardRow.jsx";
import EditButton from "./EditButton.jsx";

/**
 * The time grid: a tile per weekday with its blocks, and the two timing options in the header.
 * Time slots can be edited but not added or deleted, so there is no "Add" tile.
 */
export default function TimeSlotsCard({ timeSlots, days, onEditDay, onEditTiming }) {
  return (
    <CardRow
      title="Time Slots"
      meta={`Gap ${timeSlots.max_time_gap}m · Overlap ${timeSlots.min_time_overlap}m`}
      actions={
        <Button size="sm" variant="ghost" onClick={onEditTiming}>
          Advanced timing options…
        </Button>
      }
    >
      {days.map((day) => {
        const blocks = timeSlots.times[day] ?? [];
        return (
          <article key={day} className="item-card day-tile">
            <h3 className="item-card__title">{DAY_NAMES[day] ?? day}</h3>
            {blocks.length === 0 ? (
              <p className="item-card__note">No blocks</p>
            ) : (
              <ul className="day-tile__blocks">
                {blocks.map((block, i) => (
                  <li key={i}>
                    <span>
                      {block.start}–{block.end}
                    </span>
                    <span className="muted">{block.spacing}m</span>
                  </li>
                ))}
              </ul>
            )}
            <EditButton label={`${DAY_NAMES[day] ?? day} time blocks`} onEdit={() => onEditDay?.(day)} />
          </article>
        );
      })}
    </CardRow>
  );
}
