/**
 * The "Export PDF" dialog of the Schedule Viewer.
 *
 * The user picks a schedule, how to group it (room and lab, or faculty), everything or one
 * room, lab, or faculty member, and the paper size; reviews what will be exported; then
 * saves a print-friendly PDF. It works on the schedules already in the session, generated
 * or imported. Nothing is regenerated and nothing is changed.
 *
 * This component only collects the choices. What goes in the PDF is decided in
 * schedulePdf.js, drawn in schedulePdfDocument.js, and saved through exportSchedulePdf.js.
 */
import { useId, useState } from "react";

import Banner from "../../components/Banner.jsx";
import Button from "../../components/Button.jsx";
import Dialog from "../../components/dialogs/Dialog.jsx";
import Field from "../../components/Field.jsx";
import { plural } from "../../format.js";
import { useAction } from "../../state/useAction.js";

import { exportSchedulePdf } from "./exportSchedulePdf.js";
import {
  DEFAULT_PAPER,
  FAILED_MESSAGE,
  GROUPINGS,
  NO_SCHEDULES_MESSAGE,
  PAPER_SIZES,
  PdfExportError,
  buildSchedulePdf,
  describeSchedulePdf,
  resourceOptions,
} from "./schedulePdf.js";
import { useSchedules } from "./useSchedules.js";

/** A group of radio buttons with a legend: `options` is `[{ value, label }]`. */
function Choice({ legend, options, value, onChange, disabled }) {
  const name = useId();
  return (
    <fieldset className="pdf-export__choice" disabled={disabled}>
      <legend>{legend}</legend>
      {options.map((option) => (
        <label key={option.value} className="pdf-export__option">
          <input
            type="radio"
            name={name}
            value={option.value}
            checked={option.value === value}
            onChange={() => onChange(option.value)}
          />
          {option.label}
        </label>
      ))}
    </fieldset>
  );
}

/** Build the PDF's description, or return the reason it can't be built. */
function preview(options) {
  try {
    return { pdf: buildSchedulePdf(options), problem: null };
  } catch (error) {
    if (error instanceof PdfExportError) return { pdf: null, problem: error };
    throw error;
  }
}

/** The options for the "specific" list, or none while the schedule can't be read. */
function optionsFor(view, groupBy) {
  try {
    return resourceOptions(view, groupBy);
  } catch {
    return [];
  }
}

/**
 * `scheduleCount` schedules are available; `initialNumber` (from 1) and `initialGroupBy`
 * are what the viewer is showing. `onExported({ name, method })` is called once the file
 * is saved; `onClose` closes the dialog. `refreshKey` reloads the schedule when the
 * session's schedules change while the dialog is open.
 */
