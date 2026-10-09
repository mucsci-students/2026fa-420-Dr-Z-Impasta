/* eslint-disable react-refresh/only-export-components */
import {
  loadConfiguration,
  loadEmptyConfig,
  validateConfig,
  saveConfig,
  addItem,
  replaceItem,
} from "../components/APICommunication";

const ConfigStatusObj = Object.freeze({
  NONE: "none",
  INCOMPLETE: "incomplete",
  VALID: "valid",
});

const buildError = (error, title, labels, onDismiss) => {
  return { error: error, title: title, labels: labels, onDismiss: onDismiss };
};

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export const Load = async (event, setLoadingFile, setError) => {
  const file = event.target.files[0];
  if (!file) return;

  setLoadingFile(true);
  try {
    const res = await loadConfiguration(file);

    if (!res.ok) {
      const component = buildError(
        res,
        "Invalid configuration file",
        res.issues,
        () => setError(null)
      );
      setError(component);
      return;
    }

    return res.json();
  } catch (err) {
    console.error("Load failed:", err);
    return err;
  } finally {
    await sleep(2000);
    setLoadingFile(false);
  }
};

export const Empty_Click = async (setLoadingFile) => {
  setLoadingFile(true);
  try {
    const res = await loadEmptyConfig();
    return res;
  } catch (err) {
    console.error("Loading empty config failed:", err);
    return err;
  } finally {
    await sleep(2000);
    setLoadingFile(false);
  }
};

// TODO: add UI error handling
export const Validate = async () => {
  try {
    const res = await validateConfig();
    return { status: res["report"]["status"], issues: res["report"]["issues"] };
  } catch (err) {
    console.error("Validate failed:", err);
    return err;
  }
};

// TODO: change status on GUI to the green Saved/Valid when the file is saved
export const Save = async () => {
  const report = await Validate();

  if (report["status"] === ConfigStatusObj.VALID) {
    try {
      const { content, filename } = await saveConfig();
      await Download(content, filename);
      return content;
    } catch (err) {
      // Cancelling the save dialog throws an AbortError; not a real failure.
      if (err && err.name !== "AbortError") {
        console.error("Save failed:", err);
      }
      return err;
    }
  }

  return report["issues"];
};

const Download = async (content, filename) => {
  const text =
    typeof content === "string" ? content : JSON.stringify(content, null, 2);

  if ("showSaveFilePicker" in window) {
    const fileHandle = await window.showSaveFilePicker({
      suggestedName: filename,
      types: [
        {
          description: "JSON configuration",
          accept: { "application/json": [".json"] },
        },
      ],
    });

    const writable = await fileHandle.createWritable();
    await writable.write(text);
    await writable.close();
    return;
  }

  // Fallback for browsers without the File System Access API
  const blob = new Blob([text], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;

  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
};

// TODO: add a UI for errors
export const ValidateAndSaveItem = async (editing, draft, setEditing) => {
  const area = editing.area;
  const index = editing.index;

  try {
    const res =
      index == null
        ? await addItem(area, draft)
        : await replaceItem(area, index, draft);

    if (!res.ok) {
      console.log(await res.json());
    } else {
      setEditing(null);
    }

    return res;
  } catch (err) {
    console.error("Saving item failed:", err);
    return err;
  }
};
