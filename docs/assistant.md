# The AI assistant

The assistant is a chat in the GUI that turns plain-language requests into the
application's own actions: inspecting and editing the configuration, validating, saving,
and generating schedules. It doesn't make changes by itself. It calls defined **tools**,
and each tool runs the same Controller and Model code the GUI's buttons use. So the
scheduler library validates every change, and the GUI's safeguards (confirmed deletes,
unsaved-change warnings, Save As) apply.

It runs with `uv run zimpasta --gui`. The hosted browser version doesn't have it, because
the OpenAI key must never reach a browser.

## Setting it up

The assistant uses OpenAI. Put the API key in the environment before starting the app; it
is read once at startup.

```bash
export OPENAI_API_KEY=...        # macOS / Linux; your key goes after the =
```

```powershell
$env:OPENAI_API_KEY = "..."      # Windows PowerShell
```

Then start the GUI as usual (`uv run zimpasta --gui`). Never commit the key, put it in a
configuration file, or paste it into the chat or a screenshot. It stays on the Python side;
the browser only ever talks to `/api/chat`.

| Variable | Default | Meaning |
| --- | --- | --- |
| `OPENAI_API_KEY` | (none) | The API key. Without it the chat says how to set it, and nothing else changes |
| `ZIMPASTA_AI_MODEL` | `gpt-6-luna` | The OpenAI model. It must support function calling in the Responses API |

## What it can do

| Tool | What it does |
| --- | --- |
| `inspect_configuration` | An overview (status, counts, unsaved changes, problems), the items of one area with their indexes, or the time slots or settings |
| `describe_fields` | The library's field definitions and allowed values for one kind of item, with an existing example |
| `edit_configuration` | Add, update, and delete rooms, labs, courses, faculty, and class patterns (with their meetings), and update time slots and settings, as **one batch: all of it is applied, or none of it** |
| `new_configuration` | Start a new, empty configuration |
| `validate_configuration` | Ask the library whether the configuration is valid, and list its problems |
| `save_configuration` | Prepare saving to a JSON file; the user finishes it with Save |
| `generate_schedules` | Start generation, optionally overriding the limit or optimizer flags for this run only |
| `generation_status` | How the current or last run is going, and how many schedules the viewer has |

Example requests:

- "How many faculty members are there, and what are their credit limits?"
- "Add a room called Roddy 140 with 40 seats."
- "Raise Dr. Hardy's maximum credits to 12 and remove Friday from her availability."
- "Add CMSC 499, 3 credits, capacity 25, in Roddy 136, taught by Hardy."
- "Rename lab Linux to Linux Lab." (references to it are renamed too)
- "Delete room Roddy 147." (asks for confirmation first)
- "Set the generation limit to 5 and turn on the pack_rooms optimizer."
- "Is the configuration valid?" / "Save the configuration."
- "Generate 3 schedules without optimization."

The model sees the last few messages, so follow-ups like "now make it 45 seats" work. It
also gets a short summary of the current state with each message: what is open, each
item's index and name, whether it is saved, and how generation is going.

## How it behaves

**Applied or saved.** An edit changes the configuration in memory, as the editor's Apply
does. The header's pill shows "Unsaved changes", and the edit's chat entry says it hasn't
been saved. Saving is separate. "Save the configuration" prepares the file, and the chat
shows a **Save** button that opens the same Save As dialog as the editor. The chat says
"Saved" only after the file was written.

