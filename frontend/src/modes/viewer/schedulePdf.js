/**
 * What goes into a schedule PDF, decided from the same reply the viewer shows
 * (docs/web-api.md → `GET /api/schedules/{number}?group=room|faculty`).
 *
 * This file has no PDF library and no React: it turns a schedule view plus the user's
 * choices into a plain description of the document (header lines, one section per room,
 * lab, or faculty member, table rows, file name). schedulePdfDocument.js draws that
 * description; PdfExportDialog.jsx collects the choices.
 *
 * Nothing here changes the view it is given. The export is read-only.
 *
 * Row order (the same in every section): by the first weekday a row meets, then start
 * time, then course, then section. Sections keep the server's order: rooms by name, then
 * labs by name; faculty by name.
 */

export const NO_RESOURCE = "No physical resource assigned";
export const NO_SCHEDULES_MESSAGE =
  "No schedules are available to export. Generate or import a schedule first.";
export const FAILED_MESSAGE =
  "PDF export failed. Your existing schedule has not been changed. Please try again.";

export const APP_TITLE = "Dr. ZImpasta Course Schedule";

export const GROUPINGS = {
  room: { label: "Room / Lab", all: "All rooms and labs", one: "Specific room or lab" },
  faculty: { label: "Faculty", all: "All faculty members", one: "Specific faculty member" },
};

/** Paper sizes by the names jsPDF knows. US Letter is the default. */
export const PAPER_SIZES = {
  letter: { label: "US Letter (8.5 × 11 in)", name: "US Letter" },
  a4: { label: "A4 (210 × 297 mm)", name: "A4" },
};
export const DEFAULT_PAPER = "letter";

const KIND_LABELS = { room: "Room", lab: "Lab", faculty: "Faculty" };
/** The kinds of group each export covers. Online and unassigned meetings have no room. */
const EXPORTED_KINDS = { room: ["room", "lab"], faculty: ["faculty"] };
const DAY_CODES = ["M", "T", "W", "Th", "F", "Sa", "Su"];

/**
 * An export that can't go ahead, with a message written for the user. `code` is
 * "no_schedules", "invalid_schedule", "invalid_grouping", "invalid_paper",
 * "missing_selection", "unknown_resource", "empty", "malformed", or "load_failed".
 */
export class PdfExportError extends Error {
  constructor(code, message, options) {
    super(message, options);
    this.name = "PdfExportError";
    this.code = code;
  }
}

// ------------------------------------------------------------------ formatting

/** "9:00 AM" from minutes after midnight, or "TBA" when the time is missing. */
export function formatClock(minutes) {
  if (typeof minutes !== "number" || !Number.isFinite(minutes) || minutes < 0) return "TBA";
  const hours = Math.floor(minutes / 60) % 24;
  const mins = String(Math.floor(minutes % 60)).padStart(2, "0");
  return `${hours % 12 || 12}:${mins} ${hours < 12 ? "AM" : "PM"}`;
}

/** "MWF" or "TTh" from day numbers (1 = Monday), in weekday order; "TBA" when empty. */
export function formatDayCodes(dayNumbers) {
  const codes = [...new Set(dayNumbers)]
    .filter((day) => Number.isInteger(day) && day >= 1 && day <= DAY_CODES.length)
    .sort((a, b) => a - b)
    .map((day) => DAY_CODES[day - 1]);
  return codes.length ? codes.join("") : "TBA";
}