export default function PdfExportDialog({
  scheduleCount,
  initialNumber,
  initialGroupBy = "room",
  refreshKey,
  onClose,
  onExported,
}) {
  const [chosenNumber, setChosenNumber] = useState(initialNumber);
  const [groupBy, setGroupBy] = useState(initialGroupBy);
  const [scope, setScope] = useState("all");
  const [resourceKey, setResourceKey] = useState("");
  const [paper, setPaper] = useState(DEFAULT_PAPER);
  const [attempted, setAttempted] = useState(false);
  const [failure, setFailure] = useState(null);

  // Schedules can be cleared or replaced while the dialog is open.
  const number = Math.min(chosenNumber, Math.max(scheduleCount, 1));
  const { view: loaded, error: loadError } = useSchedules({ number, group: groupBy, refreshKey });
  // The hook keeps the previous reply while the next one loads; only use a matching one.
  const view = loaded?.number === number && loaded?.group === groupBy ? loaded : null;
  const loading = scheduleCount > 0 && !view && !loadError;

  const wording = GROUPINGS[groupBy];
  const options = view ? optionsFor(view, groupBy) : [];
  const selectedKey = options.some((option) => option.value === resourceKey) ? resourceKey : "";
  const choices = { view, groupBy, scope, resourceKey: selectedKey, paper };
  const { pdf, problem } = view ? preview(choices) : { pdf: null, problem: null };
  const needsSelection = problem?.code === "missing_selection";
  const summary = pdf && describeSchedulePdf(pdf);

  const save = useAction(() => exportSchedulePdf(choices));

  /** Check the choices, then make and save the PDF. */
  async function handleExport() {
    setAttempted(true);
    setFailure(null);
    if (!pdf) return; // The reason is on screen: a field error or a banner.
    const result = await save.run();
    if (result.skipped) return;
    if (!result.ok) {
      console.error("PDF export failed", result.error);
      setFailure(result.error instanceof PdfExportError ? result.error.message : FAILED_MESSAGE);
      return;
    }
    if (result.value) onExported(result.value); // null: the Save As dialog was cancelled.
  }

  /** Forget an earlier failure once the choices change. */
  function change(setter) {
    return (value) => {
      setFailure(null);
      setter(value);
    };
  }

  const nativeSave = typeof window.showSaveFilePicker === "function";

  return (
    <Dialog
      open
      title="Export schedule as PDF"
      onClose={onClose}
      width="min(560px, calc(100vw - 32px))"
      actions={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button
            variant="primary"
            busy={save.busy}
            disabled={loading || scheduleCount === 0 || (!pdf && !needsSelection)}
            onClick={handleExport}
            data-autofocus
          >
            {save.busy ? "Exporting…" : "Export PDF"}
          </Button>
        </>
      }
    >
      {scheduleCount === 0 ? (
        <Banner tone="warning" title="Nothing to export.">
          {NO_SCHEDULES_MESSAGE}
        </Banner>
      ) : (
        <div className="pdf-export">
          <Field label="Schedule">
            <select
              value={number}
              disabled={save.busy}
              onChange={(event) => change(setChosenNumber)(Number(event.target.value))}
            >
              {Array.from({ length: scheduleCount }, (_, i) => (
                <option key={i + 1} value={i + 1}>
                  Schedule {i + 1}
                </option>
              ))}
            </select>
          </Field>

          <Choice
            legend="Group by"
            value={groupBy}
            disabled={save.busy}
            onChange={change((value) => {
              setGroupBy(value);
              setResourceKey("");
            })}
            options={Object.entries(GROUPINGS).map(([value, group]) => ({
              value,
              label: group.label,
            }))}
          />

          <Choice
            legend="Export scope"
            value={scope}
            disabled={save.busy}
            onChange={change(setScope)}
            options={[
              { value: "all", label: wording.all },
              { value: "one", label: wording.one },
            ]}
          />

          {scope === "one" && (
            <Field
              label={groupBy === "room" ? "Room or lab" : "Faculty member"}
              required
              error={attempted && needsSelection ? problem.message : undefined}
            >
              <select
                value={selectedKey}
                disabled={save.busy || loading}
                onChange={(event) => change(setResourceKey)(event.target.value)}
              >
                <option value="">{loading ? "Loading…" : "Choose…"}</option>
                {options.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </Field>
          )}

          <Choice
            legend="Paper"
            value={paper}
            disabled={save.busy}
            onChange={change(setPaper)}
            options={Object.entries(PAPER_SIZES).map(([value, size]) => ({
              value,
              label: size.label,
            }))}
          />

          {loadError && (
            <Banner tone="danger" title={`Couldn't read schedule ${number}.`}>
              {loadError} Your schedules have not been changed.
            </Banner>
          )}
          {problem && !needsSelection && (
            <Banner
              tone="warning"
              title={problem.code === "empty" ? "Nothing to export." : "Can't export this schedule."}
            >
              {problem.message}
            </Banner>
          )}

          {pdf && (
            <section className="pdf-export__review" aria-label="Review">
              <h3>Review</h3>
              <dl>
                {pdf.details.map(([label, value]) => (
                  <div key={label}>
                    <dt>{label}</dt>
                    <dd>{value}</dd>
                  </div>
                ))}
                <div>
                  <dt>Contents</dt>
                  <dd>
                    {plural(summary.sections, "table")}, {plural(summary.rows, "row")} ·{" "}
                    {summary.paper}, portrait
                  </dd>
                </div>
                <div>
                  <dt>File</dt>
                  <dd className="mono">{pdf.filename}</dd>
                </div>
              </dl>
              <p className="muted">
                {nativeSave
                  ? "Your browser will ask where to save the file, and asks before replacing an existing one."
                  : "The file goes to your browser's downloads folder. The browser chooses the location and never replaces an existing file."}
              </p>
            </section>
          )}

          {failure && (
            <Banner tone="danger" title="Couldn't export." onDismiss={() => setFailure(null)}>
              {failure}
            </Banner>
          )}
        </div>
      )}
    </Dialog>
  );
}
