/**
 * The dialog for adding or editing a class pattern, opened from PatternCard or "Add pattern".
 * It's an edit dialog like CourseDialog. The Enabled switch is the inverse of `disabled`.
 * Rules such as "one lab meeting per pattern" are checked by the library on Save, not here.
 */

import { useState } from "react";
import Button from "../../../components/Button.jsx";
import Field from "../../../components/Field.jsx";
import { formIssues } from "../../../components/issues.js";
import { DELIVERY_NAMES } from "../labels.js";
import EditDialog from "./EditDialog.jsx";
import { useDraft } from "./useDraft.js";

const NEW_MEETING = { day: "MON", start_time: null, duration: 50, lab: false, delivery: "in_person" };
const NEW_PATTERN = { credits: null, meetings: [NEW_MEETING], disabled: false, start_time: null };
const WEEKDAYS = ["MON", "TUE", "WED", "THU", "FRI"];

const toNumber = (text) => (text === "" ? null : Number(text));
const toTime = (text) => (text === "" ? null : text);   // an empty time box means "not set"

// Row keys for meetings, so removing a row doesn't hand its state to the next one
let nextMeetingKey = 0;
const newMeetingKeys = (count) => Array.from({ length: count }, () => nextMeetingKey++);

/**
 * Add or edit a class pattern and its meetings. Edits a draft; nothing changes until Save succeeds.
 * `options` is the reply from api.config.options(); fallbacks are used until it arrives.
 */
