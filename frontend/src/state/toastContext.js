import { createContext, useContext } from "react";

export const ToastContext = createContext(null);

/**
 * `notify({ tone, title, message })` shows a short confirmation in the corner, for
 * example after saving. `tone` is "success" (default), "info", or "danger". Errors that
 * need attention belong inline, next to what failed, not in a toast.
 */
export function useToast() {
  const notify = useContext(ToastContext);
  if (!notify) throw new Error("useToast must be used inside <ToastProvider>.");
  return notify;
}
