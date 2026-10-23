# AI assistant: backend spec

The chat panel (`frontend/src/chat/`) is done. It calls one route the backend still
needs: `POST /api/assistant`. Until that route exists, the chat shows "Demo" replies.

## Where the code goes

| File | Add |
| --- | --- |
| `src/zimpasta/assistant/` (new) | `prompt.py` base prompt · `tools.py` tools and argument schemas · `service.py` model/tool loop · `model_client.py` LLM API wrapper (a fake in tests) |
| `controller/routes.py` | `POST /api/assistant` |
| `controller/app_controller.py` | `ask_assistant(message, confirm)` and `apply_batch(operations)` |
| `model/workspace.py` | `apply_batch(operations)`: several edits in one commit, all or nothing |
| `controller/errors.py` | 503 `assistant_unavailable`, 409 `confirmation_expired` |

The API key comes from the `ZIMPASTA_AI_API_KEY` environment variable and never goes to
the browser. No key, or the browser version: 503 `assistant_unavailable`.

## Request

```json
{"message": "Add a room called Roddy 150 with capacity 30", "confirm": null}
```

To approve a pending action, send `{"confirm": "<token>"}`. Each request stands alone
(no chat history).

## Reply

Always 200 when the assistant ran, even if the action failed.

```json
{
  "outcome": "succeeded",
  "reply": "Added room Roddy 150. It isn't saved to a file yet.",
  "actions": [{"tool": "add_item", "ok": true, "summary": "Added room Roddy 150", "error": null}],
  "issues": [],
  "config": {"changed": true, "revision": 8, "dirty": true},
  "generation_started": false,
  "save_requested": false,
  "confirmation": null
}
```

- `outcome`: `succeeded`, `failed`, `needs_confirmation`, `needs_information`, or
  `unsupported`. Set it from the tool results, never from the model's text.
- `actions[].error`: `{code, message}` from the Model's exception when `ok` is false.
- `issues`: the same shape as the issues in API errors.
- `confirmation`: `{token, question, details, confirm_label}` when `needs_confirmation`.

## Tools

Every tool calls `AppController`. Check the arguments first; bad ones give a failed
action with code `bad_arguments`.

| Tool | Calls |
| --- | --- |
| `inspect(area)` | `state()`, `list_items(area)`, or time slots / settings from `configuration()` |
| `get_item(area, index)` | `get_item` |
| `get_schema(area)`, `get_options()` | `schema()`, `options()` |
| `add_item(area, item)` | queued, then `apply_batch` |
| `update_item(area, index, changes)` | merged into `get_item(...)["item"]`, queued, then `apply_batch` |
| `delete_item(area, index)` | `delete_impact`, needs confirmation, then `apply_batch` |
| `update_time_slots(values)`, `update_settings(values)` | queued, then `apply_batch` |
| `validate()` | `validate_configuration()` |
| `save_configuration()` | `export_configuration()` to check it can be saved; sets `save_requested` |
| `generate_schedules(limit?, optimizer_flags?)` | `start_generation(...)`; sets `generation_started` |

Areas: `rooms`, `labs`, `courses`, `faculty`, `patterns` (meetings are inside patterns),
plus time slots and settings.

## Rules

1. **All or nothing.** Queue edits while the model works, then apply them with one
   `apply_batch`. If the scheduler library rejects the result, nothing changes.
2. **Confirm deletes.** Don't run a batch with a delete. Store it under a token
   (`secrets.token_hex(8)`) and reply `needs_confirmation`. On `{"confirm": token}`, run
   exactly that batch. Tokens work once and expire after 10 minutes, on any new request,
   or if the configuration changed.
3. **Saving happens in the browser.** The server can't open the save dialog.
   `save_requested: true` makes the chat show a Save JSON… button that runs the existing
   `Save()`.
4. **Generation runs in the background.** Start it and return; the chat follows
   `GET /api/state`.

## Base prompt

It must say:

- The assistant edits the scheduler configuration and runs app actions, nothing else.
- Which tools exist and what each does; every change goes through a tool.
- The scheduler library decides validity (use `validate`).
- Unsupported request: explain. Missing information: ask.
- Report success only after a tool confirms it, and say when changes aren't saved.

Send with each request: the configuration's status and counts, an `index: name` list per
area, and `options()`.

## Tests

Use a fake model client. Cover: an add succeeds; an invalid edit fails with nothing
applied; two edits where one is invalid apply neither; a delete needs confirmation and its
token works once; an unsupported request; the save and generate flags; no API key gives 503.
