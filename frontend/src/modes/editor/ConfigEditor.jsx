/**
 * Configuration Editor (mode 01): the page where users build the scheduler's input.
 *
 * Clicking a card sets `editing`, which opens that item's dialog. Saving calls a handler
 * in src/state/eventHandlers.js, then refresh(); the revision goes up and the full
 * configuration (`doc`) is fetched again. This component never edits `doc` itself; the
 * server is the only source of truth.
 *
 * New here? Read docs/gui.md first. The API calls are in src/api/client.js (`api.config`).
 */
import EmptyState from "../../components/EmptyState.jsx";
import IssueList from "../../components/IssueList.jsx";
import PageHeader from "../../components/PageHeader.jsx";
import { Penne } from "../../components/PastaMarks.jsx";
import Spinner from "../../components/Spinner.jsx";
import { clockTime, configStatus, describeCounts, plural } from "../../format.js";
import { useAppState } from "../../state/appStateContext.js";
import { useEffect, useState, useRef } from "react";
import { api } from "../../api/client.js";
import Button from "../../components/Button.jsx";
import Banner from "../../components/Banner.jsx";
import CardRow from "./cards/CardRow.jsx";
import ResourceCard from "./cards/ResourceCard.jsx";
import CourseCard from "./cards/CourseCard.jsx";
import FacultyCard from "./cards/FacultyCard.jsx";
import PatternCard from "./cards/PatternCard.jsx";
import TimeSlotsCard from "./cards/TimeSlotsCard.jsx";
import SettingsCard from "./cards/SettingsCard.jsx";
import ResourceDialog from "./dialogs/ResourceDialog.jsx";
import CourseDialog from "./dialogs/CourseDialog.jsx";
import PatternDialog from "./dialogs/PatternDialog.jsx";
import FacultyDialog from "./dialogs/FacultyDialog.jsx";
import DeleteDialog from "./dialogs/DeleteDialog.jsx";
import DayBlocksDialog from "./dialogs/DayBlocksDialog.jsx";
import TimeSlotsDialog from "./dialogs/TimeSlotsDialog.jsx";
import ConfirmDialog from "../../components/ConfirmDialog.jsx";

import ErrorMessage from "../../components/ErrorMessage.jsx";
import { Load, ConfirmLoad, Empty_Click, ValidateConfig, SaveConfig, ValidateAndSaveItem, DeleteItem, UpdateTimeSlots, UpdateSettings, TogglePatternDisabled, getHistoryLength, getCurrHistoryLength, redoAction, undoAction, pushToHist } from "../../state/eventHandlers";

