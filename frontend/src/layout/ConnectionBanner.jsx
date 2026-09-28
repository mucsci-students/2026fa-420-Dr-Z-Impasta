import Banner from "../components/Banner.jsx";
import { useAppState } from "../state/appStateContext.js";

/** Shown under the header while the Python server isn't answering; clears itself on reconnect. */
export default function ConnectionBanner() {
  const { connectionError } = useAppState();
  if (!connectionError) return null;
  return (
    <div className="connection">
      <Banner tone="danger" title="Can't reach the Dr. ZImpasta server.">
        It may have been stopped. Start it again with <code>uv run zimpasta --gui</code>; this page
        reconnects on its own. Nothing you already applied is lost while the server keeps running.
      </Banner>
    </div>
  );
}
