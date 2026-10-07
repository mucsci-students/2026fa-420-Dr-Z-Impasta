import { loadConfiguration, loadEmptyConfig, validateConfig, saveConfig, addItem, replaceItem, deleteItem, updateTimeSlot } from "../components/APICommunication";

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
		//config.status = "valid";
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

// TODO: add UI error handling
export const Validate = async() => {

	try {
		const res = await validateConfig();
		return {"status": res["report"]["status"], "issues": res["report"]["issues"]};

	} catch(err) {
		return err;
	}
};

// TODO: change status on GUI to the green Saved/Valid when the file is saved
export const Save = async() => {

	const report = await Validate();
	if(report["status"] == ConfigStatusObj.VALID) {
		try {
			const {content, filename} = await saveConfig();
			Download(content, filename);
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
	link.download = exported["filename"];

	document.body.appendChild(link);
	link.click();
        link.remove();
	URL.revokeObjectURL(url);
};

// TODO: add a UI for errors
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
		const res = await deleteItem(area, index);
		setDeleting(null);
		setEditing(null);

	} catch(err) {
		//console.log(err);
		return;
	}
};

//TODO: fix
export const UpdateTimeSlot = async(vals) => {

	try {
		const res = await updateTimeSlot(vals);
		const resJSON = await res.json();
		console.log(resJSON);
	} catch(err) {
	}
};
