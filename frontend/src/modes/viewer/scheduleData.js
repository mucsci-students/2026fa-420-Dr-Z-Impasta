/**
 * Display helpers for the Schedule Viewer.
 *
 * The server groups each schedule (docs/web-api.md → `GET /api/schedules/{number}`):
 *
 *   { number, count, group, totals: { sections, ... },
 *     groups: [ { name, kind, sections, meeting_count,
 *                 meetings: [ { course_id, section, faculty, room, lab, day_number,
 *                               start, end, kind, delivery, ... } ] } ] }
 *
 * `kind` is room, lab, online, or unassigned when grouped by room, and faculty otherwise.
 * This file only reshapes that reply for the timetable and table; it decides nothing
 * about where a meeting belongs.
 */

export const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
export const START_HOUR = 8;
export const END_HOUR = 20;

/** Format minutes after midnight as HH:MM, or return TBA for missing or NaN values. */
export function formatMinutes(minutes) {
  if (minutes == null || Number.isNaN(minutes)) return "TBA";
  const hours = String(Math.floor(minutes / 60)).padStart(2, "0");
  const mins = String(minutes % 60).padStart(2, "0");
  return `${hours}:${mins}`;
}

const GROUP_TYPES = {
  room: "Room",
  lab: "Lab",
  online: "Online",
  unassigned: "Unassigned",
  faculty: "Faculty",
};

/** Where a meeting takes place, for the "Room / lab" column and the faculty view. */
function placeOf(meeting) {
  if (meeting.delivery === "online") return "Online";
  return (meeting.kind === "lab" ? meeting.lab : meeting.room) ?? "";
}

/** The server's groups as cards, each with the events the timetable and table show. */
export function toGroups(view) {
  return (view?.groups ?? []).map((group) => ({
    key: `${group.kind}:${group.name}`,
    name: group.name,
    type: GROUP_TYPES[group.kind] ?? "Unassigned",
    sectionCount: group.sections,
    events: group.meetings.map((meeting, index) => ({
      id: `${index}-${meeting.course}-${meeting.day_number}-${meeting.start}`,
      courseId: meeting.course_id,
      sectionId: meeting.section,
      faculty: meeting.faculty ?? "",
      place: placeOf(meeting),
      isLab: meeting.kind === "lab",
      isOnline: meeting.delivery === "online",
      day: DAYS[meeting.day_number - 1] ?? null,
      start: meeting.start,
      end: meeting.end,
    })),
  }));
}

const PATH_WORDS = { times: "meeting" };

/**
 * Where a problem in a schedule file is, in words. The server locates each problem by its
 * position in the file: "0.1.times.0.day" in a file of several schedules, "1.times.0.day"
 * in a file of one schedule (a list of sections). Either way this gives
 * "Schedule 1 · section 2 · meeting 1 · day" or "Section 2 · meeting 1 · day".
 */
export function describeSchedulePath(path) {
  const parts = String(path ?? "").split(".").filter(Boolean);
  const isIndex = (part) => /^\d+$/.test(part);
  const words = [];
  if (parts.length === 1 || isIndex(parts[1])) words.push(`Schedule ${Number(parts.shift()) + 1}`);
  if (isIndex(parts[0] ?? "")) words.push(`section ${Number(parts.shift()) + 1}`);
  for (const part of parts) {
    if (isIndex(part) && words.length) words[words.length - 1] += ` ${Number(part) + 1}`;
    else words.push(PATH_WORDS[part] ?? part);
  }
  const text = words.join(" · ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** Sort order for tables and exports: by day, then start time, then course. */
export function compareEvents(a, b) {
  const dayA = a.day ? DAYS.indexOf(a.day) : Infinity;
  const dayB = b.day ? DAYS.indexOf(b.day) : Infinity;
  return (
    dayA - dayB ||
    (a.start ?? Infinity) - (b.start ?? Infinity) ||
    a.courseId.localeCompare(b.courseId, undefined, { numeric: true })
  );
}
