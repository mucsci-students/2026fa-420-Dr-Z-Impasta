/**
 * PDF export of the Schedule Viewer (frontend/src/modes/viewer/schedulePdf*.js).
 * Run with `npm test` in frontend/ (node --test).
 *
 * The schedules are tests/fixtures/pdf_export_schedules.json, a file in the format
 * Load JSON imports. tests/fixtures/pdf_export_views.json holds what the server answers
 * for each of its schedules (`GET /api/schedules/{n}?group=room|faculty`);
 * tests/model/test_pdf_export_fixture.py keeps the two files in step.
 *
 * Most tests draw a real PDF and read the text back out of it.
 */
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { test } from "node:test";

import { exportSchedulePdf } from "../frontend/src/modes/viewer/exportSchedulePdf.js";
import { saveFile } from "../frontend/src/files.js";
import {
  FAILED_MESSAGE,
  NO_RESOURCE,
  NO_SCHEDULES_MESSAGE,
  PdfExportError,
  buildSchedulePdf,
  exportableGroups,
  formatClock,
  formatDayCodes,
  pdfFilename,
  resourceOptions,
} from "../frontend/src/modes/viewer/schedulePdf.js";
import {
  createSchedulePdfFile,
  drawSchedulePdf,
  pdfText,
} from "../frontend/src/modes/viewer/schedulePdfDocument.js";

const FIXTURES = path.join(import.meta.dirname, "fixtures");
const VIEWS = JSON.parse(fs.readFileSync(path.join(FIXTURES, "pdf_export_views.json"), "utf-8"));
const LONG_NAME = "Dr. Maximiliana Alexandrovna Featherstonehaugh-Montgomery-Vanderbilt III";
const NOW = new Date(2026, 10, 13, 10, 13);

/** The server's reply for schedule `number`, frozen so any attempt to change it throws. */
function view(number, group) {
  return deepFreeze(structuredClone(VIEWS[number][group]));
}

function deepFreeze(value) {
  if (value && typeof value === "object") {
    Object.values(value).forEach(deepFreeze);
    Object.freeze(value);
  }
  return value;
}

/** The PDF's pages, each a list of `{ text, x }` in drawing order. */
function readPages(doc) {
  const streams = doc.output().split("endstream").slice(0, -1);
  return streams
    .map((chunk) => chunk.slice(chunk.lastIndexOf("stream") + 6))
    .filter((content) => content.includes(" Tj"))
    .map((content) => {
      const items = [];
      let x = 0;
      for (const line of content.split("\n")) {
        const moved = /^(-?[\d.]+) (-?[\d.]+) Td$/.exec(line);
        if (moved) x = Number(moved[1]);
        // A wrapped line starts with "T*" (next line) and keeps the same x.
        const shown = /^(?:T\* )?\((.*)\) Tj$/.exec(line);
        if (shown) items.push({ text: shown[1].replace(/\\([()\\])/g, "$1"), x });
      }
      return items;
    });
}

function draw(options) {
  const pdf = buildSchedulePdf(options);
  const pages = readPages(drawSchedulePdf(pdf, { now: NOW }));
  return { pdf, pages, texts: pages.flat().map((item) => item.text) };
}

/** `[course, section, type, other, days, start, end]` for each row of a section. */
function rowsOf(pdf, name, kind) {
  const section = pdf.sections.find((s) => s.name === name && (!kind || s.kind === kind));
  assert.ok(section, `no section for ${name}`);
  return section.rows.map((r) => [r.course, r.section, r.type, r.other, r.days, r.start, r.end]);
}

function expectError(action, code) {
  assert.throws(action, (error) => {
    assert.ok(error instanceof PdfExportError, `expected a PdfExportError, got ${error}`);
    assert.equal(error.code, code);
    assert.ok(error.message.length > 10);
    return true;
  });
}

// ------------------------------------------------------------------ formatting

test("times are 12-hour clock times and missing ones say TBA", () => {
  assert.equal(formatClock(540), "9:00 AM");
  assert.equal(formatClock(590), "9:50 AM");
  assert.equal(formatClock(0), "12:00 AM");
  assert.equal(formatClock(720), "12:00 PM");
  assert.equal(formatClock(735), "12:15 PM");
  assert.equal(formatClock(1230), "8:30 PM");
  assert.equal(formatClock(null), "TBA");
  assert.equal(formatClock(undefined), "TBA");
  assert.equal(formatClock(Number.NaN), "TBA");
});

