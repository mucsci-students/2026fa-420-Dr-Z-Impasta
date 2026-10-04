import { loadConfiguration, loadEmptyConfig, validateConfig, saveConfig } from "../components/APICommunication";

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


const Download = async (content, filename) => {

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

