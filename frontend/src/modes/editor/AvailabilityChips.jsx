// Description: Mo–Fr chips showing each day's available time ranges, or "off".

const DAYS = [
  ["MON", "Mo"],
  ["TUE", "Tu"],
  ["WED", "We"],
  ["THU", "Th"],
  ["FRI", "Fr"],
];

/** "11:00" → "11", "13:30" → "13:30": the short times the mockup uses. */
function shortTime(time) {
  const [hours, minutes] = time.split(":");
  return minutes === "00" ? String(Number(hours)) : `${Number(hours)}:${minutes}`;
}

/** Mo–Fr chips showing each day's available time ranges, or "off". */
export default function AvailabilityChips({ times }) {
  return (
    <ul className="avail">
      {DAYS.map(([key, label]) => {
        const ranges = times[key] ?? [];
        return (
          <li key={key} className={`avail__day ${ranges.length === 0 ? "avail__day--off" : ""}`}>
            <span className="avail__label">{label}</span>
            {ranges.length === 0 ? (
              <span>off</span>
            ) : (
              ranges.map((r, i) => (
                <span key={i}>
                  {shortTime(r.start)}–{shortTime(r.end)}
                </span>
              ))
            )}
          </li>
        );
      })}
    </ul>
  );
}