test("days are joined in weekday order", () => {
  assert.equal(formatDayCodes([5, 1, 3]), "MWF");
  assert.equal(formatDayCodes([4, 2]), "TTh");
  assert.equal(formatDayCodes([2, 2]), "T");
  assert.equal(formatDayCodes([]), "TBA");
  assert.equal(formatDayCodes([null, 9]), "TBA");
});

test("file names describe the schedule, grouping, and resource", () => {
  assert.equal(pdfFilename({ number: 1, groupBy: "room" }), "schedule_1_room_lab.pdf");
  assert.equal(pdfFilename({ number: 1, groupBy: "faculty" }), "schedule_1_faculty.pdf");
  assert.equal(
    pdfFilename({ number: 2, groupBy: "room", group: { kind: "room", name: "Roddy 140" } }),
    "schedule_2_room_roddy_140.pdf",
  );
  assert.equal(
    pdfFilename({ number: 2, groupBy: "room", group: { kind: "lab", name: "Linux" } }),
    "schedule_2_lab_linux.pdf",
  );
  assert.equal(
    pdfFilename({ number: 3, groupBy: "faculty", group: { kind: "faculty", name: "Dr. Smith" } }),
    "schedule_3_faculty_dr_smith.pdf",
  );
  assert.equal(
    pdfFilename({ number: 1, groupBy: "faculty", group: { kind: "faculty", name: "../Zoë?" } }),
    "schedule_1_faculty_zoe.pdf",
  );
});

// ------------------------------------------------------------------ room and lab export

test("all rooms and labs: every room and lab has its own section, rooms first", () => {
  const { pdf, texts } = draw({ view: view(1, "room"), groupBy: "room" });

  assert.deepEqual(
    pdf.sections.map((section) => section.heading),
    ["ROOM: Annex 12", "ROOM: Roddy 140", "ROOM: Roddy 147", "LAB: Annex 12", "LAB: Linux", "LAB: Mac"],
  );
  assert.equal(pdf.filename, "schedule_1_room_lab.pdf");
  for (const section of pdf.sections) assert.ok(texts.includes(section.heading), section.heading);
  // The document says what it is.
  assert.ok(texts.includes("DR. ZIMPASTA COURSE SCHEDULE"));
  assert.ok(texts.includes("Schedule 1 - Room and Lab Schedule"));
  assert.deepEqual(pdf.details, [
    ["Schedule", "Schedule 1 of 3"],
    ["Grouped By", "Room / Lab"],
    ["Export Scope", "All rooms and labs (6)"],
  ]);
  for (const [label, value] of pdf.details) {
    assert.ok(texts.includes(`${label}:`), label);
    assert.ok(texts.includes(value), value);
  }
  assert.ok(texts.includes("November 13, 2026 at 10:13 AM"));
  assert.deepEqual(pdf.columns, ["Course", "Section", "Type", "Faculty", "Days", "Start", "End"]);
});

test("a room's rows have the right course, section, faculty, days, and times, in order", () => {
  const { pdf } = draw({ view: view(1, "room"), groupBy: "room" });

  // By first weekday, then start time, then course and section.
  assert.deepEqual(rowsOf(pdf, "Roddy 140", "room"), [
    ["CMSC 161", "02", "Lecture", "Dr. Smith", "MWF", "8:00 AM", "8:50 AM"],
    ["CMSC 161", "01", "Lecture", "Dr. Smith", "MWF", "9:00 AM", "9:50 AM"],
    ["CMSC 162", "01", "Lecture", "Dr. Jones", "TTh", "11:00 AM", "12:15 PM"],
    // The lab meets in Linux; this room stays reserved for the section meanwhile.
    ["CMSC 162", "01", "Lab (room reserved)", "Dr. Jones", "W", "1:00 PM", "2:50 PM"],
  ]);
  assert.deepEqual(rowsOf(pdf, "Linux", "lab"), [
    ["CMSC 162", "01", "Lab", "Dr. Jones", "W", "1:00 PM", "2:50 PM"],
  ]);
  // CMSC 340.02 does not keep its room during its lab, so Roddy 147 has no lab row for it.
  assert.deepEqual(rowsOf(pdf, "Roddy 147", "room"), [
    ["CMSC 453", "01", "Lecture", "Dr. Brown", "MW", "10:00 AM", "10:50 AM"],
    ["CMSC 340", "02", "Lecture", "Dr. Smith", "MF", "2:00 PM", "2:50 PM"],
    ["CMSC 453", "01", "Lab (room reserved)", "Dr. Brown", "Th", "4:00 PM", "5:50 PM"],
  ]);
  assert.ok(pdf.notes.some((note) => note.startsWith("Lab (room reserved):")));
});

