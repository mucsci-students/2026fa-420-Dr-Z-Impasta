# Accounts and saved states

Users can create an account, log in, and keep several **states** of the application in it.
A state is one configuration with its schedules, such as a Biology department's
configuration and the schedules generated from it. Users switch between states, and
everything is still there after logging out and back in.

This is the Sprint 4 team feature. This document covers the backend (Model, Controller,
and API); the GUI calls it through `api.account` and `api.states` in
`frontend/src/api/client.js`.

## The feature

**User problem.** A scheduler user works on several departments or terms at once. Before
this feature, the app held one configuration in memory, and the user had to save and
re-load JSON files by hand to move between them. Closing the app lost any unsaved work.

**Workflow.**
1. Sign up with a username and password. Whatever is open becomes the account's first
   state ("My first state"), so nothing is lost.
2. Work as usual. Every applied edit, finished generation, schedule import, and clear is
   saved to the open state automatically, whether it came from the editor, the generator,
   the viewer, or the AI assistant.
3. Create a new state, such as "Computer Science". It opens empty, or as a copy of the
   open state. Load or build its configuration there.
4. Switch between states. The open one is saved first, then the other one opens with its
   configuration, its unsaved changes (relative to its JSON file), and its schedules.
5. Rename or delete states. The open state can't be deleted.
6. Log out. The open state is saved and closed. Logging in again reopens the state that
   was open last.

**Acceptance criteria.**
- A user can sign up, log in, and log out. Wrong passwords and unknown usernames get the
  same message. Passwords are stored only as salted scrypt hashes.
- A logged-in user can create, rename, delete, list, and switch between their states.
- Each state keeps its configuration (including unsaved-change tracking against its JSON
  file) and its schedules (generated or imported, with their settings).
- Changes made through any interface are saved to the open state without a manual step.
- States persist across logging out and in, and across restarting the app.
- One user can never see or change another user's states.
- If the database can't be reached, edits still apply, the app says the state isn't
  saved, and it saves again with the next change. Switching or logging out refuses to
  continue until the open state is saved, so nothing is lost.
- Logging in over unsaved work asks first, as loading a file does.
- The configuration library still validates everything: a state that no longer validates
  is refused when opened, and the open configuration is kept.

**Size: Large.**
- It adds persistent, multi-user storage to an app that until now had only in-memory
  state.
- It touches the Model (a new accounts package, change notifications on the workspace and
  schedule set, snapshot and restore of both), the Controller (nine routes and their
  errors), configuration (`.env`, a database driver), and the browser version (which must
  turn it off).
- It interacts with every workflow that changes state, including generation and the AI
  assistant, and needs locking so autosave can't deadlock with a switch.
- It needs failure handling for an external service, and tests that run without it.

**Effects.**
- **State:** the database is the record of each user's states. The workspace and schedule
  set remain the single in-memory copy of the open one.
- **Architecture:** new Model code in `src/zimpasta/model/accounts/`. Two patterns are
  added (below). The Controller only routes and guards. There is still one workspace per
  running app.
- **Testing:** every routine test uses an in-memory SQLite store. One opt-in live test
  uses the real database.

## Setting it up

