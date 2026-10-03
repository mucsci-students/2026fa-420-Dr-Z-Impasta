// Description:
// | Field    | Control                       | Notes
// | name     | text, required                |
// | capacity | number, required              |
// | features | TagInput                      |
// | times    | checkbox + AvailabilityEditor | "Always available" checked = null;
// |          |                               | unchecked shows the editor

import { useState } from "react";
import Button from "../../../components/Button.jsx";
import ConfirmDialog from "../../../components/ConfirmDialog.jsx";
import Dialog from "../../../components/Dialog.jsx";
import ErrorMessage from "../../../components/ErrorMessage.jsx";
import Field from "../../../components/Field.jsx";
import UnsavedChangesPrompt from "../../../components/UnsavedChangesPrompt.jsx";
import { issuesFor } from "../../../components/issues.js";
import TagInput from "../TagInput.jsx";

const NEW_RESOURCE = { name: "", capacity: null, features: [], times: null };
const NO_HOURS = { MON: [], TUE: [], WED: [], THU: [], FRI: [] };

/** Add or edit a room or lab. Edits a draft; nothing changes until Save succeeds. */
export default function ResourceDialog({ area, index, resource, suggestions, busy, error, onSave, onCancel, onDelete }) {
  const isNew = index === null;
  const kind = area === "rooms" ? "room" : "lab";
  const original = { ...NEW_RESOURCE, ...resource };   // fill defaults the document may omit
  const [draft, setDraft] = useState(original);
  const isDirty = JSON.stringify(draft) !== JSON.stringify(original);
  const [confirmingDiscard, setConfirmingDiscard] = useState(false);

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
    const found = issuesFor(error?.issues, { area, index: index ?? undefined, field });
    return found.length > 0 ? found.map((issue) => issue.message).join(" ") : undefined;
  }

  // The prompts are siblings of the Dialog, not children: React bubbles a nested <dialog>'s
  // Escape (cancel event) up the component tree, which would also close this one.
  return (
    <>
      <Dialog
        open
        title={isNew ? `Add ${kind}` : `Edit ${original.name}`}
        onClose={requestClose}
        actions={
          <>
            {!isNew && (
              <Button variant="danger" onClick={onDelete} disabled={busy}>Delete</Button>
            )}
            <Button onClick={requestClose} disabled={busy}>Cancel</Button>
            <Button variant="primary" busy={busy} onClick={() => onSave?.(draft)}>
              {isNew ? `Add ${kind}` : "Save"}
            </Button>
          </>
        }
      >
        <ErrorMessage error={error} title="Not saved." />

        <Field label="Name" required error={errorFor("name")}>
          <input value={draft.name} onChange={(e) => set("name", e.target.value)} data-autofocus />
        </Field>

        <Field label="Capacity" required help={`Maximum students the ${kind} can hold.`} error={errorFor("capacity")}>
          <input type="number" min={1} value={draft.capacity ?? ""} onChange={(e) => set("capacity", e.target.value === "" ? null : Number(e.target.value))} />
        </Field>

        <Field label="Features" help="Tags such as projector. Courses can require them." error={errorFor("features")}>
          <TagInput value={draft.features} onChange={(tags) => set("features", tags)} suggestions={suggestions} />
        </Field>

        <label className="checkbox">
          {/*<input type="checkbox" checked={draft.times === null} onChange={(e) => set("times", e.target.checked ? null : original.times ?? NO_HOURS)} />*/}
          Availability: Always / Set hours
        </label>
        {draft.times !== null && <p className="muted">Day-by-day hours: next step (AvailabilityEditor).</p>}
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
        <p>Your changes to this {kind} haven't been saved.</p>
      </ConfirmDialog>
    </>
  );
}
