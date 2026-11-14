import Button from "./Button.jsx";
import Dialog from "./Dialog.jsx";

/**
 * Ask before doing something. Use `destructive` for anything that deletes, clears, or
 * discards; its confirm button is red and Cancel is focused first.
 */
export default function ConfirmDialog({
  open,
  title,
  children,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  destructive = false,
  busy = false,
  onConfirm,
  onCancel,
  extraActions,
}) {
  return (
    <Dialog
      open={open}
      title={title}
      onClose={onCancel}
      tone={destructive ? "danger" : undefined}
      actions={
        <>
          <Button onClick={onCancel} data-autofocus={destructive || undefined} disabled={busy}>
            {cancelLabel}
          </Button>
          {extraActions}
          <Button
            variant={destructive ? "danger" : "primary"}
            onClick={onConfirm}
            busy={busy}
            data-autofocus={!destructive || undefined}
          >
            {confirmLabel}
          </Button>
        </>
      }
    >
      {children}
    </Dialog>
  );
}
