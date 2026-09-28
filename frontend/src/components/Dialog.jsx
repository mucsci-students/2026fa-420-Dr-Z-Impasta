import { useEffect, useId, useRef } from "react";

/**
 * A modal dialog built on the native <dialog> element, which keeps keyboard focus inside
 * it and closes on Escape (calling `onClose`). Render it with `open` and put the buttons
 * in `actions`; give the one that should have focus first a `data-autofocus` attribute.
 */
export default function Dialog({ open, title, onClose, actions, tone, children, width }) {
  const ref = useRef(null);
  const titleId = useId();

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      dialog.showModal();
      dialog.querySelector("[data-autofocus]")?.focus();
    }
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      className={`dialog ${tone ? `dialog--${tone}` : ""}`}
      aria-labelledby={titleId}
      style={width ? { width } : undefined}
      onCancel={(event) => {
        event.preventDefault();
        onClose?.();
      }}
    >
      {open && (
        <>
          <header className="dialog__header">
            <h2 id={titleId} className="dialog__title">
              {title}
            </h2>
            {onClose && (
              <button type="button" className="dialog__close" aria-label="Close" onClick={onClose}>
                ×
              </button>
            )}
          </header>
          <div className="dialog__body">{children}</div>
          {actions && <footer className="dialog__actions">{actions}</footer>}
        </>
      )}
    </dialog>
  );
}
