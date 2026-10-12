import { IN_BROWSER } from "../api/backend.js";
import Banner from "../components/Banner.jsx";
import { useAppState } from "../state/appStateContext.js";

/** Shown under the header while the Python server isn't answering; clears itself on reconnect. */
export default function ConnectionBanner() {
  const { connectionError } = useAppState();
  if (!connectionError) return null;
  if (IN_BROWSER) {
    // Python runs in this tab, so there's no server to restart: the error says what to do.
    return (
      <div className="connection">
        <Banner tone="danger" title="Dr. ZImpasta isn't running.">
          {connectionError.message}
        </Banner>
      </div>
    );
  }
  return (
    <div className="connection">
      <Banner tone="danger" title="Can't reach the Dr. ZImpasta server.">
        It may have been stopped. Start it again with <code>uv run zimpasta --gui</code>; this page
        reconnects on its own. Nothing you already applied is lost while the server keeps running.
      </Banner>
    </div>
  );
}
