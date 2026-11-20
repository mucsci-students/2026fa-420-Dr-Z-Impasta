import { useState } from "react";
import { createState } from "../../state/eventHandlers.js";
import Button from "../Button.jsx";
import Field from "../Field.jsx";
import Dialog from "./Dialog.jsx";
import CheckboxList from "../../modes/editor/CheckboxList.jsx";


export default function AddStateDialog({open, onClose, onFormSubmit}) {
	const [copy, setCopy] = useState(false);
  	const [error, setError] = useState(null);  
	
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
        			// Prevent page reload
        			event.preventDefault();

				const data = new FormData(event.currentTarget);
				const title = data.get("title");
				try {
					const res = await createState(title, copy, setError);
					console.log(res);
					setCopy(false);
					
					if(res == true) {
						onFormSubmit(title);
					}
				}
				catch(error) {
					console.log(error);
				}
			
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
				onChange={() => setCopy(true)}
				error=""
				/>
			</form>
		</Dialog>
	);
}


