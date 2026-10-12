import { cloneElement, useId } from "react";
import HelpTip from "./HelpTip.jsx";

/**
 * A labelled form control with optional help and an error underneath:
 *
 *   <Field label="Capacity" required help="Seats in the room." error={message}>
 *     <input type="number" value={...} onChange={...} />
 *   </Field>
 *
 * The control gets an id, `aria-invalid`, and `aria-describedby` wired to the error.
 */
export default function Field({ label, required = false, help, error, children, inline = false }) {
  const id = useId();
  const errorId = `${id}-error`;
  const control = cloneElement(children, {
    id,
    "aria-invalid": error ? true : undefined,
    "aria-describedby": error ? errorId : undefined,
    required: required || undefined,
  });
  return (
    <div className={`field ${inline ? "field--inline" : ""} ${error ? "field--error" : ""}`}>
      <label className="field__label" htmlFor={id}>
        {label}
        {required && (
          <span className="field__required" aria-hidden="true">
            *
          </span>
        )}
        {help && <HelpTip text={help} />}
      </label>
      {control}
      {error && (
        <p className="field__error" id={errorId}>
          <span aria-hidden="true">⚠ </span>
          {error}
        </p>
      )}
    </div>
  );
}
