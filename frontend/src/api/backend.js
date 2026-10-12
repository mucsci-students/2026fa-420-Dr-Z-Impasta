/**
 * Where API requests go, chosen when the GUI is built (docs/gui.md):
 *
 * - `npm run build` and `npm run dev`: the Python server (`zimpasta --gui`), with fetch().
 * - `npm run build:browser`: Python running in this tab (Pyodide in a Web Worker), for the
 *   hosted version. It answers the same routes with the same replies.
 *
 * Vite replaces `import.meta.env.MODE` when it builds, so each build contains only its
 * own backend.
 */
export const IN_BROWSER = import.meta.env.MODE === "browser";

let browserBackend;

/** fetch(), sent to whichever backend this build uses. */
export function send(url, init) {
  if (IN_BROWSER) {
    browserBackend ??= import("./browser/pythonBackend.js");
    return browserBackend.then((backend) => backend.send(url, init));
  }
  return fetch(url, init);
}