test("the rows are printed in the PDF exactly as described", () => {
  const { pdf, texts } = draw({ view: view(1, "room"), groupBy: "room", scope: "one", resourceKey: "room:Roddy 140" });

  // The first two rows fit on one line per cell, so the cells follow the headings in order.
  const start = texts.indexOf("End") + 1;
  const expected = rowsOf(pdf, "Roddy 140");
  assert.deepEqual(texts.slice(start, start + 14), [...expected[0], ...expected[1]]);
  // Every value of every row is in the PDF ("Lab (room reserved)" may wrap in its cell).
  const all = texts.join(" ");
  for (const value of expected.flat()) assert.ok(all.includes(value), `${value} is missing`);
});

test("a room and a lab with the same name stay separate", () => {
  const { pdf } = draw({ view: view(1, "room"), groupBy: "room" });

  assert.deepEqual(rowsOf(pdf, "Annex 12", "room"), [
    ["CMSC 420", "01", "Lecture", LONG_NAME, "TTh", "1:30 PM", "2:45 PM"],
  ]);
  assert.deepEqual(rowsOf(pdf, "Annex 12", "lab"), [
    ["CMSC 453", "01", "Lab", "Dr. Brown", "Th", "4:00 PM", "5:50 PM"],
  ]);
  const options = resourceOptions(view(1, "room"), "room");
  assert.deepEqual(
    options.filter((option) => option.label.startsWith("Annex 12")),
    [
      { value: "room:Annex 12", label: "Annex 12 (Room)" },
      { value: "lab:Annex 12", label: "Annex 12 (Lab)" },
    ],
  );
});

test("a specific room: only that room is in the PDF", () => {
  const { pdf, texts } = draw({
    view: view(1, "room"),
    groupBy: "room",
    scope: "one",
    resourceKey: "room:Roddy 147",
  });

  assert.deepEqual(pdf.sections.map((section) => section.heading), ["ROOM: Roddy 147"]);
  assert.equal(pdf.filename, "schedule_1_room_roddy_147.pdf");
  assert.ok(texts.includes("Room: Roddy 147"));
  assert.ok(texts.includes("ROOM: Roddy 147"));
  assert.ok(!texts.some((text) => text.includes("Roddy 140") || text.includes("Linux")));
  assert.ok(!texts.includes("CMSC 161"));
});

test("a specific lab: only that lab is in the PDF", () => {
  const { pdf, texts } = draw({
    view: view(1, "room"),
    groupBy: "room",
    scope: "one",
    resourceKey: "lab:Annex 12",
  });

  assert.deepEqual(pdf.sections.map((section) => section.heading), ["LAB: Annex 12"]);
  assert.equal(pdf.filename, "schedule_1_lab_annex_12.pdf");
  assert.ok(texts.includes("Lab: Annex 12"));
  assert.ok(!texts.includes("ROOM: Annex 12"));
  assert.ok(!texts.includes("CMSC 420"), "the room named Annex 12 must not be mixed in");
  assert.ok(texts.includes("CMSC 453"));
});

test("online meetings and meetings without a room are counted, not given a room", () => {
  const { pdf, texts } = draw({ view: view(1, "room"), groupBy: "room" });

  assert.ok(!pdf.sections.some((section) => ["Online", "No room"].includes(section.name)));
  assert.ok(!texts.includes("CMSC 101"));
  const note = pdf.notes.find((text) => text.startsWith("3 meetings"));
  assert.ok(note, "the PDF says how many meetings are not listed");
  assert.match(note, /online or have no room/);
});

// ------------------------------------------------------------------ faculty export

