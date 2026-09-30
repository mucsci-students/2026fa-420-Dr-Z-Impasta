/**
 * Client-side exports for the Schedule Viewer.
 *
 * If src/api/client.js has export calls for schedules, prefer those so the
 * files match what the CLI writes; these are the fallback.
 */
import { buildEvents, compareEvents, formatMinutes } from "./scheduleData.js";

function downloadFile(fileName, text, type) {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function csvCell(value) {
  return `"${String(value ?? "").replaceAll('"', '""')}"`;
}

/** JSONWriter format: always a list of schedules, so the file loads back. */
export function exportScheduleJson(schedule, number) {
  downloadFile(
    `schedule-${number}.json`,
    JSON.stringify([schedule], null, 2),
    "application/json",
  );
}

/** Exports the whole schedule (every room, lab and faculty), not only the selected card. */
export function exportScheduleCsv(schedule, number) {
  const header = ["Course", "Section", "Type", "Faculty", "Room/Lab", "Day", "Start", "End"];
  const rows = buildEvents(schedule)
    .sort(compareEvents)
    .map((event) => [
      event.courseId,
      event.sectionId,
      event.isOnline ? "Online" : event.isLab ? "Lab" : "Lecture",
      event.faculty,
      event.place,
      event.day,
      formatMinutes(event.start),
      formatMinutes(event.end),
    ]);

  const csv = [header, ...rows].map((row) => row.map(csvCell).join(",")).join("\n");
  downloadFile(`schedule-${number}.csv`, csv, "text/csv;charset=utf-8");
}