# Web API

The GUI's views talk to the Python side only through this JSON API, served under `/api` on
`127.0.0.1`. Each route calls one method of `AppController`
(`src/zimpasta/controller/app_controller.py`), which coordinates the Model in
`src/zimpasta/model/`. FastAPI also serves interactive docs of these routes at `/docs`.

The browser version (docs/cloudflare-pages.md) answers the same routes from Python running
in the page (`src/zimpasta/browser.py`), with two differences: a run generates at most
`generation.max_schedules` schedules (see *Generation*), and the AI assistant isn't
available (see *Assistant*).

## Conventions

- Request and response bodies are JSON. Send `Content-Type: application/json` on any
  request with a body; POSTs without a body (cancel, validate, new) may omit it.
- Configuration items are the scheduler library's own JSON shapes, exactly as they appear
  in a configuration file. `GET /api/config` returns them in canonical form (every field
  present, `null` for unset optional fields); send an item back in the same shape.
- Items are addressed by **area** and **index**: `rooms`, `labs`, `courses`, `faculty`,
  `patterns` (the time-slot class patterns), and the item's position in that list.
  Course ids repeat across sections, so a position is the only stable address. After any
  change, use the returned document; indexes after a deleted item shift down by one.

## Errors

Every error has one shape. `code` is for program logic; `message` is written for users.

```json
{"error": {"code": "edit_rejected",
           "message": "The change was not applied: Minimum credits (99) cannot be greater than maximum credits (14)",
           "issues": [{"path": "config.faculty.1.minimum_credits", "code": "faculty_minimum_exceeds_maximum_credits",
                       "message": "Minimum credits (99) cannot be greater than maximum credits (14)",
                       "area": "faculty", "index": 1, "field": "minimum_credits"}]}}
```

`issues` locates each problem so a form can show it next to the right control: `area` and
`index` pick the item, `field` names the field (dotted for nested fields, such as
`meetings.0.duration`). Settings problems have `area: "settings"`, time-grid problems
`area: "time_slots"`, and whole-configuration problems `area: null`.

| Status | `code` | When |
| --- | --- | --- |
| 400 | `bad_request` | Missing or mistyped request fields (`details` lists them) |
| 400 | `malformed_json`, `unreadable_file` | An uploaded file is not JSON |
| 400 | `bad_host` | The request was not addressed to localhost |
| 403 | `cross_origin` | A state-changing request came from another site |
| 400 | `empty_message`, `message_too_long`, `invalid_answer` | A chat message or a pending answer that can't be used |
| 404 | `not_found` | Unknown area, index, schedule number, pending chat action, or endpoint |
| 409 | `no_configuration` | Nothing has been created or loaded |
| 409 | `configuration_incomplete` | Save or generate on an incomplete or invalid configuration (`issues` says what's wrong) |
| 409 | `unsaved_changes` | New or load would discard edits; `changes` lists them |
| 409 | `delete_blocked` | A delete without `force=true` that `impact` warns about, or one the server can't keep even forced (`can_force` false) |
| 409 | `generation_running` | A run is already in progress |
| 409 | `no_schedules` | Export or view with no schedules |
| 409 | `chat_busy` | The assistant is still answering the previous message |
| 409 | `pending_settled`, `not_saved` | A pending chat action was already answered, or "saved" was reported before the file was saved |
| 415 | `json_required` | A request body was not JSON |
| 422 | `edit_rejected` | The library rejected an edit; nothing changed |
| 422 | `invalid_configuration` | A loaded file is JSON but not a valid configuration |
| 422 | `invalid_overrides` | A run's limit or optimizer flags are not valid |
| 422 | `invalid_schedule_file` | An imported schedule file is not in the schedule format |
| 500 | `unexpected` | A bug. The message is friendly and includes a `reference` found in the server log |
| 503 | `ai_not_configured` | No OpenAI key, or the browser version; the message says what to do |

## State

`GET /api/state` returns what the header and every mode need:

```json
{"config": {"status": "valid", "name": "sample_config.json", "revision": 4, "saved_revision": 2,
            "dirty": true, "changes": [{"revision": 3, "action": "edited", "area": "faculty",
            "summary": "Faculty member Hardy: maximum_credits 14 → 12"}],
            "issues": [], "warnings": [], "validated_at": "2026-09-28T16:41:00",
            "counts": {"rooms": 3, "labs": 2, "sections": 17, "courses": 12, "faculty": 9,
                       "patterns": 16, "enabled_patterns": 9}},
 "generation": {"state": "idle", "running": false, "found": 0, ...},
 "schedules": {"count": 0, "source": null, "name": null, "created_at": null},
 "assistant": {"available": true, "reason": null, "model": "gpt-6-luna", "busy": false,
               "entries": 6, "last_entry": "m6", "waiting": 0}}
```

`config.status` is `none` (nothing open), `incomplete` (a new configuration still missing
a room, course, or faculty member; `issues` says which), `invalid` (a forced delete left
problems between items, such as a section with no room, after a forced delete or edit; `issues` lists them, and any edit
that keeps each item valid on its own is accepted, even one that adds problems), or `valid`.

`config.warnings` lists what keeps a valid configuration from having any schedule, found
by the library's quick checks after every change (for example, a disabled class pattern was
the only one putting a faculty member on their mandatory day). They never block an edit.
Each has the same shape as an issue. An empty list doesn't promise a schedule exists.

