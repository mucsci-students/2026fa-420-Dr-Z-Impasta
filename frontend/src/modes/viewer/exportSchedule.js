/**
 * Exports go through the server (api.schedules.exportFile), which writes the same
 * JSON and CSV files as the shell. This file only hands the result to the browser.
 */
import { api } from "../../api/client.js";

function downloadFile({ content, filename, type }) {
  const url = URL.createObjectURL(new Blob([content], { type: type || "application/octet-stream" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

/** `which` is a schedule number (starting at 1) or "all"; `format` is "json" or "csv". */
export async function exportSchedules({ which, format }) {
  downloadFile(await api.schedules.exportFile({ which, format }));
}