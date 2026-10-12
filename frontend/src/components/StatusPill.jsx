/** A dot and a label, like "Valid · saved". The label carries the meaning, not the color. */
export default function StatusPill({ tone = "neutral", children, ...rest }) {
  return (
    <span className={`pill pill--${tone}`} {...rest}>
      <span className="pill__dot" aria-hidden="true" />
      {children}
    </span>
  );
}
