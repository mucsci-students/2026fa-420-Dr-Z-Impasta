import { useBlocker } from "react-router";
import { useWarnBeforeUnload } from "../state/useWarnBeforeUnload.js";
import ConfirmDialog from "./ConfirmDialog.jsx";

/**
 * Put this in a page that has a form draft. While `when` is true, switching modes or
 * closing the tab asks first, so an unapplied draft is never dropped silently.
 */
export default function UnsavedChangesPrompt({
  when,
  title = "Leave without applying?",
  message = "Your changes in this form haven't been applied. If you leave, they'll be lost.",
}) {
  const blocker = useBlocker(when);

  useWarnBeforeUnload(when);

  return (
    <ConfirmDialog
      open={blocker.state === "blocked"}
      title={title}
      destructive
      confirmLabel="Leave and discard"
      cancelLabel="Stay"
      onConfirm={() => blocker.proceed?.()}
      onCancel={() => blocker.reset?.()}
    >
      <p>{message}</p>
    </ConfirmDialog>
  );
}
