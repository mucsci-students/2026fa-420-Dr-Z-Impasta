import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The Python API started by `npm run dev:api`. `npm run dev` starts both it and Vite.
const API = "http://127.0.0.1:8765";

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    // Keep the browser's Host header (changeOrigin: false) so the API's same-origin
    // check sees localhost:5173 in both Host and Origin.
    proxy: { "/api": { target: API, changeOrigin: false } },
  },
  // The browser version's worker imports pyodide, which loads its own files at runtime.
  optimizeDeps: { exclude: ["pyodide"] },
  worker: {
    format: "es",
    rolldownOptions: {
      onLog(level, log, handler) {
        // pyodide.mjs also runs on Node; its node:* imports are never reached in a browser.
        if (log.message?.includes("externalized for browser compatibility")) return;
        handler(level, log);
      },
    },
  },
  build: {
    // The Python package serves the built GUI (`uv run zimpasta --gui`). The browser
    // version (`npm run build:browser`, mode "browser") is a separate static site.
    outDir: mode === "browser" ? "dist-browser" : "../src/zimpasta/web",
    emptyOutDir: true,
  },
}));
