# Building on the GUI

The GUI is the **View** in our MVC design: a React app in `frontend/`, written in plain
JavaScript and built with Vite. It shows things and collects input. It never validates
scheduler data or runs workflows itself: every action goes to the Python **Controller**
through the JSON API ([web-api.md](web-api.md)), and the **Model** asks the scheduler library.

## Running it while you work

```bash
cd frontend
npm run dev
```

This starts two processes: the Python API on port 8765 (`npm run dev:api`, which runs
`uv run zimpasta --gui --no-browser --port 8765`) and Vite on port 5173 (`npm run dev:web`),
at http://localhost:5173 (open it yourself), which reloads the page as you save. Vite forwards `/api` to
the Python server. Python changes need `npm run dev` restarted; React changes don't.

Before pushing: `npm run lint` and `npm run build` in `frontend/`, and `uv run pytest` at the
root.

## Two backends, one GUI

The same GUI is built two ways. `npm run build` and `npm run dev` talk to the Python server
(`zimpasta --gui`). `npm run build:browser` makes the browser version hosted on Cloudflare
Pages: Python runs in the page, in a Web Worker, and answers the same routes
(docs/cloudflare-pages.md). `api/backend.js` picks the backend when Vite builds, and
`api/client.js` is the same for both, so **modes don't need to know which one they run
on**. Keep using `api.*` for everything and it works in both.

What differs for a mode in the browser version:

- A run generates at most `options.generation.max_schedules` schedules (5). Read it from
  `api.config.options()` and use it as the `max` of the schedule-count input; it is `null`
  on the server.
- While a schedule is being solved, calls wait until it's done (5 to 20 seconds). Show
  progress from `state.generation.found`.

To try the browser version: `npm run build:browser`, then `npm run preview:browser`, and
open http://localhost:4173. `npm run test:browser` runs its Python in Node.

## Where things are

```
frontend/src/
  main.jsx            loads fonts and styles, renders the router
  router.jsx          routes: /editor, /generator, /viewer (and / → /editor)
  App.jsx             the frame: app state, toasts, header, current page
  modes.js            the three modes, in tab order
  api/client.js       every API call, and ApiError
  api/backend.js      where calls go: the server, or Python in the browser (api/browser/)
  files.js            pickFile() and saveFile(): the browser's open and save dialogs
  format.js           shared wording: plural(), clockTime(), configStatus(), describeCounts()
  state/
    AppStateProvider.jsx, appStateContext.js   polls GET /api/state; useAppState()
    useAction.js      runs an API call for a button, ignoring double clicks
    ToastProvider.jsx, toastContext.js         useToast() for success confirmations
  components/         shared building blocks (below)
  layout/             header, connection banner, error and not-found pages, and the
                      browser version's start-up notice (BrowserSession.jsx)
  modes/
    editor/ConfigEditor.jsx          Configuration Editor
    generator/ScheduleGenerator.jsx  Schedule Generator
    viewer/ScheduleViewer.jsx        Schedule Viewer
  styles/             tokens.css (colors, spacing, fonts from the mockups) and component CSS
frontend/scripts/     build-browser.mjs and test-browser.mjs, for the browser version
```

Each mode owns its folder. Split a mode into more files there (`RoomCard.jsx`,
`FacultyDialog.jsx`, ...) rather than growing one file. If two modes need the same piece,
move it to `components/`.

## Components

| Component | Use it for |
| --- | --- |
| `PageHeader` | Each mode's title row: title, one line of context, page actions |
| `Card` | A bordered section with a title row (`title`, `meta`, `actions`, `footer`) |
| `Button` | `variant="primary"` for the page's main action, `"danger"` for destructive ones, `"ghost"` for links; `busy` while its action runs |
| `Badge`, `StatusPill` | Short labels and status like "Valid · saved"; the text carries the meaning, color only reinforces it |
| `Banner` | A message across a section; `tone` is info, success, warning, or danger, and `title` states it in words |
| `ErrorMessage` | Show a failed call: the server's message plus every located issue |
| `IssueList`, `issuesFor()` | List issues, or pick the ones for one field to show next to it |
| `Field`, `HelpTip` | A labelled control with required marker, help, and its error, all wired for screen readers |
| `Dialog`, `ConfirmDialog` | Modal dialogs; `ConfirmDialog destructive` for deletes, clears, and discards |
| `UnsavedChangesPrompt` | Put in a page with a form draft; asks before switching modes or closing the tab |
| `SegmentedControl` | A small one-of-a-few toggle, like Room & lab / Faculty |
| `EmptyState`, `Spinner` | Nothing to show yet (with an optional `mark` icon), or loading |
| `Farfalle`, `Penne`, `Rotelle`, `Lasagna`, `Ravioli` | Small pasta-shaped line icons from `PastaMarks.jsx`, a nod to the team's name. Decorative only (hidden from screen readers); they take the text color, so set it with a token |

