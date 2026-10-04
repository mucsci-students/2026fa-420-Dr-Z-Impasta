
export const loadConfiguration = async (file) => {
	const content = await file.text();

	const response = await fetch("/api/config/load", {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
		},
		body: JSON.stringify({
			filename: file.name,
			content: content,
			discard_changes: false,
		}),
	});
	return response;
	
};

export const loadEmptyConfig = async() => {
	const response = await fetch("/api/config/load_empty", {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
		},
		body: JSON.stringify({}),
	});
	return response.json();
};

export const validateConfig = async () => {
	const response = await fetch("/api/config/validate", {
		method: "POST",
	});
	return response.json();
};

export const saveConfig = async () => {
	const response = await fetch("api/config/export", {
		method: "GET",
	});

	const filename = response.headers.get("Content-Disposition").split("=")[1];
	const resJSON = await response.json();
	return { "content": resJSON, "filename" : filename.replace(".json", "") };
};