## Configuration

| Method and path | Body | Returns |
| --- | --- | --- |
| `GET /api/config` | | `{state, document, sections}`; `sections` are labels such as `CMSC 140.02` |
| `GET /api/config/schema` | | The library's JSON Schema for a whole configuration |
| `GET /api/config/options` | | `weekdays`, `modalities`, `delivery_modes`, `optimizer_flags` with descriptions, and `generation.max_schedules` |
| `POST /api/config/new` | `{discard_changes?}` | New incomplete configuration, as `GET /api/config` |
| `POST /api/config/load` | `{filename, content, discard_changes?}` | The loaded configuration |
| `POST /api/config/validate` | | `{report: {status, valid, issues, checked_at}, state}` |
| `GET /api/config/export` | | The file to save: body is the JSON, `Content-Disposition` has the name, `X-Config-Revision` the revision |
| `POST /api/config/saved` | `{revision, filename?}` | Updated `state`, after the file was written |
| `GET /api/config/{area}` | | `{area, items}` |
| `POST /api/config/{area}` | the new item | 201, `{state, document, sections, change, index}` |
| `GET /api/config/{area}/{index}` | | `{area, index, item}` |
| `PUT /api/config/{area}/{index}` | the whole item; `?force=true` applies it even if the configuration then has problems (the class pattern On/Off switch uses this) | `{state, document, sections, change, index}` |
| `GET /api/config/{area}/{index}/impact` | | `{label, can_delete, can_force, blocking, cascades, problems}`; changes nothing |
| `DELETE /api/config/{area}/{index}` | `?force=true` to delete anyway | `{state, document, sections, change, impact}` |
| `PUT /api/config/time-slots` | any of `times`, `max_time_gap`, `min_time_overlap` | As for items |
| `PUT /api/config/settings` | any of `limit`, `optimizer_flags` | As for items |

**Loading** sends the text the browser read from the chosen file. The server keeps only
the file name. A malformed or invalid file is reported and nothing changes. If the file
is fine but there are unsaved changes, the reply is `409 unsaved_changes` with the list;
ask the user, then send the same request with `"discard_changes": true`.

**Saving** is three steps, because the browser writes the file:

1. `GET /api/config/export` and remember `X-Config-Revision`.
2. Write the body with the browser's save dialog.
3. When the write succeeds, `POST /api/config/saved` with that revision and the name used.

Edits made between steps 1 and 3 stay marked unsaved.

**Renaming** a room, lab, faculty member, or course (the only section with that id)
updates every reference to it in the same change.

## Generation

| Method and path | Body | Returns |
| --- | --- | --- |
| `POST /api/generation` | `{limit?, optimizer_flags?}` | 202 and the job status |
| `GET /api/generation` | | The job status |
| `POST /api/generation/cancel` | | The job status |

Omitted or `null` overrides use the configured value. `optimizer_flags` is the complete
list for the run, so `[]` turns optimization off. Overrides never change the configuration.

