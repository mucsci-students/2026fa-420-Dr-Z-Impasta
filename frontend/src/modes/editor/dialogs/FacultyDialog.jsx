// Description:
// |     Field           |       Control	    |              Notes
// | name	             | text, required	    |
// | minimum_credits	 | number, required	    |
// | maximum_credits	 | number, required	    |
// | unique_course_limit | number, required	    |
// | maximum_days	     | number (min=0 max=5) | Optional; defaults to 5
// | times	             | AvailabilityEditor	| Required. An empty day means unavailable
// | mandatory_days	     | Mo–Fr checkboxes	    |
// | course_preferences	 | PreferenceEditor	    | Pick from the course IDs in the document, plus an 
// |                     |                      | integer score
// | room_preferences	 | PreferenceEditor	    | Pick from room names
// | lab_preferences	 | PreferenceEditor	    | Pick from lab names

import { useState } from "react";
import Button from "../../../components/Button.jsx";
import ConfirmDialog from "../../../components/ConfirmDialog.jsx";
import Dialog from "../../../components/Dialog.jsx";
import ErrorMessage from "../../../components/ErrorMessage.jsx";
import Field from "../../../components/Field.jsx";
import UnsavedChangesPrompt from "../../../components/UnsavedChangesPrompt.jsx";
import { issuesFor } from "../../../components/issues.js";
import AvailabilityEditor from "../AvailabilityEditor.jsx";
import CheckboxList from "../CheckboxList.jsx";
import PreferenceEditor from "../PreferenceEditor.jsx";
//import { InvalidField }  from "../../../state/EventHandlers.jsx"; 

const WEEKDAYS = ["MON", "TUE", "WED", "THU", "FRI"];

const NEW_FACULTY = {
  name: "",
  maximum_credits: null,
  maximum_days: 5,
  minimum_credits: null,
  unique_course_limit: null,
  times: { MON: [], TUE: [], WED: [], THU: [], FRI: [] },
  course_preferences: {},
  room_preferences: {},
  lab_preferences: {},
  mandatory_days: [],
};

/** Text from a number box → a number, or null when empty. */
const toNumber = (text) => (text === "" ? null : Number(text));

/**
 * Add or edit a faculty member. Edits a draft; nothing changes until Save succeeds.
 * `courseIds`, `rooms`, and `labs` are the names their preferences can use. A new faculty
 * member starts with no hours; a day with no hours means they can't teach that day.
 */
