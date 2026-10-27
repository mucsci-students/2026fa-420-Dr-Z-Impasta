/**
 * "Ask Dr. ZImpasta": a button in the bottom-right corner that slides a chat panel in from
 * the right, covering half the window. The rest of the app stays usable beside it, so you
 * can keep a schedule in view while you ask about it. The conversation is kept by the
 * server, so it survives closing the panel and reloading the page; "New chat" starts over.
 *
 * The panel slides with CSS keyframe animations run step by step ("open", then "closing"
 * until the slide-out ends, then "closed", which removes it), because Safari can skip a
 * plain CSS transition when an element is hidden in the same moment.
 *
 * Its left edge can be dragged to resize it, or pushed all the way right to close it
 * (./useResizablePanel.js).
 *
 * Messages go to the AI assistant's API (`/api/chat`, docs/assistant.md) through
 * ./useChat.js, and each transcript entry is drawn by ChatEntry. After every request the
 * app state is refreshed, so the Configuration Editor and Schedule Viewer catch up.
 */
import { useEffect, useId, useRef, useState } from "react";
import Button from "../components/Button.jsx";
import { Farfalle } from "../components/PastaMarks.jsx";
import ChatEntry from "./ChatEntry.jsx";
import { MAX_MESSAGE_LENGTH, useChat } from "./useChat.js";
import { useResizablePanel } from "./useResizablePanel.js";
import "./chat.css";

/** Longest the slide-out can take; after this the panel is removed even if the browser
 * never reports the animation's end. Keep it a little above the CSS duration. */
const CLOSE_FALLBACK_MS = 400;

/** How long the launcher shows just the logo before "Ask Dr. ZImpasta" unfurls. */
const UNFURL_DELAY_MS = 600;

/** Example requests for things the assistant's tools can do (docs/assistant.md). */
const SUGGESTIONS = [
  "How many rooms are there?",
  "Add a room called Roddy 150 with 30 seats",
  "Is the configuration valid?",
  "Generate 3 schedules",
];

/** Tools that change the configuration, and the one that starts generation. */
const EDIT_TOOLS = new Set(["edit_configuration", "new_configuration"]);
const RUN_TOOL = "generate_schedules";

/** A small "+" for the New chat button. */
function PlusIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
      <path d="M6 1.5v9M1.5 6h9" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

