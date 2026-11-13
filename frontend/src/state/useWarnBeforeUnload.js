import { useEffect } from "react";

/**
 * While `when` is true, closing or reloading the tab first asks the browser's own "Leave
 * site?" question, so work that would be lost isn't dropped silently.
 */
export function useWarnBeforeUnload(when) {
  useEffect(() => {
    if (!when) return undefined;
    const warn = (event) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [when]);
}
