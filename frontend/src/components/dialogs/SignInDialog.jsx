import { useState } from "react";
import Button from "../Button.jsx";
import Dialog from "./Dialog.jsx";
import Field from "../Field.jsx";
import { authenticateUser, createUser } from "../../state/eventHandlers.js";

/**
 * Collects a username and password in a modal. The form submit handler is the integration
 * point for backend authentication; each input's `name` is its FormData key.
 */
export default function SignInDialog({ open, onClose, mode = "signin" }) {
  const [message, setMessage] = useState("");
  const [credentialsValid, setCredentialsValid] = useState(true);
  const [usernameValue, setUsernameValue] = useState("");
  const [passwordValue, setPasswordValue] = useState("");
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
  };

  return (
    <Dialog
      open={open}
      title={title}
      onClose={close}
      className="sign-in-dialog"
      width="min(38ch, calc(100vw - 32px))"
      actions={
        <Button type="submit" form="sign-in-form" variant="primary">
          {title}
        </Button>
      }
    >
      <form
        id="sign-in-form"
        className="sign-in-form"
        onSubmit={async (event) => {
          event.preventDefault();
          const data = new FormData(event.currentTarget);
          const username = data.get("username");
          const password = data.get("password");
          const result = isSignUp
            ? await createUser(username, password)
            : await authenticateUser(username, password);
          const successful = result === true;
          setCredentialsValid(successful);

          if (!successful) {
            if (result?.code === "accounts_unavailable") {
              setMessage(
                'Accounts are unavailable, so sign-in and account creation will not work. Read the "Accounts and saved states" section in README to configure them.',
              );
            } else {
              setMessage(
                isSignUp ? result?.message || "Could not create account." : "Invalid login.",
              );
            }
          } else {
            close();
          }
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
