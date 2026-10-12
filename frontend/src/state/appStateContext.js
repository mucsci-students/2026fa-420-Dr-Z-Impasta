import { createContext, useContext } from "react";

export const AppStateContext = createContext(null);

/**
 * `{ state, loading, connectionError, refresh }` where `state` is the latest
 * GET /api/state reply (null until the first one arrives). Call `refresh()` after any
 * action so every mode and the header update straight away.
 */
export function useAppState() {
  const value = useContext(AppStateContext);
  if (!value) throw new Error("useAppState must be used inside <AppStateProvider>.");
  return value;
}
