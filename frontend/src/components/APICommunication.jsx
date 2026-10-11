import {send} from "../api/backend.js";

export const loadConfiguration = async(filename, content, discardChanges = false) => {
	const response = await send("/api/config/load", {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
		},
		body: JSON.stringify({
			filename: filename,
			content: content,
			discard_changes: discardChanges,
		}),
	});
	return response;
	
};

export const loadEmptyConfig = async(content, filename) => {
	const response = await send("/api/config/load_empty", {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
		},
		body: JSON.stringify({
			filename: filename,
			content: content,
		}),
	});
	return response;
};

export const validateConfig = async() => {
	const response = await send("/api/config/validate", {
		method: "POST",
	});
	return response.json();
};

export const saveConfig = async(request) => {
	const response = await send("/api/config/saved", {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
		},
		body: JSON.stringify(request),
	});
	return response.json()
};

export const exportConfig = async() => {

	const response = await send("/api/config/export", {
		method: "GET",
	});

	// The server sends: attachment; filename="sample.json"
	const disposition = response.headers.get("Content-Disposition") ?? "";
	const filename = /filename="?([^"]+)"?/.exec(disposition)?.[1] ?? "configuration.json";
	const content = await response.text();   // the library's JSON, exactly as it should be saved
	const revision = response.headers.get("X-Config-Revision");

	return { "content": content, "filename" : filename, "revision" : revision };
};

export const addItem = async(area, object) => {

	const response = await send(`/api/config/${area}`, {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
		},
		body: JSON.stringify(object),
	});
	return response;
};

export const replaceItem = async(area, index, item) => {

	const response = await send(`/api/config/${area}/${index}`, {
		method: "PUT",
		headers: {
			"Content-Type": "application/json",
		},
		body: JSON.stringify(item),
	});

	return response;
};

export const deleteItem = async(area, index) => {
	
	const response = await send(`/api/config/${area}/${index}`, {
		method: "DELETE",
		headers: {
			"Content-Type": "application/json",
		},
	});
	return response;
};

export const updateTimeSlot = async(values) => {

	const response = await send("/api/config/time-slots", {
		method: "PUT",
		headers: {
			"Content-Type": "application/json",
		},
		body: JSON.stringify(values),
	});
	return response;
};

export const updateSettings = async(values) => {

	const response = await send("/api/config/settings", {
		method: "PUT",
		headers: {
			"Content-Type": "application/json",
		},
		body: JSON.stringify(values),
	});
	return response;
};
