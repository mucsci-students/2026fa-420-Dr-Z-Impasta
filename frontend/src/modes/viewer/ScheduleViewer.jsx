/**
 * Schedule Viewer (mode 03).
 *
 * Shows the session's schedules (generated or imported) grouped by room & lab or by
 * faculty, as a weekly timetable or a table. Load JSON, Export and Clear go through
 * the server (api.schedules in src/api/client.js); the schedules are read with
 * useSchedules.js and shaped for display in scheduleData.js.
 */
import { useMemo, useRef, useState } from "react";
import { Link } from "react-router";

import { api } from "../../api/client.js";
import Badge from "../../components/Badge.jsx";
import Card from "../../components/Card.jsx";
import EmptyState from "../../components/EmptyState.jsx";
import ErrorMessage from "../../components/ErrorMessage.jsx";
import PageHeader from "../../components/PageHeader.jsx";
import { Lasagna } from "../../components/PastaMarks.jsx";
import Spinner from "../../components/Spinner.jsx";
import { plural } from "../../format.js";
import { useAppState } from "../../state/appStateContext.js";
import { useToast } from "../../state/toastContext.js";

import { exportSchedules } from "./exportSchedule.js";
import { describeSchedulePath, toGroups } from "./scheduleData.js";
import ScheduleTable from "./ScheduleTable.jsx";
import Timetable from "./Timetable.jsx";
import { useSchedules } from "./useSchedules.js";
import "./viewer.css";

const BADGE_TONES = {
  Room: "neutral",
  Lab: "success",
  Faculty: "info",
  Online: "neutral",
  Unassigned: "warning",
};

const GROUP_OPTIONS = [
  { value: "room", label: "Room & lab" },
  { value: "faculty", label: "Faculty" },
];

const VIEW_OPTIONS = [
  { value: "timetable", label: "Timetable" },
  { value: "table", label: "Table" },
];

/* Temporary: a quick Generate button on the empty page, only in `npm run dev`,
   so the viewer can be tested before the Schedule Generator page is finished. */
const QUICK_GENERATE = import.meta.env.DEV;
const QUICK_GENERATE_LIMIT = 5;

