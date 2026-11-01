/**
 * The dialog for adding or editing a room or lab (`area` says which), opened from ResourceCard or
 * "Add room" / "Add lab". It's an edit dialog like CourseDialog. "Unrestricted availability" saves
 * times as null; unticking it brings back the last hours set, or weekdays 08:00–17:00.
 */

import { useState } from "react";
import Field from "../../../components/Field.jsx";
import { formIssues, issuesFor } from "../../../components/issues.js";
import AvailabilityEditor from "../AvailabilityEditor.jsx";
import TagInput from "../TagInput.jsx";
import EditDialog from "./EditDialog.jsx";
import { useDraft } from "./useDraft.js";

const NEW_RESOURCE = { name: "", capacity: null, features: [], times: null };
const WEEKDAYS = ["MON", "TUE", "WED", "THU", "FRI"];
/** Where set hours start when "Unrestricted availability" is unticked, so the room isn't left unusable. */
const WORKDAY = [{ start: "08:00", end: "17:00" }];

/**
 * Add or edit a room or lab. Edits a draft; nothing changes until Save succeeds.
 * `options` is the reply from api.config.options(); fallbacks are used until it arrives.
 */
export default function ResourceDialog({ area, index, resource, suggestions, options, busy, error, onSave, onCancel, onDelete }) {
  const isNew = index === null;
  const kind = area === "rooms" ? "room" : "lab";
  const original = { ...NEW_RESOURCE, ...resource };   // fill defaults the document may omit
  const { draft, set, isDirty } = useDraft(original);
  const weekdays = options?.weekdays?.length ? options.weekdays : WEEKDAYS;
  // The hours to bring back when "Unrestricted availability" is unticked
  const [lastHours, setLastHours] = useState(original.times);
  const { errorFor, errorClass, unplaced } = formIssues(error?.issues, {
    area,
    index: index ?? undefined,
    fields: ["name", "capacity", "features", "times"],
  });

  /** Tick: remember the hours, then clear them. Untick: bring back the remembered or default hours. "Unrestricted availability" means the resource is always available. */
  function setUnrestrictedAvailability(unrestricted) {
    if (unrestricted) {
      setLastHours(draft.times);
      set("times", null);
    } else {
      set("times", lastHours ?? Object.fromEntries(weekdays.map((day) => [day, WORKDAY])));
    }
  }

  return (
    <EditDialog
      title={isNew ? `Add ${kind}` : `Edit ${original.name}`}
      what={`this ${kind}`}
      isDirty={isDirty}
      error={error}
      unplaced={unplaced}
      busy={busy}
      saveLabel={isNew ? `Add ${kind}` : "Save"}
      onSave={() => onSave?.(draft)}
      onCancel={onCancel}
      onDelete={isNew ? undefined : onDelete}
    >
      <Field label="Name" required error={errorFor("name")}>
        <input className={errorClass("name")} value={draft.name} onChange={(e) => set("name", e.target.value)} data-autofocus />
      </Field>

      <Field label="Capacity" required help={`Maximum students the ${kind} can hold.`} error={errorFor("capacity")}>
        <input className={errorClass("capacity")} type="number" min={1} value={draft.capacity ?? ""} onChange={(e) => set("capacity", e.target.value === "" ? null : Number(e.target.value))} />
      </Field>

      <Field label="Features" help="Tags such as projector. Courses can require them." error={errorFor("features")}>
        <TagInput className={errorClass("features")} value={draft.features} onChange={(tags) => set("features", tags)} suggestions={suggestions} />
      </Field>

      <label className="checkbox">
        <input
          type="checkbox"
          checked={draft.times === null}
          onChange={(e) => setUnrestrictedAvailability(e.target.checked)}
        />
        Unrestricted availability
      </label>
      {draft.times !== null && (
        <AvailabilityEditor
          legend={`When the ${kind} can be used`}
          value={draft.times}
          onChange={(times) => set("times", times)}
          days={weekdays}
          issues={issuesFor(error?.issues, { area, index: index ?? undefined, field: "times" })}
        />
      )}
    </EditDialog>
  );
}
