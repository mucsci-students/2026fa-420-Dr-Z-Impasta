/**
 * The chat's data, from the AI assistant's API (`/api/chat`, see docs/assistant.md).
 *
 * The transcript lives in the Python process, so it survives reloading the tab. This hook
 * keeps a copy and fetches it again whenever the polled app state reports a different last
 * entry (`state.assistant.last_entry`), and after each message, answer, or New chat. While
 * a message is being answered, the actions it runs appear as the poll picks them up.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api/client.js";
import { useAppState } from "../state/appStateContext.js";

/** The server's limit on one message. */
export const MAX_MESSAGE_LENGTH = 4000;

/**
 * `{ entries, outgoing, busy, error, available, reason, send, answer, clear }`.
 *
 * - `outgoing`: the message being sent, until the transcript shows it.
 * - `busy`: a request is running (from here or another tab), so sending waits.
 * - `error`: the ApiError from the last request that couldn't run, or null.
 * - `available` / `reason`: whether the assistant can be used, and if not, why.
 */
export function useChat() {
  const { state, refresh } = useAppState();
  const assistant = state?.assistant ?? null;

  const [entries, setEntries] = useState([]);
  const [outgoing, setOutgoing] = useState(null); // { text, after: id of the last entry before it }
  const [working, setWorking] = useState(false);
  const [error, setError] = useState(null);
  const latest = useRef(0); // numbers transcript fetches, so an older answer can't replace a newer one

  const load = useCallback(() => {
    const ticket = ++latest.current;
    return api.chat.transcript().then(
      (transcript) => {
        if (ticket === latest.current) setEntries(transcript.entries ?? []);
      },
      () => {}, // Left as it is; the next poll tries again.
    );
  }, []);

  // Catch up whenever the server's transcript ends somewhere else than ours. This runs on
  // every poll (`assistant` is a new object each time), so a failed fetch is retried.
  const serverLast = assistant?.last_entry ?? null;
  const localLast = entries.at(-1)?.id ?? null;
  useEffect(() => {
    if (assistant && serverLast !== localLast) load();
  }, [assistant, serverLast, localLast, load]);

  /** Run one request, then bring the transcript and the app state up to date. */
  async function run(request) {
    setWorking(true);
    setError(null);
    let ok = true;
    try {
      await request();
    } catch (failure) {
      setError(failure);
      ok = false;
    }
    await load();
    refresh().catch(() => {});
    setOutgoing(null);
    setWorking(false);
    return ok;
  }

  /** Send a message. Resolves to false if it couldn't be sent (see `error`). */
  function send(text) {
    setOutgoing({ text, after: localLast });
    return run(() => api.chat.send(text));
  }

  /** Answer a pending entry: "confirm" or "cancel", or "saved" or "cancel" for a save. */
  function answer(pendingId, value, filename) {
    return run(() => api.chat.answer(pendingId, value, filename));
  }

  /** New chat: the server forgets the transcript and anything still waiting. */
  function clear() {
    return run(async () => {
      await api.chat.clear();
      latest.current += 1;
      setEntries([]);
    });
  }

  // Once the server's copy shows the message, stop showing our own.
  const echoed = outgoing !== null && entriesAfter(entries, outgoing.after).some(isUser);

  return {
    entries,
    outgoing: echoed ? null : outgoing?.text ?? null,
    busy: working || Boolean(assistant?.busy),
    error,
    available: assistant ? assistant.available : true,
    reason: assistant?.reason ?? null,
    send,
    answer,
    clear,
  };
}

function entriesAfter(entries, id) {
  if (id === null) return entries;
  const position = entries.findIndex((entry) => entry.id === id);
  return position === -1 ? entries : entries.slice(position + 1);
}

function isUser(entry) {
  return entry.role === "user";
}