test("all faculty: every faculty member has a section with where each meeting is", () => {
  const { pdf, texts } = draw({ view: view(1, "faculty"), groupBy: "faculty" });

  assert.deepEqual(
    pdf.sections.map((section) => section.heading),
    ["Dr. Brown", "Dr. Jones", LONG_NAME, "Dr. Smith"],
  );
  assert.equal(pdf.filename, "schedule_1_faculty.pdf");
  assert.deepEqual(pdf.columns, ["Course", "Section", "Type", "Room / Lab", "Days", "Start", "End"]);
  assert.ok(texts.includes("Schedule 1 - Faculty Schedule"));
  assert.ok(texts.includes("All faculty members (4)"));
  assert.deepEqual(rowsOf(pdf, "Dr. Smith"), [
    ["CMSC 161", "02", "Lecture", "Roddy 140", "MWF", "8:00 AM", "8:50 AM"],
    ["CMSC 161", "01", "Lecture", "Roddy 140", "MWF", "9:00 AM", "9:50 AM"],
    ["CMSC 340", "02", "Lecture", "Roddy 147", "MF", "2:00 PM", "2:50 PM"],
    ["CMSC 340", "02", "Lab", "Mac (Lab)", "T", "8:00 AM", "9:50 AM"],
  ]);
  assert.deepEqual(rowsOf(pdf, "Dr. Brown"), [
    ["CMSC 453", "01", "Lecture", "Roddy 147", "MW", "10:00 AM", "10:50 AM"],
    ["CMSC 110", "90", "Lecture", "Online", "T", "6:00 PM", "8:30 PM"],
    ["CMSC 453", "01", "Lab", "Annex 12 (Lab)", "Th", "4:00 PM", "5:50 PM"],
  ]);
});

test("a faculty meeting without a room says so and no room is invented", () => {
  const { pdf, texts } = draw({ view: view(1, "faculty"), groupBy: "faculty" });

  assert.deepEqual(rowsOf(pdf, "Dr. Jones"), [
    ["CMSC 101", "01", "Lecture", NO_RESOURCE, "MW", "10:00 AM", "11:15 AM"],
    ["CMSC 162", "01", "Lecture", "Roddy 140", "TTh", "11:00 AM", "12:15 PM"],
    ["CMSC 162", "01", "Lab", "Linux (Lab)", "W", "1:00 PM", "2:50 PM"],
  ]);
  assert.equal(NO_RESOURCE, "No physical resource assigned");
  assert.ok(texts.join(" ").includes("No physical resource"));
});

test("a specific faculty member: only that person is in the PDF", () => {
  const { pdf, texts } = draw({
    view: view(1, "faculty"),
    groupBy: "faculty",
    scope: "one",
    resourceKey: "faculty:Dr. Jones",
  });

  assert.deepEqual(pdf.sections.map((section) => section.heading), ["Dr. Jones"]);
  assert.equal(pdf.filename, "schedule_1_faculty_dr_jones.pdf");
  assert.ok(texts.includes("Faculty member: Dr. Jones"));
  assert.ok(!texts.some((text) => text.includes("Dr. Smith") || text.includes("Dr. Brown")));
  assert.ok(texts.includes("CMSC 162") && !texts.includes("CMSC 161"));
});

// ------------------------------------------------------------------ which schedule

test("the selected schedule is the one exported", () => {
  const first = draw({ view: view(1, "faculty"), groupBy: "faculty" });
  const second = draw({ view: view(2, "faculty"), groupBy: "faculty" });

  assert.equal(second.pdf.filename, "schedule_2_faculty.pdf");
  assert.ok(second.texts.includes("Schedule 2 of 3"));
  assert.ok(second.texts.includes("Schedule 2 - Faculty Schedule"));
  assert.deepEqual(second.pdf.sections.map((section) => section.name), ["Dr. Jones", "Dr. Smith"]);
  // In schedule 2, CMSC 161.01 is Dr. Jones's, in Roddy 147 on Tuesday and Thursday.
  assert.deepEqual(rowsOf(second.pdf, "Dr. Jones"), [
    ["CMSC 161", "01", "Lecture", "Roddy 147", "TTh", "9:30 AM", "10:45 AM"],
  ]);
  assert.notDeepEqual(rowsOf(first.pdf, "Dr. Jones"), rowsOf(second.pdf, "Dr. Jones"));
  assert.ok(!second.texts.includes("CMSC 453"));
});

test("the options for a specific resource come from the selected schedule only", () => {
  assert.deepEqual(
    resourceOptions(view(2, "room"), "room").map((option) => option.value),
    ["room:Roddy 140", "room:Roddy 147", "lab:Mac"],
  );
  assert.deepEqual(
    resourceOptions(view(2, "faculty"), "faculty"),
    [
      { value: "faculty:Dr. Jones", label: "Dr. Jones" },
      { value: "faculty:Dr. Smith", label: "Dr. Smith" },
    ],
  );
  assert.deepEqual(exportableGroups(view(3, "room"), "room"), []);
});

// ------------------------------------------------------------------ validation and empty cases

