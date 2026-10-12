import { useCallback, useRef, useState } from "react";

/**
 * Wrap an async action (usually an `api.*` call) for a button:
 *
 *   const save = useAction(() => api.config.validate());
 *   <Button busy={save.busy} onClick={save.run}>Validate</Button>
 *   {save.error && <ErrorMessage error={save.error} />}
 *
 * While the action runs, further calls are ignored, so a double click can't send the
 * request twice. `run` resolves to `{ ok: true, value }` or `{ ok: false, error }` and
 * never rejects; the error is also kept in `error` until the next run or `clearError()`.
 */
export function useAction(action) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const running = useRef(false);

  const run = useCallback(
    async (...args) => {
      if (running.current) return { ok: false, error: null, skipped: true };
      running.current = true;
      setBusy(true);
      setError(null);
      try {
        return { ok: true, value: await action(...args) };
      } catch (caught) {
        setError(caught);
        return { ok: false, error: caught };
      } finally {
        running.current = false;
        setBusy(false);
      }
    },
    [action],
  );

  const clearError = useCallback(() => setError(null), []);
  return { run, busy, error, clearError };
}