/** The launcher button and the slide-in chat panel. */
export default function ChatAssistant() {
  const [phase, setPhase] = useState("closed"); // "closed" | "open" | "closing"
  const [draft, setDraft] = useState("");
  const chat = useChat();
  const [expanded, setExpanded] = useState(false); // the launcher shows its label, not just the logo

  const launcherRef = useRef(null);
  const panelRef = useRef(null);
  const inputRef = useRef(null);
  const listRef = useRef(null);
  const panelId = useId();
  const titleId = useId();

  const open = phase === "open";
  const resize = useResizablePanel(panelRef, closePanel);
  const launcherHidden = open; // it comes back as soon as the panel starts sliding out

  // Opening puts the cursor in the message box; closing gives focus back to the button.
  useEffect(() => {
    if (phase === "open") inputRef.current?.focus();
    if (phase === "closing") launcherRef.current?.focus();
  }, [phase]);

  // Remove the panel once it has slid out, even if the animation's end is never reported.
  useEffect(() => {
    if (phase !== "closing") return undefined;
    const timer = setTimeout(
      () => setPhase((now) => (now === "closing" ? "closed" : now)),
      CLOSE_FALLBACK_MS,
    );
    return () => clearTimeout(timer);
  }, [phase]);

  // Whenever the launcher is showing (on page load, and each time the panel closes), it
  // appears as the logo and then unfurls into "Ask Dr. ZImpasta".
  useEffect(() => {
    if (launcherHidden) return undefined;
    const timer = setTimeout(() => setExpanded(true), UNFURL_DELAY_MS);
    return () => clearTimeout(timer);
  }, [launcherHidden]);

  /** Open the panel; the launcher folds back into the logo as it steps aside. */
  function openPanel() {
    resize.settle();
    setExpanded(false);
    setPhase("open");
  }

  /** Slide the panel out; it is removed when the slide-out ends. */
  function closePanel() {
    setPhase((now) => (now === "open" ? "closing" : now));
  }

  /** The slide-out finished: remove the panel. */
  function handleAnimationEnd(event) {
    if (event.target === event.currentTarget && event.animationName === "chat-slide-out") {
      setPhase("closed");
    }
  }

  const { entries, outgoing, busy, available } = chat;
  const empty = entries.length === 0 && outgoing === null;
  const canSend = available && !busy;

  // Keep the newest message in view, including when the panel opens again.
  useEffect(() => {
    const list = listRef.current;
    if (list) list.scrollTop = list.scrollHeight;
  }, [entries, outgoing, busy, chat.error, phase]);

  // The newest change to the configuration and the newest run, which show live status.
  const latestEdit = entries.findLast((entry) => EDIT_TOOLS.has(entry.tool))?.id;
  const latestRun = entries.findLast((entry) => entry.tool === RUN_TOOL)?.id;

  /** Send what's in the message box (or a suggestion). If it can't be sent, it goes back. */
  async function send(text) {
    const message = text.trim();
    if (!message || !canSend) return;
    setDraft("");
    const sent = await chat.send(message);
    if (!sent) setDraft((current) => current || message);
    inputRef.current?.focus();
  }

  /** Start over: the server clears the transcript; back to the welcome screen. */
  async function newChat() {
    setDraft("");
    await chat.clear();
    inputRef.current?.focus();
  }

  /** Enter sends; Shift+Enter starts a new line. */
  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      send(draft);
    }
  }

  return (
    <>
      <button
        ref={launcherRef}
        type="button"
        className={`chat-launcher${expanded ? " chat-launcher--expanded" : ""}${
          launcherHidden ? " chat-launcher--hidden" : ""
        }`}
        aria-expanded={open}
        aria-controls={phase === "closed" ? undefined : panelId}
        onClick={openPanel}
      >
        <Farfalle size={18} className="chat-launcher__mark" />
        <span className="chat-launcher__label-wrap">
          <span className="chat-launcher__label">
            <span className="chat-launcher__text">Ask Dr. ZImpasta</span>
          </span>
        </span>
      </button>

      {phase !== "closed" && (
        <aside
          id={panelId}
          ref={panelRef}
          className={`chat-panel chat-panel--${phase}${resize.dragging ? " chat-panel--dragging" : ""}`}
          style={resize.style}
          aria-labelledby={titleId}
          onKeyDown={(event) => event.key === "Escape" && closePanel()}
          onAnimationEnd={handleAnimationEnd}
        >
          <div className="chat-panel__resize" {...resize.handleProps} />
          <header className="chat-panel__header">
            <div>
              <h2 id={titleId} className="chat-panel__title">
                Ask Dr. ZImpasta
              </h2>
              <p className="chat-panel__subtitle">
                Change the configuration, validate, save, or generate schedules
              </p>
            </div>
            <div className="chat-panel__actions">
              <Button
                size="sm"
                onClick={newChat}
                disabled={busy || (empty && !draft)}
                title="Clear this conversation and start a new one"
              >
                <PlusIcon />
                New chat
              </Button>
              <button
                type="button"
                className="chat-panel__close"
                aria-label="Close chat"
                onClick={closePanel}
              >
                ×
              </button>
            </div>
          </header>

          <div className="chat-panel__messages" ref={listRef} aria-live="polite">
            {empty && (
              <div className="chat-welcome">
                <Farfalle size={32} className="chat-welcome__mark" />
                <p className="chat-welcome__text">
                  Hi, I'm Dr. ZImpasta. Tell me what to change in the configuration, or ask me to
                  validate it, save it, or generate schedules.
                </p>
                {available && (
                  <div className="chat-welcome__suggestions">
                    {SUGGESTIONS.map((suggestion) => (
                      <button
                        key={suggestion}
                        type="button"
                        className="chat-suggestion"
                        disabled={!canSend}
                        onClick={() => send(suggestion)}
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}

            {entries.map((entry) => (
              <ChatEntry
                key={entry.id}
                entry={entry}
                latestEdit={entry.id === latestEdit}
                latestRun={entry.id === latestRun}
                busy={busy}
                onAnswer={chat.answer}
              />
            ))}

            {outgoing !== null && (
              <div className="chat-message chat-message--user">
                <span className="visually-hidden">You:</span>
                {outgoing}
              </div>
            )}

            {chat.error && (
              <div className="chat-message chat-message--assistant chat-message--failed">
                <span className="visually-hidden">Dr. ZImpasta:</span>
                Sorry, that didn't work. {chat.error.message}
              </div>
            )}

            {busy && (
              <div className="chat-message chat-message--assistant chat-message--typing">
                <span className="visually-hidden">Dr. ZImpasta is typing</span>
                <span className="chat-dot" aria-hidden="true" />
                <span className="chat-dot" aria-hidden="true" />
                <span className="chat-dot" aria-hidden="true" />
              </div>
            )}
          </div>

          {!available && chat.reason && (
            <p className="chat-unavailable" role="status">
              {chat.reason}
            </p>
          )}

          <form
            className="chat-panel__composer"
            onSubmit={(event) => {
              event.preventDefault();
              send(draft);
            }}
          >
            <textarea
              ref={inputRef}
              className="chat-panel__input"
              rows={1}
              maxLength={MAX_MESSAGE_LENGTH}
              disabled={!available}
              value={draft}
              placeholder="Describe a change, or ask to validate, save, or generate…"
              aria-label="Message to Dr. ZImpasta"
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={handleKeyDown}
            />
            <button type="submit" className="btn btn--primary" disabled={!draft.trim() || !canSend}>
              Send
            </button>
          </form>
        </aside>
      )}
    </>
  );
}
