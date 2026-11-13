/**
 * The Configuration Editor's actions. Every server call goes through `api` (client.js).
 *
 * Every editor action follows the GUI's error rule (docs/gui.md, "Handling errors"): it
 * takes the setter for where its error is shown and resolves to true if the change went
 * through or false if not. It never rejects, and it shows every failure, including an
 * unreachable server. Page-level errors go through `setError` (shown above the banner);
 * a dialog's or card's errors go through its own setter.
 *
 * validateConfig and saveConfig are the exception: the chat also uses them and shows results
 * its own way, so they work like `api` (resolve with the result, reject with an ApiError, or
 * for saveConfig an Error if the file couldn't be written). The editor's buttons call them
 * through validateShowingErrors and saveShowingErrors, which follow the rule.
 */
import { api } from "../api/client.js";
import { saveFile } from "../files.js";
import { ConfigFileOriginator, ConfigFileHistory } from "./configEditorMemento"

const ORIGINATOR = new ConfigFileOriginator();
let HISTORY = null;

/** Show an error above ConfigEditor's banner, with a button that dismisses it. */
const showPageError = (setError, error, title) =>
	setError({ error, title, onDismiss: () => setError(null) });

// How many snapshots the undo and redo histories hold (0 before the first load).
export const undoStepCount = () => {
	if(HISTORY != null)
		return (HISTORY.getSnapshots()).length;
	else
		return 0;
};
export const redoStepCount = () => {
	if(HISTORY != null)
		return (HISTORY.getCurrSnapshots()).length;
	else
		return 0;
};

// Snapshots are made and restored only by the originator (the Memento pattern): it turns
// the configuration into a memento with storeFile() and back with restore(), and HISTORY
// (the caretaker) keeps the mementos without looking inside them.

// Record a snapshot of `content` on the undo history, or on the redo history.
export const recordUndoStep = (content) => {
	ORIGINATOR.set(content);
	HISTORY.push(ORIGINATOR.storeFile());
};
const recordRedoStep = (content) => {
	ORIGINATOR.set(content);
	HISTORY.pushToCurr(ORIGINATOR.storeFile());
};


export const redo = async(currDoc, filename, setError, setPendingLoad) => {
	const memento = HISTORY.popCurr();
	if(memento == undefined) return false;

	// push snapshot of current state, before re-doing, to undo-action's history array
	recordUndoStep(currDoc);

	ORIGINATOR.restore(memento);
	return sendLoad(filename, JSON.stringify(ORIGINATOR.doc), true, setError, setPendingLoad);
};

export const undo = async(currDoc, filename, setError, setPendingLoad) => {
	const memento = HISTORY.pop();
	if(memento == undefined) return false;

	// push snapshot of current state, before undoing, to redo-action's history array
	recordRedoStep(currDoc);

	ORIGINATOR.restore(memento);
	return sendLoad(filename, JSON.stringify(ORIGINATOR.doc), true, setError, setPendingLoad);
};

/** Send a file's text to the server, then show what happened. */
const sendLoad = async(filename, content, discardChanges, setError, setPendingLoad) => {
	try {
		await api.config.load({ filename, content, discardChanges });
	} catch(error) {
		if(error.code === "unsaved_changes") {
			// Ask first; confirmLoad sends it again if the user agrees
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

export const loadFile = async(event, setLoadingFile, setError, setPendingLoad) => {
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
export const confirmLoad = async(pending, setPendingLoad, setLoadingFile, setError) => {
	setPendingLoad(null);
	setLoadingFile(true);
	try {
		return await sendLoad(pending.filename, pending.content, true, setError, setPendingLoad);
	} finally {
		setLoadingFile(false);
	}
};

export const startNewConfig = async(setLoadingFile, setError, setPendingLoad) => {
	setLoadingFile(true);
	try {
		// The starter file is served next to the GUI, not by the API, so this is a plain
		// fetch(). send() would pass it to Python in the browser build, which doesn't serve it.
		let content;
		try {
			const response = await fetch('/new_config.json');
			if (!response.ok) throw new Error(`The server answered ${response.status}.`);
			content = await response.text();
		} catch {
			showPageError(setError, { message: "The empty starter configuration couldn't be downloaded. Reload the page and try again." }, "Couldn't start a new configuration");
			return false;
		}
		return await sendLoad("unnamed.json", content, false, setError, setPendingLoad);
	}
	finally {
		await new Promise(resolve => setTimeout(resolve, 2000));
		setLoadingFile(false);
	}
};

/** Check the whole configuration now. Resolves to the report: `{ status, valid, issues, checked_at }`. */
export const validateConfig = async() => {
	const { report } = await api.config.validate();
	return report;
};

/**
 * Export the configuration, ask where to save it, then tell the server it was saved.
 * Resolves to true if saved, or false if the user closed the save dialog. An invalid
 * configuration rejects with an ApiError whose `issues` say what to fix.
 */
export const saveConfig = async() => {
	const { content, filename, revision } = await api.config.exportFile();
	const saved = await saveFile({ suggestedName: filename, content });
	if(!saved) return false;
	await api.config.markSaved({ revision, filename });
	return true;
};

/** The editor's Validate button: validateConfig, showing a failure on the page. The banner shows the result. */
export const validateShowingErrors = async(setError) => {
	try {
		await validateConfig();
	} catch(error) {
		showPageError(setError, error, "Couldn't validate the configuration");
		return false;
	}
	setError(null);
	return true;
};

/** The editor's Save button: saveConfig, showing a failure on the page. Resolves to false if not saved. */
export const saveShowingErrors = async(setError) => {
	let saved;
	try {
		saved = await saveConfig();
	} catch(error) {
		showPageError(setError, error, "Couldn't save the configuration");
		return false;
	}
	setError(null);
	return saved;
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

export const saveItem = async(editing, draft, setEditing, setLocalError) => {
	const { area, index } = editing;
	return applyEdit(
		() => (index == null ? api.config.add(area, draft) : api.config.replace(area, index, draft)),
		setEditing,
		setLocalError,
	);
};

/**
 * A class pattern's On/Off switch, which flips its `disabled` field. Always applied (force),
 * so patterns can be turned off in any order; if that leaves the configuration with
 * problems, the banner lists them. A failure is shown at the top of the page (`setError`),
 * since no dialog is open.
 */
export const togglePatternDisabled = async(index, pattern, setError) => {
	try {
		await api.config.replace("patterns", index, { ...pattern, disabled: !pattern.disabled }, true);
	} catch(err) {
		showPageError(setError, err, "Couldn't change the class pattern");
		return false;
	}
	setError(null);
	return true;
};

/** `force`: the user confirmed the delete after the dialog warned what it breaks. */
export const deleteItem = async(deleting, setDeleting, setEditing, setLocalError, force = false) => {
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

export const updateTimeSlots = async(vals, setEditing, setLocalError) =>
	applyEdit(() => api.config.updateTimeSlots(vals), setEditing, setLocalError);

export const updateSettings = async(vals, setSettingsError) => {
	try {
		await api.config.updateSettings(vals);
	} catch(err) {
		setSettingsError(err);
		return false;
	}
	setSettingsError(null);
	return true;
};