test("a missing room, lab, or faculty selection is reported in plain words", () => {
  expectError(() => buildSchedulePdf({ view: view(1, "room"), groupBy: "room", scope: "one" }), "missing_selection");
  assert.throws(
    () => buildSchedulePdf({ view: view(1, "room"), groupBy: "room", scope: "one", resourceKey: "" }),
    { message: "Choose a room or lab to export." },
  );
  assert.throws(
    () => buildSchedulePdf({ view: view(1, "faculty"), groupBy: "faculty", scope: "one" }),
    { message: "Choose a faculty member to export." },
  );
});

test("a resource that is not in the schedule is refused", () => {
  expectError(
    () => buildSchedulePdf({ view: view(2, "room"), groupBy: "room", scope: "one", resourceKey: "lab:Linux" }),
    "unknown_resource",
  );
  // "Online" is a group in the view, but it is not a room or a lab.
  expectError(
    () => buildSchedulePdf({ view: view(1, "room"), groupBy: "room", scope: "one", resourceKey: "online:Online" }),
    "unknown_resource",
  );
});

test("no schedules, a wrong grouping, and a wrong paper size are refused", () => {
  assert.throws(() => buildSchedulePdf({ view: null, groupBy: "room" }), {
    code: "no_schedules",
    message: NO_SCHEDULES_MESSAGE,
  });
  assert.equal(
    NO_SCHEDULES_MESSAGE,
    "No schedules are available to export. Generate or import a schedule first.",
  );
  expectError(() => buildSchedulePdf({ view: view(1, "room"), groupBy: "building" }), "invalid_grouping");
  expectError(() => buildSchedulePdf({ view: view(1, "room"), groupBy: "room", paper: "legal" }), "invalid_paper");
  expectError(() => buildSchedulePdf({ view: { ...view(1, "room"), number: 0 }, groupBy: "room" }), "invalid_schedule");
});

test("an empty schedule gets a clear message instead of a blank PDF", () => {
  const empty = { number: 4, count: 4, group: "faculty", totals: {}, groups: [] };
  assert.throws(() => buildSchedulePdf({ view: empty, groupBy: "faculty" }), {
    code: "empty",
    message: "Schedule 4 has no meetings, so there is nothing to export.",
  });
  // Schedule 3 is one online section: it has a faculty PDF but nothing by room or lab.
  assert.throws(() => buildSchedulePdf({ view: view(3, "room"), groupBy: "room" }), {
    code: "empty",
    message:
      "Schedule 3 has no meetings in a room or lab, so there is nothing to export by room and lab.",
  });
  assert.equal(buildSchedulePdf({ view: view(3, "faculty"), groupBy: "faculty" }).sections.length, 1);
});

test("malformed schedule data is refused with a message, not a crash", () => {
  const good = structuredClone(VIEWS[1].room);
  const cases = [
    "not a view",
    { ...good, groups: undefined },
    { ...good, groups: [null] },
    { ...good, groups: [{ kind: "room", meetings: [] }] },
    { ...good, groups: [{ name: "Roddy 140", kind: "room" }] },
    { ...good, groups: [{ name: "Roddy 140", kind: "room", meetings: [{ faculty: "Dr. Smith" }] }] },
    { ...good, groups: [{ name: "Roddy 140", kind: "room", meetings: ["CMSC 161"] }] },
    { ...good, group: "faculty" },
  ];
  for (const bad of cases) {
    expectError(() => buildSchedulePdf({ view: bad, groupBy: "room" }), "malformed");
  }
});

test("missing optional values are shown clearly", () => {
  const view1 = structuredClone(VIEWS[1].room);
  const room = view1.groups.find((group) => group.name === "Annex 12" && group.kind === "room");
  room.meetings = [
    { course: "CMSC 499", course_id: "CMSC 499", section: "", faculty: null, room: "Annex 12", kind: "lecture" },
  ];
  const { pdf, texts } = draw({ view: view1, groupBy: "room", scope: "one", resourceKey: "room:Annex 12" });

  assert.deepEqual(rowsOf(pdf, "Annex 12"), [["CMSC 499", "-", "Lecture", "Not assigned", "TBA", "TBA", "TBA"]]);
  assert.ok(texts.includes("Not assigned") && texts.includes("TBA"));
  assert.ok(pdf.notes.some((note) => note.startsWith("TBA:")));
});

// ------------------------------------------------------------------ layout

test("US Letter is the default paper and A4 is available", () => {
  const letter = drawSchedulePdf(buildSchedulePdf({ view: view(1, "room"), groupBy: "room" }));
  const a4 = drawSchedulePdf(buildSchedulePdf({ view: view(1, "room"), groupBy: "room", paper: "a4" }));

  assert.deepEqual(
    [letter.internal.pageSize.getWidth(), letter.internal.pageSize.getHeight()],
    [612, 792],
  );
  assert.equal(Math.round(a4.internal.pageSize.getWidth()), 595);
  assert.equal(Math.round(a4.internal.pageSize.getHeight()), 842);
});

