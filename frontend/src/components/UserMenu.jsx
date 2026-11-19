import { useEffect, useRef, useState } from "react";
import SignInDialog from "./dialogs/SignInDialog.jsx";
import AddStateDialog from "./dialogs/AddStateDialog";
import Button from "./Button.jsx";
import ErrorMessage from "./ErrorMessage.jsx";
import { api } from "../api/client.js";
import { useAppState } from "../state/appStateContext.js";
import { useAction } from "../state/useAction.js";

/**
 * The account menu in the shared header. Outside clicks close the menu, while sign-in
 * opens in its own dialog.
 */
export default function UserMenu() {
    const { state, refresh } = useAppState();
    const signedIn = Boolean(state?.account?.user);
    const signOut = useAction(async () => {
        await api.account.logOut();
        await refresh();
    });
    // AI_CONTEXT: USER_MENU_STATE — `open` controls the account popup; `signInOpen` controls
    // the sign-in dialog; `menuRef` lets the outside-click handler identify popup clicks.
    const [open, setOpen] = useState(false);
    const [signInOpen, setSignInOpen] = useState(false);
    const [signUpOpen, setSignUpOpen] = useState(false);
    const [addStateOpen, setAddStateOpen] = useState(false);
    const [formInfo, setFormInfo] = useState({});
    const [buttons, setButtons] = useState([]);
    const menuRef = useRef(null);

    useEffect(() => {
        if (!open) return;

        function handlePointerDown(event) {
            if (!menuRef.current?.contains(event.target)) {
                setOpen(false);
            }
        }

        document.addEventListener("pointerdown", handlePointerDown);
        return () => document.removeEventListener("pointerdown", handlePointerDown);
    }, [open]);

    return (
        <div className="user-menu" ref={menuRef}>
            <Button
                className="user-menu__button"
                aria-label="Account"
                aria-expanded={open}
                onClick={() => setOpen((isOpen) => !isOpen)}
            >
                <svg
                    className="user-menu__avatar"
                    viewBox="0 0 24 24"
                    aria-hidden="true"
                >
                    <circle cx="12" cy="8" r="4" fill="currentColor" />
                    <path d="M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7H4z" fill="currentColor" />
                </svg>
            </Button>

            {open && (
                <div className="user-menu__popup">
                    <p>{state?.account?.user?.username ?? "Guest User"}</p>

                    <div className="state-buttons">
                        {buttons.map(() => (
                            <Button>"State"</Button>

                        ))}
                    </div>

                    <Button onClick={() => { setAddStateOpen(true) }}>
                        Add State
                    </Button>



                    {!signedIn && (
                        <Button
                            onClick={() => {
                                setOpen(false);
                                setSignUpOpen(true);
                            }}
                        >
                            Create account
                        </Button>
                    )}

                    {signedIn ? (
                        <Button
                            busy={signOut.busy}
                            onClick={async () => {
                                const result = await signOut.run();
                                if (result.ok) setOpen(false);
                            }}
                        >
                            Sign out
                        </Button>
                    ) : (
                        <Button
                            onClick={() => {
                                setOpen(false);
                                setSignInOpen(true);
                            }}
                        >
                            {/* AI_CONTEXT: SIGN_IN_DIALOG_TRIGGER — This opens SignInDialog below. */}
                            Sign in
                        </Button>
                    )}
                    <ErrorMessage
                        error={signOut.error}
                        title="Couldn't sign out"
                        onDismiss={signOut.clearError}
                    />
                </div>
            )}
            <SignInDialog open={signInOpen} onClose={() => setSignInOpen(false)} mode="signin" />
            <SignInDialog open={signUpOpen} onClose={() => setSignUpOpen(false)} mode="signup" />

            <AddStateDialog
                open={addStateOpen}
                onClose={() => setAddStateOpen(false)}
                onFormSubmit={(info) => {
                    setFormInfo(info);
                    console.log(formInfo);
                    const newButton = createStateButton(info);
                    setButtons(prevButtons => [...prevButtons, newButton]);
                }}
            />
        </div>
    );
}

const createStateButton = (data) => {
    console.log(data);
    return (
        <Button>
            getattr(data, "name", "State")
        </Button>
    );
};
