/**
 * Start the Python API inside Pyodide and return its request handler. Shared by the Web
 * Worker (python.worker.js) and the Node check (scripts/test-browser.mjs).
 *
 * `files` is dist-browser/python/zimpasta.json from `npm run build:browser`: the package's
 * source files by path. They are written into site-packages, then zimpasta.browser
 * installs its requirements and builds the app (src/zimpasta/browser.py).
 *
 * The returned function takes a request as JSON text and resolves to the reply as JSON
 * text; see zimpasta.browser.handle().
 */
export async function bootPython({ loadPyodide, indexURL, files }) {
  const pyodide = await loadPyodide(indexURL ? { indexURL } : {});
  await pyodide.loadPackage(["micropip", "pydantic", "fastapi"], { messageCallback: () => {} });

  const sitePackages = pyodide.runPython("import sysconfig; sysconfig.get_path('purelib')");
  for (const [path, text] of Object.entries(files)) {
    const target = `${sitePackages}/${path}`;
    pyodide.FS.mkdirTree(target.slice(0, target.lastIndexOf("/")));
    pyodide.FS.writeFile(target, text);
  }

  await pyodide.runPythonAsync(`
import importlib
importlib.invalidate_caches()
import zimpasta.browser
await zimpasta.browser.install()
zimpasta.browser.start()
`);
  const { handle } = pyodide.pyimport("zimpasta.browser");
  return (request) => handle(request);
}