export default function FacultyDialog({
  index,
  faculty,
  courseIds = [],
  rooms = [],
  labs = [],
  options,
  busy,
  error,
  onSave,
  onCancel,
  onDelete
}) {
  const isNew = index === null;
  const original = { ...NEW_FACULTY, ...faculty }; // fill defaults the document may omit
  const [draft, setDraft] = useState(original);
  const isDirty = JSON.stringify(draft) !== JSON.stringify(original);
  const [confirmingDiscard, setConfirmingDiscard] = useState(false);
  const weekdays = options?.weekdays?.length ? options.weekdays : WEEKDAYS;
  // Problems that have no field in this dialog to appear under; the banner lists them instead
  const FIELDS = [ "name", "minimum_credits", "maximum_credits", "unique_course_limit", "maximum_days", "mandatory_days", "times", "course_preferences", "room_preferences", "lab_preferences" ];
  const unplaced = (error?.issues ?? []).filter((issue) =>
    issue.area !== "faculty" ||
    (index !== null && issue.index !== index) ||
    !FIELDS.some((f) => issue.field === f || issue.field?.startsWith(`${f}.`)),
  );

  /** Cancel, Escape, or ×: ask first if there are unsaved edits. */
  function requestClose() {
    if (isDirty) setConfirmingDiscard(true);
    else onCancel?.();
  }

  /** Change one field of the draft. */
  function set(field, value) {
    setDraft((d) => ({ ...d, [field]: value }));
  }

  /** The library's message for one field, if the last Save was rejected. */
  function errorFor(field) {
    const found = issuesFor(error?.issues, { area: "faculty", index: index ?? undefined, field });
    return found.length > 0 ? found.map((issue) => issue.message).join(" ") : undefined;
  }
  /** A function to assign the input field the 'input-error' class if it contains invalid data */
  function classNameFunc(field) {
    if ((error?.issues ?? []).some((issue) => issue.field === field)) {
      return "input-error";
    } else {
      return "";
    }
  }

  // The prompts are siblings of the Dialog, not children; see ResourceDialog.
  return (
    <>
      <Dialog
        open
        width="600px"
        title={isNew ? "Add faculty member" : `Edit ${original.name}`}
        onClose={requestClose}
        actions={
          <>
            {!isNew && (
              <Button variant="danger" onClick={onDelete} disabled={busy}>
                Delete
              </Button>
            )}
            <Button onClick={requestClose} disabled={busy}>
              Cancel
            </Button>
            <Button variant="primary" busy={busy} onClick={() => onSave?.(draft)}>
              {isNew ? "Add faculty member" : "Save"}
            </Button>
          </>
        }
      >
        <ErrorMessage error={error && { message: "The change was not applied.", issues: unplaced }} title="Not saved." />

        <Field label="Name" required error={errorFor("name")}>
          <input className={classNameFunc("name")} value={draft.name} onChange={(e) => set("name", e.target.value)} data-autofocus />
        </Field>

        <div className="form-grid">
          <Field label="Minimum credits" required error={errorFor("minimum_credits")}>
            <input
              className={classNameFunc("minimum_credits")}
              type="number"
              min={0}
              value={draft.minimum_credits ?? ""}
              onChange={(e) => set("minimum_credits", toNumber(e.target.value))}
            />
          </Field>
          <Field label="Maximum credits" required error={errorFor("maximum_credits")}>
            <input
              className={classNameFunc("maximum_credits")}
              type="number"
              min={0}
              value={draft.maximum_credits ?? ""}
              onChange={(e) => set("maximum_credits", toNumber(e.target.value))}
            />
          </Field>
          <Field
            label="Different courses"
            required
            help="The most different courses they can teach."
            error={errorFor("unique_course_limit")}
          >
            <input
              className={classNameFunc("unique_course_limit")}
              type="number"
              min={1}
              value={draft.unique_course_limit ?? ""}
              onChange={(e) => set("unique_course_limit", toNumber(e.target.value))}
            />
          </Field>
          <Field label="Teaching days" help="The most days a week they teach, 0 to 5." error={errorFor("maximum_days")}>
            <input
              className={classNameFunc("maximum_days")}
              type="number"
              min={0}
              max={5}
              value={draft.maximum_days ?? ""}
              onChange={(e) => set("maximum_days", toNumber(e.target.value))}
            />
          </Field>
        </div>
        <CheckboxList
          legend="Must teach on"
          options={weekdays}
          value={draft.mandatory_days}
          onChange={(days) => set("mandatory_days", days)}
          error={errorFor("mandatory_days")}
        />

        <AvailabilityEditor
          legend="When they can teach"
          value={draft.times}
          onChange={(times) => set("times", times)}
          days={weekdays}
          issues={issuesFor(error?.issues, { area: "faculty", index: index ?? undefined, field: "times" })}
        />

        <PreferenceEditor
          legend="Course preferences"
          options={courseIds}
          value={draft.course_preferences}
          onChange={(prefs) => set("course_preferences", prefs)}
          addLabel="+ Add course"
          error={errorFor("course_preferences")}
        />
        <PreferenceEditor
          legend="Room preferences"
          options={rooms}
          value={draft.room_preferences}
          onChange={(prefs) => set("room_preferences", prefs)}
          addLabel="+ Add room"
          error={errorFor("room_preferences")}
        />
        <PreferenceEditor
          legend="Lab preferences"
          options={labs}
          value={draft.lab_preferences}
          onChange={(prefs) => set("lab_preferences", prefs)}
          addLabel="+ Add lab"
          error={errorFor("lab_preferences")}
        />
      </Dialog>
      <UnsavedChangesPrompt when={isDirty} />
      <ConfirmDialog
        open={confirmingDiscard}
        title="Discard changes?"
        destructive
        confirmLabel="Discard"
        cancelLabel="Keep editing"
        onConfirm={onCancel}
        onCancel={() => setConfirmingDiscard(false)}
      >
        <p>Your changes to this faculty member haven't been saved.</p>
      </ConfirmDialog>
    </>
  );
}
