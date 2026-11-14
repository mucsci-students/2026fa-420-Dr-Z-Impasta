import { useState } from "react";
import Button from "../Button.jsx";
import Dialog from "./Dialog.jsx";
import Field from "../Field.jsx";
import { authenticateUser } from "../../state/eventHandlers.js";

/**
 * Collects a username and password in a modal. The form submit handler is the integration
 * point for backend authentication; each input's `name` is its FormData key.
 */
export default function SignInDialog({ open, onClose }) {
  const [message, setMessage] = useState("");
	const [loginStatus, setLoginStatus] = useState(true);
  const close = () => {
    setMessage("");
    onClose?.();
  };

  return (
    <Dialog
      open={open}
      title="Sign in"
      onClose={close}
      className="sign-in-dialog"
      width="min(38ch, calc(100vw - 32px))"
      actions={
        <Button type="submit" form="sign-in-form" variant="primary">
          Sign in
        </Button>
      }
    >
      <form
        id="sign-in-form"
        className="sign-in-form"
        onSubmit={async (event) => {
          event.preventDefault();
		const data = new FormData(event.currentTarget);
		const res = await authenticateUser(data.get("username"), data.get("password"))
		setLoginStatus(res);

		if(res == false) {
			setMessage("Invalid login.");
		}
        }}
      >
        <Field label="Username" required>
          <input type="text" name="username" autoComplete="username" data-autofocus className={!loginStatus ? "login-error" : ""}/>
        </Field>
        <Field label="Password" required>
          <input type="password" name="password" autoComplete="current-password" className={!loginStatus ? "login-error" : ""}/>
        </Field>
        {message && (
          <p className="sign-in-form__message" role="status">
            {message}
          </p>
        )}
      </form>
    </Dialog>
  );
}
