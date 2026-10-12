import Spinner from "./Spinner.jsx";

/**
 * A button. `variant` is "primary" (the main action on a page), "secondary" (default),
 * "danger" (destructive: delete, clear, discard), or "ghost" (link-like). While `busy`,
 * it shows a spinner and can't be clicked again.
 */
export default function Button({
  variant = "secondary",
  size,
  busy = false,
  disabled = false,
  type = "button",
  className = "",
  children,
  ...rest
}) {
  const classes = ["btn", `btn--${variant}`, size && `btn--${size}`, className]
    .filter(Boolean)
    .join(" ");
  return (
    <button
      type={type}
      className={classes}
      disabled={disabled || busy}
      aria-busy={busy || undefined}
      {...rest}
    >
      {busy && <Spinner size="sm" label="" />}
      {children}
    </button>
  );
}
