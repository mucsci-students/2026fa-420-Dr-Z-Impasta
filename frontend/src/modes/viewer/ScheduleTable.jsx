/**
 * Table view: every meeting in the selected group, sorted by day and time.
 */
import { compareEvents, formatMinutes } from "./scheduleData.js";

export default function ScheduleTable({ events }) {
  const rows = [...events].sort(compareEvents);

  return (
    <div className="schedule-table-wrapper">
      <table className="schedule-table">
        <thead>
          <tr>
            <th>Course</th>
            <th>Section</th>
            <th>Type</th>
            <th>Faculty</th>
            <th>Room / lab</th>
            <th>Day</th>
            <th>Time</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((event) => (
            <tr key={event.id}>
              <td className="mono">{event.courseId}</td>
              <td className="mono">{event.sectionId || "—"}</td>
              <td>{event.isOnline ? "Online" : event.isLab ? "Lab" : "Lecture"}</td>
              <td>{event.faculty || "—"}</td>
              <td>{event.place || "—"}</td>
              <td>{event.day ?? "—"}</td>
              <td className="mono">
                {formatMinutes(event.start)}–{formatMinutes(event.end)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}