/**
 * The browser version's backend: the Python API running in a Web Worker
 * (python.worker.js). send() posts a fetch-style request to the worker and turns the
 * reply into a Response, so client.js reads it exactly as it reads the server's.
 */

const worker = new Worker(new URL("./python.worker.js", import.meta.url), { type: "module" });
const pending = new Map();
let nextId = 1;
let crashed = null;

worker.addEventListener("message", ({ data }) => {
  const settle = pending.get(data.id);
  pending.delete(data.id);
  settle?.(data);
});

worker.addEventListener("error", (event) => {
  event.preventDefault();
  crashed = `Dr. ZImpasta stopped running in this tab (${event.message || "the worker failed"}).`;
  for (const settle of pending.values()) settle({ error: crashed });
  pending.clear();
});

export function send(url, init = {}) {
  if (crashed) return Promise.resolve(toResponse({ error: crashed }));
  const request = {
    method: init.method ?? "GET",
    url,
    headers: Object.entries(init.headers ?? {}),
    body: init.body ?? "",
  };
  const id = nextId++;
  return new Promise((resolve) => {
    pending.set(id, (reply) => resolve(toResponse(reply)));
    worker.postMessage({ id, request: JSON.stringify(request) });
  });
}

/** The worker's reply as a Response; a failure reads like an unreachable server. */
function toResponse({ response, error }) {
  if (error !== undefined) {
    return new Response(JSON.stringify({ error: { code: "network_error", message: error } }), {
      status: 503,
      headers: { "Content-Type": "application/json" },
    });
  }
  const { status, headers, body } = JSON.parse(response);
  return new Response(body, { status, headers });
}
