/** A small progress indicator. Give `label` unless the surrounding text already says it. */
export default function Spinner({ size = "md", label = "Loading" }) {
  return (
    <span
      className={`spinner spinner--${size}`}
      role={label ? "status" : undefined}
      aria-label={label || undefined}
      aria-hidden={label ? undefined : true}
    />
  );
}
