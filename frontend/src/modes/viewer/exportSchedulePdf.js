/**
 * PDF export, next to the JSON and CSV export in exportSchedule.js.
 *
 * JSON and CSV files are written by the server. A PDF is a way of showing a schedule, so
 * it is made here in the View, from the same grouped reply the viewer already displays
 * (`api.schedules.view`). Nothing is sent to the server and no schedule is changed.
 *
 * saveFile() (src/files.js) decides where the file goes, exactly as for JSON and CSV: the
 * Save As dialog in Chrome and Edge, which asks before replacing a file, or a download
 * elsewhere, which never overwrites.
 */
import { saveFile } from "../../files.js";

import { PdfExportError, buildSchedulePdf } from "./schedulePdf.js";

/**
 * The drawing code, loaded on the first export so jsPDF isn't part of the page's first
 * download. A browser that failed to fetch it may not try again until the page is
 * reloaded. The browser version loses its session on reload, so the message says to save
 * the schedules as JSON first.
 */
async function loadDocumentCode() {
  try {
    return (await import("./schedulePdfDocument.js")).createSchedulePdfFile;
  } catch (error) {
    throw new PdfExportError(
      "load_failed",
      "The PDF exporter couldn't be loaded. Your existing schedule has not been changed. " +
        "Check your connection and try again. If it keeps failing, export the schedules as " +
        "JSON, then reload the page.",
      { cause: error },
    );
  }
}

/**
 * Export `view` (one schedule, grouped by `groupBy`) as a PDF. See buildSchedulePdf() for
 * the options. Resolves to `{ name, method }` once saved, or null if the user cancelled
 * the Save As dialog. Rejects with a PdfExportError when the choices are incomplete or
 * there is nothing to export, and with the underlying error if drawing or saving fails.
 *
 * `save` and `draw` are replaceable for tests.
 */
export async function exportSchedulePdf(options, { save = saveFile, draw } = {}) {
  const pdf = buildSchedulePdf(options);
  const createFile = draw ?? (await loadDocumentCode());
  const file = createFile(pdf);
  return save({ suggestedName: file.filename, content: file.content, type: "application/pdf" });
}
