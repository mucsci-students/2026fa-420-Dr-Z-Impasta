/**
 * `npm run test:browser`: run the browser version's Python in Node, the way the Web Worker
 * does, and use the API end to end: state, loading the sample configuration, the schedule
 * cap, a generation run on the event loop, and its schedules. Run `npm run build:browser`
 * first. The first run downloads Pyodide's packages and z3 (about 15 MB).
 */
import { readFileSync } from "node:fs";
import { loadPyodide } from "pyodide";
import { bootPython } from "../src/api/browser/bootPython.js";

const started = performance.now();
const seconds = () => ((performance.now() - started) / 1000).toFixed(1);
const files = JSON.parse(readFileSync(new URL("../dist-browser/python/zimpasta.json", import.meta.url)));
const sample = readFileSync(new URL("../../examples/sample_config.json", import.meta.url), "utf8");

const handle = await bootPython({ loadPyodide, files });
console.log(`Python ready after ${seconds()} s`);

async function call(method, url, body) {
  const request = { method, url, headers: [["Content-Type", "application/json"]], body: body ? JSON.stringify(body) : "" };
  const reply = JSON.parse(await handle(JSON.stringify(request)));
  return { status: reply.status, data: JSON.parse(reply.body) };
}

function expect(condition, message, detail) {
  if (!condition) {
    console.error(`FAILED: ${message}`, detail ?? "");
    process.exit(1);
  }
  console.log(`ok: ${message}`);
}

let reply = await call("GET", "/api/state");
expect(reply.status === 200 && reply.data.config.status === "none", "GET /api/state", reply);

reply = await call("POST", "/api/config/load", { filename: "sample_config.json", content: sample });
expect(reply.status === 200 && reply.data.state.status === "valid", "the sample configuration loads", reply);

reply = await call("GET", "/api/config/options");
const cap = reply.data.generation?.max_schedules;
expect(Number.isInteger(cap), `options report the cap (${cap})`, reply);

reply = await call("POST", "/api/generation", { limit: cap + 1 });
expect(reply.status === 422, "a run above the cap is refused", reply);

reply = await call("POST", "/api/generation", { limit: 1 });
expect(reply.status === 202 && reply.data.running, "a run starts", reply);

const deadline = Date.now() + 5 * 60_000;
do {
  await new Promise((resolve) => setTimeout(resolve, 500));
  reply = await call("GET", "/api/generation");
} while (reply.data.running && Date.now() < deadline);
expect(reply.data.state === "succeeded" && reply.data.found === 1, `the run finishes (${seconds()} s)`, reply);

reply = await call("GET", "/api/schedules");
expect(reply.status === 200 && reply.data.count === 1, "its schedule reaches the viewer", reply);