export default function PatternDialog({ index, pattern, options, busy, error, onSave, onCancel, onDelete }) {
  const isNew = index === null;
  const original = pattern ?? NEW_PATTERN;
  const { draft, set, isDirty } = useDraft(original);

  // One key per row of draft.meetings, in the same order
  const [meetingKeys, setMeetingKeys] = useState(() => newMeetingKeys(original.meetings.length));
  // The row keys when Save was last pressed; the server's `meetings.N` errors refer to these positions
  const [savedKeys, setSavedKeys] = useState(meetingKeys);

  const weekdays = options?.weekdays?.length ? options.weekdays : WEEKDAYS;
  const deliveryModes = options?.delivery_modes?.length ? options.delivery_modes : Object.keys(DELIVERY_NAMES);

  function save() {
    setSavedKeys(meetingKeys);
    onSave?.(draft);
  }

  /** Change one field of meeting number i. */
  function setMeeting(i, field, value) {
    set("meetings", draft.meetings.map((m, j) => (j === i ? { ...m, [field]: value } : m)));
  }

  /** Add a meeting on the first weekday the pattern doesn't use yet. */
  function addMeeting() {
    const used = new Set(draft.meetings.map((m) => m.day));
    const day = weekdays.find((d) => !used.has(d)) ?? weekdays[0];
    const [key] = newMeetingKeys(1);
    set("meetings", [...draft.meetings, { ...NEW_MEETING, day }]);
    setMeetingKeys((keys) => [...keys, key]);
  }

  function removeMeeting(i) {
    set("meetings", draft.meetings.filter((_, j) => j !== i));
    setMeetingKeys((keys) => keys.filter((_, j) => j !== i));
  }

  const { errorFor, errorClass, unplaced } = formIssues(error?.issues, {
    area: "patterns",
    index: index ?? undefined,
    fields: ["credits", "start_time", "disabled", "meetings"],
  });

  /**
   * The field the server's errors use for the meeting row with this key ("meetings.2"), from
   * where the row was at the last Save, or null if it was added since.
   */
  function meetingField(key) {
    const position = savedKeys.indexOf(key);
    return position === -1 ? null : `meetings.${position}`;
  }

  return (
    <EditDialog
      width="640px"
      title={isNew ? "Add class pattern" : `Edit ${original.credits}-credit pattern`}
      what="this pattern"
      isDirty={isDirty}
      error={error}
      unplaced={unplaced}
      busy={busy}
      saveLabel={isNew ? "Add pattern" : "Save"}
      onSave={save}
      onCancel={onCancel}
      onDelete={isNew ? undefined : onDelete}
    >
      <div className="form-grid">
        <Field label="Credits" required error={errorFor("credits")}>
          <input className={errorClass("credits")} type="number" min={1} value={draft.credits ?? ""}
            onChange={(e) => set("credits", toNumber(e.target.value))} data-autofocus />
        </Field>
        {/* The button sits beside the Field, not inside it: Field gives its one child the label's id */}
        <div className="time-field">
          <Field label="Start time" help="Optional. Meetings without their own start time begin here." error={errorFor("start_time")}>
            <input className={errorClass("start_time")} type="time" value={draft.start_time ?? ""}
              onChange={(e) => set("start_time", toTime(e.target.value))} />
          </Field>
          {/* Browsers give a time box no reliable way to empty it, so this sets it back to "any" */}
          {draft.start_time && (
            <Button size="sm" variant="ghost" onClick={() => set("start_time", null)}>
              Any time
            </Button>
          )}
        </div>
      </div>

      <label className="toggle">
        <input type="checkbox" role="switch" checked={!draft.disabled}
          onChange={(e) => set("disabled", !e.target.checked)} />
        <span>{draft.disabled ? "Disabled: the scheduler won't use it" : "Enabled"}</span>
      </label>

      <fieldset className="meetings-editor">
        <legend>Meetings</legend>
        <div className="meetings-editor__head" aria-hidden="true">
          <span>Day</span><span>Minutes</span><span>Lab</span><span>Delivery</span><span>Own start</span><span />
        </div>
        {draft.meetings.map((m, i) => {
          const rowField = meetingField(meetingKeys[i]);
          const rowError = rowField && errorFor(rowField);
          return (
            <div key={meetingKeys[i]} className="meetings-editor__row">
              <select aria-label={`Meeting ${i + 1} day`} value={m.day}
                onChange={(e) => setMeeting(i, "day", e.target.value)}>
                {weekdays.map((d) => <option key={d} value={d}>{d}</option>)}
              </select>
              <input className={errorClass("duration")} type="number" min={1} aria-label={`Meeting ${i + 1} minutes`} value={m.duration ?? ""}
                onChange={(e) => setMeeting(i, "duration", toNumber(e.target.value))} />
              <input type="checkbox" aria-label={`Meeting ${i + 1} is the lab`} checked={m.lab}
                onChange={(e) => setMeeting(i, "lab", e.target.checked)} />
              <select aria-label={`Meeting ${i + 1} delivery`} value={m.delivery}
                onChange={(e) => setMeeting(i, "delivery", e.target.value)}>
                {deliveryModes.map((d) => (
                  <option key={d} value={d}>
                    {DELIVERY_NAMES[d] ?? d}
                  </option>
                ))}
              </select>
              <input type="time" aria-label={`Meeting ${i + 1} start time`} value={m.start_time ?? ""}
                onChange={(e) => setMeeting(i, "start_time", toTime(e.target.value))} />
              {/* One cell for both buttons, so the × sits right after the time box and moves
                  over when "Any" appears */}
              <div className="meetings-editor__end">
                {/* Clears the meeting's own start time, like "Any time" above */}
                {m.start_time && (
                  <Button size="sm" variant="ghost" aria-label={`Any start time for meeting ${i + 1}`}
                    onClick={() => setMeeting(i, "start_time", null)}>
                    Any
                  </Button>
                )}
                <button type="button" className="meetings-editor__remove" aria-label={`Remove meeting ${i + 1}`}
                  onClick={() => removeMeeting(i)}>
                  ×
                </button>
              </div>
              {rowError && <p className="field__error meetings-editor__error">{rowError}</p>}
            </div>
          );
        })}
        <Button size="sm" variant="ghost" onClick={addMeeting}>
          + Add meeting
        </Button>
        {errorFor("meetings", true) && <p className="field__error">{errorFor("meetings", true)}</p>}
      </fieldset>
    </EditDialog>
  );
}
