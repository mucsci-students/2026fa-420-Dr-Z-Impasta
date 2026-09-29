import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The Python API started by `npm run dev:api`. `npm run dev` starts both it and Vite.
const API = "http://127.0.0.1:8765";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    // Keep the browser's Host header (changeOrigin: false) so the API's same-origin
    // check sees localhost:5173 in both Host and Origin.
    proxy: { "/api": { target: API, changeOrigin: false } },
  },
  build: {
    // The Python package serves the built GUI: `uv run zimpasta --gui`.
    outDir: "../src/zimpasta/web",
    emptyOutDir: true,
  },
});