/** "roddy_147" from "Roddy 147": lowercase letters and digits joined by underscores. */
function slug(text) {
  return String(text)
    .normalize("NFKD")
    .replace(/\p{M}/gu, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

/**
 * The download's name: schedule_1_room_lab.pdf, schedule_1_faculty.pdf,
 * schedule_1_room_roddy_147.pdf, schedule_1_lab_mac.pdf, schedule_1_faculty_hardy.pdf.
 * The kind is part of a single resource's name so a room and a lab that share a name
 * get different files.
 */
export function pdfFilename({ number, groupBy, group = null }) {
  const base = `schedule_${number}`;
  if (!group) return `${base}_${groupBy === "faculty" ? "faculty" : "room_lab"}.pdf`;
  const name = slug(group.name) || "unnamed";
  return `${base}_${group.kind}_${name}.pdf`;
}

// ------------------------------------------------------------------ reading the view

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function malformed(detail) {
  return new PdfExportError(
    "malformed",
    `This schedule can't be exported because its data is incomplete (${detail}). ` +
      "Your existing schedule has not been changed.",
  );
}

/** Check the reply has what the export reads, so a bad one fails with a clear message. */
function checkView(view, groupBy) {
  if (!GROUPINGS[groupBy]) {
    throw new PdfExportError("invalid_grouping", "Choose Room / Lab or Faculty to group by.");
  }
  if (view == null) throw new PdfExportError("no_schedules", NO_SCHEDULES_MESSAGE);
  if (!isObject(view) || !Array.isArray(view.groups)) throw malformed("no groups");
  if (!Number.isInteger(view.number) || view.number < 1) {
    throw new PdfExportError("invalid_schedule", "Choose a schedule to export.");
  }
  if (view.group !== groupBy) throw malformed(`grouped by ${view.group}, not ${groupBy}`);
  view.groups.forEach((group, index) => {
    const where = `group ${index + 1}`;
    if (!isObject(group)) throw malformed(where);
    if (typeof group.name !== "string" || typeof group.kind !== "string") {
      throw malformed(`${where} has no name or kind`);
    }
    if (!Array.isArray(group.meetings)) throw malformed(`${group.name} has no meetings list`);
    group.meetings.forEach((meeting, position) => {
      const which = `${group.name}, meeting ${position + 1}`;
      if (!isObject(meeting)) throw malformed(which);
      if (typeof (meeting.course_id ?? meeting.course) !== "string") {
        throw malformed(`${which} has no course`);
      }
    });
  });
}

/** `kind:name`, so a room and a lab with the same name stay separate. */
function groupKey(group) {
  return `${group.kind}:${group.name}`;
}

/**
 * The rooms and labs, or the faculty members, this schedule can be exported for:
 * `[{ key, kind, name, type, meetings }]` in the server's order. Online and unassigned
 * groups are left out of the room view because they are not a room or a lab.
 */
export function exportableGroups(view, groupBy) {
  checkView(view, groupBy);
  return view.groups
    .filter((group) => EXPORTED_KINDS[groupBy].includes(group.kind))
    .map((group) => ({
      key: groupKey(group),
      kind: group.kind,
      name: group.name,
      type: KIND_LABELS[group.kind],
      meetings: group.meetings,
    }));
}

/** Options for the "specific room, lab, or faculty member" list: `[{ value, label }]`. */
export function resourceOptions(view, groupBy) {
  return exportableGroups(view, groupBy).map((group) => ({
    value: group.key,
    label: groupBy === "room" ? `${group.name} (${group.type})` : group.name,
  }));
}

// ------------------------------------------------------------------ rows

/** Where a meeting physically is, for the faculty export. Never invents a room. */
function placeOf(meeting) {
  if (meeting.delivery === "online") return "Online";
  if (meeting.kind === "lab") return meeting.lab ? `${meeting.lab} (Lab)` : NO_RESOURCE;
  return meeting.room || NO_RESOURCE;
}

function typeOf(meeting, groupBy) {
  if (meeting.kind !== "lab") return "Lecture";
  // In a room's section, a lab meeting is listed because the room stays reserved for it.
  return groupBy === "room" && meeting.room_held_for_lab ? "Lab (room reserved)" : "Lab";
}

function endOf(meeting) {
  if (typeof meeting.end === "number") return meeting.end;
  if (typeof meeting.start === "number" && typeof meeting.duration === "number") {
    return meeting.start + meeting.duration;
  }
  return null;
}

function courseOf(meeting) {
  return meeting.course_id ?? meeting.course;
}

const collator = new Intl.Collator("en", { numeric: true, sensitivity: "base" });

/** By first weekday, then start time, then course, then section. */
function compareRows(a, b) {
  return (
    a.firstDay - b.firstDay ||
    a.startMinutes - b.startMinutes ||
    collator.compare(a.course, b.course) ||
    collator.compare(a.section, b.section)
  );
}

/**
 * One group's meetings as table rows. The server lists a meeting once per weekday; rows
 * that differ only by weekday are joined so "Days" reads MWF, as on a printed schedule.
 */
export function toRows(group, groupBy) {
  const rows = new Map();
  for (const meeting of group.meetings) {
    const course = courseOf(meeting);
    const section = meeting.section || "";
    const type = typeOf(meeting, groupBy);
    const other = groupBy === "room" ? meeting.faculty || "Not assigned" : placeOf(meeting);
    const start = typeof meeting.start === "number" ? meeting.start : null;
    const end = endOf(meeting);
    const key = JSON.stringify([course, section, type, other, start, end]);
    if (!rows.has(key)) {
      rows.set(key, { course, section, type, other, start, end, days: [] });
    }
    rows.get(key).days.push(meeting.day_number);
  }
  return [...rows.values()]
    .map((row) => {
      const days = row.days.filter((day) => Number.isInteger(day));
      return {
        course: row.course,
        section: row.section || "-",
        type: row.type,
        other: row.other,
        days: formatDayCodes(days),
        start: formatClock(row.start),
        end: formatClock(row.end),
        firstDay: days.length ? Math.min(...days) : Infinity,
        startMinutes: row.start ?? Infinity,
      };
    })
    .sort(compareRows);
}

const COLUMNS = {
  room: ["Course", "Section", "Type", "Faculty", "Days", "Start", "End"],
  faculty: ["Course", "Section", "Type", "Room / Lab", "Days", "Start", "End"],
};

function countText(count, singular, plural = `${singular}s`) {
  return `${count} ${count === 1 ? singular : plural}`;
}

// ------------------------------------------------------------------ the document

/**
 * Describe the PDF for one schedule.
 *
 * - `view`: the server's reply for the schedule, grouped the same way as `groupBy`.
 * - `groupBy`: "room" or "faculty".
 * - `scope`: "all", or "one" with `resourceKey` (a `value` from resourceOptions()).
 * - `paper`: a key of PAPER_SIZES.
 *
 * Returns `{ filename, paper, title, subtitle, details, columns, sections, notes,
 * footer }`. Each section is `{ kind, type, name, heading, summary, rows }` and each row
 * `{ course, section, type, other, days, start, end }`. Throws PdfExportError when the
 * choices are incomplete or there is nothing to export.
 */
export function buildSchedulePdf({ view, groupBy, scope = "all", resourceKey = "", paper }) {
  const groups = exportableGroups(view, groupBy);
  const wording = GROUPINGS[groupBy];
  const paperKey = paper ?? DEFAULT_PAPER;
  if (!PAPER_SIZES[paperKey]) {
    throw new PdfExportError("invalid_paper", "Choose US Letter or A4 paper.");
  }
  if (scope !== "all" && scope !== "one") {
    throw new PdfExportError("missing_selection", "Choose what to export.");
  }

  let chosen = groups;
  if (scope === "one") {
    if (!resourceKey) {
      throw new PdfExportError(
        "missing_selection",
        groupBy === "room" ? "Choose a room or lab to export." : "Choose a faculty member to export.",
      );
    }
    chosen = groups.filter((group) => group.key === resourceKey);
    if (!chosen.length) {
      throw new PdfExportError(
        "unknown_resource",
        groupBy === "room"
          ? `That room or lab has no meetings in schedule ${view.number}. Choose another.`
          : `That faculty member has no meetings in schedule ${view.number}. Choose another.`,
      );
    }
  }

  const sections = chosen
    .map((group) => {
      const rows = toRows(group, groupBy);
      const sectionsCount = new Set(
        group.meetings.map((meeting) => meeting.course ?? `${meeting.course_id}.${meeting.section}`),
      ).size;
      return {
        kind: group.kind,
        type: group.type,
        name: group.name,
        heading: groupBy === "room" ? `${group.type.toUpperCase()}: ${group.name}` : group.name,
        summary: `${countText(sectionsCount, "section")} · ${countText(group.meetings.length, "meeting")}`,
        rows,
      };
    })
    .filter((section) => section.rows.length);

  if (!sections.length) {
    throw new PdfExportError(
      "empty",
      groupBy === "room"
        ? `Schedule ${view.number} has no meetings in a room or lab, so there is nothing to export by room and lab.`
        : `Schedule ${view.number} has no meetings, so there is nothing to export.`,
    );
  }

  const single = scope === "one" ? chosen[0] : null;
  const scopeText = single
    ? `${groupBy === "room" ? single.type : "Faculty member"}: ${single.name}`
    : `${wording.all} (${sections.length})`;
  const scheduleText =
    Number.isInteger(view.count) && view.count > 0
      ? `Schedule ${view.number} of ${view.count}`
      : `Schedule ${view.number}`;

  return {
    filename: pdfFilename({ number: view.number, groupBy, group: single }),
    paper: paperKey,
    title: APP_TITLE,
    subtitle: `Schedule ${view.number} - ${groupBy === "room" ? "Room and Lab" : "Faculty"} Schedule`,
    details: [
      ["Schedule", scheduleText],
      ["Grouped By", wording.label],
      ["Export Scope", scopeText],
    ],
    columns: COLUMNS[groupBy],
    sections,
    notes: notesFor(view, groupBy, sections),
    footer: `Schedule ${view.number} · ${wording.label}${single ? ` · ${single.name}` : ""}`,
  };
}

/** Short explanations printed after the tables, only when they apply. */
function notesFor(view, groupBy, sections) {
  const notes = [];
  const rows = sections.flatMap((section) => section.rows);
  if (rows.some((row) => row.type === "Lab (room reserved)")) {
    notes.push(
      "Lab (room reserved): the lab meeting takes place in its lab, and this room stays reserved for the section during it.",
    );
  }
  if (groupBy === "room") {
    const elsewhere = view.groups
      .filter((group) => !EXPORTED_KINDS.room.includes(group.kind))
      .reduce((total, group) => total + group.meetings.length, 0);
    if (elsewhere) {
      notes.push(
        `${countText(elsewhere, "meeting")} in this schedule ${elsewhere === 1 ? "is" : "are"} online or ${elsewhere === 1 ? "has" : "have"} no room, so ${elsewhere === 1 ? "it is" : "they are"} not listed here. The faculty export lists every meeting.`,
      );
    }
  }
  if (rows.some((row) => row.days === "TBA" || row.start === "TBA" || row.end === "TBA")) {
    notes.push("TBA: the schedule has no day or time for this meeting.");
  }
  return notes;
}

/** Counts for the dialog's review: `{ sections, rows, paper }`. */
export function describeSchedulePdf(pdf) {
  return {
    sections: pdf.sections.length,
    rows: pdf.sections.reduce((total, section) => total + section.rows.length, 0),
    paper: PAPER_SIZES[pdf.paper].name,
  };
}
