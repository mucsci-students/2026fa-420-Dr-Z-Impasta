/**
 * The dialog for adding or editing a faculty member, opened from FacultyCard or "Add faculty".
 * It's an edit dialog like CourseDialog. In "When they can teach", a day with no hours means
 * they can't teach that day.
 */

import Field from "../../../components/Field.jsx";
import { formIssues, issuesFor } from "../../../components/issues.js";
import AvailabilityEditor from "../AvailabilityEditor.jsx";
import CheckboxList from "../CheckboxList.jsx";
import PreferenceEditor from "../PreferenceEditor.jsx";
import EditDialog from "./EditDialog.jsx";
import { useDraft } from "./useDraft.js";

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
  const { draft, set, isDirty } = useDraft(original);
  const weekdays = options?.weekdays?.length ? options.weekdays : WEEKDAYS;
  const { errorFor, errorClass, unplaced } = formIssues(error?.issues, {
    area: "faculty",
    index: index ?? undefined,
    fields: [
      "name", "minimum_credits", "maximum_credits", "unique_course_limit", "maximum_days",
      "mandatory_days", "times", "course_preferences", "room_preferences", "lab_preferences",
    ],
  });

  return (
    <EditDialog
      width="600px"
      title={isNew ? "Add faculty member" : `Edit ${original.name}`}
      what="this faculty member"
      isDirty={isDirty}
      error={error}
      unplaced={unplaced}
      busy={busy}
      saveLabel={isNew ? "Add faculty member" : "Save"}
      onSave={() => onSave?.(draft)}
      onCancel={onCancel}
      onDelete={isNew ? undefined : onDelete}
    >
      <Field label="Name" required error={errorFor("name")}>
        <input className={errorClass("name")} value={draft.name} onChange={(e) => set("name", e.target.value)} data-autofocus />
      </Field>

      <div className="form-grid">
        <Field label="Minimum credits" required error={errorFor("minimum_credits")}>
          <input
            className={errorClass("minimum_credits")}
            type="number"
            min={0}
            value={draft.minimum_credits ?? ""}
            onChange={(e) => set("minimum_credits", toNumber(e.target.value))}
          />
        </Field>
        <Field label="Maximum credits" required error={errorFor("maximum_credits")}>
          <input
            className={errorClass("maximum_credits")}
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
            className={errorClass("unique_course_limit")}
            type="number"
            min={1}
            value={draft.unique_course_limit ?? ""}
            onChange={(e) => set("unique_course_limit", toNumber(e.target.value))}
          />
        </Field>
        <Field label="Teaching days" help="The most days a week they teach, 0 to 5." error={errorFor("maximum_days")}>
          <input
            className={errorClass("maximum_days")}
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
    </EditDialog>
  );
}