**Most schedules per run.** `GET /api/config/options` has `generation.max_schedules`: `null`
for `zimpasta --gui` (no limit beyond the library's), and 5 in the browser version. When it
is set, a configured `limit` above it is lowered for the run (`settings.limit_capped` is
true and the message says so), and a `limit` override above it is refused with `422
invalid_overrides` and an issue with code `limit_above_maximum` on field `limit`. Use it as
the `max` of the schedule-count input.

Poll `GET /api/generation` (every half second is plenty) while `running` is true:

```json
{"state": "running", "running": true, "found": 3, "message": "Generating... 3 of 5 schedules found.",
 "settings": {"limit": 5, "optimizer_flags": ["faculty_course"], "configured_limit": 100,
              "configured_optimizer_flags": ["faculty_course", "pack_rooms"],
              "limit_overridden": true, "optimizer_flags_overridden": true,
              "max_limit": null, "limit_capped": false},
 "config_name": "sample_config.json", "config_revision": 4, "started_at": "...", "elapsed_seconds": 6.2,
 "finished_at": null, "detail": null, "completion_reason": null, "cancel_requested": false}
```

`state` ends as `succeeded` (the schedules are now in `/api/schedules`), `infeasible`,
`solver_error`, `failed` (`detail` has specifics), or `cancelled`. Only `succeeded`
replaces the schedules. Cancelling takes effect after the schedule in progress.

In the browser version, Python is busy while it solves a schedule, so requests made then
(including these polls) are answered when that schedule is done, typically 5 to 20
seconds. Show progress from `found` rather than expecting steady updates.

## Schedules

| Method and path | Returns |
| --- | --- |
| `GET /api/schedules` | `{count, source, name, created_at, schedules: [{number, sections, faculty, rooms, labs}]}`; generated sets also carry `limit`, `optimizer_flags`, `completion_reason` |
| `GET /api/schedules/{number}?group=room\|faculty` | `{number, count, group, totals, groups}` |
| `POST /api/schedules/import` with `{filename, content}` | The summary |
| `GET /api/schedules/export?format=json\|csv&which=all\|N` | The file, with its name in `Content-Disposition` |
| `DELETE /api/schedules` | The empty summary |

Schedule numbers start at 1. Each group in a view is
`{name, kind, sections, meeting_count, meetings}`: `kind` is `room`, `lab`, `online`, or
`unassigned` when grouped by room, and `faculty` otherwise. Each meeting has `course`,
`course_id`, `section`, `faculty`, `room`, `lab`, `day` (`MON`...), `day_number`, `start`
and `end` (minutes), `start_time` and `end_time` (`HH:MM`), `duration`, `kind`
(`lecture` or `lab`), `delivery`, `other` (the faculty member in the room view, the room
or lab in the faculty view), and `room_held_for_lab` (a lab meeting shown under the room
the section keeps reserved).

## Assistant

The AI chat ([assistant.md](assistant.md)). The transcript is kept by the server, so every
page shows the same one.

| Method and path | Body | Returns |
| --- | --- | --- |
| `GET /api/chat` | | `{entries, busy, available, reason, model}` |
| `POST /api/chat` | `{message}` (1-4000 characters) | `{added, state}`: the entries this message added, and the app state |
| `POST /api/chat/pending/{id}` | `{answer, filename?}` | `{added, state}` |
| `DELETE /api/chat` | | `{added: [], state}`; the transcript is empty |

`POST /api/chat` returns when the assistant has finished, after any tool calls, typically a
few seconds. Requests that can't start are errors: `503 ai_not_configured` (no key) or
`409 chat_busy`. If OpenAI fails partway, the reply is still `200`, and its last entry is
a `notice` with `error.code` `ai_unavailable` that says which actions, if any, already
ran.

`answer` is `confirm` or `cancel` for a `confirm` entry, and `saved` (with the file name)
or `cancel` for a `save` entry. A confirmation whose configuration changed since it was
proposed is not applied; it is answered with a `notice` whose `error.code` is
`pending_expired`. Entry fields are described in [assistant.md](assistant.md#the-chat-panel-and-the-api).

