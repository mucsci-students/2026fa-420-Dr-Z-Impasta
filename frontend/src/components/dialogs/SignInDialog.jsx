import { useState } from "react";
import Button from "../Button.jsx";
import Dialog from "./Dialog.jsx";
import Field from "../Field.jsx";
import { userSignsSubmit } from "../../state/eventHandlers.js";

/**
 * Collects a username and password in a modal. The form submit handler is the integration
 * point for backend authentication; each input's `name` is its FormData key.
 */
export default function SignInDialog({ open, onClose, mode = "signin", addStates, setButtons }) {
  const [message, setMessage] = useState("");
  const [credentialsValid, setCredentialsValid] = useState(true);
  const [usernameValue, setUsernameValue] = useState("");
  const [passwordValue, setPasswordValue] = useState("");
  const [loading, setLoading] = useState(null);
  const [error, setError] = useState(null);

  const isSignUp = mode === "signup";
  const title = isSignUp ? "Create account" : "Sign in";
  const normalizedUsername = usernameValue.trim().toLowerCase();
  const requirements = [
    {
      label: "Username is 3 to 32 characters",
      met: normalizedUsername.length >= 3 && normalizedUsername.length <= 32,
    },
    {
      label: "Username starts with a letter or number",
      met: /^[a-z0-9]/.test(normalizedUsername),
    },
    {
      label: "Username uses only letters, numbers, dots, dashes, or underscores",
      met: /^[a-z0-9._-]*$/.test(normalizedUsername),
    },
    {
      label: "Password is 8 to 128 characters",
      met: passwordValue.length >= 8 && passwordValue.length <= 128,
    },
  ];

  const close = () => {
    setMessage("");
    setCredentialsValid(true);
    setUsernameValue("");
    setPasswordValue("");
    onClose?.();
    setLoading(false);
  };

  return (
    <Dialog
      open={open}
      title={title}
      onClose={close}
      className="sign-in-dialog"
      width="min(38ch, calc(100vw - 32px))"
      actions={
        <Button 
	      id={loading ? "loading" : ""}
	      type="submit" 
	      form="sign-in-form" 
	      variant="primary"
	      onClick={async() => {setLoading(true);}}>
          {title}
        </Button>
      }
    >
      <form
        id="sign-in-form"
        className="sign-in-form"
        onSubmit={async (event) => {
		const res = await userSignsSubmit(event, setMessage, isSignUp, setError, setCredentialsValid);
		if(res == true) {
			close();
			addStates(setButtons);
		}
		else
			console.log(error);
        }}
      >
        <Field label="Username" required>
          <input
            type="text"
            name="username"
            autoComplete="username"
            data-autofocus
            value={usernameValue}
            onChange={(event) => setUsernameValue(event.target.value)}
            className={!credentialsValid ? "login-error" : ""}
          />
        </Field>
        <Field label="Password" required>
          <input
            type="password"
            name="password"
            autoComplete={isSignUp ? "new-password" : "current-password"}
            value={passwordValue}
            onChange={(event) => setPasswordValue(event.target.value)}
            className={!credentialsValid ? "login-error" : ""}
          />
        </Field>
        {isSignUp && (
          <section className="sign-up-requirements" aria-label="Account requirements">
            <p className="sign-up-requirements__title">Requirements</p>
            <ul className="sign-up-requirements__list">
              {requirements.map(({ label, met }) => (
                <li
                  key={label}
                  className={
                    met ? "sign-up-requirements__item is-met" : "sign-up-requirements__item"
                  }
                  aria-label={`${label}: ${met ? "met" : "not met"}`}
                >
                  <span aria-hidden="true">{met ? "✓" : "•"}</span>
                  <span className="sign-up-requirements__text">{label}</span>
                </li>
              ))}
            </ul>
          </section>
        )}
        {message && (
          <p className="sign-in-form__message" role="status">
            {message}
          </p>
        )}
      </form>
    </Dialog>
  );
}
