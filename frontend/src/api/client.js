/**
 * The only place the View talks to the server. Every route in docs/web-api.md has one
 * function here, so components never build URLs or parse responses themselves.
 *
 * Successful calls resolve to the parsed JSON (or, for downloads, `{ content, filename }`).
 * Failed calls reject with an ApiError carrying the server's `code`, user-facing `message`,
 * and located `issues`. If the server can't be reached, `code` is "network_error".
 */

export class ApiError extends Error {
  constructor({ status = 0, code = "error", message, issues = [], ...extra }) {
    super(message || "The request failed.");
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.issues = issues;
    this.extra = extra;
  }
}

const UNREACHABLE =
  "Can't reach the Dr. ZImpasta server. It may have been stopped; start it again with `uv run zimpasta --gui`.";

async function request(method, path, body) {
  const init = { method, headers: { Accept: "application/json" } };
  if (body !== undefined) {
    init.headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(body);
  }
  let response;
  try {
    response = await fetch(`/api${path}`, init);
  } catch {
    throw new ApiError({ code: "network_error", message: UNREACHABLE });
  }
  return response.ok ? readSuccess(response) : Promise.reject(await readError(response));
}

async function readSuccess(response) {
  const disposition = response.headers.get("Content-Disposition") || "";
  if (disposition.startsWith("attachment")) {
    const match = /filename="([^"]+)"/.exec(disposition);
    return {
      content: await response.text(),
      filename: match ? match[1] : "download",
      type: (response.headers.get("Content-Type") || "").split(";")[0],
      revision: Number(response.headers.get("X-Config-Revision") ?? NaN),
    };
  }
  return response.json();
}

async function readError(response) {
  try {
    const { error } = await response.json();
    if (error) return new ApiError({ status: response.status, ...error });
  } catch {
    // Not a JSON error body; fall through to a generic message.
  }
  const message =
    response.status === 502 || response.status === 504
      ? UNREACHABLE
      : `The server answered ${response.status} ${response.statusText}.`;
  return new ApiError({
    status: response.status,
    code: response.status >= 500 ? "network_error" : "http_error",
    message,
  });
}

const get = (path) => request("GET", path);
const post = (path, body) => request("POST", path, body);
const put = (path, body) => request("PUT", path, body);
const del = (path) => request("DELETE", path);
const query = (params) => `?${new URLSearchParams(params)}`;

/** Areas that hold lists of items: "rooms", "labs", "courses", "faculty", "patterns". */
export const AREAS = ["rooms", "labs", "courses", "faculty", "patterns"];

export const api = {
  state: () => get("/state"),

  config: {
    get: () => get("/config"),
    schema: () => get("/config/schema"),
    options: () => get("/config/options"),
    create: ({ discardChanges = false } = {}) =>
      post("/config/new", { discard_changes: discardChanges }),
    load: ({ filename, content, discardChanges = false }) =>
      post("/config/load", { filename, content, discard_changes: discardChanges }),
    validate: () => post("/config/validate"),
    /** Resolves to `{ content, filename, revision }` for the save dialog. */
    exportFile: () => get("/config/export"),
    markSaved: ({ revision, filename }) => post("/config/saved", { revision, filename }),
    list: (area) => get(`/config/${area}`),
    item: (area, index) => get(`/config/${area}/${index}`),
    add: (area, item) => post(`/config/${area}`, item),
    replace: (area, index, item) => put(`/config/${area}/${index}`, item),
    deleteImpact: (area, index) => get(`/config/${area}/${index}/impact`),
    remove: (area, index) => del(`/config/${area}/${index}`),
    updateTimeSlots: (values) => put("/config/time-slots", values),
    updateSettings: (values) => put("/config/settings", values),
  },

  generation: {
    status: () => get("/generation"),
    /** `limit` and `optimizerFlags` override this run only; leave them undefined to use the configuration's. */
    start: ({ limit, optimizerFlags } = {}) =>
      post("/generation", { limit: limit ?? null, optimizer_flags: optimizerFlags ?? null }),
    cancel: () => post("/generation/cancel"),
  },

  schedules: {
    summary: () => get("/schedules"),
    /** `group` is "room" (rooms and labs) or "faculty". Numbers start at 1. */
    view: (number, group = "room") => get(`/schedules/${number}${query({ group })}`),
    importFile: ({ filename, content }) => post("/schedules/import", { filename, content }),
    /** `which` is "all" or a schedule number; `format` is "json" or "csv". */
    exportFile: ({ which = "all", format = "json" } = {}) =>
      get(`/schedules/export${query({ which: String(which), format })}`),
    clear: () => del("/schedules"),
  },
};
