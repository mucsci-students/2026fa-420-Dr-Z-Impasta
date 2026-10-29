/**
 * The frame every edit dialog shares (docs/gui.md, "Edit in a draft"): the "Not saved."
 * banner, the Delete / Cancel / Save buttons, and the prompts that stop unsaved edits being
 * dropped. The dialog itself keeps the draft (useDraft) and puts its fields in `children`.
 */

import { useState } from "react";
import Button from "../../../components/Button.jsx";
import ConfirmDialog from "../../../components/ConfirmDialog.jsx";
import Dialog from "../../../components/Dialog.jsx";
import ErrorMessage from "../../../components/ErrorMessage.jsx";
import UnsavedChangesPrompt from "../../../components/UnsavedChangesPrompt.jsx";

/**
 * `what` finishes "Your changes to … haven't been saved." (e.g. "this room").
 * `error` is the last failed Save; `unplaced` are its issues that no field shows (formIssues).
 * Leave out `onDelete` for a new item, or a dialog that can't delete.
 */
export default function EditDialog({
  title,
  width,
  what,
  isDirty,
  error,
  unplaced = [],
  busy,
  saveLabel = "Save",
  onSave,
  onCancel,
  onDelete,
  children,
}) {
  const [confirmingDiscard, setConfirmingDiscard] = useState(false);

  /** Cancel, Escape, or ×: ask first if there are unsaved edits. */
  function requestClose() {
    if (isDirty) setConfirmingDiscard(true);
    else onCancel?.();
  }

  // Issues mean the library rejected the draft; without them (e.g. the server couldn't be
  // reached) the error's own message says what happened.
  const message = error?.issues?.length ? "The change was not applied." : error?.message;

  // The prompts are siblings of the Dialog, not children: React bubbles a nested <dialog>'s
  // Escape (cancel event) up the component tree, which would also close this one.
  return (
    <>
      <Dialog
        open
        width={width}
        title={title}
        onClose={requestClose}
        actions={
          <>
            {onDelete && (
              <Button variant="danger" onClick={onDelete} disabled={busy}>Delete</Button>
            )}
            <Button onClick={requestClose} disabled={busy}>Cancel</Button>
            <Button variant="primary" busy={busy} onClick={onSave}>{saveLabel}</Button>
          </>
        }
      >
        <ErrorMessage error={error && { message, issues: unplaced }} title="Not saved." />
        {children}
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
        <p>Your changes to {what} haven't been saved.</p>
      </ConfirmDialog>
    </>
  );
}
