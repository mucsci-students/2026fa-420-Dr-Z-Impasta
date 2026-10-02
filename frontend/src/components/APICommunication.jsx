
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
	return await response;
	
};