The app connects to a PostgreSQL database; the team uses [Neon](https://neon.tech). In the
Neon console, open the project, choose **Connect**, and copy the connection string. It
looks like `postgresql://user:password@ep-...neon.tech/neondb?sslmode=require`. That is
the database credential, not a Neon API key, which the app never needs.

Put it in a `.env` file at the repository root (`.env` is gitignored):

```
DATABASE_URL=postgresql://user:password@ep-example.us-east-2.aws.neon.tech/neondb?sslmode=require
OPENAI_API_KEY=...
```

`uv run zimpasta --gui` reads `.env` when it starts. Variables already set in the
environment take precedence. The tables (`zimpasta_users` and `zimpasta_states`) are
created on first use. Without `DATABASE_URL`, everything except accounts works as before,
and the account panel says how to set it up.

Everyone who runs the app with the same `DATABASE_URL` uses the same database. Share the
connection string only with the team and grader, and never commit or paste it anywhere
public.

## API

| Method and path | Body | Returns |
| --- | --- | --- |
| `GET /api/account` | | `{available, reason, user, state, sync}` |
| `POST /api/account/signup` | `{username, password, discard_changes?}` | `{states, state}` |
| `POST /api/account/login` | `{username, password, discard_changes?}` | `{states, state}` |
| `POST /api/account/logout` | | `{states: [], state}` |
| `GET /api/states` | | `{states, account}` |
| `POST /api/states` | `{name, copy_current?}` | 201, `{states, state}`: the new state is open |
| `POST /api/states/{id}/open` | | `{states, state}` |
| `PATCH /api/states/{id}` | `{name}` | `{states, account}` |
| `DELETE /api/states/{id}` | | `{states, account}` |

- `state` in a reply is the full app state from `GET /api/state`, so the GUI can redraw
  every mode after a switch. The polled app state includes the same `account` block.
- Each entry in `states` is `{id, name, created_at, updated_at, current}`.
- `sync` is `{status, saved_at, error}`, where `status` is `idle` (logged out), `saved`,
  or `failed`. With `failed`, `error` says why, and the next change retries.

Errors use the usual shape:

| Status | `code` | When |
| --- | --- | --- |
| 400 | `invalid_account_input` | Username: 3 to 32 letters, digits, `.`, `_`, `-`. Password: 8 to 128 characters. State name: 1 to 60 characters |
| 401 | `invalid_credentials` | Wrong username or password; one message for both |
| 401 | `not_logged_in` | A state route without logging in |
| 404 | `state_not_found` | No such state for this user |
| 409 | `username_taken`, `state_name_taken` | Already in use |
| 409 | `state_in_use` | Deleting the open state |
| 409 | `unsaved_changes` | Logging in would replace unsaved work; send again with `discard_changes: true` |
| 409 | `generation_running`, `chat_busy` | Logging in or out, creating, or switching while a run or a chat message is in progress |
| 503 | `accounts_unavailable` | No `DATABASE_URL`, or the browser version |
| 503 | `account_storage_failed` | The database couldn't be reached |

Logging in or out also clears the AI chat transcript, so the next person never sees it.

## Code

| File | Contents |
| --- | --- |
| `model/accounts/service.py` | `AccountService`: sign up, log in and out, autosave, and create, switch, rename, and delete states |
| `model/accounts/records.py` | `AccountStore` (the repository interface), the record types, and the errors |
| `model/accounts/sql_store.py` | `SqlAccountStore` on SQLAlchemy Core: PostgreSQL through psycopg for Neon, SQLite for tests |
| `model/accounts/passwords.py` | Salted scrypt hashing, constant-time checks |
| `model/observable.py` | `Subject`, the Observer pattern's base |
| `model/workspace.py`, `model/schedules.py` | Change notifications, and `record()` / `restore()` |
| `controller/app_controller.py`, `routes.py`, `errors.py` | The account methods, routes, and statuses |

**Patterns added in Sprint 4:**
- **Observer:** `ConfigWorkspace` and `ScheduleSet` are subjects, and `AccountService` is
  their observer. Every change is saved however it was made, without the editor, the
  generator, the viewer, or the AI tools knowing that accounts exist.
- **Repository:** `AccountStore` gives the service users and states by meaning ("the
  states of this user"), and `SqlAccountStore` hides SQL. The same service runs on Neon
  in the app and on SQLite in tests.

Concurrency: the service uses the workspace's own lock. So an edit's autosave (which runs
inside the edit) and a switch from another request can't wait on each other.

## Tests

- `tests/model/accounts/` covers passwords, the store, and the service, all on in-memory
  SQLite: rules, isolation between users, autosave, switching, persistence, and failures.
- `tests/model/test_observable.py` covers notifications and record/restore.
- `tests/controller/test_accounts_api.py` covers the routes.
- `tests/test_browser.py` checks that accounts are off in the browser version.
- `tests/live/test_accounts_live.py` creates a throwaway account in the real database,
  checks its states persist through a new connection, and deletes it. It runs only with
  `uv run pytest -m live` and `DATABASE_URL` set (from the environment or `.env`).

## Limitations

- One logged-in user per running app, matching its single workspace. Two people use two
  copies of the app.
- No password reset, account deletion screen, or email. An administrator can delete a user
  in the database, which deletes their states.
- The browser (Cloudflare) version has no accounts.
- The AI chat transcript is not part of a state.
- Each autosave writes the whole state. That's fine for configurations of this size, and
  it adds the database round trip to each edit.
