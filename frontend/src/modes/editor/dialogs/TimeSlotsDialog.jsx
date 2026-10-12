// Description:
// | Field            | Control          | Notes
// | max_time_gap     | number (minutes) | Default 30. Max gap for two meetings to
// |                  |                  | count as back-to-back
// | min_time_overlap | number (minutes) | Default 45. Min overlap between meetings
// |                  |                  | on different days of a pattern

import { useState } from "react";
import Button from "../../../components/Button.jsx";
import ConfirmDialog from "../../../components/ConfirmDialog.jsx";
import Dialog from "../../../components/Dialog.jsx";
import ErrorMessage from "../../../components/ErrorMessage.jsx";
import Field from "../../../components/Field.jsx";
import UnsavedChangesPrompt from "../../../components/UnsavedChangesPrompt.jsx";
import { issuesFor } from "../../../components/issues.js";

const toNumber = (text) => (text === "" ? null : Number(text));

/**
 * The "Advanced timing options": max_time_gap and min_time_overlap. Save hands back
 * just those two, ready for api.config.updateTimeSlots(values).
 */
export default function TimeSlotsDialog({ timeSlots, busy, error, onSave, onCancel }) {
  const original = { max_time_gap: timeSlots.max_time_gap, min_time_overlap: timeSlots.min_time_overlap };
  const [draft, setDraft] = useState(original);
  const isDirty = JSON.stringify(draft) !== JSON.stringify(original);
  const [confirmingDiscard, setConfirmingDiscard] = useState(false);

  // Problems with nowhere to appear in this dialog; the banner lists them instead
  const FIELDS = ["max_time_gap", "min_time_overlap"];
  const unplaced = (error?.issues ?? []).filter((issue) =>
    issue.area !== "time_slots" ||
    !FIELDS.some((f) => issue.field === f || issue.field?.startsWith(`${f}.`)),
  );

  /** Cancel, Escape, or ×: ask first if there are unsaved edits. */
  function requestClose() {
    if (isDirty) setConfirmingDiscard(true);
    else onCancel?.();
  }

  function set(field, value) {
    setDraft((d) => ({ ...d, [field]: value }));
  }

  /** The library's message for one field. */
  function errorFor(field) {
    const found = issuesFor(error?.issues, { area: "time_slots", field });
    return found.length > 0 ? found.map((issue) => issue.message).join(" ") : undefined;
  }

  // The prompts are siblings of the Dialog, not children; see ResourceDialog.
  return (
    <>
      <Dialog
        open
        width="480px"
        title="Advanced timing options"
        onClose={requestClose}
        actions={
          <>
            <Button onClick={requestClose} disabled={busy}>Cancel</Button>
            <Button variant="primary" busy={busy} onClick={() => onSave?.(draft)}>Save</Button>
          </>
        }
      >
        <ErrorMessage error={error && { message: "The change was not applied.", issues: unplaced }} title="Not saved." />

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
        <p>Your changes to the timing options haven't been saved.</p>
      </ConfirmDialog>
    </>
  );
}
