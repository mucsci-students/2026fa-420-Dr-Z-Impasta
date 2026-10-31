/**
 * The "Advanced timing options…" dialog on TimeSlotsCard. It's an edit dialog like CourseDialog.
 * What each option means is in its field's help text below.
 */

import Field from "../../../components/Field.jsx";
import { formIssues } from "../../../components/issues.js";
import EditDialog from "./EditDialog.jsx";
import { useDraft } from "./useDraft.js";

const toNumber = (text) => (text === "" ? null : Number(text));

/**
 * The "Advanced timing options": max_time_gap and min_time_overlap. Save hands back
 * just those two, ready for api.config.updateTimeSlots(values).
 */
export default function TimeSlotsDialog({ timeSlots, busy, error, onSave, onCancel }) {
  const original = { max_time_gap: timeSlots.max_time_gap, min_time_overlap: timeSlots.min_time_overlap };
  const { draft, set, isDirty } = useDraft(original);
  const { errorFor, unplaced } = formIssues(error?.issues, {
    area: "time_slots",
    fields: ["max_time_gap", "min_time_overlap"],
  });

  return (
    <EditDialog
      width="480px"
      title="Advanced timing options"
      what="the timing options"
      isDirty={isDirty}
      error={error}
      unplaced={unplaced}
      busy={busy}
      onSave={() => onSave?.(draft)}
      onCancel={onCancel}
    >
      <div className="form-grid">
        <Field
          label="Max time gap (min)"
          required
          help="Two meetings this many minutes apart or less count as back-to-back. Default 30."
          error={errorFor("max_time_gap")}
        >
          <input type="number" min={1} value={draft.max_time_gap ?? ""}
            onChange={(e) => set("max_time_gap", toNumber(e.target.value))} data-autofocus />
        </Field>
        <Field
          label="Min overlap (min)"
          required
          help="The minimum overlap, in minutes, between a pattern's meetings on different days. Default 45."
          error={errorFor("min_time_overlap")}
        >
          <input type="number" min={1} value={draft.min_time_overlap ?? ""}
            onChange={(e) => set("min_time_overlap", toNumber(e.target.value))} />
        </Field>
      </div>
    </EditDialog>
  );
}
