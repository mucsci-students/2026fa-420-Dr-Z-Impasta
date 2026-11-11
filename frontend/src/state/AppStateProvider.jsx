import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api/client.js";
import { AppStateContext } from "./appStateContext.js";

const IDLE_POLL_MS = 3000;
const RUNNING_POLL_MS = 600;
const RETRY_MS = 3000;

/**
 * Keeps the server's application state (configuration status, generation progress,
 * schedule counts) available to every component, polling faster while schedules are
 * being generated and noticing when the server stops answering.
 */
export default function AppStateProvider({ children }) {
  const [state, setState] = useState(null);
  const [connectionError, setConnectionError] = useState(null);

  // Never rejects, so callers don't need a catch: it resolves to the new state, or to null
  // if the fetch failed. An unreachable server is shown by ConnectionBanner, and the next
  // poll tries again.
  const refresh = useCallback(async () => {
    try {
      const next = await api.state();
      setState(next);
      setConnectionError(null);
      return next;
    } catch (error) {
      if (error.code === "network_error") setConnectionError(error);
      return null;
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    let timer;
    async function poll() {
      const next = await refresh();
      const delay = !next ? RETRY_MS : next.generation?.running ? RUNNING_POLL_MS : IDLE_POLL_MS;
      if (!cancelled) timer = setTimeout(poll, delay);
    }
    poll();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [refresh]);

  const value = useMemo(
    () => ({ state, loading: state === null && !connectionError, connectionError, refresh }),
    [state, connectionError, refresh],
  );
  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>;
}
