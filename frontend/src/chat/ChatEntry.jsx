/**
 * One entry of the chat transcript (docs/assistant.md): what the user typed, Dr. ZImpasta's
 * reply, an action's outcome (✓ done, ✗ failed, ? waiting for you), or a notice from the
 * app. An action waiting for the user shows Confirm / Cancel, or Save JSON… / Cancel.
 */
import { useState } from "react";
import { Link } from "react-router";
import Button from "../components/Button.jsx";
import IssueList from "../components/IssueList.jsx";
import Spinner from "../components/Spinner.jsx";
import { plural } from "../format.js";
import { useAppState } from "../state/appStateContext.js";
import { Save } from "../state/eventHandlers.js";

/**
 * `latestEdit` / `latestRun`: this is the newest change to the configuration / the newest
 * generation started from the chat, so it shows whether that's saved / how the run is going.
 * `onAnswer(pendingId, answer)` answers a pending action; `busy` while a request runs.
 */
export default function ChatEntry({ entry, latestEdit, latestRun, busy, onAnswer }) {
  if (entry.role === "user" || entry.role === "assistant") {
    return (
      <div className={`chat-message chat-message--${entry.role}`}>
        <span className="visually-hidden">
          {entry.role === "user" ? "You:" : "Dr. ZImpasta:"}
        </span>
        {entry.text}
      </div>
    );
  }
  if (entry.role === "notice") {
    return (
      <p className={`chat-notice${entry.error ? " chat-notice--failed" : ""}`}>{entry.text}</p>
    );
  }
  return (
    <ToolEntry
      entry={entry}
      latestEdit={latestEdit}
      latestRun={latestRun}
      busy={busy}
      onAnswer={onAnswer}
    />
  );
}

const MARKS = { done: "✓", failed: "✗", waiting: "?", settled: "?" };
const LABELS = {
  done: "Done",
  failed: "Failed",
  waiting: "Waiting for you",
  settled: "Answered",
};

/** An action the assistant ran, written from the tool's actual result. */
function ToolEntry({ entry, latestEdit, latestRun, busy, onAnswer }) {
  const { state } = useAppState();
  const result = entry.result ?? { status: "failed" };
  const pending = entry.pending;
  const waiting = pending?.state === "waiting";
  const mark = result.status === "waiting" && !waiting ? "settled" : result.status;
  const error = result.error ?? entry.error;
  const done = result.status === "done";

  return (
    <div
      className={`chat-message chat-message--assistant chat-message--tool${
        result.status === "failed" ? " chat-message--failed" : ""
      }${waiting ? " chat-message--confirm" : ""}`}
    >
      <div className="assistant-reply">
        <p className={`assistant-actions__item assistant-actions__item--${mark}`}>
          <span className="assistant-actions__mark" aria-hidden="true">
            {MARKS[mark] ?? "?"}
          </span>
          <span>
            <span className="visually-hidden">{LABELS[mark]}: </span>
            {entry.text}
            {error?.message && error.message !== entry.text && (
              <span className="assistant-actions__error">{error.message}</span>
            )}
          </span>
        </p>

        <IssueList issues={error?.issues} />

        {pending && <PendingAction pending={pending} busy={busy} onAnswer={onAnswer} />}

        {latestEdit && done && <SavedStatus config={state?.config} />}

        {latestRun && done && <GenerationProgress generation={state?.generation} />}
      </div>
    </div>
  );
}

const SETTLED = {
  confirmed: "Confirmed.",
  cancelled: "Cancelled.",
  saved: "Saved.",
  expired: "Expired: the configuration changed first.",
};

/** What a pending action needs from the user, or how it was answered. */
function PendingAction({ pending, busy, onAnswer }) {
  const { refresh } = useAppState();
  const [save, setSave] = useState(null); // { status: "saving" } or { status: "failed", error }

  if (pending.state !== "waiting") {
    return <p className="assistant-reply__note">{SETTLED[pending.state] ?? pending.state}</p>;
  }

  /** The editor's own save (validate, export, save dialog, mark saved), then tell the chat. */
  async function handleSave() {
    setSave({ status: "saving" });
    let saved;
    try {
      saved = await Save();
    } catch (error) {
      setSave({ status: "failed", error });
      return;
    }
    setSave(null);
    if (!saved) {
      onAnswer(pending.id, "cancel"); // the user closed the save dialog
      return;
    }
    await refresh().catch(() => {});
    onAnswer(pending.id, "saved");
  }

  const isSave = pending.kind === "save";
  return (
    <div className="assistant-confirm">
      {pending.details?.length > 0 && (
        <ul className="assistant-confirm__details">
          {pending.details.map((detail) => (
            <li key={detail}>{detail}</li>
          ))}
        </ul>
      )}
      <div className="assistant-reply__buttons">
        {isSave ? (
          <Button
            size="sm"
            variant="primary"
            busy={save?.status === "saving"}
            disabled={busy}
            onClick={handleSave}
          >
            Save JSON…
          </Button>
        ) : (
          <Button
            size="sm"
            variant="danger"
            disabled={busy}
            onClick={() => onAnswer(pending.id, "confirm")}
          >
            Confirm
          </Button>
        )}
        <Button
          size="sm"
          disabled={busy || save?.status === "saving"}
          onClick={() => onAnswer(pending.id, "cancel")}
        >
          Cancel
        </Button>
      </div>
      {save?.status === "failed" &&
        (save.error.issues?.length > 0 ? (
          <>
            <p className="assistant-reply__note">Can't save yet: the configuration isn't valid.</p>
            <IssueList issues={save.error.issues} />
          </>
        ) : (
          <p className="assistant-reply__note">
            Couldn't save: {save.error.message || "The file couldn't be written."}
          </p>
        ))}
    </div>
  );
}

/** Whether the newest change is saved to a file yet, following the app state. */
function SavedStatus({ config }) {
  if (!config) return null;
  return (
    <p className="assistant-reply__status">
      {config.dirty ? (
        <span className="assistant-chip assistant-chip--applied">
          Applied · not saved to a file yet
        </span>
      ) : (
        <span className="assistant-chip assistant-chip--saved">Applied and saved</span>
      )}
      <Link to="/editor">Open the Configuration Editor</Link>
    </p>
  );
}

/** A run started from the chat, followed through the app state the header already polls. */
function GenerationProgress({ generation }) {
  if (!generation) return null;
  if (generation.running) {
    const limit = generation.settings?.limit;
    return (
      <p className="assistant-reply__follow-up assistant-reply__note">
        <Spinner size="sm" label="" />
        Generating… {generation.found}
        {limit ? ` of ${limit}` : ""} found.
      </p>
    );
  }
  return (
    <div className="assistant-reply__follow-up">
      <p className="assistant-reply__note">{generation.message}</p>
      {generation.state === "succeeded" && generation.found > 0 && (
        <Link className="btn btn--primary btn--sm" to="/viewer">
          View {plural(generation.found, "schedule")}
        </Link>
      )}
    </div>
  );
}
