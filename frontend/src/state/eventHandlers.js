import { api } from "../api/client.js";
import { saveFile } from "../files.js";
import { ConfigFileMemento, ConfigFileOriginator, ConfigFileHistory } from "./configEditorMemento"

let MEMENTO = null;
const ORIGINATOR = new ConfigFileOriginator();
let HISTORY = null;

const ConfigStatusObj = Object.freeze({
	NONE: "none",
	INCOMPLETE: "incomplete",
	INVALID: "invalid",
	VALID: "valid"
});

/** A page-level error for ConfigEditor's ErrorMessage. */
const pageError = (error, title, labels, onDismiss) => {
	return { "error" : error, "title" : title, "labels" : labels, "onDismiss" : onDismiss };
};

// getters to see the length of the history arrays
export const getHistoryLength = () => {
	if(HISTORY != null)
		return (HISTORY.getSnapshots()).length;
	else
		return 0;
};
export const getCurrHistoryLength = () => {
	if(HISTORY != null)
		return (HISTORY.getCurrSnapshots()).length;
	else
		return 0;
};

// pushes snapshot of history to appropriate array
export const pushToHist = (content) => {
	HISTORY.push(new ConfigFileMemento(content));
};
const pushToCurr = (content) => {
	HISTORY.pushToCurr(new ConfigFileMemento(content));
};


export const redoAction = async(currDoc, filename, setError, setPendingLoad) => {
	const restore = HISTORY.popCurr();

	// push snapshot of current state, before re-doing, to undo-action's history array
	pushToHist(currDoc);

	ORIGINATOR.set(restore);
	ORIGINATOR.storeFile();

	if(restore != undefined)
		await sendLoad(filename, JSON.stringify(restore.getFile()), true, setError, setPendingLoad);

};

export const undoAction = async(currDoc, filename, setError, setPendingLoad) => {
	const prevState = HISTORY.pop();

	// push snapshot of current state, before undoing, to redo-action's history array
	pushToCurr(currDoc);
	
	ORIGINATOR.set(prevState);
	ORIGINATOR.storeFile();


	if(prevState != undefined)
		await sendLoad(filename, JSON.stringify(prevState.getFile()), true, setError, setPendingLoad);

};

/** Send a file's text to the server, then show what happened. */
const sendLoad = async(filename, content, discardChanges, setError, setPendingLoad) => {
	try {
		await api.config.load({ filename, content, discardChanges });
	} catch(error) {
		if(error.code === "unsaved_changes") {
			// Ask first; ConfirmLoad sends it again if the user agrees
			setPendingLoad({ filename, content, changes: error.extra?.changes ?? [] });
			return false;
		}
		setError(pageError(error, `Couldn't load ${filename}`, undefined, () => setError(null)));
		return false;
	}

	setError(null);

	//only set the memento objects on initial load
	if(HISTORY == null) {
		ORIGINATOR.set(JSON.parse(content));
		HISTORY = new ConfigFileHistory(ORIGINATOR);
	}

	return true;
};

export const Load = async(event, setLoadingFile, setError, setPendingLoad) => {
	const file = event.target.files[0];
	event.target.value = "";   // so choosing the same file again still triggers onChange
	if(!file) return false;

	setLoadingFile(true);
	try {
		let content;
		try {
			content = await file.text();
		} catch {
			setError(pageError({ message: `${file.name} couldn't be read. Check that the file still exists and you can open it.` }, `Couldn't load ${file.name}`, undefined, () => setError(null)));
			return false;
		}
		return await sendLoad(file.name, content, false, setError, setPendingLoad);
	} finally {
		setLoadingFile(false);
	}
};

/** The user agreed to discard their unsaved changes: load the same file again. */
export const ConfirmLoad = async(pending, setPendingLoad, setLoadingFile, setError) => {
	setPendingLoad(null);
	setLoadingFile(true);
	try {
		return await sendLoad(pending.filename, pending.content, true, setError, setPendingLoad);
	} finally {
		setLoadingFile(false);
	}
};

export const Empty_Click = async(setLoadingFile, setError, setPendingLoad) => {
	setLoadingFile(true);
	try {
		// The starter file is served next to the GUI, not by the API, so this is a plain
		// fetch(). send() would pass it to Python in the browser build, which doesn't serve it.
		const response = await fetch(`${import.meta.env.BASE_URL}new_config.json`).catch(() => null);
		if(!response?.ok) {
			setError(pageError({ message: "The starter configuration couldn't be loaded. Reload the page and try again." }, "Couldn't start a new configuration", undefined, () => setError(null)));
			return false;
		}
		return await sendLoad("unnamed.json", await response.text(), false, setError, setPendingLoad);
	}
	finally {
		await new Promise(resolve => setTimeout(resolve, 2000));
		setLoadingFile(false);
	}
};

export const Validate = async() => {
	try {
		const { report } = await api.config.validate();
		return { "status": report.status, "issues": report.issues };
	} catch(err) {
		return err;
	}
};

/**
 * Validate, export, ask where to save, then tell the server it was saved.
 * Returns the saved content, null if the user closed the save dialog, the issues if the
 * configuration isn't valid, or the error if something failed.
 */
export const Save = async() => {
	const report = await Validate();
	if(report instanceof Error) return report;
	if(report.status !== ConfigStatusObj.VALID) return report.issues;

	try {
		const { content, filename, revision } = await api.config.exportFile();
		const saved = await saveFile({ suggestedName: filename, content });
		if(!saved) return null;
		await api.config.markSaved({ revision, filename: saved.name });
		return content;
	} catch(err) {
		return err;
	}
};

/** Send one edit from a dialog. On success close the dialog; on failure show why in it. */
const applyEdit = async(request, setEditing, setLocalError) => {
	try {
		await request();
	} catch(err) {
		setLocalError(err);
		return false;
	}
	setEditing(null);
	setLocalError(null);
	return true;
};

export const ValidateAndSaveItem = async(editing, draft, setEditing, setLocalError) => {
	const { area, index } = editing;
	return applyEdit(
		() => (index == null ? api.config.add(area, draft) : api.config.replace(area, index, draft)),
		setEditing,
		setLocalError,
	);
};

/**
 * A class pattern's On/Off switch. Always applied (force), so patterns can be turned off in
 * any order; if that leaves the configuration with problems, the banner lists them. A
 * failure is shown at the top of the page (`setError`), since no dialog is open.
 */
export const TogglePattern = async(index, pattern, setError) => {
	try {
		await api.config.replace("patterns", index, { ...pattern, disabled: !pattern.disabled }, true);
	} catch(err) {
		setError(pageError(err, "Couldn't change the class pattern", undefined, () => setError(null)));
		return false;
	}
	setError(null);
	return true;
};

/** `force`: the user confirmed the delete after the dialog warned what it breaks. */
export const DeleteItem = async(deleting, setDeleting, setEditing, setLocalError, force = false) => {
	try {
		await api.config.remove(deleting.area, deleting.index, force);
	} catch(err) {
		setLocalError(err);
		return false;   // keep the dialog open so the reason stays visible
	}
	setLocalError(null);
	setDeleting(null);
	setEditing(null);
	return true;
};

export const UpdateTimeSlot = async(vals, setEditing, setLocalError) =>
	applyEdit(() => api.config.updateTimeSlots(vals), setEditing, setLocalError);

export const UpdateSettings = async(vals, setSettingsError) => {
	try {
		await api.config.updateSettings(vals);
	} catch(err) {
		setSettingsError(err);
		return false;
	}
	setSettingsError(null);
	return true;
};
