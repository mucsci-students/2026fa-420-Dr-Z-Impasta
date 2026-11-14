import { useState } from "react";
import { createState } from "../../state/eventHandlers.js";
import Button from "../Button.jsx";
import Field from "../Field.jsx";
import Dialog from "./Dialog.jsx";
import CheckboxList from "../../modes/editor/CheckboxList.jsx";

export default function AddStateDialog({open, onClose}) {
	const [copy, setCopy] = useState(false);
	const [formInfo, setFormInfo] = useState({});

	return (
		<Dialog
		open={open}
		title="Add a State"
		onClose={onClose}
		className="add-state-dialog"
		width="min(38ch, calc(100vw - 32px))"
		actions={
			<Button type="submit" form="add-state-form" variant="primary">
			Create State
			</Button>
		}
		>
			<form
			id="add-state-form"
			className="add-state-form"
			onSubmit={async (event) => {
				const data = new FormData(event.currentTarget);
				const title = data.get("title");
				const res = await createState(title, copy);
				setCopy(false);
				setFormInfo({title, res});
			
			}}
			>
				<Field label="Title" required>
					<input type="text" name="title" />
				</Field>
			
				{/*TODO: add error handling*/}
				<CheckboxList 
				legend=""
				options={["Copy Current State?"]}
				value={copy ? ["Copy Current State?"] : []}
				onChange={(selected) => setCopy(true)}
				error=""
				/>
			</form>
		</Dialog>
	);
}

export const getFormInfo = () => {
	return formInfo;
};

