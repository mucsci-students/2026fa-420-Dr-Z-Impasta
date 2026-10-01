/**
 * Runs the Python API for the browser version, off the page's main thread.
 *
 * Pyodide itself comes from its CDN, at the version of the `pyodide` npm package; its
 * WebAssembly packages are built for that version, and so is z3-solver's. The zimpasta
 * package comes from this site (python/zimpasta.json). Requests are answered in order;
 * while a schedule is being solved they wait (see EventLoopRunner in
 * src/zimpasta/model/generation_job.py).
 */
import { loadPyodide, version } from "pyodide";
import { bootPython } from "./bootPython.js";

const PYODIDE_URL = `https://cdn.jsdelivr.net/pyodide/v${version}/full/`;
const PACKAGE_URL = new URL(`${import.meta.env.BASE_URL}python/zimpasta.json`, self.location.origin);

const ready = start();
ready.catch(() => {}); // reported with each request below

async function start() {
  const response = await fetch(PACKAGE_URL);
  if (!response.ok || !response.headers.get("Content-Type")?.includes("json")) {
    throw new Error("this site is missing its Python files (python/zimpasta.json)");
  }
  return bootPython({ loadPyodide, indexURL: PYODIDE_URL, files: await response.json() });
}

self.addEventListener("message", async ({ data: { id, request } }) => {
  let handle;
  try {
    handle = await ready;
  } catch (error) {
    self.postMessage({
      id,
      error:
        "Dr. ZImpasta couldn't start in this browser. Check your internet connection, then " +
        `reload the page. (${summarize(error)})`,
    });
    return;
  }
  try {
    self.postMessage({ id, response: await handle(request) });
  } catch (error) {
    self.postMessage({ id, error: `The request failed inside the browser: ${summarize(error)}` });
  }
});

/** The last line of a Python traceback, or the error's message. */
function summarize(error) {
  const lines = String(error?.message ?? error).trim().split("\n");
  return lines[lines.length - 1];
}
