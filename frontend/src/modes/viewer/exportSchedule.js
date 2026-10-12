/**
 * Exports go through the server (api.schedules.exportFile), which writes the same
 * JSON and CSV files as the shell. saveFile() (src/files.js) then lets the user choose
 * where it goes: the Save As dialog in Chrome and Edge, which asks before replacing a
 * file, or a download elsewhere, which never overwrites (README → "The GUI" → Files).
 */
import { api } from "../../api/client.js";
import { saveFile } from "../../files.js";

const TYPES = { json: "application/json", csv: "text/csv" };

/**
 * `which` is a schedule number (starting at 1) or "all"; `format` is "json" or "csv".
 * Resolves to `{ name, method }` once saved, or null if the user cancelled the dialog.
 */
export async function exportSchedules({ which, format }) {
  const file = await api.schedules.exportFile({ which, format });
  return saveFile({ suggestedName: file.filename, content: file.content, type: TYPES[format] });
}