**Deleting** always asks first, as the editor's delete dialog does. The chat shows what
will be removed, including references that go with it (for example, a faculty member
removed from a course's list), with **Confirm** and **Cancel**. Nothing changes until
Confirm. A delete that other items need (such as a course's only room) is refused, and
the reply says which items depend on it. Starting a new configuration over unsaved
changes asks the same way. A confirmation goes stale if the configuration changes before
it is answered, and the chat then asks you to request it again.

**Failures keep the last valid configuration.** If the library rejects any part of an
edit, none of it is applied, and the chat shows the library's reasons. If OpenAI can't be
reached, rejects the key, or rate-limits the request, the chat says so in plain words and
nothing changes. If that happens after some actions already ran, the chat lists exactly
which ones did.

**Truthful outcomes.** Every tool call appears in the chat as its own entry, written from
the tool's actual result, not from the model's wording. A result's status is `done`,
`failed`, or `waiting`, and the model is told to claim success only for `done`.

**Generation** started from the chat is the same background job as the Generate button.
The progress bar in the Schedule Generator shows it, and the schedules appear in the
Schedule Viewer when it finishes.

**Unsupported requests** (anything outside these tools, such as running code or general
questions) get a short explanation of what the assistant can do instead. Requests that are
missing something, such as which room or a capacity, get one clarifying question.

**Limits that keep API use bounded:**
- One message at a time; a second send while one is running is refused.
- At most 6 model calls per message, a 60-second timeout per call, and at most 1 retry.
- Replies are capped at 2000 output tokens.

## The chat panel and the API

The transcript lives in the Python process, like the configuration, so it is the same on
every page and survives reloading the tab. The panel reads it with `api.chat.transcript()`
and watches `state.assistant` in the polled app state (`entries`, `last_entry`, `busy`,
`waiting`, `available`, `reason`), refetching when `last_entry` changes. Routes and errors
are in [web-api.md](web-api.md#assistant).

Each transcript entry:

```json
{"id": "m4", "role": "tool", "text": "Waiting for confirmation: Delete faculty member Dr. Jones and 1 reference to it?",
 "at": "2026-10-23T14:02:11", "tool": "edit_configuration",
 "result": {"status": "waiting", "ok": false, "summary": "...", "error": null},
 "error": null,
 "pending": {"id": "p5", "kind": "confirm", "prompt": "Delete faculty member Dr. Jones and 1 reference to it?",
             "details": ["Removed faculty member Dr. Jones and 1 reference to it",
                         "Also removes Dr. Jones from course section CS 102.01 (faculty)"],
             "revision": 7, "state": "waiting"}}
```

- `role` is `user`, `assistant` (the model's reply), `tool` (an action's outcome, with
  `result`), or `notice` (the app speaking: a cancellation, an API failure in `error`, or
  a step limit).
- A `pending` entry needs the user:
  - `kind: "confirm"`: show Confirm and Cancel, and send `api.chat.answer(id, "confirm" | "cancel")`.
  - `kind: "save"`: show Save. Run the editor's usual save (`api.config.exportFile()`,
    `saveFile()`, `api.config.markSaved()`), then send `api.chat.answer(id, "saved", filename)`,
    or `"cancel"` if the dialog was dismissed.
- `state` changes to `confirmed`, `cancelled`, `saved`, or `expired` once answered.

## Code

`src/zimpasta/controller/assistant/` is Controller code: it decides what a chat message
does and carries it out through `AppController`.

| File | Contents |
| --- | --- |
| `session.py` | `Assistant`: the transcript, the busy guard, pending actions, and the bounded loop between the model and the tools |
| `tools.py` | The tools: argument models (pydantic, checked before anything runs), handlers, and `ToolRegistry.dispatch` |
| `prompt.py` | `BASE_PROMPT` (the AI's role, tools, and rules) and the state summary sent with each message |
| `client.py` | `AIClient` and `OpenAIClient`, the only code that knows about OpenAI |

Design patterns:
- **Command:** each tool is a named action with defined arguments, run through one
  dispatcher.
- **Adapter:** `OpenAIClient` adapts the OpenAI SDK to `AIClient`, so tests use a scripted
  fake.

The Model gained one method, `ConfigWorkspace.transaction()`, which undoes a group of
edits if any of them fails.

## Tests

`tests/controller/assistant/` covers the requirements without calling OpenAI. It uses
`FakeAIClient` (in `tests/helpers.py`), which plays back scripted replies and tool calls
and records every request:

- tool registration and argument definitions;
- dispatch to the right action;
- edits accepted or rejected by the library, and combined edits that are all-or-nothing;
- deletes with references (confirm, cancel, expired) and blocked deletes;
- saving and generation, with the results reaching the viewer;
- unknown tools, malformed or incomplete arguments, a missing key, API failures, and the
  busy guard;
- outcomes taken from tool results rather than the model's text.

One live test makes a single real request that adds a room. It is deselected by default:

```bash
uv run pytest -m live          # needs OPENAI_API_KEY; skipped without it
```

In GitHub Actions it runs only from the **AI live test** workflow, started by hand from
the Actions tab, which reads the `OPENAI_API_KEY` repository secret in that one step.
