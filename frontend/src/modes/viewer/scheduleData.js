/**
 * Schedule data helpers for the Schedule Viewer.
 *
 * Reads the scheduler library's JSONWriter format (README → "Schedule JSON format"):
 *
 *   [                                  ← a list of schedules
 *     [                                ← one schedule: a list of course assignments
 *       { "course": "CS 102.01", "faculty": "Dr. Jones",
 *         "room": "Room 101", "lab": "Lab 101",
 *         "times": [{ "day": 1, "start": 900, "duration": 75, "delivery": "in_person" }, ...],
 *         "lab_index": 1, "reserve_room_during_lab": true }
 *     ]
 *   ]
 *
 * day 1–5 = Monday–Friday, start = minutes after midnight, duration = minutes.
 * room, lab and lab_index appear only when assigned; lab_index says which of
 * `times` is the lab meeting.
 *
 * Everything that knows this shape lives here; components only see "events".
 */

export const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
export const START_HOUR = 8;
export const END_HOUR = 20;

/* ------------------------------------------------------------------ */
/* Schedules and assignments                                           */
/* ------------------------------------------------------------------ */

/**
 * The list of schedules in whatever the app state or a file holds:
 * a bare list of schedules, or an object wrapping one (items / schedules / results).
 */
export function getScheduleList(schedules) {
  if (!schedules) return [];
  if (Array.isArray(schedules)) return schedules;
  return schedules.items ?? schedules.schedules ?? schedules.results ?? [];
}

/** One schedule's course assignments. A schedule is a list (or { assignments }). */
export function getAssignments(schedule) {
  if (Array.isArray(schedule)) return schedule;
  return schedule?.assignments ?? schedule?.sections ?? [];
}

/** "CS 102.01" → { courseId: "CS 102", sectionId: "01" }. */
function splitCourse(value) {
  const text = String(value ?? "").trim();
  const match = text.match(/^(.*)\.(\d+)$/);
  if (match) return { courseId: match[1], sectionId: match[2] };
  return { courseId: text || "Unknown", sectionId: "" };
}

/* ------------------------------------------------------------------ */
/* Times                                                               */
/* ------------------------------------------------------------------ */

/** Format minutes after midnight as HH:MM, or return TBA for missing or NaN values. */
export function formatMinutes(minutes) {
  if (minutes == null || Number.isNaN(minutes)) return "TBA";
  const hours = String(Math.floor(minutes / 60)).padStart(2, "0");
  const mins = String(minutes % 60).padStart(2, "0");
  return `${hours}:${mins}`;
}

/** Coerce a value with Number and return null when the result is not finite. */
function toNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

/* ------------------------------------------------------------------ */
/* Events and groups                                                   */
/* ------------------------------------------------------------------ */

/**
 * Which rooms/labs a meeting occupies.
 * - Online meetings occupy none.
 * - The lab meeting occupies the lab, and also the room when
 *   reserve_room_during_lab is true.
 * - Every other meeting occupies the room.
 */
function getResources(assignment, isLab, isOnline) {
  if (isOnline) return [];
  const room = assignment.room ? { type: "Room", name: String(assignment.room) } : null;
  const lab = assignment.lab ? { type: "Lab", name: String(assignment.lab) } : null;

  if (isLab) {
    const resources = [];
    if (lab) resources.push(lab);
    if (room && (assignment.reserve_room_during_lab || !lab)) resources.push(room);
    return resources;
  }
  return room ? [room] : [];
}

/**
 * Flattens one schedule into events: one per meeting in `times`.
 * Each event has everything the timetable, table and exports need.
 */
export function buildEvents(schedule) {
  return getAssignments(schedule).flatMap((assignment, assignmentIndex) => {
    const { courseId, sectionId } = splitCourse(assignment?.course);
    const faculty = assignment?.faculty ? String(assignment.faculty) : "";
    const times = Array.isArray(assignment?.times) ? assignment.times : [];

    return times.map((time, timeIndex) => {
      const dayNumber = toNumber(time?.day);
      const start = toNumber(time?.start);
      const duration = toNumber(time?.duration);
      const isLab = assignment.lab_index != null && Number(assignment.lab_index) === timeIndex;
      const isOnline = time?.delivery === "online";
      const resources = getResources(assignment, isLab, isOnline);

      return {
        id: `${assignmentIndex}-${timeIndex}`,
        assignment,
        courseId,
        sectionId,
        faculty,
        resources,
        // What to show on a timetable block: the lab for a lab meeting, else the room.
        place: isOnline ? "Online" : resources[0]?.name ?? "",
        isLab,
        isOnline,
        day: dayNumber >= 1 && dayNumber <= 5 ? DAYS[dayNumber - 1] : null,
        start,
        end: start != null && duration != null ? start + duration : null,
      };
    });
  });
}

const TYPE_ORDER = { Room: 0, Faculty: 0, Lab: 1, Online: 2, Unassigned: 3 };

/** Groups events by room/lab or by faculty, for the cards and the views. */
export function groupEvents(events, groupBy) {
  const groups = new Map();

  /** Append an event to its group and track distinct assignment objects for section counts. */
  function add(key, name, type, event) {
    if (!groups.has(key)) {
      groups.set(key, { key, name, type, events: [], sections: new Set() });
    }
    const group = groups.get(key);
    group.events.push(event);
    group.sections.add(event.assignment);
  }

  events.forEach((event) => {
    if (groupBy === "faculty") {
      if (event.faculty) add(`faculty:${event.faculty}`, event.faculty, "Faculty", event);
      else add("unassigned", "Unassigned", "Unassigned", event);
    } else if (event.isOnline) {
      add("online", "Online", "Online", event);
    } else if (event.resources.length) {
      event.resources.forEach(({ type, name }) => add(`${type}:${name}`, name, type, event));
    } else {
      add("unassigned", "Unassigned", "Unassigned", event);
    }
  });

  return [...groups.values()]
    .map((group) => ({ ...group, sectionCount: group.sections.size }))
    .sort(
      (a, b) =>
        TYPE_ORDER[a.type] - TYPE_ORDER[b.type] ||
        a.name.localeCompare(b.name, undefined, { numeric: true }),
    );
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