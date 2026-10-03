import { loadConfiguration, loadEmptyConfig } from "../components/APICommunication";

export const Load = async (event, setLoadingFile) => {
	setLoadingFile(true);
	const file = event.target.files[0];
	if (!file) return;
	try {
		const res = await loadConfiguration(file);

		if (!res.ok) {
			const errorText = await res.text();
			console.log("Server response:", errorText);
			throw new Error(errorText);
		}

		else {
			return res.json();
		}
	} catch (err) {
		return err;
	} finally {
		await new Promise(resolve => setTimeout(resolve, 2000));
		//config.status = "valid";
		setLoadingFile(false);
	}
}

export const Empty_Click = async (setLoadingFile) => {
	setLoadingFile(true);
	try {
		const res = await loadEmptyConfig();
		return res.json();

		} catch (error) {
			return error;
		} finally {
			await new Promise(resolve => setTimeout(resolve, 2000));
			setLoadingFile(false);
		}
}

