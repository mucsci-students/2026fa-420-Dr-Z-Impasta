import { useState } from "react";

export default function LoginMenu() {
    const [open, setOpen] = useState(false);

    return (
        <div className="login-menu">
            <button
                type="button"
                className="login-menu__button"
                aria-label="Account"
                aria-expanded={open}
                onClick={() => setOpen((isOpen) => !isOpen)}
            >
                <svg
                    className="login-menu__avatar"
                    viewBox="0 0 24 24"
                    aria-hidden="true"
                >
                    <circle cx="12" cy="8" r="4" fill="currentColor" />
                    <path d="M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7H4z" fill="currentColor" />
                </svg>
            </button>

            {open && (
                <div className="login-menu__popup">
                    <button type="button">Sign in</button>
                </div>
            )}
        </div>
    );
}