/** Render labeled options and report the selected value through onChange. */
function Segmented({ label, value, options, onChange }) {
  return (
    <div className="segmented">
      <span className="segmented__label">{label}</span>
      <div className="segmented__options" role="group" aria-label={label}>
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            className={`segmented__option${
              option.value === value ? " segmented__option--active" : ""
            }`}
            aria-pressed={option.value === value}
            onClick={() => onChange(option.value)}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}

/** Display session schedules with grouping, navigation, import, export, and clearing. */
export default function ScheduleViewer() {
  const { state, loading } = useAppState();
  const notify = useToast();

  // --- All hooks first, before any early return (Rules of Hooks). ---
  const [scheduleIndex, setScheduleIndex] = useState(0);
  const [groupBy, setGroupBy] = useState("room");
  const [view, setView] = useState("timetable");
  const [selectedKey, setSelectedKey] = useState(null);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState(null);
  const fileInputRef = useRef(null);

  // Keep the selected schedule within the number the server has.
  const available = state?.schedules?.count ?? 0;
  const index = Math.min(scheduleIndex, Math.max(available - 1, 0));

  // Refetch whenever the polled state says the schedules or the generation changed.
  const refreshKey = JSON.stringify([state?.schedules ?? null, state?.generation?.state ?? null]);
  const {
    loading: schedulesLoading,
    view: scheduleView,
    error: loadError,
    reload,
  } = useSchedules({ number: index + 1, group: groupBy, refreshKey });

  const scheduleCount = scheduleView?.count ?? 0;
  const groups = useMemo(() => toGroups(scheduleView), [scheduleView]);
  const currentGroup = groups.find((group) => group.key === selectedKey) ?? groups[0] ?? null;

  // --- Server actions ---
  /** Run a server action with busy/error state and reload schedules on success. */
  async function run(action) {
    setBusy(true);
    setActionError(null);
    try {
      await action();
      reload();
    } catch (error) {
      setActionError(error);
    } finally {
      setBusy(false);
    }
  }

  /** Import the selected JSON file and reset schedule and group selection on success. */
  function handleLoadJson(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    run(async () => {
      await api.schedules.importFile({ filename: file.name, content: await file.text() });
      setScheduleIndex(0);
      setSelectedKey(null);
    });
  }

  /** Open the hidden JSON file input when it is mounted. */
  const openFilePicker = () => fileInputRef.current?.click();
  const fileInput = (
    <input
      ref={fileInputRef}
      type="file"
      accept=".json,application/json"
      hidden
      onChange={handleLoadJson}
    />
  );
  // The server's message plus every problem it found, each with where it is in the file.
  const shownError = actionError
    ? {
        message: actionError.message,
        issues: actionError.issues?.map((issue) => ({
          ...issue,
          field: issue.area ? issue.field : describeSchedulePath(issue.path),
        })),
      }
    : loadError && { message: loadError };
  const errorMessage = (
    <ErrorMessage
      error={shownError}
      onDismiss={actionError ? () => setActionError(null) : undefined}
    />
  );

  // --- Early returns ---
  if (loading || schedulesLoading) {
    return (
      <>
        <PageHeader title="Schedules" />
        <Spinner label="Loading schedules" />
      </>
    );
  }

  // Loading failed: say so and offer a retry instead of claiming there are no schedules.
  if (loadError) {
    return (
      <>
        <PageHeader title="Schedules" />
        {errorMessage}
        <EmptyState
          title="Couldn't load the schedules"
          mark={<Lasagna size={40} />}
          actions={
            <button className="btn btn--primary" type="button" onClick={reload}>
              Retry
            </button>
          }
        >
          Nothing was deleted. The schedules couldn't be read from the server, so try again.
        </EmptyState>
      </>
    );
  }

  if (!scheduleCount) {
    const generating = state?.generation?.state === "running";
    const canGenerate = QUICK_GENERATE && state?.config?.status === "valid";

    return (
      <>
        <PageHeader title="Schedules" />
        {errorMessage}
        <EmptyState
                    title={generating ? "Generating schedules…" : "No schedules yet"}
                    mark={<Lasagna size={40} />}
          actions={
            <>
              {fileInput}
              <Link className="btn btn--primary" to="/generator">
                Go to the Schedule Generator
              </Link>
              <button className="btn" type="button" onClick={openFilePicker} disabled={busy}>
                Load JSON…
              </button>
              {canGenerate && (
                <button
                  className="btn"
                  type="button"
                  disabled={busy || generating}
                  onClick={() => run(() => api.generation.start({ limit: QUICK_GENERATE_LIMIT }))}
                >
                  Quick generate ({QUICK_GENERATE_LIMIT}) · dev
                </button>
              )}
            </>
          }
        >
          {generating
            ? state.generation.message || "The schedules appear here as soon as the run finishes."
            : "Generate schedules from a valid configuration, or load a schedule JSON file exported earlier. They appear here to browse by room and lab or by faculty."}
        </EmptyState>
      </>
    );
  }

  // --- Handlers ---
  /** Select a zero-based schedule index, wrapping at either end of the list. */
  function goToSchedule(nextIndex) {
    setScheduleIndex((nextIndex + scheduleCount) % scheduleCount);
  }

  /** Change the grouping mode and reset the selected resource or faculty card. */
  function changeGroupBy(value) {
    setGroupBy(value);
    setSelectedKey(null);
  }

  /** Export the current schedule or all schedules in the selected JSON or CSV format. */
  function handleExport(event) {
    const [which, format] = event.target.value.split(":");
    if (!format) return;
    run(async () => {
      const saved = await exportSchedules({ which: which === "all" ? "all" : index + 1, format });
      if (!saved) return; // The user cancelled the Save As dialog.
      notify({
        title: "Exported.",
        message:
          saved.method === "picker"
            ? `Saved ${saved.name}.`
            : `${saved.name} is in your browser's downloads folder.`,
      });
    });
  }

  /** Confirm clearing all session schedules, then reset selection on success. */
  function clearResults() {
    if (!window.confirm("Clear all generated and loaded schedules?")) return;
    run(async () => {
      await api.schedules.clear();
      setScheduleIndex(0);
      setSelectedKey(null);
    });
  }

  return (
    <>
      <PageHeader title="Schedules" subtitle={plural(scheduleCount, "schedule")} />
      {errorMessage}

      <Card
        className="schedule-viewer"
        actions={
          <div className="schedule-viewer__actions">
            {fileInput}
            <button className="btn" type="button" onClick={openFilePicker} disabled={busy}>
              Load JSON…
            </button>
            <select
              className="btn"
              value=""
              onChange={handleExport}
              disabled={busy}
              aria-label="Export schedules"
            >
              <option value="" disabled>
                Export…
              </option>
              <option value="current:json">This schedule · JSON</option>
              <option value="current:csv">This schedule · CSV</option>
              <option value="all:json">All schedules · JSON</option>
              <option value="all:csv">All schedules · CSV</option>
            </select>
            <button className="btn btn--danger" type="button" onClick={clearResults} disabled={busy}>
              Clear results…
            </button>
          </div>
        }
      >
        <div className="schedule-toolbar">
          <div className="schedule-picker">
            <button
              className="btn"
              type="button"
              onClick={() => goToSchedule(index - 1)}
              aria-label="Previous schedule"
            >
              ‹
            </button>
            <select
              className="btn"
              value={index}
              onChange={(event) => setScheduleIndex(Number(event.target.value))}
              aria-label="Schedule"
            >
              {Array.from({ length: scheduleCount }, (_, i) => (
                <option key={i} value={i}>
                  Schedule {i + 1}
                </option>
              ))}
            </select>
            <span className="muted">of {scheduleCount}</span>
            <button
              className="btn"
              type="button"
              onClick={() => goToSchedule(index + 1)}
              aria-label="Next schedule"
            >
              ›
            </button>
          </div>

          <Segmented
            label="Group by"
            value={groupBy}
            options={GROUP_OPTIONS}
            onChange={changeGroupBy}
          />
          <Segmented label="Show as" value={view} options={VIEW_OPTIONS} onChange={setView} />

          <span className="schedule-toolbar__summary muted">
            {plural(scheduleView.totals.sections, "section")} ·{" "}
            {groupBy === "faculty"
              ? plural(groups.length, "faculty member")
              : plural(groups.length, "room & lab", "rooms & labs")}
          </span>
        </div>

        <div className="resource-cards">
          {groups.map((group) => (
            <button
              key={group.key}
              type="button"
              className={`resource-card${
                group.key === currentGroup?.key ? " resource-card--selected" : ""
              }`}
              aria-pressed={group.key === currentGroup?.key}
              onClick={() => setSelectedKey(group.key)}
            >
              <span className="resource-card__top">
                <strong className="resource-card__name">{group.name}</strong>
                <Badge tone={BADGE_TONES[group.type]}>{group.type}</Badge>
              </span>
              <span className="resource-card__meta">
                {plural(group.sectionCount, "section")} · {plural(group.events.length, "meeting")}
              </span>
            </button>
          ))}
        </div>

        {currentGroup ? (
          <section className="schedule-result">
            <div className="schedule-result__header">
              <h2>
                {currentGroup.name}{" "}
                <span className="muted">
                  {plural(currentGroup.sectionCount, "section")} ·{" "}
                  {plural(currentGroup.events.length, "meeting")}
                </span>
              </h2>
              <div className="legend">
                <span className="legend__item">
                  <span className="legend__swatch" /> Lecture
                </span>
                <span className="legend__item">
                  <span className="legend__swatch legend__swatch--lab" /> Lab meeting
                </span>
              </div>
            </div>

            {view === "timetable" ? (
              <Timetable events={currentGroup.events} groupBy={groupBy} />
            ) : (
              <ScheduleTable events={currentGroup.events} />
            )}
          </section>
        ) : (
          <p className="muted">This schedule has no meetings to show.</p>
        )}
      </Card>
    </>
  );
}
