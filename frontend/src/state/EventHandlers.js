import { loadConfiguration, loadEmptyConfig, validateConfig, saveConfig, exportConfig, addItem, replaceItem, deleteItem, updateTimeSlot, updateSettings } from "../components/APICommunication";

const ConfigStatusObj = Object.freeze({
	NONE: "none",
	INCOMPLETE: "incomplete",
	VALID: "valid"
});

const Error = (error, title, labels, onDismiss) => {
	return { "error" : error, "title" : title, "labels" : labels, "onDismiss" : onDismiss };
};

/** Send a file's text to the server, then show what happened. */
const sendLoad = async(filename, content, discardChanges, setError, setPendingLoad) => {
	const res = await loadConfiguration(filename, content, discardChanges);
	if(res.ok) {
		setError(null);
		return true;
	}

	const { error } = await res.json();
	if(error?.code === "unsaved_changes") {
		// Ask first; ConfirmLoad sends it again if the user agrees
		setPendingLoad({ filename, content, changes: error.changes ?? [] });
		return false;
	}
	setError(Error({ message: error?.message, issues: error?.issues }, `Couldn't load ${filename}`, undefined, () => setError(null)));
	return false;
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
			setError(Error({ message: `${file.name} couldn't be read. Check that the file still exists and you can open it.` }, `Couldn't load ${file.name}`, undefined, () => setError(null)));
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

export const Validate = async() => {

	try {
		const res = await validateConfig();
		return {"status": res["report"]["status"], "issues": res["report"]["issues"]};

	} catch(err) {
		return err;
	}
};

const saveConfigInternally = async(request) => {
	try {
		const res = await saveConfig(request);
		return res;
	} catch(err) {
		return err;
	}
};

export const Save = async() => {

	const report = await Validate();
	if(report["status"] == ConfigStatusObj.VALID) {

		try {
			const {content, filename, revision} = await exportConfig();
			await Download(content, filename);
			await saveConfigInternally({revision : revision, filename : filename});
			return content;

		} catch(err) {
			return err;
		}
	} else {
		return report["issues"];
	}
};


const Download = async(content, filename) => {

	if ("showSaveFilePicker" in window) {
		const fileHandle = await window.showSaveFilePicker({
			suggestedName: filename,
			types: [
			{
				description: "JSON configuration",
				accept: {
					"application/json": [".json"],
				},
			},
		],
	});

	const writable = await fileHandle.createWritable();
	await writable.write(content);
	await writable.close();

	return;
	}

	// Fallback
	const blob = new Blob(
		[content],
                { type: "application/json" }
	);
	const url = URL.createObjectURL(blob);
	const link = document.createElement("a");
        link.href = url;
	link.download = filename;

	document.body.appendChild(link);
	link.click();
        link.remove();
	URL.revokeObjectURL(url);
};

export const ValidateAndSaveItem = async(editing, draft, setEditing, setLocalError) => {
	const area = editing.area;
	const index = editing.index;
	
	if(index == null) {

		try {
			const res = await handleItem(await addItem(area, draft), setEditing, setLocalError);
			return res;
		} catch(err) {
			return err;
		}

	} else {

		try {
			const res = await handleItem(await replaceItem(area, index, draft), setEditing, setLocalError);
			return res;
		} catch(err) {
			return err;
		}
	}
};

const handleItem = async (res, setEditing, setLocalError) => {

	if(!res.ok) {
		const resJSON = await res.json();
		setErrors(setLocalError, resJSON);

	} else {
		setEditing(null);
		setLocalError(null);
	}

	return res;
};


const setErrors = (setLocalError, resJSON) => {
  setLocalError(resJSON.error ?? { message: "The change was not applied." });   // { message, issues: [{ area, index, field, message }] }
};

export const DeleteItem = async(deleting, setDeleting, setEditing, setLocalError) => {
	try {
		const res = await deleteItem(deleting.area, deleting.index);
		if(!res.ok) {
			const { error } = await res.json();
			setLocalError(error ?? { message: "Nothing was deleted." });
			return false;   // keep the dialog open so the reason stays visible
		}
		setLocalError(null);
		setDeleting(null);
		setEditing(null);
		return true;
	} catch {
		setLocalError({ message: "The server couldn't be reached. Nothing was deleted." });
		return false;
	}
};

export const UpdateTimeSlot = async(vals, setEditing, setLocalError) => {

	try {
    return await handleItem(await updateTimeSlot(vals), setEditing, setLocalError);
	} catch(err) {
		return err;
	}
};

export const UpdateSettings = async(vals, setSettingsError) => {
	try {
		const res = await updateSettings(vals);
		if(!res.ok) {
			const { error } = await res.json();
			setSettingsError(error ?? { message: "The change was not applied." });
			return false;
		}
		setSettingsError(null);
		return true;
	} catch {
		setSettingsError({ message: "The server couldn't be reached. The change was not applied." });
		return false;
	}
};
