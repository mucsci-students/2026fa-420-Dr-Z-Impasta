/**
 * The dialog for adding or editing a course section, opened from CourseCard or "Add course".
 * Every edit dialog works the same way: it changes a local `draft`, and Save sends the draft to the
 * server, which checks it and returns issues to show under each field (docs/gui.md, "Edit in a draft").
 * Faculty "Any" saves null: anyone whose course preferences include this course can teach it.
 */

import Field from "../../../components/Field.jsx";
import { formIssues } from "../../../components/issues.js";
import CheckboxList from "../CheckboxList.jsx";
import TagInput from "../TagInput.jsx";
import { MODALITY_NAMES } from "../labels.js";
import EditDialog from "./EditDialog.jsx";
import { useDraft } from "./useDraft.js";

const NEW_COURSE = {
  course_id: "",
  section_id: null,
  credits: null,
  capacity: null,
  room: [],
  lab: [],
  conflicts: [],
  faculty: null,
  modality: "in_person",
  required_room_features: [],
  required_lab_features: [],
  reserve_room_during_lab: true,
};

/** Text from a number box → a number, or null when empty. */
const toNumber = (text) => (text === "" ? null : Number(text));

/**
 * Add or edit a course section. Edits a draft; nothing changes until Save succeeds.
 * `rooms`, `labs`, `faculty`, and `courseIds` are the names to choose from; the
 * suggestion lists are the features existing rooms and labs already have. `options` is the
 * reply from api.config.options(); fallbacks are used until it arrives.
 */
export default function CourseDialog({
  index,
  course,
  label,
  rooms = [],
  labs = [],
  faculty = [],
  courseIds = [],
  roomFeatures = [],
  labFeatures = [],
  options,
  busy,
  error,
  onSave,
  onCancel,
  onDelete
}) {
  const isNew = index === null;
  const original = { ...NEW_COURSE, ...course };   // fill defaults the document may omit
  const { draft, set, isDirty } = useDraft(original);
  const modalities = options?.modalities?.length ? options.modalities : Object.keys(MODALITY_NAMES);
  const { errorFor, errorClass, unplaced } = formIssues(error?.issues, {
    area: "courses",
    index: index ?? undefined,
    fields: [
      "course_id", "section_id", "credits", "capacity", "modality", "room", "required_room_features",
      "lab", "required_lab_features", "reserve_room_during_lab", "faculty", "conflicts",
    ],
  });

  // A course can't conflict with itself; keep any saved IDs even if no course has them now.
  const conflictOptions = [...new Set([...courseIds, ...draft.conflicts])].filter((id) => id !== draft.course_id);

  return (
    <EditDialog
      title={isNew ? "Add course" : `Edit ${label ?? original.course_id}`}
      what="this course"
      isDirty={isDirty}
      error={error}
      unplaced={unplaced}
      busy={busy}
      saveLabel={isNew ? "Add course" : "Save"}
      onSave={() => onSave?.(draft)}
      onCancel={onCancel}
      onDelete={isNew ? undefined : onDelete}
    >
      <div className="form-grid">
        <Field label="Course ID" required help="Repeating an ID adds another section." error={errorFor("course_id")}>
          <input className={errorClass("course_id")} value={draft.course_id} onChange={(e) => set("course_id", e.target.value)} placeholder="CMSC 140" data-autofocus />
        </Field>
        <Field label="Section" help="Leave blank to number sections automatically (.01, .02…)." error={errorFor("section_id")}>
          <input className={errorClass("section_id")} value={draft.section_id ?? ""} onChange={(e) => set("section_id", e.target.value === "" ? null : e.target.value)} />
        </Field>
        <Field label="Credits" required error={errorFor("credits")}>
          <input className={errorClass("credits")} type="number" min={1} value={draft.credits ?? ""} onChange={(e) => set("credits", toNumber(e.target.value))} />
        </Field>
        <Field label="Capacity" required help="Most students the section can hold." error={errorFor("capacity")}>
          <input className={errorClass("capacity")} type="number" min={1} value={draft.capacity ?? ""} onChange={(e) => set("capacity", toNumber(e.target.value))} />
        </Field>
      </div>

      <Field label="Modality" error={errorFor("modality")}>
        <select value={draft.modality} onChange={(e) => set("modality", e.target.value)}>
          {modalities.map((m) => (
            <option key={m} value={m}>{MODALITY_NAMES[m] ?? m}</option>
          ))}
        </select>
      </Field>

      <CheckboxList legend="Rooms" options={rooms} value={draft.room} onChange={(v) => set("room", v)} empty="No rooms yet" error={errorFor("room")} fieldName="room" />
      <Field label="Required room features" help="Only rooms with every tag can hold this course." error={errorFor("required_room_features")}>
        <TagInput value={draft.required_room_features} onChange={(tags) => set("required_room_features", tags)} suggestions={roomFeatures} />
      </Field>

      <CheckboxList legend="Labs" className={errorClass("lab")} options={labs} value={draft.lab} onChange={(v) => set("lab", v)} empty="No labs yet" error={errorFor("lab")} fieldName="lab" />
      {draft.lab.length > 0 && (
        <>
          <Field label="Required lab features" help="Only labs with every tag can hold the lab meeting." error={errorFor("required_lab_features")}>
            <TagInput value={draft.required_lab_features} onChange={(tags) => set("required_lab_features", tags)} suggestions={labFeatures} />
          </Field>
          <label className="checkbox">
            <input type="checkbox" checked={draft.reserve_room_during_lab} onChange={(e) => set("reserve_room_during_lab", e.target.checked)} />
            Keep the room reserved during the lab
          </label>
        </>
      )}

      <fieldset className="checkbox-list">
        <legend>Faculty</legend>
        <label className="checkbox">
          <input type="radio" name="faculty-mode" checked={draft.faculty === null} onChange={() => set("faculty", null)} />
          Any (from faculty course preferences)
        </label>
        <label className={`checkbox ${errorClass("faculty")}`}>
          <input className={errorClass("faculty")} type="radio" name="faculty-mode" checked={draft.faculty !== null} onChange={() => set("faculty", original.faculty ?? [])} />
          Specific
        </label>
      </fieldset>
      {draft.faculty !== null && (
        <CheckboxList legend="Who can teach it" options={faculty} value={draft.faculty} onChange={(v) => set("faculty", v)} empty="No faculty yet" error={errorFor("faculty")} fieldName="faculty" />
      )}

      <CheckboxList legend="Conflicts" options={conflictOptions} value={draft.conflicts} onChange={(v) => set("conflicts", v)} empty="No other courses" error={errorFor("conflicts")} />
    </EditDialog>
  );
}
