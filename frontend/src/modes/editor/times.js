/** Helpers for the editor's "HH:MM" times. */

/** "16:30" → "17:30", stopping at "23:59" so a range stays inside the day. */
export function hourAfter(time) {
  const [hours, minutes] = time.split(":").map(Number);
  if (hours >= 23) return "23:59";
  return `${String(hours + 1).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
}