## Patterns

**Read shared state with `useAppState()`.** It gives `state` (the latest `GET /api/state`:
configuration status and counts, generation progress, schedule counts), `loading`,
`connectionError`, and `refresh()`. It polls every 3 seconds, and every 0.6 seconds while
schedules are being generated, so the Generator can show progress by reading
`state.generation`. Call `refresh()` after your own actions so the header updates at once.

**Fetch what your page shows** with `api.*` calls in your mode (for example
`api.config.get()` for the whole document, or `api.schedules.view(n, "faculty")`). Refetch
after changes; every configuration change also returns the new `document`.

**Run actions with `useAction`:**

```jsx
const validate = useAction(() => api.config.validate());

<Button busy={validate.busy} onClick={async () => {
  const result = await validate.run();
  if (result.ok) { notify({ title: "Valid.", message: "..." }); refresh(); }
}}>Validate</Button>
<ErrorMessage error={validate.error} onDismiss={validate.clearError} />
```

`run()` ignores clicks while the call is in flight and never throws; failures land in
`error`, which is an `ApiError` with `code`, `message`, and `issues`.

**Edit in a draft, apply through the API.** Keep form values in component state (a copy of
the item from the document). *Cancel* just drops the copy. *Validate & apply* sends the whole
item with `api.config.replace(area, index, item)` (or `add`). If the library rejects it, the
reply is `edit_rejected` with issues located by `area`, `index`, and `field`; show them next to
the fields with `issuesFor(error.issues, { area, index, field })`, keep the draft open, and
nothing has changed on the server. While a draft differs from the applied item, render
`<UnsavedChangesPrompt when={isDirty} />`.

**Deletes preview first.** Call `api.config.deleteImpact(area, index)`. If `can_delete` is
false, show `blocking` (and `problems`) and change nothing. Otherwise list `cascades` in a
`ConfirmDialog destructive` and call `api.config.remove(area, index)` on confirm.

**Unsaved changes on New and Load.** Call `api.config.load({ filename, content })` with the
file from `pickFile()`. If the error `code` is `unsaved_changes`, `error.extra.changes` lists
them: show them in a `ConfirmDialog` and, if the user agrees, call again with
`discardChanges: true`.

**Saving files** takes three steps so a cancelled or failed save never marks anything saved:

```js
const file = await api.config.exportFile();                 // { content, filename, revision }
const saved = await saveFile({ suggestedName: file.filename, content: file.content });
if (saved) await api.config.markSaved({ revision: file.revision, filename: saved.name });
```

Schedule export is the same without `markSaved`:
`api.schedules.exportFile({ which: "all" | n, format: "json" | "csv" })`.

**Confirm success, explain failure.** After something succeeds, say so: `useToast()` for a
short confirmation, or update the page visibly. Show failures inline, next to what failed, in
the user's words. Don't ask anyone to look in the terminal.

## Rules that keep MVC honest

- No scheduler rules in components. Don't re-check capacities, credit ranges, time formats,
  or references in JavaScript beyond simple input hints (`type="number"`, `min`, required
  markers). The library decides; show what it says.
- No workflows in components. If an action needs several server steps or a decision the
  server should make, add a method to `AppController` and a route in `routes.py`, with pytest
  tests, and call that one route.
- Only `api/client.js` builds URLs. Add a function there when you add a route. Don't call
  `fetch("/api/...")` directly: the browser version has no server to answer it.
- The model and controller also run in the browser, on Pyodide, so they can't start
  threads or processes or open files. The browser version can't run anything that does.
- Use the design tokens in `styles/tokens.css`, not raw colors, so the modes look alike.
- Keep the pasta touches quiet. So far they are the farfalle brand mark, one mark per empty
  state (penne for the Editor, rotelle for the Generator, lasagna for the Viewer), the
  spinner's spaghetti twirl, and the rippled underline on the active tab. Draw new ones
  the same way: 24×24 line art with a 1.6 stroke in `currentColor`.
- Controls need labels (use `Field`), destructive actions need `variant="danger"` and a
  confirmation, and nothing may rely on color alone.
