/**
 * `npm run build:browser`: the browser version, which runs the Python API in the page.
 *
 * 1. Vite builds the GUI in "browser" mode into dist-browser/ (see src/api/backend.js).
 * 2. The Python the browser needs (zimpasta.browser, the model, and the controller) is
 *    bundled into dist-browser/python/zimpasta.json as { "zimpasta/...": "source" }.
 *
 * Preview it with `npm run preview:browser`; `npm run test:browser` runs its Python in Node.
 */
import { mkdirSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "vite";

const frontend = fileURLToPath(new URL("..", import.meta.url));
const source = join(frontend, "..", "src");
const output = join(frontend, "dist-browser", "python");

/** What the browser imports, relative to src/. Nothing else from the package is needed. */
const PACKAGE = ["zimpasta/__init__.py", "zimpasta/browser.py", "zimpasta/model/", "zimpasta/controller/"];

await build({ root: frontend, mode: "browser" });

const files = {};
for (const entry of readdirSync(join(source, "zimpasta"), { recursive: true })) {
  const path = `zimpasta/${entry.replaceAll("\\", "/")}`;
  const wanted = PACKAGE.some((prefix) => path === prefix || (prefix.endsWith("/") && path.startsWith(prefix)));
  if (wanted && !path.includes("__pycache__") && /\.(py|json)$/.test(path)) {
    files[path] = readFileSync(join(source, path), "utf8");
  }
}
mkdirSync(output, { recursive: true });
writeFileSync(join(output, "zimpasta.json"), JSON.stringify(files));
console.log(`Bundled ${Object.keys(files).length} Python files into dist-browser/python/zimpasta.json`);
