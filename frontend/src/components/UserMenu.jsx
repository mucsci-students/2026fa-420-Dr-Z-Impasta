import { useEffect, useRef, useState } from "react";
import SignInDialog from "./SignInDialog.jsx";

/**
 * The account menu in the shared header. Outside clicks close the menu, while sign-in
 * opens in its own dialog.
 */
export default function UserMenu() {
    // AI_CONTEXT: USER_MENU_STATE — `open` controls the account popup; `signInOpen` controls
    // the sign-in dialog; `menuRef` lets the outside-click handler identify popup clicks.
    const [open, setOpen] = useState(false);
    const [signInOpen, setSignInOpen] = useState(false);
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
            <button
                type="button"
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
            </button>

            {open && (
                <div className="user-menu__popup">
                    <p>Guest User</p>
                    {/* AI_CONTEXT: ACCOUNT_PROJECT_SELECTION — These are placeholders with no
                        selection handler yet. Render backend projects here and pass each
                        project's stable ID (not its display name) to the click handler. */}
                    <button type="button">Project 1</button>
                    <button type="button">Project 2</button>
                    <button type="button">Project 3</button>
                    <button type="button">Add Project</button>
                    <button
                        type="button"
                        onClick={() => {
                            setOpen(false);
                            setSignInOpen(true);
                        }}
                    >
                        {/* AI_CONTEXT: SIGN_IN_DIALOG_TRIGGER — This opens SignInDialog below. */}
                        Sign in
                    </button>
                </div>
            )}
            <SignInDialog open={signInOpen} onClose={() => setSignInOpen(false)} />
        </div>
    );
}