test("a long faculty name wraps inside its column instead of being cut off", () => {
  for (const paper of ["letter", "a4"]) {
    const pdf = buildSchedulePdf({
      view: view(1, "room"),
      groupBy: "room",
      scope: "one",
      resourceKey: "room:Annex 12",
      paper,
    });
    const doc = drawSchedulePdf(pdf, { now: NOW });
    const items = readPages(doc).flat();
    const texts = items.map((item) => item.text);

    // The name is too long for one line of its column, so it is split over several...
    assert.ok(!texts.includes(LONG_NAME));
    const first = texts.findIndex((text) => LONG_NAME.startsWith(text) && text.length > 3);
    assert.ok(first > 0, "the start of the name is in the PDF");
    let rest = LONG_NAME;
    let lines = 0;
    for (const { text } of items.slice(first)) {
      if (!rest.startsWith(text)) break;
      rest = rest.slice(text.length).trimStart();
      lines += 1;
    }
    // ...and every part of it is there.
    assert.equal(rest, "", `the whole name is printed on ${paper}`);
    assert.ok(lines >= 2, "the name wraps");

    // Nothing is drawn outside the margins.
    const pageWidth = doc.internal.pageSize.getWidth();
    for (const item of items) {
      assert.ok(item.x >= 54 - 0.01, `"${item.text}" starts left of the margin`);
      assert.ok(
        item.x + doc.getTextWidth(item.text) <= pageWidth - 54 + 0.5,
        `"${item.text}" runs past the right margin on ${paper}`,
      );
    }
  }
});

test("a long faculty name wraps in its own heading too", () => {
  const { texts } = draw({
    view: view(1, "faculty"),
    groupBy: "faculty",
    scope: "one",
    resourceKey: `faculty:${LONG_NAME}`,
  });
  assert.ok(texts.join(" ").includes(LONG_NAME));
});

/** A schedule with `rooms` rooms of `rows` single meetings each, built from real meetings. */
function bigView(rooms, rows) {
  const sample = VIEWS[1].room.groups.find((group) => group.name === "Roddy 140").meetings[0];
  return {
    number: 1,
    count: 1,
    group: "room",
    totals: {},
    groups: Array.from({ length: rooms }, (_, r) => ({
      name: `Hall ${String(r + 1).padStart(2, "0")}`,
      kind: "room",
      sections: rows,
      meeting_count: rows,
      meetings: Array.from({ length: rows }, (_, i) => ({
        ...sample,
        course: `CMSC ${100 + i}.01`,
        course_id: `CMSC ${100 + i}`,
        section: "01",
        day_number: (i % 5) + 1,
        start: 480 + i * 5,
        end: 530 + i * 5,
      })),
    })),
  };
}

test("a long schedule runs over several pages and stays readable", () => {
  const { pdf, pages } = draw({ view: bigView(3, 70), groupBy: "room" });
  const texts = pages.map((page) => page.map((item) => item.text));

  assert.ok(pages.length >= 5, `expected several pages, got ${pages.length}`);
  // Every row is printed exactly once.
  const printed = texts.flat().filter((text) => /^CMSC \d+$/.test(text));
  assert.equal(printed.length, 3 * 70);
  assert.equal(pdf.sections.reduce((total, section) => total + section.rows.length, 0), 210);

  texts.forEach((page, index) => {
    // Page numbers and the schedule's name are on every page.
    assert.ok(page.includes(`Page ${index + 1} of ${pages.length}`), `page ${index + 1} is numbered`);
    assert.ok(page.includes("Schedule 1 · Room / Lab"));
    // Column headings are repeated wherever a table continues.
    const tables = page.filter((text) => text === "Course").length;
    const rows = page.filter((text) => /^CMSC \d+$/.test(text)).length;
    assert.ok(tables >= 1 && rows >= 1, `page ${index + 1} has a table with headings`);
    // A row is never split: each one has its course, start, and end on the same page.
    assert.equal(page.filter((text) => /^\d+:\d\d [AP]M$/.test(text)).length, rows * 2);
  });
  // A table that continues says which room it belongs to.
  assert.ok(texts[1].includes("ROOM: Hall 01 (continued)"));
  assert.ok(!texts[0].includes("ROOM: Hall 01 (continued)"));
  // Rows keep their order across pages.
  const firstRoom = texts.flat().filter((text) => /^CMSC \d+$/.test(text)).slice(0, 70);
  const days = pdf.sections[0].rows.map((row) => row.days);
  assert.deepEqual(days.slice(0, 14), Array(14).fill("M"));
  assert.equal(firstRoom[0], "CMSC 100");
  assert.equal(firstRoom[1], "CMSC 105");
});

