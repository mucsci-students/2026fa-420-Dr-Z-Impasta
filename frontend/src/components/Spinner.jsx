/** A strand of spaghetti twirled on a fork, seen from above. */
const TWIRL = "M14 12C14.18 12.51 14.15 13.16 13.84 13.76C13.52 14.35 12.91 14.87 12.14 15.08C11.36 15.3 10.43 15.2 9.61 14.73C8.8 14.26 8.12 13.41 7.85 12.37C7.57 11.33 7.71 10.11 8.31 9.06C8.92 8.01 9.99 7.15 11.29 6.79C12.59 6.43 14.11 6.59 15.41 7.31C16.71 8.03 17.77 9.31 18.24 10.87C18.71 12.42 18.56 14.23 17.75 15.79C16.93 17.35 15.45 18.65 13.65 19.24C11.85 19.84 9.74 19.73 7.91 18.84C6.08 17.96 4.54 16.3 3.79 14.27C3.04 12.23 3.09 9.82 4.02 7.71C4.96 5.59 6.77 3.8 9.03 2.87";

/**
 * A small progress indicator: a turning twirl in the current text color. Give `label`
 * unless the surrounding text already says it; with `label=""` it is decorative.
 */
export default function Spinner({ size = "md", label = "Loading" }) {
  return (
    <svg
      className={`spinner spinner--${size}`}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.2"
      strokeLinecap="round"
      role={label ? "status" : undefined}
      aria-label={label || undefined}
      aria-hidden={label ? undefined : true}
      focusable="false"
    >
      <path d={TWIRL} />
    </svg>
  );
}
