/**
 * Auto | Light | Dark, as three small icon buttons in the header. Auto matches the
 * computer's setting. The choice is remembered in this browser (see src/theme.js).
 */
import { useTheme } from "../theme.js";

/** Half filled: follows whichever the computer uses. */
function AutoIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" aria-hidden="true">
      <circle cx="8" cy="8" r="5.5" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <path d="M8 2.5a5.5 5.5 0 0 1 0 11z" fill="currentColor" />
    </svg>
  );
}

function SunIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      aria-hidden="true"
    >
      <circle cx="8" cy="8" r="3" />
      <path d="M8 1.5v1.5M8 13v1.5M1.5 8H3M13 8h1.5M3.4 3.4l1.06 1.06M11.54 11.54l1.06 1.06M3.4 12.6l1.06-1.06M11.54 4.46l1.06-1.06" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M13.5 9.6A5.75 5.75 0 0 1 6.4 2.5a5.75 5.75 0 1 0 7.1 7.1z" />
    </svg>
  );
}

const OPTIONS = [
  { value: "system", label: "Auto (match your computer)", Icon: AutoIcon },
  { value: "light", label: "Light", Icon: SunIcon },
  { value: "dark", label: "Dark", Icon: MoonIcon },
];

/** The header's theme switch. */
export default function ThemeToggle() {
  const { choice, choose } = useTheme();

  return (
    <div className="segmented segmented--icons" role="group" aria-label="Theme">
      <div className="segmented__options">
        {OPTIONS.map(({ value, label, Icon }) => (
          <button
            key={value}
            type="button"
            className="segmented__option"
            aria-pressed={value === choice}
            title={`Theme: ${label}`}
            onClick={() => choose(value)}
          >
            <Icon />
            <span className="visually-hidden">{label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

