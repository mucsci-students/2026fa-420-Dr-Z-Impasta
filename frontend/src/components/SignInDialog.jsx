import { useState } from "react";
import Button from "./Button.jsx";
import Dialog from "./Dialog.jsx";
import Field from "./Field.jsx";

/**
 * Collects a username and password in a modal. The form submit handler is the integration
 * point for backend authentication; each input's `name` is its FormData key.
 */
export default function SignInDialog({ open, onClose }) {
  const [message, setMessage] = useState("");
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
        onSubmit={(event) => {
          event.preventDefault();
          // Replace this placeholder with the auth request. Read "username" and "password"
          // from FormData and send them in the request body, not in a URL or logs.
          setMessage("Authentication is not connected yet.");
        }}
      >
        <Field label="Username" required>
          <input type="text" name="username" autoComplete="username" data-autofocus />
        </Field>
        <Field label="Password" required>
          <input type="password" name="password" autoComplete="current-password" />
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
