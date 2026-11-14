import Button from "../Button.jsx";
import Field from "../Field.jsx";
import Dialog from "./Dialog.jsx";

export default function AddProjectDialog({open, onClose}) {
	return (
		<Dialog
		open={open}
		title="Add a Project"
		onClose={onClose}
		className="add-project-dialog"
		width="min(38ch, calc(100vw - 32px))"
		actions={
			<Button type="submit" form="add-project-form" variant="primary">
			Create Project
			</Button>
		}
		>
			<form
			id="add-project-form"
			className="add-project-form"
			onSubmit={() => {
			}}
			>
				<Field label="Title" required>
					<input type="text" name="title" />
				</Field>
			</form>
		</Dialog>
	);
}
