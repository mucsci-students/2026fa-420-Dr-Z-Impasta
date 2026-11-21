import { useState } from "react";
import { addStateAction } from "../../state/eventHandlers.js";
import Button from "../Button.jsx";
import Field from "../Field.jsx";
import Dialog from "./Dialog.jsx";
import CheckboxList from "../../modes/editor/CheckboxList.jsx";


export default function AddStateDialog({open, onClose, onFormSubmit}) {
	const [copy, setCopy] = useState(false);
  	const [error, setError] = useState(null);  
	const [loading, setLoading] = useState(false);


	const close = () => {
		onClose?.();
		setLoading(false);
	};	

	return (
		<Dialog
		open={open}
		title="Add a State"
		onClose={close}
		className="add-state-dialog"
		width="min(38ch, calc(100vw - 32px))"
		actions={
			<Button 
			id={loading ? "loading" : ""}
			type="submit" 
			form="add-state-form" 
			variant="primary"
			onClick={() => setLoading(true) }>
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
				const res = await addStateAction(title, copy, setError);
				
				if(res == true)
					onFormSubmit(true);
				else {
					onFormSubmit(false);
					console.log(error);
				}
				setCopy(false);
				setLoading(false);
			
			}}
			>
				<Field label="Title" required>
					<input type="text" name="title" maxLength={32} />
				</Field>
			
				<CheckboxList 
				legend=""
				options={["Copy Current State?"]}
				value={copy ? ["Copy Current State?"] : []}
				onChange={(values) =>
					setCopy(
						values.includes("Copy Current State?"))
				}
				error=""
				/>
			</form>
		</Dialog>
	);
}


