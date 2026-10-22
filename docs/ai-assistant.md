# AI assistant ("Ask Dr. ZImpasta")

The assistant lets a user type a request such as *"Add a room called Roddy 150 with
capacity 30"* or *"Generate 5 schedules"*. The AI turns the request into calls to a fixed
set of **tools**. The tools run the operation through `AppController`, exactly like a
button in the GUI would, and the GUI shows what actually happened.

The work is split in two:

| Part | Who | Where | Status |
| --- | --- | --- | --- |
| Chat window, reply display, confirm / save / generation follow-up | GUI | `frontend/src/chat/` | Built |
| `POST /api/assistant`, tools, base prompt, model client | Backend | `src/zimpasta/assistant/` (new) plus small additions listed below | To do |

The two halves meet at **one route** with **one reply shape**, specified under
[The API contract](#the-api-contract). Until the route exists, the GUI shows clearly
labeled demo replies (see [Demo replies](#demo-replies-until-the-backend-exists)), and it
switches to the real assistant automatically once the route answers.

Requirements this covers: project spec sections 3 (AI chat tool), 4 (AI capabilities
and application tools), and 5 (AI role and base prompt). The
[checklist](#requirements-checklist) at the end maps each requirement to the code that
meets it.

---

## How a request flows

```
User types a request ─▶ ChatAssistant.jsx ─▶ POST /api/assistant {"message": ...}
                                                     │
                                       routes.py ─▶ AppController.ask_assistant()
                                                     │
                                         Assistant.ask()   (src/zimpasta/assistant/service.py)
                                          │  1. build the base prompt + current state
                                          │  2. ask the model; it answers with tool calls
                                          │  3. run read-only tools now, queue edits
                                          │  4. deletes or discards? → needs_confirmation
                                          │  5. apply all queued edits as ONE batch
                                          │  6. then validate / save / generate if asked
                                          ▼
                                 AssistantReply (outcome, actions, issues, ...)
                                                     │
GUI shows the reply, refreshes the editor/viewer ◀───┘
```

The model never edits anything itself. It can only ask for tools, and every tool goes
through `AppController`, which uses the existing Model (`ConfigWorkspace`,
`GenerationJob`, `ScheduleSet`) and the scheduler library for validation. Whether a
request **succeeded** is decided from the tools' results, never from the model's text.

---

## Where the backend code goes

New package, next to `controller/` and `model/`:

```
src/zimpasta/assistant/
  __init__.py        exports Assistant, AssistantUnavailable
  prompt.py          BASE_PROMPT and build_context(controller): the role, tools, and state
  tools.py           TOOLS: name, description, JSON-Schema arguments, and a handler per tool
  service.py         Assistant.ask(message, confirm): the model/tool loop, edit queue,
                     confirmation tokens, building the reply
  model_client.py    thin wrapper around the LLM provider's API (one function: complete()),
                     so tests can pass a fake
  reply.py           AssistantReply and ActionResult dataclasses with to_dict()
```

Small additions to existing files:

| File | Add |
| --- | --- |
| `src/zimpasta/model/workspace.py` | `ConfigWorkspace.apply_batch(operations)`: several edits committed as one change, or none (see [Combined edits](#combined-edits-all-or-nothing)) |
| `src/zimpasta/controller/app_controller.py` | `apply_batch(operations)` (calls the workspace) and `ask_assistant(message, confirm)` (calls `self.assistant.ask`). Create the `Assistant` in `__init__` with a reference to the controller |
| `src/zimpasta/controller/routes.py` | `AssistantRequest` model and `POST /api/assistant` (below) |
| `src/zimpasta/controller/errors.py` | Register `AssistantUnavailable` → 503 `assistant_unavailable`, and `ConfirmationExpired` → 409 `confirmation_expired` |
| `pyproject.toml` | The LLM provider's SDK, if you use one |
| `docs/web-api.md` | The *AI assistant* section is already there; remove its "Not built yet" once the route works |
| `tests/` | See [Tests](#tests) |

Nothing in `frontend/` needs to change for the backend to work.

### Configuration and secrets

- Read the provider API key from an environment variable (for example
  `ZIMPASTA_AI_API_KEY`). Never send it to the browser and never write it to a file.
- If the key is missing, `ask_assistant` raises `AssistantUnavailable`
  ("The assistant isn't set up: set ZIMPASTA_AI_API_KEY and restart zimpasta.").
  The GUI shows that message in the chat.
- The **browser version** (`src/zimpasta/browser.py`, Pyodide) has no server and no
  safe place for a key. There the route should raise `AssistantUnavailable` with a message
  saying the assistant needs the local app (`uv run zimpasta --gui`).

---

## The API contract

### `POST /api/assistant`

Request body (`AssistantRequest`):

```json
{"message": "Add a room called Roddy 150 with capacity 30", "confirm": null}
```

| Field | Type | Meaning |
| --- | --- | --- |
| `message` | string, 1–2000 chars, or `null` | The user's request. Required unless `confirm` is set |
| `confirm` | string or `null` | The `token` from a previous reply's `confirmation`: run exactly the actions that reply described. `message` is ignored |

Each request is interpreted on its own, using the current application state. The GUI
does **not** send the conversation history, and the backend does not need to keep one
(spec section 3: one-off requests are enough).

Suggested route (in `routes.py`):

```python
class AssistantRequest(BaseModel):
    message: str | None = Field(default=None, min_length=1, max_length=2000)
    confirm: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")  # from pydantic; errors.py turns this into 400 bad_request
    def _message_or_confirm(self) -> "AssistantRequest":
        if not self.message and not self.confirm:
            raise ValueError("Send a message, or a confirm token.")
        return self


@router.post("/assistant")
def ask_assistant(app: App, request: AssistantRequest) -> dict:
    """Run one natural-language request through the assistant's tools (docs/ai-assistant.md)."""
    return app.ask_assistant(request.message, confirm=request.confirm)
```

### The reply (HTTP 200)

The route answers **200 whenever the assistant ran**, including when the requested action
failed: a failed action is a normal, explainable outcome, not a server error.

```json
{
  "outcome": "succeeded",
  "reply": "Added room Roddy 150 with capacity 30. It's applied but not saved to a file yet.",
  "actions": [
    {"tool": "add_item", "ok": true, "summary": "Added room Roddy 150", "error": null}
  ],
  "issues": [],
  "config": {"changed": true, "revision": 8, "dirty": true},
  "generation_started": false,
  "save_requested": false,
  "confirmation": null
}
```

| Field | Type | Meaning |
| --- | --- | --- |
| `outcome` | `"succeeded"` · `"failed"` · `"needs_confirmation"` · `"needs_information"` · `"unsupported"` | Overall result, **computed from the tool results** (see below) |
| `reply` | string | What to tell the user, in plain words. Written by the model, but it must agree with `outcome` |
| `actions` | list of ActionResult | Every tool that **changed or would change** something, in order. Read-only lookups (`inspect`, `list_items`, ...) may be left out |
| `issues` | list of Issue | Located problems from the scheduler library or the Model, in the same shape as API errors (`path`, `code`, `message`, `area`, `index`, `field`). Empty when there are none |
| `config` | object | State after the request: `changed` (did the revision change during this request?), `revision`, `dirty` (unsaved changes exist), from `ConfigWorkspace.snapshot()` |
| `generation_started` | bool | A generation run was started. The GUI follows it through `GET /api/state` |
| `save_requested` | bool | The user asked to save and the configuration is valid. The GUI shows a **Save JSON…** button that runs the existing save workflow |
| `confirmation` | object or `null` | Set only when `outcome` is `needs_confirmation`, see below |

**ActionResult**

```json
{"tool": "update_item", "ok": false, "summary": "Change faculty Zoppetti's maximum credits to 30",
 "error": {"code": "edit_rejected", "message": "The change was not applied: Maximum credits ..."}}
```

`summary` describes the action in user terms. Use the Model's own `Change.summary` when
the action succeeded. `error` is `null` when `ok` is true; otherwise it is the Model
exception's `code` and `message` (`EditRejected`, `DeleteBlocked`, `NotValid`,
`GenerationBusy`, `UnsavedChanges`, ...).

**Outcomes**

| `outcome` | When | What was applied |
| --- | --- | --- |
| `succeeded` | Every action's `ok` is true (or the request only looked things up) | Everything in `actions` |
| `failed` | Any action failed | **Nothing from this request's edits.** The batch is all-or-nothing, so `config.changed` is false. Explain why in `reply` and list `issues` |
| `needs_confirmation` | The request would delete something, or discard unsaved changes | Nothing yet. See [Confirmation](#confirmation-same-safeguards-as-the-gui) |
| `needs_information` | Required details are missing ("add a room" with no name or capacity) | Nothing. `reply` asks for what's missing |
| `unsupported` | Outside the tools ("email this to my chair", shell commands, code) | Nothing. `reply` says what the assistant can do instead |

Set `outcome` in Python from the tool results. If the model's text claims success but a
tool failed, the reply's `outcome` is still `failed` (spec section 4: an AI response
alone does not satisfy an action request).

### Errors (non-200)

These use the app's normal error shape (`{"error": {"code", "message", "issues"}}`):

| Status | `code` | When |
| --- | --- | --- |
| 400 | `bad_request` | No `message` and no `confirm`, or the message is too long |
| 409 | `confirmation_expired` | `confirm` names an unknown, used, or expired token |
| 503 | `assistant_unavailable` | No API key, the browser version, or the model provider can't be reached |
| 500 | `unexpected` | A bug (already handled by `errors.py`) |

The GUI shows `message` in a red bubble and the user can simply try again. Nothing in the
application has changed.

---

## Tools

Each tool has a name, a description the model reads, an argument schema (JSON Schema),
and a handler. **Validate the arguments against the schema before running the handler.**
Bad arguments become a failed ActionResult with code `bad_arguments`; they never reach
the Model. Handlers only call `AppController` methods.

| Tool | Arguments | Calls | Notes |
| --- | --- | --- | --- |
| `inspect` | `area`: one of `summary`, `rooms`, `labs`, `courses`, `faculty`, `patterns`, `time_slots`, `settings` | `controller.state()["config"]` for `summary`; `controller.list_items(area)` for lists; the `time_slot_config` (minus `classes`) or `limit` / `optimizer_flags` from `controller.configuration()["document"]` | Read-only, runs immediately. Return items **with their index**, because edits address items by position |
| `get_item` | `area`, `index` | `controller.get_item(area, index)` | Read-only |
| `get_options` | — | `controller.options()` | Weekdays, modalities, optimizer flags with descriptions |
| `get_schema` | `area` | the matching part of `controller.schema()` | So the model knows each item's fields |
| `add_item` | `area`, `item` (object) | queued, then `apply_batch` | `item` in the library's JSON shape |
| `update_item` | `area`, `index`, `changes` (object of fields to set) | queued; the handler merges `changes` into `controller.get_item(area, index)["item"]`, then `apply_batch` replaces it | Merging on the server means the model doesn't have to resend every field. Renames still update references (`ConfigWorkspace.replace` does it) |
| `delete_item` | `area`, `index` | `controller.delete_impact(area, index)` first; queued only after confirmation; then `apply_batch` | Always needs confirmation, like the editor's Delete dialog. If `can_delete` is false, fail with the `DeleteBlocked` message and the impact's `blocking` / `problems` |
| `update_time_slots` | `values`: any of `times`, `max_time_gap`, `min_time_overlap` | queued, then `apply_batch` | Same fields `PUT /api/config/time-slots` accepts |
| `update_settings` | `values`: any of `limit`, `optimizer_flags` | queued, then `apply_batch` | |
| `validate` | — | `controller.validate_configuration()` | The scheduler library decides validity. Put the report's issues in `issues` |
| `save_configuration` | — | `controller.export_configuration()` to confirm it's savable (raises `NotValid` / `NoConfiguration` otherwise) | Does **not** write a file; sets `save_requested: true`. See [Saving](#saving-through-the-existing-workflow) |
| `generate_schedules` | `limit` (optional int), `optimizer_flags` (optional list) | `controller.start_generation(limit=..., optimizer_flags=...)` | Runs after the batch. Returns once the run has *started*; set `generation_started: true`. `GenerationBusy`, `NotValid`, and `InvalidOverrides` become a failed action |

The spec's required configuration areas map onto these tools like this:

| Required area | Tool `area` value |
| --- | --- |
| rooms, labs, courses, faculty | `rooms`, `labs`, `courses`, `faculty` |
| class patterns | `patterns` |
| meetings | the `meetings` list inside a class pattern: `update_item` on `patterns` |
| time slots | `update_time_slots` / `inspect time_slots` |
| global settings | `update_settings` / `inspect settings` |

Item shapes are the scheduler library's own, exactly as in a configuration file; see
`GET /api/config/schema` and docs/web-api.md. Indexes shift down after a delete, so look
items up again after deleting.

### Combined edits: all or nothing

The spec requires that one request never leaves its edits half applied. Today each
workspace edit commits on its own, so the assistant must not call `add_item`, `update_item`,
and so on one by one. Instead:

1. While the model is working, **queue** edit tools instead of running them, and answer
   the model with `{"queued": true}`. Read-only tools run immediately, so the model can
   look up names and indexes.
2. When the model is done, run every queued edit with **one** call to
   `controller.apply_batch(operations)`.
3. `ConfigWorkspace.apply_batch` builds one candidate document by applying each operation
   in order to a deep copy (the same steps `add`, `replace`, and `remove` use today,
   factored into helpers that don't commit). It then calls `_commit` **once**. The library
   validates the whole result, and if it rejects it, `EditRejected` is raised and the stored
   configuration, revision, and journal are exactly as before.

Sketch for `workspace.py`:

```python
def apply_batch(self, operations: list[dict]) -> Change:
    """Apply several edits as one change: all of them, or none if the library rejects the result.

    Each operation is {"op": "add" | "replace" | "remove" | "time_slots" | "settings", ...}.
    """
    with self._lock:
        candidate = copy.deepcopy(self._require_document())
        summaries = []
        for operation in operations:
            candidate, summary = self._apply_operation(candidate, operation)  # no commit
            summaries.append(summary)
        areas = {operation["area"] for operation in operations}
        area = areas.pop() if len(areas) == 1 else "batch"  # also add "batch" to Change.area's docstring
        return self._commit(candidate, lambda doc: ("edited", area, "; ".join(summaries)))
```

The tests for this matter most: a batch whose second edit is invalid must leave
`revision`, `document()`, and `changes` unchanged.

### Confirmation: same safeguards as the GUI

The ordinary GUI asks before it deletes anything (the Delete dialog, which shows
`delete_impact`) and before it discards unsaved changes (`UnsavedChanges`). The assistant
does the same:

1. If the queued edits include a delete, do **not** run the batch. (The same goes for
   anything that would raise `UnsavedChanges`, which only matters if you add tools that
   start a new configuration or load a file; the spec doesn't require those.) Instead,
   store the queued operations under a random token (`secrets.token_hex(8)`) with the
   current `revision`, and reply:

   ```json
   {"outcome": "needs_confirmation",
    "reply": "Deleting room Roddy 147 also removes it from 2 course sections. Go ahead?",
    "actions": [{"tool": "delete_item", "ok": true, "summary": "Delete room Roddy 147", "error": null}],
    "confirmation": {
      "token": "9f2c41d07ab35e18",
      "question": "Delete room Roddy 147?",
      "details": ["CMSC 140.01 will no longer list Roddy 147", "CMSC 152.01 will no longer list Roddy 147"],
      "confirm_label": "Delete room"
    },
    "issues": [], "config": {"changed": false, "revision": 8, "dirty": true},
    "generation_started": false, "save_requested": false}
   ```

   Build `details` from the impact's `cascades` (and, for unsaved changes, from the
   `changes` summaries).
2. The GUI shows the question, the details, and **Confirm** / **Cancel** buttons. Confirm
   sends `{"confirm": "<token>"}`.
3. On confirm, run the stored operations with `apply_batch` and reply as usual. Don't ask
   the model again: run exactly what the user saw.
4. Tokens are single-use. They expire after 10 minutes, when any other assistant request
   arrives, or when `revision` has changed since (the configuration was edited elsewhere).
   An expired token gets 409 `confirmation_expired` and nothing runs. Cancel needs no
   request: the GUI says nothing was changed, and the token simply expires.

### Saving through the existing workflow

Saving in this app happens in the **browser**: `Save()` in
`frontend/src/state/EventHandlers.js` validates, exports the JSON (`GET /api/config/export`),
opens the save dialog, writes the file, and then marks that revision saved
(`POST /api/config/saved`). The server can't open that dialog, and browsers only allow it
right after a click. So:

- `save_configuration` only checks that the configuration can be saved and sets
  `save_requested: true`.
- The GUI shows a **Save JSON…** button in the reply. Clicking it runs the same `Save()`, so
  the configuration is saved exactly as with the editor's button, and then the reply shows
  "Saved as …".

"Applied" and "saved" stay distinct: every edit reply says whether the configuration
changed (`config.changed`) and at which `revision`. The GUI shows *Applied · not saved to
a file yet* until the app's `saved_revision` (in `GET /api/state`) reaches that revision,
then *Applied and saved*, whichever way it was saved.

### Generation

`generate_schedules` starts the background job and returns. Generation can take a while,
and the request shouldn't wait for it. The GUI then follows `state.generation` from
`GET /api/state` (it already polls it) and updates the reply: *Generating… 3 of 5 found*,
then *5 schedules generated* with a **View schedules** link. The Schedule Viewer picks up
the new schedules by itself.

---

## Base prompt (spec section 5)

`prompt.py` builds the system prompt from a fixed text plus the current state. It must say:

1. **Role.** You are Dr. ZImpasta's assistant. You help edit the course scheduler's
   configuration and run the application's actions: inspect, add, update, delete,
   validate, save, and generate. You are not a general chatbot.
2. **Tools.** List every tool with one line on what it does (the `TOOLS` descriptions).
3. **Use tools for everything.** Any change or action must be done with a tool. Never say
   something was changed, saved, or generated unless the tool result says it succeeded.
4. **The scheduler library decides validity.** Don't guess whether a configuration is
   valid. Use `validate`, and explain the issues it returns.
5. **Unsupported requests.** If a request isn't covered by the tools (email, files on
   disk, shell commands, code, questions unrelated to the schedule), say so plainly and
   say what you can do instead.
6. **Missing information.** If required fields are missing (for example a room's capacity),
   ask for them instead of inventing values. If something is ambiguous (two sections of
   CMSC 340), ask which one.
7. **Report honestly.** Report success only after the tool confirms it. Say whether
   changes are applied but not saved.

Context given with every request (so it can interpret requests without a conversation):

- `controller.state()["config"]`: status, file name, dirty, counts.
- For each area, a short list of `index: name` (for example `0: Roddy 136`), and course
  section ids from `ConfigWorkspace.section_labels()`, so names in the request can be
  matched to indexes.
- `controller.options()`: weekdays, modalities, optimizer flags.
- The full schema is too big to include every time; the model calls `get_schema(area)`
  when it needs field details.

---

## The GUI side (already built)

Files in `frontend/src/chat/`:

| File | What it does |
| --- | --- |
| `ChatAssistant.jsx` | The "Ask Dr. ZImpasta" button and slide-in panel; sends each request, keeps the visible conversation, New chat |
| `AssistantReply.jsx` | Shows one reply: text, each action ✓/✗, issues (`IssueList`), *Applied · not saved to a file yet* / *Applied and saved*, Confirm/Cancel, Save JSON…, generation progress with View schedules |
| `assistant.js` | Calls `api.assistant.ask()`; falls back to demo replies while the route doesn't exist |
| `useResizablePanel.js` | Dragging the panel's edge |
| `chat.css` | Styles |

After any reply with `config.changed` or `generation_started`, the GUI refreshes the app
state immediately, so the Configuration Editor (which reloads when the revision changes)
and the Schedule Viewer (which reloads when the schedules change) show the result right away.

### Demo replies (until the backend exists)

While there's no `POST /api/assistant` route, the server answers **405 Method Not
Allowed** (the GUI's own pages are served for every unknown path, for GET only; a 404 is
treated the same way). Then `assistant.js` returns demo replies, each marked **Demo** in
the chat. They show each reply type (confirmation for "delete …", Save JSON… for "save",
a failure for "fail") without claiming to change anything. Once the route exists, the GUI
uses it automatically. Nothing needs to be switched off.

To try the real route from a terminal while building it:

```bash
curl -s -X POST http://127.0.0.1:8765/api/assistant \
  -H 'Content-Type: application/json' \
  -d '{"message": "Add a room called Roddy 150 with capacity 30"}'
```

(Use the port `zimpasta --gui` prints; `npm run dev` starts the API on 8765.)

---

## Tests

Put them next to the existing ones, with a fake model client that returns scripted tool
calls (the same idea as `FakeSchedulerFactory` in `tests/helpers.py`), so the tests are
fast and need no API key.

- `tests/model/test_workspace.py`: `apply_batch` commits all edits as one revision; if
  any edit is invalid, nothing changes (`revision`, `document()`, `changes`).
- `tests/assistant/` is a new folder; give it an empty `__init__.py` like the other test folders.
- `tests/assistant/test_tools.py`: each tool rejects bad arguments (`bad_arguments`)
  without touching the Model; each tool calls the right controller method.
- `tests/assistant/test_service.py`:
  - add → `succeeded`, `config.changed`, revision + 1;
  - invalid edit → `failed`, issues, nothing applied;
  - two edits where the second is invalid → `failed`, neither applied;
  - delete → `needs_confirmation`; confirm with the token → applied; reused or expired
    token → `confirmation_expired`; edit elsewhere in between → expired;
  - model claims success without calling a tool → not `succeeded`;
  - unsupported request → `unsupported`, nothing changed;
  - save on an incomplete configuration → failed `configuration_incomplete`; on a valid one
    → `save_requested`;
  - generate → `generation_started`; while a run is going → failed `generation_running`;
  - no API key → `AssistantUnavailable`.
- `tests/controller/test_api.py`: `POST /api/assistant` returns the reply shape, 400 for
  an empty request, 503 when unavailable.

---

## Requirements checklist

| Requirement (project spec) | Where it's met |
| --- | --- |
| §3 Clearly identifiable chat input; enter and submit a request | GUI: launcher button and message box (`ChatAssistant.jsx`) |
| §3 See that the request is being processed | GUI: typing indicator; Send disabled while waiting |
| §3 Understandable result, including success or failure | Backend: `outcome`, `reply`, `actions`, `issues`. GUI: `AssistantReply.jsx` |
| §3 Changes shown in the Configuration Editor | Backend: edits go through `AppController`. GUI: refresh after `config.changed` |
| §3 Generated results shown in the Schedule Viewer | Backend: `start_generation`. GUI: progress and View schedules |
| §3 Recover without restarting or losing the last valid state | Backend: all-or-nothing batch; errors are replies. GUI: error bubble, keep typing, New chat |
| §4 Explicitly defined tools with argument structures, validated first | Backend: `tools.py` schemas; `bad_arguments` |
| §4 Inspect; create, update, delete in every required area | Backend: `inspect`, `get_item`, `add_item`, `update_item`, `delete_item`, `update_time_slots`, `update_settings` |
| §4 Validate with the scheduler library | Backend: `validate` → `ConfigWorkspace.validate()` |
| §4 Save as JSON through the existing save workflow | Backend: `save_configuration` → `save_requested`. GUI: Save JSON… runs `Save()` |
| §4 Generate from the current valid configuration | Backend: `generate_schedules` → `start_generation` |
| §4 Through Controllers and existing Model behavior | Backend: every handler calls `AppController` |
| §4 Structured success / failure information | The reply shape above |
| §4 Same deletion, overwrite, and unsaved-change safeguards | Backend: confirmation tokens built from `delete_impact` / `UnsavedChanges`. GUI: Confirm/Cancel |
| §4 Last valid configuration kept; combined edits not partly applied | Backend: `apply_batch` |
| §4 Applied vs. saved is clear | Backend: `config.changed`, `config.revision`. GUI: *Applied · not saved to a file yet* / *Applied and saved* |
| §5 Base prompt: role, tools, tools-only actions, library decides validity, unsupported, missing info, report success only after tools confirm | Backend: `prompt.py` |
| §5 Enough context to interpret requests | Backend: state, item names with indexes, options, `get_schema` |
