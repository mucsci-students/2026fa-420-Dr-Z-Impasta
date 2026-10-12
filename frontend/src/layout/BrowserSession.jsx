import { useEffect } from "react";
import Banner from "../components/Banner.jsx";
import { useAppState } from "../state/appStateContext.js";

/**
 * Only in the browser version, where Python runs in this tab: says what's happening while
 * it starts, and asks before the tab closes or reloads with work that would be lost.
 */
export default function BrowserSession() {
  const { state, loading } = useAppState();
  const atRisk = Boolean(
    state?.config?.dirty ||
      state?.generation?.running ||
      (state?.schedules?.count > 0 && state.schedules.source === "generated"),
  );

  useEffect(() => {
    if (!atRisk) return undefined;
    const warn = (event) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [atRisk]);

  if (!loading) return null;
  return (
    <div className="connection">
      <Banner tone="info" title="Starting Dr. ZImpasta in your browser.">
        It runs entirely on your computer, so the first visit downloads about 15 MB and can take a
        minute. Later visits start faster.
      </Banner>
    </div>
  );
}
