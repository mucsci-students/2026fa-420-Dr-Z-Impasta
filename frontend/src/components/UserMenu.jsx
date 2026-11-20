import { useEffect, useRef, useState } from "react";
import SignInDialog from "./dialogs/SignInDialog.jsx";
import AddStateDialog from "./dialogs/AddStateDialog";
import Button from "./Button.jsx";
import Dialog from "./dialogs/Dialog.jsx";
import ErrorMessage from "./ErrorMessage.jsx";
import Field from "./Field.jsx";
import { api } from "../api/client.js";
import { useAppState } from "../state/appStateContext.js";
import { useAction } from "../state/useAction.js";
import { isLoggedIn } from "../state/eventHandlers.js";
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
    const [savedStates, setSavedStates] = useState([]);
    const [confirmingDeleteId, setConfirmingDeleteId] = useState(null);
    const [renamingState, setRenamingState] = useState(null);
    const [newStateName, setNewStateName] = useState("");
    const menuRef = useRef(null);
    const deleteState = useAction(async (id) => {
        const { states } = await api.states.remove(id);
        setSavedStates(states);
    });
    const handleDeleteClick = async (id) => {
        if (confirmingDeleteId !== id) {
            setConfirmingDeleteId(id);
            return;
        }

        const result = await deleteState.run(id);
        if (result.ok) setConfirmingDeleteId(null);
    };
    const renameState = useAction(async (id, newName) => {
        const { states } = await api.states.rename(id, newName);
        setSavedStates(states);
    });
    const loadStates = useAction(async () => {
        const { states } = await api.states.list();
        setSavedStates(states);
    });
    const normalizedStateName = newStateName.trim().replace(/\s+/g, " ");
    const stateNameTaken = savedStates.some((savedState) =>
        savedState.id !== renamingState?.id && savedState.name === normalizedStateName
    );
    const stateNameValid =
        normalizedStateName.length > 0 &&
        normalizedStateName.length <= 32 &&
        !stateNameTaken;
    const stateNameError = normalizedStateName.length === 0
        ? (newStateName.length > 0 ? "A state name is required." : null)
        : normalizedStateName.length > 32
            ? "State names must be 32 characters or fewer."
            : stateNameTaken
                ? "You already have a state with this name."
                : null;

    const openRenameDialog = (savedState) => {
        renameState.clearError();
        setRenamingState(savedState);
        setNewStateName(savedState.name);
    };

    const closeRenameDialog = () => {
        setRenamingState(null);
        renameState.clearError();
    };

    const confirmRename = async (event) => {
        event.preventDefault();
        if (!renamingState || !stateNameValid) return;

        const result = await renameState.run(renamingState.id, normalizedStateName);
        if (result.ok) setRenamingState(null);
    };

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
                    <h3 className="card_title">{state?.account?.user?.username ?? "Guest User"}</h3>

                    <div className="state-buttons">
                        {savedStates.map((savedState) => (
                            <div
                                className={`state-button${savedState.current ? " state-button--active" : ""}`}
                                key={savedState.id}
                            >
                                <span className="state-button__name">
                                    {savedState.name}
                                </span>
                                <Button onClick={() => openRenameDialog(savedState)}>
                                    Edit
                                </Button>
                                <Button
                                    variant="danger"
                                    busy={deleteState.busy}
                                    onClick={() => handleDeleteClick(savedState.id)}
                                >
                                    {confirmingDeleteId === savedState.id ? "Confirm" : "Delete"}
                                </Button>
                            </div>
                        ))}
                    </div>

                    <Button onClick={async () => { await checkLoggedIn(setSignInOpen, setAddStateOpen) }}>
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
                            Sign in
                        </Button>
                    )}
                    <ErrorMessage
                        error={signOut.error}
                        title="Couldn't sign out"
                        onDismiss={signOut.clearError}
                    />
                    <ErrorMessage
                        error={deleteState.error}
                        title="Couldn't delete state"
                        onDismiss={deleteState.clearError}
                    />
                    <ErrorMessage
                        error={loadStates.error}
                        title="Couldn't load states"
                        onDismiss={loadStates.clearError}
                    />
                </div>
            )}
            <SignInDialog
                open={signInOpen}
                onClose={() => setSignInOpen(false)}
                mode="signin"
                addStates={loadStates.run}
                setButtons={setSavedStates}
            />

            <SignInDialog
                open={signUpOpen}
                onClose={() => setSignUpOpen(false)}
                mode="signup"
                addStates={loadStates.run}
                setButtons={setSavedStates}
            />

            <AddStateDialog
                open={addStateOpen}
                onClose={() => setAddStateOpen(false)}
                onFormSubmit={async () => {
                    await loadStates.run();
                    setAddStateOpen(false);
                }}
            />

            <Dialog
                open={Boolean(renamingState)}
                title="Rename state"
                onClose={closeRenameDialog}
                className="rename-state-dialog"
                width="min(38ch, calc(100vw - 32px))"
                actions={
                    <>
                        <Button onClick={closeRenameDialog}>
                            Cancel
                        </Button>
                        <Button
                            type="submit"
                            form="rename-state-form"
                            variant="success"
                            busy={renameState.busy}
                            disabled={!stateNameValid}
                        >
                            Confirm
                        </Button>
                    </>
                }
            >
                <form id="rename-state-form" onSubmit={confirmRename}>
                    <Field label="New state name" required error={stateNameError}>
                        <input
                            type="text"
                            name="name"
                            autoComplete="off"
                            data-autofocus
                            maxLength={32}
                            value={newStateName}
                            onChange={(event) => setNewStateName(event.target.value)}
                        />
                    </Field>
                </form>
                <ErrorMessage
                    error={renameState.error}
                    title="Couldn't rename state"
                    onDismiss={renameState.clearError}
                />
            </Dialog>

        </div>
    );
};

const checkLoggedIn = async (setSignInOpen, setAddStateOpen) => {
    try {
        const user_status = await isLoggedIn();

        if (!user_status) {
            setSignInOpen(true);
        }

        else
            setAddStateOpen(true);
    }
    catch (error) {
        console.log(error);
    }
};
