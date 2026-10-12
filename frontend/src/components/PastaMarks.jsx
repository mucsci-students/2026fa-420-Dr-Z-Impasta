/**
 * Small pasta-shaped marks, a nod to the team's name. Each is a plain line icon that
 * inherits the text color (`currentColor`), so color it with a design token in CSS and
 * it stays in the palette. They are decorative: always hidden from screen readers, and
 * never the only way something is said. Keep them quiet: the brand mark in the header, one
 * per empty state, and the spinner's spaghetti twirl (Spinner.jsx) are the whole set so far.
 */

function Mark({ size = 24, className, children }) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {children}
    </svg>
  );
}

/** Farfalle: the brand mark in the header, and the favicon. */
export function Farfalle(props) {
  return (
    <Mark {...props}>
      <path d="M12 12C10 9 7.2 6.6 4.2 6.6a1.35 1.35 0 0 0 0 2.7a1.35 1.35 0 0 0 0 2.7a1.35 1.35 0 0 0 0 2.7a1.35 1.35 0 0 0 0 2.7C7.2 17.4 10 15 12 12ZM12 12C14 9 16.8 6.6 19.8 6.6a1.35 1.35 0 0 1 0 2.7a1.35 1.35 0 0 1 0 2.7a1.35 1.35 0 0 1 0 2.7a1.35 1.35 0 0 1 0 2.7C16.8 17.4 14 15 12 12Z" />
      <ellipse cx="12" cy="12" rx="1.7" ry="2.6" fill="currentColor" stroke="none" />
    </Mark>
  );
}

/** Penne, which also reads as a pencil: the Configuration Editor. */
export function Penne(props) {
  return (
    <Mark {...props}>
      <path d="M5.6 14.28L17.8 2.08M5.6 21.92L17.8 9.72M5.6 14.28a1.3 3.82 0 0 0 0 7.64M17.8 2.08a1.6 3.82 0 1 1 0 7.64a1.6 3.82 0 1 1 0 -7.64M7.8 16.83L15.4 4.63M7.8 19.37L15.4 7.17" />
    </Mark>
  );
}

/** Rotelle, a wheel that turns: the Schedule Generator. */
export function Rotelle(props) {
  return (
    <Mark {...props}>
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="2.6" />
      <path d="M12 14.6L12 20.4M9.75 13.3L4.73 16.2M9.75 10.7L4.73 7.8M12 9.4L12 3.6M14.25 10.7L19.27 7.8M14.25 13.3L19.27 16.2" />
    </Mark>
  );
}

/** Lasagna, layered like a timetable: the Schedule Viewer. */
export function Lasagna(props) {
  return (
    <Mark {...props}>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="M3 9.7q1.5 -1.1 3 0t3 0t3 0t3 0t3 0t3 0M3 14.3q1.5 -1.1 3 0t3 0t3 0t3 0t3 0t3 0" />
    </Mark>
  );
}

/** Ravioli with a pinked edge and a stitched seam: pages that don't exist. */
export function Ravioli(props) {
  return (
    <Mark {...props}>
      <path d="M4 4L5 2.9L6 4L7 2.9L8 4L9 2.9L10 4L11 2.9L12 4L13 2.9L14 4L15 2.9L16 4L17 2.9L18 4L19 2.9L20 4L21.1 5L20 6L21.1 7L20 8L21.1 9L20 10L21.1 11L20 12L21.1 13L20 14L21.1 15L20 16L21.1 17L20 18L21.1 19L20 20L19 21.1L18 20L17 21.1L16 20L15 21.1L14 20L13 21.1L12 20L11 21.1L10 20L9 21.1L8 20L7 21.1L6 20L5 21.1L4 20L2.9 19L4 18L2.9 17L4 16L2.9 15L4 14L2.9 13L4 12L2.9 11L4 10L2.9 9L4 8L2.9 7L4 6L2.9 5L4 4Z" />
      <rect x="8" y="8" width="8" height="8" rx="4" strokeDasharray="0.1 2.6" />
    </Mark>
  );
}
