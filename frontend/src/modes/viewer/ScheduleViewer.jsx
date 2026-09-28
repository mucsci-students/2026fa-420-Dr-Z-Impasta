/**
 * Schedule Viewer (mode 03).
 *
 * The foundation provides the page frame, the "no schedules yet" state, and the summary
 * line. The Schedule Viewer feature adds schedule navigation, the Room & lab / Faculty
 * grouping (SegmentedControl), timetable and table views, Load JSON…, Export (JSON and
 * CSV, one or all), and Clear. Start from docs/gui.md; the calls are `api.schedules` in
 * src/api/client.js, and each view comes ready-grouped from GET /api/schedules/{n}.
 */
import { Link } from "react-router";
import EmptyState from "../../components/EmptyState.jsx";
import PageHeader from "../../components/PageHeader.jsx";
import Spinner from "../../components/Spinner.jsx";
import { clockTime, plural } from "../../format.js";
import { useAppState } from "../../state/appStateContext.js";

export default function ScheduleViewer() {
  const { state, loading } = useAppState();

  if (loading) {
    return (
      <>
        <PageHeader title="Schedules" />
        <Spinner label="Loading" />
      </>
    );
  }

  const schedules = state?.schedules;
  if (!schedules?.count) {
    return (
      <>
        <PageHeader title="Schedules" />
        <EmptyState
          title="No schedules yet"
          actions={
            <Link className="btn btn--primary" to="/generator">
              Go to the Schedule Generator
            </Link>
          }
        >
          Generate schedules from a valid configuration, or load a schedule JSON file exported
          earlier. They appear here to browse by room and lab or by faculty.
        </EmptyState>
      </>
    );
  }

  const origin = schedules.source === "generated" ? "generated" : "loaded";
  return (
    <PageHeader
      title="Schedules"
      subtitle={
        <>
          {plural(schedules.count, "schedule")} · {origin} {clockTime(schedules.created_at)}
          {schedules.name && (
            <>
              {" "}
              from <span className="mono">{schedules.name}</span>
            </>
          )}
        </>
      }
    />
  );
}
