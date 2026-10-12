import { useEffect } from "react";
import { useBlocker } from "react-router";
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

  useEffect(() => {
    if (!when) return undefined;
    const warn = (event) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [when]);

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
