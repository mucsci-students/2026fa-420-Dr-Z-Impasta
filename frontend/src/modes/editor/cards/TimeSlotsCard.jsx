// Description: One tile per weekday listing its blocks (start–end, spacing).
//
// Missing From Mockup: Max time gap (max_time_gap, default 30) and Min overlap
// (min_time_overlap, default 45). The mockup hides them behind "Advanced timing options…", so add
// a small line like Gap 30m · Overlap 45m in the header or under the tiles. Then they're visible
// without opening the dialog.

import Button from "../../../components/Button.jsx";
import { DAY_NAMES } from "../labels.js";
import CardRow from "./CardRow.jsx";

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
          <article
            key={day}
            className="item-card day-tile"
            tabIndex={0}
            aria-label={`${DAY_NAMES[day] ?? day} time blocks`}
            onClick={() => onEditDay?.(day)}
            onKeyDown={(e) => {
              if (e.target === e.currentTarget && (e.key === "Enter" || e.key === " ")) {
                e.preventDefault();
                onEditDay?.(day);
              }
            }}
          >
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
          </article>
        );
      })}
    </CardRow>
  );
}
