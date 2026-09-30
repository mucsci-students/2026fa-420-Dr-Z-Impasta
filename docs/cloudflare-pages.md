# The browser version on Cloudflare Pages

The hosted Dr. ZImpasta is the whole app running in the visitor's browser, with no server.
It is the same React GUI, and the same Python model and controller, compiled for the
browser:

- A Web Worker loads [Pyodide](https://pyodide.org) (Python compiled to WebAssembly) from
  its CDN.
- It installs z3 and the scheduler library, which both publish WebAssembly builds for
  that Pyodide version.
- It answers every `/api` request by calling our FastAPI app in process
  (`src/zimpasta/browser.py`).

Each browser tab is its own session.

`uv run zimpasta --gui` is unchanged and still the main way to run the GUI. The browser
version is a second build of the same code (`npm run build:browser`, see docs/gui.md).

## What's different in the browser

- **The first visit downloads about 15 MB** (Python, pydantic, FastAPI, z3). A notice
  explains the wait. Later visits use the browser's cache and start in about 5 seconds.
- **Solving is about 3× slower** than natively. The sample configuration's first schedule
  takes about 20 seconds, and each later one 6 to 9 seconds.
- **A run generates at most 5 schedules.** A larger configured `limit` is lowered for the
  run, and a larger override is refused (docs/web-api.md). With the sample configuration,
  a full run takes about 50 seconds.
- **While a schedule is being solved, other requests wait** until it's done. Cancel takes
  effect after the current schedule, as it does on the server.
- **Closing or reloading the tab ends the session.** The tab asks first when there are
  unsaved changes, a running generation, or generated schedules. Save and export to files
  as usual.

## Deployments

`.github/workflows/pages.yaml` builds the browser version and uploads it to the Cloudflare
Pages project `dr-zimpasta`:

| When | Published at |
| --- | --- |
| A pull request into `develop` is opened or updated | `https://<branch>.dr-zimpasta.pages.dev` (a preview; `/` in the branch name becomes `-`) |
| A push to `develop` (a merged pull request) | `https://dr-zimpasta.pages.dev` |

The pull request shows the preview link as a deployment, and the run's summary lists both
addresses. Every deployment also keeps its own permanent URL. Pull requests from forks
don't get the repository's secrets, so their deploy fails at its first step.

To check the browser version before pushing:

```bash
npm run build:browser
```

```bash
npm run preview:browser
```

Run both in `frontend/`, then open http://localhost:4173. `npm run test:browser` runs its
Python in Node and uses the API end to end; CI runs it on every push.

## Setup (done once)

1. A Cloudflare account owner created the project:
   `npx wrangler pages project create dr-zimpasta --production-branch=develop`.
2. They created an API token with **Account · Cloudflare Pages · Edit**. Either kind of
   token works: a user token (*My Profile → API Tokens*) or an account token (*Manage
   Account → Account API Tokens*). An account token without the Pages permission fails
   with `Authentication error [code: 10000]` on `.../upload-token`.
3. A repository admin added the `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` Actions
   secrets. Without them the workflow stops at its first step and says so.

## Removing it

Delete `.github/workflows/pages.yaml` and the `build:browser` and `test:browser` steps in
`ci.yaml`. Then delete the project in the Cloudflare dashboard (*Workers & Pages →
dr-zimpasta → Settings*) and revoke the token.