test("a section heading is never left alone at the bottom of a page", () => {
  for (const rows of [18, 19, 20, 21, 22, 23, 24, 25]) {
    const { pages } = draw({ view: bigView(4, rows), groupBy: "room" });
    for (const page of pages) {
      const texts = page.map((item) => item.text);
      texts.forEach((text, index) => {
        if (!/^ROOM: Hall \d+$/.test(text)) return;
        const after = texts.slice(index + 1).filter((value) => /^CMSC \d+$/.test(value));
        assert.ok(after.length >= 2, `${text} has rows under it on the same page (${rows} rows)`);
      });
    }
  }
});

test("the PDF is black on white with gray rules, with no navigation or buttons in it", () => {
  const doc = drawSchedulePdf(buildSchedulePdf({ view: view(1, "room"), groupBy: "room" }), { now: NOW });
  const source = doc.output();
  const texts = readPages(doc).flat().map((item) => item.text);

  // Only gray levels ("g"/"G") are used; there is no RGB color ("rg"/"RG") anywhere.
  assert.ok(!/\d (rg|RG)\n/.test(source), "no color operators");
  assert.match(source, /\n0\.?\d* g\n/);
  for (const word of ["Load JSON", "Export PDF", "Clear results", "Timetable", "Configuration"]) {
    assert.ok(!texts.some((text) => text.includes(word)), `${word} is not in the PDF`);
  }
  assert.match(source, /\/BaseFont \/Helvetica-Bold/);
});

test("characters the PDF font lacks are written in a plain form", () => {
  assert.equal(pdfText("Café – Room “A”…"), 'Café - Room "A"...');
  assert.equal(pdfText("Nguyễn"), "Nguyen");
  assert.equal(pdfText("张伟"), "??");
  assert.equal(pdfText(null), "");
});

// ------------------------------------------------------------------ read-only

test("building and drawing a PDF never changes the schedule data", () => {
  for (const group of ["room", "faculty"]) {
    const original = structuredClone(VIEWS[1][group]);
    const frozen = view(1, group); // deep-frozen: any write would throw
    const pdf = buildSchedulePdf({ view: frozen, groupBy: group });
    createSchedulePdfFile(pdf, { now: NOW });
    assert.deepEqual(frozen, original);
  }
});

test("the same choices always give the same document", () => {
  const options = { view: view(1, "room"), groupBy: "room" };
  assert.deepEqual(buildSchedulePdf(options), buildSchedulePdf(options));
  const a = drawSchedulePdf(buildSchedulePdf(options), { now: NOW });
  const b = drawSchedulePdf(buildSchedulePdf(options), { now: NOW });
  assert.deepEqual(readPages(a), readPages(b));
});

// ------------------------------------------------------------------ saving

test("exporting saves a real PDF under the descriptive name", async () => {
  const saved = [];
  const result = await exportSchedulePdf(
    { view: view(1, "faculty"), groupBy: "faculty", scope: "one", resourceKey: "faculty:Dr. Smith" },
    {
      save: async (file) => {
        saved.push(file);
        return { name: file.suggestedName, method: "download" };
      },
    },
  );

  assert.deepEqual(result, { name: "schedule_1_faculty_dr_smith.pdf", method: "download" });
  assert.equal(saved.length, 1);
  assert.equal(saved[0].type, "application/pdf");
  const bytes = Buffer.from(saved[0].content);
  assert.equal(bytes.subarray(0, 5).toString("latin1"), "%PDF-");
  assert.ok(bytes.includes("%%EOF"));
  assert.ok(bytes.includes("(Dr. Smith) Tj"));
  assert.ok(bytes.length > 3000);
});

test("cancelling the Save As dialog is not an error", async () => {
  const result = await exportSchedulePdf(
    { view: view(1, "room"), groupBy: "room" },
    { save: async () => null },
  );
  assert.equal(result, null);
});

