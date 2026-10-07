import { loadConfiguration, loadEmptyConfig, validateConfig, saveConfig, exportConfig, addItem, replaceItem, deleteItem, updateTimeSlot, updateSettings } from "../components/APICommunication";

const ConfigStatusObj = Object.freeze({
	NONE: "none",
	INCOMPLETE: "incomplete",
	VALID: "valid"
});

const Error = (error, title, labels, onDismiss) => {
	return { "error" : error, "title" : title, "labels" : labels, "onDismiss" : onDismiss };
};

export const Load = async(event, setLoadingFile, setError) => {
	setLoadingFile(true);
	const file = event.target.files[0];
	if(!file) return;
	try {
		const res = await loadConfiguration(file);

		if (!res.ok) {	
			const component = Error(res, "Invalid configuration file", res.issues, () => setError(null));
			setError(component);
			return;
		}

		else {
			return res.json();
		}
	} catch(err) {
		return err;
	} finally {
		await new Promise(resolve => setTimeout(resolve, 2000));
		setLoadingFile(false);
	}
};

export const Empty_Click = async(setLoadingFile) => {
	setLoadingFile(true);
	try {
		const res = await loadEmptyConfig();
		return res;

		} catch(error) {
			return error;
		} finally {
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
			Download(content, filename);
			saveConfigInternally({revision : revision, filename : filename});
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
	await writable.write(JSON.stringify(content));
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
	link.download = content;

	document.body.appendChild(link);
	link.click();
        link.remove();
	URL.revokeObjectURL(url);
};

export const ValidateAndSaveItem = async(editing, draft, setEditing, setLocalError) => {
	const area = editing.area;
	const index = editing.index;
	let res = null;

	if(index == null) {

		try {
			res = await addItem(area, draft);
		} catch(err) {
			return err;
		}

	} else {

		try {
			res = await replaceItem(area, index, draft);
		} catch(err) {
			return err;
		}
	}

	handleItem(res, setEditing, setLocalError);
};

const handleItem = async (res, setEditing, setLocalError) => {

	if(!res.ok) {
		const resJSON = await res.json();
		setErrors(setLocalError, resJSON);

	} else {
		setEditing(null);
		setLocalError([]);
	}

	return res;
};


const setErrors = (setLocalError, resJSON) => {
	const errorFields = [];
	for(const [key,value] of Object.entries(resJSON.error.issues)) {
		errorFields.push({"field" : value.field, "message" : value.message});
	}

	setLocalError(errorFields);
};

export const DeleteItem = async(deleting, setDeleting, setEditing) => {
	
	const area = deleting.area;
	const index = deleting.index;

	try {
		await deleteItem(area, index);
		setDeleting(null);
		setEditing(null);

	} catch(err) {
		return err;
	}
};

//TODO: fix UI for invalid data in DayBlocksDialog.jsx
export const UpdateTimeSlot = async(vals, setEditing) => {

	try {
		const res = await updateTimeSlot(vals);
		
		if(res.state.status == ConfigStatusObj.VALID) {
			setEditing(null);
			return res;
		} 

	} catch(err) {
		return err;
	}
};

export const UpdateSettings = async(vals) => {
	
	try {
		const res = await updateSettings(vals);
		return res;
	} catch(err) {
		return err;
	}

};
