import { useEffect, useRef, useState } from "react";
import SignInDialog from "./SignInDialog.jsx";

/**
 * The account menu in the shared header. Outside clicks close the menu, while sign-in
 * opens in its own dialog.
 */
export default function UserMenu() {
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
                    {/* These are placeholders. Render backend projects here and pass each
                        project's stable ID to its click handler so the right project loads. */}
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
                        Sign in
                    </button>
                </div>
            )}
            <SignInDialog open={signInOpen} onClose={() => setSignInOpen(false)} />
        </div>
    );
}