export default function ConfigEditor() {
  const { state, loading, refresh } = useAppState();
  const config = state?.config;                   // summary only; the full document is `doc`
  const [doc, setDoc] = useState(null);           // { document, sections }: the full configuration and each course's section label
  const revision = config?.revision;              // goes up on every server-side change
  const hasConfig = Boolean(config) && config.status !== "none";
  const fileInputRef = useRef(null);              // the hidden <input type="file"> that the Load JSON… buttons click
  const [loadingFile, setLoadingFile] = useState(false);   // true while New or Load JSON… is in progress
  const [editing, setEditing] = useState(null);   // the item being edited, e.g. { area: "courses", index: 2 }; index null means "add new"
  const [options, setOptions] = useState(null);   // library choices for the dialogs; they have fallbacks
  const [deleting, setDeleting] = useState(null);  // the item being deleted, e.g. { area: "rooms", index: 0 }
  const [impact, setImpact] = useState(null);      // its delete preview, from api.config.deleteImpact
  const [error, setError] = useState(null);       // a page-level error (failed New, Load, Save, …), shown above the banner
  const [localError, setLocalError] = useState(null);   // the error from a failed edit, e.g. { message, issues: [{ area, index, field, message }] }
  const [pendingLoad, setPendingLoad] = useState(null);   // a load waiting for "discard changes?"
  const [settingsError, setSettingsError] = useState(null);   // shown inside SettingsCard, which has no dialog
  const [undoReloading, setUndoReloading] = useState(false);   // true while Undo is in progress
  const [redoReloading, setRedoReloading] = useState(false);   // true while Redo is in progress

  // Fetch the full document when a configuration first exists and after every change.
  useEffect(() => {
    if (!hasConfig) return;
    api.config
      .get()
      .then((reply) => setDoc({ document: reply.document, sections: reply.sections }))
      .catch((error) => setError({ error, title: "Couldn't load the configuration", onDismiss: () => setError(null) }));
  }, [hasConfig, revision]);

  // Fetch the dialogs' choices (weekdays, optimizer flags, …) once.
  useEffect(() => {
    api.config.options().then(setOptions).catch(() => { });   // the dialogs' fallbacks cover a failure
  }, []);

  // When a delete starts, fetch its preview (this changes nothing on the server).
  useEffect(() => {
    if (!deleting) return undefined;
    let current = true;   // ignore a reply that arrives after this delete was closed
    api.config
      .deleteImpact(deleting.area, deleting.index)
      .then((reply) => current && setImpact({ ...deleting, reply }))
      .catch((error) => current && setImpact({ ...deleting, error }));
    return () => {
      current = false;
    };
  }, [deleting]);
  // Only show a preview that belongs to the item being deleted now.
  const shownImpact =
    impact && deleting && impact.area === deleting.area && impact.index === deleting.index ? impact : null;

  // --- Actions ---
  // Every button and dialog calls one of these, so they can be compared side by side. They
  // keep each action's existing undo and refresh timing, which differs between actions:
  // - Item and time-slot saves record an undo step before saving and always refresh.
  //   Delete records one only after it succeeds. The pattern switch and Global Settings
  //   aren't recorded, so an Undo after them also reverts them along with the previous edit.
  // - Load, the pattern switch, Global Settings, Delete, and Confirm Load refresh only if
  //   the change went through; the others always refresh. New on the empty page doesn't
  //   refresh at all: the next poll shows the editor.

  /** New: start from the empty starter configuration. */
  const handleNew = async ({ refreshAfter }) => {
    await Empty_Click(setLoadingFile, setError, setPendingLoad);
    if (refreshAfter) await refresh();
  };

  /** Load JSON…: the hidden file input's onChange. */
  const handleLoadJson = async (event) => {
    if (await Load(event, setLoadingFile, setError, setPendingLoad)) await refresh();
  };

  /** "Discard and load" in the unsaved-changes prompt. */
  const handleConfirmLoad = async () => {
    if (await ConfirmLoad(pendingLoad, setPendingLoad, setLoadingFile, setError)) await refresh();
  };

  const handleSave = async () => {
    await SaveConfig(setError);
    await refresh();
  };

  const handleValidate = async () => {
    await ValidateConfig(setError);
    await refresh();
  };

  /** Undo or Redo (`action`), with that button's "reloading" flag set while it runs. */
  const runHistory = async (action, setReloading) => {
    setReloading(true);
    await action(doc.document, config.name, setError, setPendingLoad);
    await refresh();
    setReloading(false);
  };
  const handleUndo = () => runHistory(undoAction, setUndoReloading);
  const handleRedo = () => runHistory(redoAction, setRedoReloading);

  /** A pattern card's On/Off switch. */
  const handleTogglePattern = async (index, pattern) => {
    if (await TogglePatternDisabled(index, pattern, setError)) await refresh();
  };

  /** A change in the Global Settings card. */
  const handleApplySettings = async (values) => {
    if (await UpdateSettings(values, setSettingsError)) await refresh();
  };

  /** A dialog's Save: record an undo step, send the edit (`save`), then refresh. */
  const saveWithUndo = async (save) => {
    pushToHist(doc.document);
    await save();
    await refresh();
  };

  /** Save in an item dialog (faculty, course, room, lab, pattern): add or replace the item. */
  const handleSaveItem = (draft) =>
    saveWithUndo(() => ValidateAndSaveItem(editing, draft, setEditing, setLocalError));

  /** Save in a time-slot dialog: one day's blocks (`{ times }`) or the timing options. */
  const handleSaveTimeSlots = (values) =>
    saveWithUndo(() => UpdateTimeSlots(values, setEditing, setLocalError));

  /** Cancel in any edit dialog. */
  const handleCloseDialog = () => {
    setLocalError(null);
    setEditing(null);
  };

  /** Delete in an item dialog: open the delete preview for the item being edited. */
  const handleStartDelete = () => {
    setLocalError(null);
    setDeleting(editing);
  };

  /** Cancel in the delete dialog: back to the edit dialog. */
  const handleCancelDelete = () => {
    setLocalError(null);
    setDeleting(null);
  };

  const handleConfirmDelete = async () => {
    const force = shownImpact?.reply?.can_delete === false;   // the user saw the warning
    if (await DeleteItem(deleting, setDeleting, setEditing, setLocalError, force)) {
      pushToHist(doc.document);
      await refresh();
    }
  };

  if (loading || loadingFile) {
    return (
      <>
        <PageHeader title="Configuration" />
        <Spinner label="Loading the configuration" />
      </>
    );
  }

  if (!config || config.status === "none") {
    return (
      <>
        <PageHeader title="Configuration" subtitle="Start a new configuration or load one from a JSON file." />
        <ErrorMessage error={error?.error} title={error?.title} onDismiss={error?.onDismiss} />
        <EmptyState
          title="No configuration loaded"
          mark={<Penne size={40} />}
          actions={
            <>
              <Button variant="primary" onClick={() => handleNew({ refreshAfter: false })}>New</Button>
              <Button onClick={() => { fileInputRef.current.click(); }}>Load JSON...</Button>
              <input
                ref={fileInputRef}
                type="file"
                style={{ display: "none" }}
                onChange={handleLoadJson} />
            </>
          }
        >
          Create an empty configuration to add rooms, labs, courses, and faculty, or load an
          existing JSON file. Files are validated before anything is replaced. The Schedule
          Generator and Viewer need a valid configuration or loaded schedules.
        </EmptyState>
      </>
    );
  }

  const status = configStatus(config);
  const canSave = config.status === "valid";   // the server only exports a valid configuration
  // Valid, but the server's quick checks found something that rules out every schedule
  // (e.g. a disabled class pattern someone needs). The messages name the items themselves.
  const warnings = (config.warnings ?? []).map(({ path, code, message }) => ({ path, code, message }));
  const bannerTone =
    warnings.length > 0 && status.tone === "success" ? "warning" : status.tone === "neutral" ? "info" : status.tone;
  const items = doc?.document.config;                     // rooms, labs, courses, faculty
  const timeSlots = doc?.document.time_slot_config;        // time blocks, timing options
  const patterns = timeSlots?.classes;                     // class patterns
  const weekdays = options?.weekdays?.length ? options.weekdays : ["MON", "TUE", "WED", "THU", "FRI"];
  const enabled = patterns?.filter((p) => !p.disabled).length;
  const settings = doc && { limit: doc.document.limit, optimizer_flags: doc.document.optimizer_flags };

  // The editor. Every card's onEdit sets `editing`; the dialogs at the bottom open from it.
  return (
    <div className="editor">
      <PageHeader
        title="Configuration"
        subtitle={
          <>
            Editing <span className="mono">{config.name ?? "an unsaved configuration"}</span>
            {config.validated_at && <> · last validated {clockTime(config.validated_at)}</>}
          </>
        }
        actions={
          <>
            <Button onClick={() => handleNew({ refreshAfter: true })}>New</Button>

            <Button onClick={() => fileInputRef.current.click()}>Load JSON...</Button>
            <input
              ref={fileInputRef}
              type="file"
              style={{ display: "none" }}
              onChange={handleLoadJson}
            />


            <Button
              disabled={!canSave}
              className={canSave ? "" : "disabled-btn"}
              aria-describedby={canSave ? undefined : "save-hint"}
              onClick={handleSave}
            >
              Save JSON...
            </Button>
            <Button variant="primary" onClick={handleValidate}>Validate</Button>

		<div className="undo-redo-row">
			<Button 
		className={undoReloading ? "reloading" : (getHistoryLength() > 1 ? "" : "disabled-btn")}
		disabled={getHistoryLength() <= 1}
		onClick={handleUndo}
		>
		Undo
		</Button>

			<Button 
		className={redoReloading ? "reloading" : (getCurrHistoryLength() > 1 ? "" : "disabled-btn")} 
		disabled={getCurrHistoryLength() <= 1}
		onClick={handleRedo}
		>
		Redo
		</Button>
		</div>
          </>

        }

      />
      <ErrorMessage error={error?.error} title={error?.title} onDismiss={error?.onDismiss} />
      <Banner tone={bannerTone} title={status.label}>
        {describeCounts(config.counts)}.
        {!canSave && (
          <>
            <p id="save-hint">Fix these before saving the configuration:</p>
            <IssueList issues={config.issues} />
          </>
        )}
        {warnings.length > 0 && (
          <>
            <p>No schedule can be generated until these are fixed:</p>
            <IssueList issues={warnings} />
          </>
        )}
      </Banner>
      {!doc ? (
        !error && <Spinner label="Loading the configuration" />   // a failed fetch is shown above instead
      ) : (
        <>
          <CardRow
            title="Faculty"
            meta={items.faculty.length}
            addLabel="Add faculty"
            onAdd={() => { setEditing({ area: "faculty", index: null }); }}
          >
            {items.faculty.map((f, i) => (

              <FacultyCard
                key={i}
                faculty={f}
                onEdit={() => setEditing({ area: "faculty", index: i })}
              />
            ))}
          </CardRow>
          <CardRow
            title="Courses"
            meta={plural(items.courses.length, "section")}
            addLabel="Add course"
            onAdd={() => { setEditing({ area: "courses", index: null }); }}
          >
            {items.courses.map((c, i) => (
              <CourseCard
                key={i}
                course={c}
                label={doc.sections[i]}

                onEdit={() => setEditing({ area: "courses", index: i })}

              />
            ))}
          </CardRow>
          <CardRow
            title="Rooms"
            meta={items.rooms.length}
            addLabel="Add room"
            onAdd={() => setEditing({ area: "rooms", index: null })}
          >
            {items.rooms.map((r, i) => (
              <ResourceCard
                key={i}
                resource={r}
                usedBy={items.courses.filter((c) => c.room.includes(r.name)).length}
                onEdit={() => setEditing({ area: "rooms", index: i })}
              />
            ))}
          </CardRow>
          <CardRow
            title="Labs"
            meta={items.labs.length}
            addLabel="Add lab"
            onAdd={() => setEditing({ area: "labs", index: null })}
          >
            {items.labs.map((l, i) => (
              <ResourceCard
                key={i}
                resource={l}
                usedBy={items.courses.filter((c) => c.lab.includes(l.name)).length}
                onEdit={() => setEditing({ area: "labs", index: i })}
              />
            ))}
          </CardRow>
          <CardRow
            title="Class Patterns"
            meta={`${enabled} of ${patterns.length} enabled`}
            addLabel="Add pattern"
            onAdd={() => { setEditing({ area: "patterns", index: null }); }}
          >
            {patterns.map((p, i) => (
              <PatternCard
                key={i}
                pattern={p}
                onEdit={() => setEditing({ area: "patterns", index: i })}
                onToggleDisabled={() => handleTogglePattern(i, p)}
              />
            ))}
          </CardRow>
          <div className="editor-pair">
            <TimeSlotsCard
              timeSlots={timeSlots}
              days={weekdays}
              onEditDay={(day) => setEditing({ area: "time_slots", day })}
              onEditTiming={() => setEditing({ area: "timing" })}
            />
            <SettingsCard
              settings={settings}
              optimizerFlagChoices={options?.optimizer_flags}
              error={settingsError}
              onApply={handleApplySettings}
            />
          </div>
          {/* Edit dialogs: at most one is open, picked by editing.area. They hide while a delete is open. */}
          {!deleting && editing?.area === "faculty" && (
            <FacultyDialog
              key={`faculty-${editing.index}`}
              index={editing.index}
              faculty={editing.index === null ? null : items.faculty[editing.index]}
              courseIds={[...new Set(items.courses.map((c) => c.course_id))]}
              rooms={items.rooms.map((r) => r.name)}
              labs={items.labs.map((l) => l.name)}
              options={options}
              onCancel={handleCloseDialog}
              onDelete={handleStartDelete}
              onSave={handleSaveItem}
              error={localError}
            />
          )}
          {!deleting && editing?.area === "courses" && (
            <CourseDialog
              key={`courses-${editing.index}`}
              index={editing.index}
              course={editing.index === null ? null : items.courses[editing.index]}
              label={editing.index === null ? null : doc.sections[editing.index]}
              rooms={items.rooms.map((r) => r.name)}
              labs={items.labs.map((l) => l.name)}
              faculty={items.faculty.map((f) => f.name)}
              courseIds={[...new Set(items.courses.map((c) => c.course_id))]}
              roomFeatures={[...new Set(items.rooms.flatMap((r) => r.features ?? []))]}
              labFeatures={[...new Set(items.labs.flatMap((l) => l.features ?? []))]}
              options={options}
              onCancel={handleCloseDialog}
              onDelete={handleStartDelete}
              onSave={handleSaveItem}
              error={localError}
            />
          )}
          {!deleting && (editing?.area === "rooms" || editing?.area === "labs") && (
            <ResourceDialog
              key={`${editing.area}-${editing.index}`}
              area={editing.area}
              index={editing.index}
              resource={editing.index === null ? null : items[editing.area][editing.index]}
              suggestions={[...new Set(items[editing.area].flatMap((r) => r.features ?? []))]}
              options={options}
              onCancel={handleCloseDialog}
              onDelete={handleStartDelete}
              onSave={handleSaveItem}
              error={localError}
            />
          )}
          {!deleting && editing?.area === "patterns" && (
            <PatternDialog
              key={`patterns-${editing.index}`}
              index={editing.index}
              pattern={editing.index === null ? null : patterns[editing.index]}
              options={options}
              onCancel={handleCloseDialog}
              onDelete={handleStartDelete}
              onSave={handleSaveItem}
              error={localError}
            />
          )}
          {editing?.area === "time_slots" && (
            <DayBlocksDialog
              key={`time_slots-${editing.day}`}
              day={editing.day}
              times={timeSlots.times}
              onCancel={handleCloseDialog}
              onSave={(times) => handleSaveTimeSlots({ times })}
              error={localError}
            />
          )}
          {editing?.area === "timing" && (
            <TimeSlotsDialog
              timeSlots={timeSlots}
              onCancel={handleCloseDialog}
              onSave={handleSaveTimeSlots}
              error={localError}
            />
          )}
          {deleting && (
            <DeleteDialog
              key={`delete-${deleting.area}-${deleting.index}`}
              impact={shownImpact?.reply ?? null}
              loadError={shownImpact?.error}
              error={localError}
              onCancel={handleCancelDelete}
              onConfirm={handleConfirmDelete}
            />
          )}
          {/* Shown when Load JSON… would overwrite unsaved changes. */}
          <ConfirmDialog
            open={pendingLoad !== null}
            title={`Discard changes and load ${pendingLoad?.filename}?`}
            destructive
            confirmLabel="Discard and load"
            cancelLabel="Keep my changes"
            onConfirm={handleConfirmLoad}
            onCancel={() => setPendingLoad(null)}
          >
            <p>These changes haven't been saved and will be lost:</p>
            <ul>
              {pendingLoad?.changes.map((change) => <li key={change.revision}>{change.summary}</li>)}
            </ul>
          </ConfirmDialog>
        </>
      )}
    </div>
  );
}
