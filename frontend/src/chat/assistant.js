/**
 * Talks to the AI assistant: `POST /api/assistant`. The request and reply are specified
 * in docs/ai-assistant.md; the backend half is built from that document.
 *
 * Until the backend route exists, the server answers 404 "There is no such API endpoint".
 * Then demo replies stand in, each marked `demo: true` so the chat labels them, and none of
 * them changes anything. Once the route answers, it's used automatically.
 */
import { api } from "../api/client.js";

/** What every reply has, so the chat can rely on each field being there. */
const EMPTY_REPLY = {
  outcome: "succeeded",
  reply: "",
  actions: [],
  issues: [],
  config: { changed: false, revision: null, dirty: false },
  generation_started: false,
  save_requested: false,
  confirmation: null,
  demo: false,
};

/**
 * Send one request: `{ message }` for a new request, or `{ confirm: token }` to approve the
 * action a previous reply asked about. Resolves to the reply (see docs/ai-assistant.md);
 * rejects with the ApiError when the assistant couldn't run (unavailable, expired token, ...).
 */
export async function askDrZimpasta({ message, confirm }) {
  try {
    return withDefaults(await api.assistant.ask({ message, confirm }));
  } catch (error) {
    if (error?.status === 404 && error?.code === "not_found") {
      return withDefaults(await demoReply({ message, confirm }));
    }
    throw error;
  }
}

function withDefaults(reply) {
  return {
    ...EMPTY_REPLY,
    ...reply,
    config: { ...EMPTY_REPLY.config, ...reply?.config },
    actions: reply?.actions ?? [],
    issues: reply?.issues ?? [],
  };
}

// ------------------------------------------------------------------- demo replies

const DEMO = "This is a demo reply: the assistant isn't connected yet, so nothing was changed.";

/** Stand-in replies that show each kind of answer, for trying the chat before the backend. */
async function demoReply({ message, confirm }) {
  await new Promise((resolve) => setTimeout(resolve, 600));

  if (confirm) {
    return {
      demo: true,
      outcome: "succeeded",
      reply: `${DEMO} With the assistant connected, the confirmed action runs here.`,
      actions: [{ tool: "delete_item", ok: true, summary: "Would have deleted it", error: null }],
    };
  }

  const text = (message ?? "").toLowerCase();
  if (/\b(delete|remove)\b/.test(text)) {
    return {
      demo: true,
      outcome: "needs_confirmation",
      reply: "Deleting can't be undone, so I'll check with you first.",
      actions: [{ tool: "delete_item", ok: true, summary: message, error: null }],
      confirmation: {
        token: "demo",
        question: `${message.replace(/[.?!]+$/, "")}?`,
        details: ["Demo: nothing will actually be deleted."],
        confirm_label: "Delete",
      },
    };
  }
  if (/\bsave\b/.test(text)) {
    return {
      demo: true,
      outcome: "succeeded",
      reply:
        "Ready to save. Click Save JSON… to choose where; it's the same save as the editor's button.",
      actions: [{ tool: "save_configuration", ok: true, summary: "Ready to save", error: null }],
      save_requested: true,
    };
  }
  if (/\b(fail|invalid|error)\b/.test(text)) {
    return {
      demo: true,
      outcome: "failed",
      reply:
        "I couldn't make that change: the scheduler library rejected it, so nothing was applied.",
      actions: [
        {
          tool: "update_item",
          ok: false,
          summary: "Set Zoppetti's maximum credits to 2",
          error: { code: "edit_rejected", message: "The change was not applied." },
        },
      ],
      issues: [
        {
          path: "config.faculty.0.maximum_credits",
          code: "faculty_minimum_exceeds_maximum_credits",
          message: "Minimum credits (12) cannot be greater than maximum credits (2)",
          area: "faculty",
          index: 0,
          field: "maximum_credits",
        },
      ],
    };
  }
  return {
    demo: true,
    outcome: "unsupported",
    reply: `${DEMO} To preview the other kinds of reply, try a message with “delete”, “save”, or “fail” in it.`,
  };
}
