/**
 * A field's error under its control: a "⚠" (hidden from screen readers) and the message.
 * Renders nothing when there is no error. Pass `id` when a control's `aria-describedby`
 * points at it, as `Field` does.
 */
export default function FieldError({ error, id }) {
  if (!error) return null;
  return (
    <p className="field__error" id={id}>
      <span aria-hidden="true">⚠ </span>
      {error}
    </p>
  );
}