test("a failure while making or saving the PDF is reported and leaves the schedule alone", async () => {
  const frozen = view(1, "room");
  const original = structuredClone(VIEWS[1].room);
  let saves = 0;
  const save = async () => {
    saves += 1;
  };

  // Drawing fails: nothing is saved.
  await assert.rejects(
    exportSchedulePdf({ view: frozen, groupBy: "room" }, {
      save,
      draw: () => {
        throw new Error("out of memory");
      },
    }),
    { message: "out of memory" },
  );
  assert.equal(saves, 0);
  // Saving fails (the browser refuses the download or the disk is full).
  await assert.rejects(
    exportSchedulePdf({ view: frozen, groupBy: "room" }, {
      save: async () => {
        throw new DOMException("The request is not allowed", "NotAllowedError");
      },
    }),
    { name: "NotAllowedError" },
  );
  // Incomplete choices fail before anything is drawn or saved.
  await assert.rejects(
    exportSchedulePdf({ view: frozen, groupBy: "room", scope: "one" }, { save }),
    { code: "missing_selection" },
  );
  assert.equal(saves, 0);
  assert.deepEqual(frozen, original);
  assert.equal(
    FAILED_MESSAGE,
    "PDF export failed. Your existing schedule has not been changed. Please try again.",
  );
});

// ------------------------------------------------------------------ JSON and CSV still save

/** Run `action` with just enough of a browser for saveFile()'s download path. */
async function withFakeBrowser(action) {
  const downloads = [];
  const blobs = [];
  const saved = { window: globalThis.window, document: globalThis.document, createObjectURL: URL.createObjectURL };
  globalThis.window = {};
  globalThis.document = {
    createElement: () => ({ click() { downloads.push({ name: this.download, href: this.href }); }, remove() {} }),
    body: { append() {} },
  };
  URL.createObjectURL = (blob) => {
    blobs.push(blob);
    return `blob:test/${blobs.length}`;
  };
  try {
    await action();
  } finally {
    globalThis.window = saved.window;
    globalThis.document = saved.document;
    URL.createObjectURL = saved.createObjectURL;
  }
  return { downloads, blobs };
}

test("JSON and CSV files are still saved as UTF-8 text, and a PDF as bytes", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] }); // saveFile() releases its URL after 10 s
  const json = JSON.stringify([[{ course: "CMSC 161.01", faculty: "Zoë" }]]);
  const csv = "CMSC 161.01,Zoë,Roddy 140,None,MON 09:00-09:50\n";
  const pdf = createSchedulePdfFile(buildSchedulePdf({ view: view(1, "room"), groupBy: "room" }));
  const results = [];

  const { downloads, blobs } = await withFakeBrowser(async () => {
    results.push(await saveFile({ suggestedName: "schedules.json", content: json }));
    results.push(await saveFile({ suggestedName: "schedules.csv", content: csv, type: "text/csv" }));
    results.push(await saveFile({ suggestedName: pdf.filename, content: pdf.content, type: "application/pdf" }));
  });

  assert.deepEqual(results, [
    { name: "schedules.json", method: "download" },
    { name: "schedules.csv", method: "download" },
    { name: "schedule_1_room_lab.pdf", method: "download" },
  ]);
  assert.deepEqual(downloads.map((download) => download.name), [
    "schedules.json",
    "schedules.csv",
    "schedule_1_room_lab.pdf",
  ]);
  assert.deepEqual(blobs.map((blob) => blob.type), [
    "application/json;charset=utf-8",
    "text/csv;charset=utf-8",
    "application/pdf",
  ]);
  assert.equal(await blobs[0].text(), json);
  assert.equal(await blobs[1].text(), csv);
  assert.deepEqual(new Uint8Array(await blobs[2].arrayBuffer()), new Uint8Array(pdf.content));
});

test("the Save As dialog is offered PDF as the file type where the browser has one", async () => {
  const asked = [];
  const written = [];
  const saved = globalThis.window;
  globalThis.window = {
    showSaveFilePicker: async (options) => {
      asked.push(options);
      return {
        name: "my schedule.pdf",
        createWritable: async () => ({ write: async (blob) => written.push(blob), close: async () => {} }),
      };
    },
  };
  try {
    const result = await exportSchedulePdf({ view: view(1, "room"), groupBy: "room" });
    assert.deepEqual(result, { name: "my schedule.pdf", method: "picker" });
  } finally {
    globalThis.window = saved;
  }
  assert.equal(asked[0].suggestedName, "schedule_1_room_lab.pdf");
  assert.deepEqual(asked[0].types, [{ description: "PDF document", accept: { "application/pdf": [".pdf"] } }]);
  assert.equal(written[0].type, "application/pdf");
  assert.equal(Buffer.from(await written[0].arrayBuffer()).subarray(0, 5).toString("latin1"), "%PDF-");
});
