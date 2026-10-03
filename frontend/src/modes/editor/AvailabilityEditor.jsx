import { useRef } from "react";
import Button from "../../components/Button.jsx";
import { DAY_NAMES } from "./labels.js";

const WEEKDAYS = ["MON", "TUE", "WED", "THU", "FRI"];

/** A day's first range: the same working day ResourceDialog starts rooms with. */
const FIRST_RANGE = { start: "08:00", end: "17:00" };

/** "16:30" → "17:30", stopping at "23:59" so the range stays inside the day. */
function hourAfter(time) {
  const [hours, minutes] = time.split(":").map(Number);
  if (hours >= 23) return "23:59";
  return `${String(hours + 1).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
}

/** A new range for a day: the working day if it has none, else an hour after its last range. */
function nextRange(ranges) {
  const last = ranges.at(-1);
  if (!last?.end) return { ...FIRST_RANGE };
  return { start: last.end, end: hourAfter(last.end) };
}

/**
 * Per-weekday time ranges: { MON: [{ start: "09:00", end: "17:00" }], TUE: [], … }.
 * A day with no ranges is unavailable. `days` are the weekdays to show (from
 * api.config.options(); fallback until it arrives). The library checks the times (start
 * before end, valid format) when the dialog is saved; `error` shows what it reports.
 */
export default function AvailabilityEditor({ value, onChange, days = WEEKDAYS, legend = "Availability", error }) {
  const addButtons = useRef({});   // day → its "+ Add hours" button, for moving focus

  /** Replace one day's list of ranges, keeping the other days. */
  function setDay(day, ranges) {
    onChange({ ...value, [day]: ranges });
  }

  /** Change the start or end of range number i on one day. */
  function setTime(day, i, field, time) {
    setDay(day, (value[day] ?? []).map((range, j) => (j === i ? { ...range, [field]: time } : range)));
  }

  function removeRange(day, i) {
    const ranges = value[day] ?? [];
    setDay(day, ranges.filter((_, j) => j !== i));
    // Removing the last range unmounts the focused ×; keep keyboard users on this day
    if (i === ranges.length - 1) addButtons.current[day]?.focus();
  }

  return (
    <fieldset className="avail-editor">
      <legend>{legend}</legend>
      {days.map((day) => {
        const name = DAY_NAMES[day] ?? day;
        const ranges = value[day] ?? [];
        return (
          <div key={day} className="avail-editor__day">
            <span className="avail-editor__name">{name}</span>
            <div className="avail-editor__ranges">
              {ranges.length === 0 && <span className="muted">Unavailable</span>}
              {ranges.map((range, i) => (
                <span key={i} className="avail-editor__range">
                  <input
                    type="time"
                    aria-label={`${name} range ${i + 1} start`}
                    value={range.start}
                    onChange={(e) => setTime(day, i, "start", e.target.value)}
                  />
                  <span aria-hidden="true">–</span>
                  <input
                    type="time"
                    aria-label={`${name} range ${i + 1} end`}
                    value={range.end}
                    onChange={(e) => setTime(day, i, "end", e.target.value)}
                  />
                  <button
                    type="button"
                    className="avail-editor__remove"
                    aria-label={`Remove ${name} range ${i + 1}`}
                    onClick={() => removeRange(day, i)}
                  >
                    ×
                  </button>
                </span>
              ))}
              <Button
                size="sm"
                variant="ghost"
                ref={(button) => {
                  addButtons.current[day] = button;
                }}
                onClick={() => setDay(day, [...ranges, nextRange(ranges)])}
              >
                + Add hours
              </Button>
            </div>
          </div>
        );
      })}
      {error && (
        <p className="field__error">
          <span aria-hidden="true">⚠ </span>
          {error}
        </p>
      )}
    </fieldset>
  );
}
