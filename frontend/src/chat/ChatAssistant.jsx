/**
 * "Ask Dr. ZImpasta": a button in the bottom-right corner that slides a chat panel in from
 * the right, covering half the window. The rest of the app stays usable beside it, so you
 * can keep a schedule in view while you ask about it. The conversation is kept while the
 * panel is closed (until the page is reloaded); "New chat" starts over.
 *
 * The panel slides with CSS keyframe animations run step by step ("open", then "closing"
 * until the slide-out ends, then "closed", which removes it), because Safari can skip a
 * plain CSS transition when an element is hidden in the same moment.
 *
 * Its left edge can be dragged to resize it, or pushed all the way right to close it
 * (./useResizablePanel.js).
 *
 * Each request is sent on its own (POST /api/assistant, see docs/ai-assistant.md); the
 * conversation shown is for the user, not sent back. Replies are drawn by AssistantReply.
 * After a reply that changed the configuration or started a run, the app state is
 * refreshed right away, so the Configuration Editor and Schedule Viewer catch up.
 */
import { useEffect, useId, useRef, useState } from "react";
import Button from "../components/Button.jsx";
import { Farfalle } from "../components/PastaMarks.jsx";
import { useAppState } from "../state/appStateContext.js";
import { askDrZimpasta } from "./assistant.js";
import AssistantReply from "./AssistantReply.jsx";
import { useResizablePanel } from "./useResizablePanel.js";
import "./chat.css";

/** Longest the slide-out can take; after this the panel is removed even if the browser
 * never reports the animation's end. Keep it a little above the CSS duration. */
const CLOSE_FALLBACK_MS = 400;

/** How long the launcher shows just the logo before "Ask Dr. ZImpasta" unfurls. */
const UNFURL_DELAY_MS = 600;

/** Example requests for things the assistant's tools can do (docs/ai-assistant.md). */
const SUGGESTIONS = [
  "Add a room called Roddy 150 with capacity 30",
  "Validate the configuration",
  "Generate 5 schedules",
  "Save the configuration",
];

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
  // { id, role: "user", text } | { id, role: "assistant", reply } | { id, role: "assistant", text, failed }
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [waiting, setWaiting] = useState(false);
  const [expanded, setExpanded] = useState(false); // the launcher shows its label, not just the logo

  const launcherRef = useRef(null);
  const panelRef = useRef(null);
  const inputRef = useRef(null);
  const listRef = useRef(null);
  const nextId = useRef(1);
  const conversation = useRef(0); // bumped by "New chat", so a late answer can't land in it
  const { refresh } = useAppState();
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

  // Keep the newest message in view, including when the panel opens again.
  useEffect(() => {
    const list = listRef.current;
    if (list) list.scrollTop = list.scrollHeight;
  }, [messages, waiting, phase]);

  /** Add a message to the conversation and return the new list. */
  function withMessage(list, message) {
    return [...list, { id: nextId.current++, ...message }];
  }

  /**
   * Send one request and add Dr. ZImpasta's reply, or what went wrong. `request` is
   * `{ message }` or `{ confirm: token }`; `shown` is what appears as the user's bubble.
   */
  async function ask(request, shown) {
    if (waiting) return;
    const asked = conversation.current;
    setMessages((current) => withMessage(current, { role: "user", text: shown }));
    setWaiting(true);
    let answer;
    try {
      const reply = await askDrZimpasta(request);
      answer = { role: "assistant", reply };
      if (reply.config.changed || reply.generation_started) refresh().catch(() => {});
    } catch (error) {
      answer = {
        role: "assistant",
        text: `Sorry, that didn't work. ${error.message}`,
        failed: true,
      };
    }
    if (asked !== conversation.current) return; // "New chat" was clicked while waiting
    setMessages((current) => withMessage(current, answer));
    setWaiting(false);
    inputRef.current?.focus();
  }

  /** Send what's in the message box (or a suggestion) as a new request. */
  function send(text) {
    const message = text.trim();
    if (!message || waiting) return;
    setDraft("");
    ask({ message }, message);
  }

  /** The user approved what a reply asked about: run exactly that. */
  function confirm(token, label) {
    ask({ confirm: token }, label);
  }

  /** Start over: clear the conversation and go back to the welcome screen. */
  function newChat() {
    conversation.current += 1;
    setMessages([]);
    setDraft("");
    setWaiting(false);
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
                disabled={messages.length === 0 && !draft}
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
            {messages.length === 0 && (
              <div className="chat-welcome">
                <Farfalle size={32} className="chat-welcome__mark" />
                <p className="chat-welcome__text">
                  Hi, I'm Dr. ZImpasta. Tell me what to change in the configuration, or ask me to
                  validate it, save it, or generate schedules.
                </p>
                <div className="chat-welcome__suggestions">
                  {SUGGESTIONS.map((suggestion) => (
                    <button
                      key={suggestion}
                      type="button"
                      className="chat-suggestion"
                      onClick={() => send(suggestion)}
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((message) => (
              <div
                key={message.id}
                className={`chat-message chat-message--${message.role}${
                  message.failed || message.reply?.outcome === "failed"
                    ? " chat-message--failed"
                    : ""
                }${message.reply?.outcome === "needs_confirmation" ? " chat-message--confirm" : ""}`}
              >
                <span className="visually-hidden">
                  {message.role === "user" ? "You:" : "Dr. ZImpasta:"}
                </span>
                {message.reply ? (
                  <AssistantReply reply={message.reply} onConfirm={confirm} busy={waiting} />
                ) : (
                  message.text
                )}
              </div>
            ))}

            {waiting && (
              <div className="chat-message chat-message--assistant chat-message--typing">
                <span className="visually-hidden">Dr. ZImpasta is typing</span>
                <span className="chat-dot" aria-hidden="true" />
                <span className="chat-dot" aria-hidden="true" />
                <span className="chat-dot" aria-hidden="true" />
              </div>
            )}
          </div>

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
              value={draft}
              placeholder="Describe a change, or ask to validate, save, or generate…"
              aria-label="Message to Dr. ZImpasta"
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={handleKeyDown}
            />
            <button type="submit" className="btn btn--primary" disabled={!draft.trim() || waiting}>
              Send
            </button>
          </form>
        </aside>
      )}
    </>
  );
}
