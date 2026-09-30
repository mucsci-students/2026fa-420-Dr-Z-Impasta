import { NavLink } from "react-router";
import { Farfalle } from "../components/PastaMarks.jsx";
import Spinner from "../components/Spinner.jsx";
import StatusPill from "../components/StatusPill.jsx";
import { configStatus } from "../format.js";
import { MODES } from "../modes.js";
import { useAppState } from "../state/appStateContext.js";

/** The top bar on every page: the app name, the three modes, and the configuration's status. */
export default function Header() {
  const { state } = useAppState();
  const config = state?.config;
  const status = configStatus(config);
  const generating = state?.generation?.running;

  return (
    <header className="topbar">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <div className="topbar__brand">
        <Farfalle size={20} className="topbar__mark" />
        <span className="topbar__name">Dr. ZImpasta</span>
        <span className="topbar__tagline">Course Scheduler</span>
      </div>
      <nav className="modes" aria-label="Modes">
        {MODES.map((mode) => (
          <NavLink key={mode.path} to={mode.path} className="modes__link">
            <span className="modes__number" aria-hidden="true">
              {mode.number}
            </span>
            {mode.label}
            {mode.path === "/generator" && generating && (
              <>
                <span className="modes__busy">
                  <Spinner size="xs" label="" />
                </span>
                <span className="visually-hidden">(generating)</span>
              </>
            )}
          </NavLink>
        ))}
      </nav>
      <div className="topbar__status">
        {config?.name && <span className="topbar__file">{config.name}</span>}
        <StatusPill tone={status.tone} aria-label={`Configuration status: ${status.label}`}>
          {status.label}
        </StatusPill>
      </div>
    </header>
  );
}
