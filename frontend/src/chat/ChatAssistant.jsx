/**
 * "Ask Dr. ZImpasta": a button in the bottom-right corner that slides a chat panel in from
 * the right, covering half the window. The rest of the app stays usable beside it, so you
 * can keep a schedule in view while you ask about it. The conversation is kept while the
 * panel is closed (until the page is reloaded).
 *
 * This is the interface. Answers come from askDrZimpasta() in ./assistant.js.
 */
import { useEffect, useId, useRef, useState } from "react";
import { Farfalle } from "../components/PastaMarks.jsx";
import { askDrZimpasta } from "./assistant.js";
import "./chat.css";

const SUGGESTIONS = [
  "Why is CMSC 340 on Tuesday?",
  "Which rooms are free on Friday afternoon?",
  "What do the optimizer options do?",
];

/** The launcher button and the slide-in chat panel. */
export default function ChatAssistant() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([]); // { id, role: "user" | "assistant", text, failed? }
  const [draft, setDraft] = useState("");
  const [waiting, setWaiting] = useState(false);

  const launcherRef = useRef(null);
  const inputRef = useRef(null);
  const listRef = useRef(null);
  const nextId = useRef(1);
  const wasOpen = useRef(false);
  const panelId = useId();
  const titleId = useId();

  // Opening puts the cursor in the message box; closing gives focus back to the button.
  useEffect(() => {
    if (open) inputRef.current?.focus();
    else if (wasOpen.current) launcherRef.current?.focus();
    wasOpen.current = open;
  }, [open]);

  // Keep the newest message in view.
  useEffect(() => {
    const list = listRef.current;
    if (list) list.scrollTop = list.scrollHeight;
  }, [messages, waiting]);

  /** Add a message to the conversation and return the new list. */
  function withMessage(list, role, text, failed = false) {
    return [...list, { id: nextId.current++, role, text, failed }];
  }

  /** Send `text` as a question, then add Dr. ZImpasta's answer (or what went wrong). */
  async function send(text) {
    const question = text.trim();
    if (!question || waiting) return;

    const conversation = withMessage(messages, "user", question);
    setMessages(conversation);
    setDraft("");
    setWaiting(true);
    try {
      const answer = await askDrZimpasta(conversation.map(({ role, text }) => ({ role, text })));
      setMessages((current) => withMessage(current, "assistant", answer));
    } catch (error) {
      setMessages((current) =>
        withMessage(current, "assistant", `Sorry, I couldn't answer that. ${error.message}`, true),
      );
    } finally {
      setWaiting(false);
      inputRef.current?.focus();
    }
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
        className={`chat-launcher${open ? " chat-launcher--hidden" : ""}`}
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen(true)}
      >
        <Farfalle size={18} />
        Ask Dr. ZImpasta
      </button>

      <aside
        id={panelId}
        className={`chat-panel${open ? " chat-panel--open" : ""}`}
        aria-labelledby={titleId}
        inert={!open}
        onKeyDown={(event) => event.key === "Escape" && setOpen(false)}
      >
        <header className="chat-panel__header">
          <div>
            <h2 id={titleId} className="chat-panel__title">
              Ask Dr. ZImpasta
            </h2>
            <p className="chat-panel__subtitle">Questions about your configuration and schedules</p>
          </div>
          <button
            type="button"
            className="chat-panel__close"
            aria-label="Close chat"
            onClick={() => setOpen(false)}
          >
            ×
          </button>
        </header>

        <div className="chat-panel__messages" ref={listRef} aria-live="polite">
          {messages.length === 0 && (
            <div className="chat-welcome">
              <Farfalle size={32} className="chat-welcome__mark" />
              <p className="chat-welcome__text">
                Hi, I'm Dr. ZImpasta. Ask me about your configuration, how a schedule was
                built, or what to change.
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
                message.failed ? " chat-message--failed" : ""
              }`}
            >
              <span className="visually-hidden">
                {message.role === "user" ? "You:" : "Dr. ZImpasta:"}
              </span>
              {message.text}
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
            placeholder="Ask about your schedules…"
            aria-label="Message to Dr. ZImpasta"
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button type="submit" className="btn btn--primary" disabled={!draft.trim() || waiting}>
            Send
          </button>
        </form>
      </aside>
    </>
  );
}
