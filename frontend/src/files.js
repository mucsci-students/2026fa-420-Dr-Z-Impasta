/**
 * Choosing and saving files with the browser's own dialogs.
 *
 * Opening: `pickFile()` shows the system file picker and reads the chosen file as text.
 * Saving: `saveFile()` uses the native "Save As" dialog where the browser has one
 * (Chrome and Edge). That dialog asks before replacing an existing file. Elsewhere the
 * file is downloaded; browsers never overwrite a download, they add " (1)" to the name.
 * Either way nothing is written without the user choosing to.
 */

export class FileReadError extends Error {
  constructor(name) {
    super(`Couldn't read ${name}. Check that it is a text file you have permission to open.`);
    this.name = "FileReadError";
  }
}

/** Resolves to `{ name, text }`, or `null` if the user cancels. */
export function pickFile({ accept = ".json,application/json" } = {}) {
  return new Promise((resolve, reject) => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = accept;
    input.addEventListener("cancel", () => resolve(null));
    input.addEventListener("change", async () => {
      const file = input.files?.[0];
      if (!file) return resolve(null);
      try {
        resolve({ name: file.name, text: await file.text() });
      } catch {
        reject(new FileReadError(file.name));
      }
    });
    input.click();
  });
}

const TYPES = {
  "application/json": { description: "JSON file", extensions: [".json"] },
  "text/csv": { description: "CSV file", extensions: [".csv"] },
};

/**
 * Resolves to `{ name, method }` where method is "picker" or "download", or `null` if the
 * user cancels the dialog. Rejects if writing fails.
 */
export async function saveFile({ suggestedName, content, type = "application/json" }) {
  if (typeof window.showSaveFilePicker === "function") {
    const kind = TYPES[type] ?? { description: "File", extensions: [] };
    let handle;
    try {
      handle = await window.showSaveFilePicker({
        suggestedName,
        types: [{ description: kind.description, accept: { [type]: kind.extensions } }],
      });
    } catch (error) {
      if (error?.name === "AbortError") return null;
      throw error;
    }
    const writable = await handle.createWritable();
    await writable.write(new Blob([content], { type: `${type};charset=utf-8` }));
    await writable.close();
    return { name: handle.name, method: "picker" };
  }
  const url = URL.createObjectURL(new Blob([content], { type: `${type};charset=utf-8` }));
  const link = Object.assign(document.createElement("a"), { href: url, download: suggestedName });
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
  return { name: suggestedName, method: "download" };
}
