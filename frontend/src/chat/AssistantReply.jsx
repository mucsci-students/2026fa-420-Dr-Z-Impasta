/**
 * One answer from Dr. ZImpasta, as specified in docs/ai-assistant.md: the reply text, each
 * action the assistant ran (or would run) with ✓ or ✗, any problems the scheduler library
 * found, whether the configuration was applied and saved, and the follow-ups a reply can
 * ask for: Confirm / Cancel, Save JSON…, and a generation run's progress.
 */
import { useState } from "react";
import { Link } from "react-router";
import Button from "../components/Button.jsx";
import IssueList from "../components/IssueList.jsx";
import Spinner from "../components/Spinner.jsx";
import { plural } from "../format.js";
import { useAppState } from "../state/appStateContext.js";
import { Save } from "../state/EventHandlers.js";

/** A reply. `onConfirm(token, label)` approves a pending action; `busy` while one is sent. */
export default function AssistantReply({ reply, onConfirm, busy }) {
  const { state, refresh } = useAppState();
  const [decision, setDecision] = useState(null); // "confirmed" | "cancelled"
  const [save, setSave] = useState(null); // { status: "saving" | "saved" | "cancelled" | "invalid" | "failed", ... }

  const changed = reply.config.changed;
  // Saved once the app's saved revision reaches this reply's revision (by this reply's
  // Save JSON…, the editor's button, or a later save), so the chip stays true over time.
  const savedRevision = state?.config?.saved_revision;
  const saved =
    typeof reply.config.revision === "number" && typeof savedRevision === "number"
      ? savedRevision >= reply.config.revision
      : !reply.config.dirty;

  async function handleSave() {
    setSave({ status: "saving" });
    const result = await Save(); // the editor's own save: validate, export, save dialog, mark saved
    if (typeof result === "string") setSave({ status: "saved" });
    else if (result?.name === "AbortError") setSave({ status: "cancelled" });
    else if (Array.isArray(result)) setSave({ status: "invalid", issues: result });
    else setSave({ status: "failed", message: result?.message ?? "The file couldn't be written." });
    await refresh();
  }

  return (
    <div className="assistant-reply">
      {reply.demo && <span className="assistant-reply__demo">Demo</span>}
      {reply.reply && <p className="assistant-reply__text">{reply.reply}</p>}

      {reply.actions.length > 0 && (
        <ul className="assistant-actions" aria-label="Actions">
          {reply.actions.map((action, position) => (
            <li
              key={position}
              className={`assistant-actions__item assistant-actions__item--${actionState(reply, action)}`}
            >
              <span className="assistant-actions__mark" aria-hidden="true">
                {action.ok ? (reply.outcome === "needs_confirmation" ? "?" : "✓") : "✗"}
              </span>
              <span>
                <span className="visually-hidden">{actionLabel(reply, action)}: </span>
                {action.summary}
                {action.error?.message && (
                  <span className="assistant-actions__error">{action.error.message}</span>
                )}
              </span>
            </li>
          ))}
        </ul>
      )}

      <IssueList issues={reply.issues} />

      {changed && (
        <p className="assistant-reply__status">
          {saved ? (
            <span className="assistant-chip assistant-chip--saved">Applied and saved</span>
          ) : (
            <span className="assistant-chip assistant-chip--applied">
              Applied · not saved to a file yet
            </span>
          )}
          <Link to="/editor">Open the Configuration Editor</Link>
        </p>
      )}

      {reply.confirmation && (
        <div className="assistant-confirm">
          <p className="assistant-confirm__question">{reply.confirmation.question}</p>
          {reply.confirmation.details?.length > 0 && (
            <ul className="assistant-confirm__details">
              {reply.confirmation.details.map((detail) => (
                <li key={detail}>{detail}</li>
              ))}
            </ul>
          )}
          {decision === null ? (
            <div className="assistant-reply__buttons">
              <Button
                variant="danger"
                size="sm"
                disabled={busy}
                onClick={() => {
                  setDecision("confirmed");
                  onConfirm(
                    reply.confirmation.token,
                    reply.confirmation.confirm_label || "Confirm",
                  );
                }}
              >
                {reply.confirmation.confirm_label || "Confirm"}
              </Button>
              <Button size="sm" disabled={busy} onClick={() => setDecision("cancelled")}>
                Cancel
              </Button>
            </div>
          ) : (
            <p className="assistant-reply__note">
              {decision === "confirmed" ? "Confirmed." : "Cancelled. Nothing was changed."}
            </p>
          )}
        </div>
      )}

      {reply.save_requested && (
        <div className="assistant-reply__follow-up">
          {save?.status === "saved" ? (
            <p className="assistant-reply__note">
              Saved{state?.config?.name ? ` as ${state.config.name}` : ""}.
            </p>
          ) : (
            <Button
              size="sm"
              variant="primary"
              busy={save?.status === "saving"}
              onClick={handleSave}
            >
              Save JSON…
            </Button>
          )}
          {save?.status === "cancelled" && (
            <p className="assistant-reply__note">Save cancelled. Nothing was written.</p>
          )}
          {save?.status === "invalid" && (
            <>
              <p className="assistant-reply__note">
                Can't save yet: the configuration isn't valid.
              </p>
              <IssueList issues={save.issues} />
            </>
          )}
          {save?.status === "failed" && (
            <p className="assistant-reply__note">Couldn't save: {save.message}</p>
          )}
        </div>
      )}

      {reply.generation_started && <GenerationProgress generation={state?.generation} />}
    </div>
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

/** "done", "failed", or "pending" (waiting for confirmation), for styling. */
function actionState(reply, action) {
  if (!action.ok) return "failed";
  return reply.outcome === "needs_confirmation" ? "pending" : "done";
}

function actionLabel(reply, action) {
  return { done: "Done", failed: "Failed", pending: "Waiting for your confirmation" }[
    actionState(reply, action)
  ];
}
