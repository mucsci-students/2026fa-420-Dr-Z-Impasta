/**
 * The Configuration Editor's actions. Every server call goes through `api` (client.js).
 *
 * The handlers follow one of two rules:
 * - Editor actions take the setters for the messages they show, and resolve to true if the
 *   change went through or false if not (the reason is on screen). Known gaps, kept as they
 *   were: when the server can't be reached, Load, ConfirmLoad, New and undo/redo reject,
 *   and item and time-slot edits resolve to false without a message. New also rejects if
 *   the starter file can't be fetched.
 * - Validate and Save are also used by the chat, which shows results its own way. They
 *   work like `api`: they resolve with the result and reject with an ApiError (or, for Save,
 *   an Error if the file couldn't be written).
 */
import { api } from "../api/client.js";
import { saveFile } from "../files.js";
import { ConfigFileMemento, ConfigFileOriginator, ConfigFileHistory } from "./configEditorMemento"

let MEMENTO = null;
const ORIGINATOR = new ConfigFileOriginator();
let HISTORY = null;

/** Show an error above ConfigEditor's banner, with a button that dismisses it. */
const showPageError = (setError, error, title) =>
	setError({ error, title, onDismiss: () => setError(null) });

/** The error to show, with `message` in place of the API's own text when the server can't be reached. */
const unreachableAs = (error, message) => (error.code === "network_error" ? { message } : error);

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

	if(restore == undefined) return false;
	return sendLoad(filename, JSON.stringify(restore.getFile()), true, setError, setPendingLoad);
};

export const undoAction = async(currDoc, filename, setError, setPendingLoad) => {
	const prevState = HISTORY.pop();

	// push snapshot of current state, before undoing, to redo-action's history array
	pushToCurr(currDoc);
	
	ORIGINATOR.set(prevState);
	ORIGINATOR.storeFile();


	if(prevState == undefined) return false;
	return sendLoad(filename, JSON.stringify(prevState.getFile()), true, setError, setPendingLoad);
};

/** Send a file's text to the server, then show what happened. */
const sendLoad = async(filename, content, discardChanges, setError, setPendingLoad) => {
	try {
		await api.config.load({ filename, content, discardChanges });
	} catch(error) {
		if(error.code === "network_error") throw error;   // not shown here
		if(error.code === "unsaved_changes") {
			// Ask first; ConfirmLoad sends it again if the user agrees
			setPendingLoad({ filename, content, changes: error.extra?.changes ?? [] });
			return false;
		}
		showPageError(setError, error, `Couldn't load ${filename}`);
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
			showPageError(setError, { message: `${file.name} couldn't be read. Check that the file still exists and you can open it.` }, `Couldn't load ${file.name}`);
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

	// The starter file is served next to the GUI, not by the API, so this is a plain
	// fetch(). send() would pass it to Python in the browser build, which doesn't serve it.
	const content = await fetch('/new_config.json')
		.then(response => {
			if (!response.ok) throw new Error('Failed to load config');
			return response.text();
		});

	const filename = "unnamed.json"
	try {
		return await sendLoad(filename, content, false, setError, setPendingLoad);
	}
	finally {
		await new Promise(resolve => setTimeout(resolve, 2000));
		setLoadingFile(false);
	}
};

/** Check the whole configuration now. Resolves to the report: `{ status, valid, issues, checked_at }`. */
export const Validate = async() => {
	const { report } = await api.config.validate();
	return report;
};

/**
 * Export the configuration, ask where to save it, then tell the server it was saved.
 * Resolves to true if saved, or false if the user closed the save dialog. An invalid
 * configuration rejects with an ApiError whose `issues` say what to fix.
 */
export const Save = async() => {
	const { content, filename, revision } = await api.config.exportFile();
	const saved = await saveFile({ suggestedName: filename, content });
	if(!saved) return false;
	await api.config.markSaved({ revision, filename });
	return true;
};

/** Send one edit from a dialog. On success close the dialog; on failure show why in it. */
const applyEdit = async(request, setEditing, setLocalError) => {
	try {
		await request();
	} catch(err) {
		if(err.code !== "network_error") setLocalError(err);   // an unreachable server isn't shown
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
		showPageError(setError, unreachableAs(err, "The server couldn't be reached. The class pattern was not changed."), "Couldn't change the class pattern");
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
		setLocalError(unreachableAs(err, "The server couldn't be reached. Nothing was deleted."));
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
		setSettingsError(unreachableAs(err, "The server couldn't be reached. The change was not applied."));
		return false;
	}
	setSettingsError(null);
	return true;
};
