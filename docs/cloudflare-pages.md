# Hosting the GUI on Cloudflare Pages

`.github/workflows/pages.yaml` builds `frontend/` and uploads the result to a Cloudflare
Pages project named `dr-zimpasta`. It is a way to share how the interface looks, not a
hosted version of the app: only the React build is on Pages. The API and the scheduler run
on your own computer (`uv run zimpasta --gui`) and accept connections from it alone, so on
Pages every mode shows the "Can't reach the Dr. ZImpasta server" banner, and nothing can be
loaded, edited, or generated there.

## Which branch deploys

The workflow runs on pushes to `develop` and `ci/cloudflare-pages`, but GitHub only runs a
workflow that exists in the pushed commit. Until `ci/cloudflare-pages` is merged, that
branch is the only one that deploys; after the merge, `develop` does, with no further
changes. Then delete the branch and remove it from the list in `pages.yaml`.

The project's production branch is `develop`, so:

| Pushed to | Published at |
| --- | --- |
| `develop` (after the merge) | `https://dr-zimpasta.pages.dev` |
| `ci/cloudflare-pages` (the test) | `https://ci-cloudflare-pages.dr-zimpasta.pages.dev` |

Each deploy also gets its own permanent URL, shown at the end of the run's log. If
`dr-zimpasta.pages.dev` is already taken, Cloudflare adds a suffix; `project create` prints
the real address.

## One-time setup

Someone with a Cloudflare account creates the project and a token:

1. Create the project, with `develop` as its production branch:

   ```bash
   npx wrangler login
   ```

   ```bash
   npx wrangler pages project create dr-zimpasta --production-branch=develop
   ```

2. In the Cloudflare dashboard, go to *My Profile → API Tokens → Create Token → Custom
   token* and grant **Account · Cloudflare Pages · Edit** for that account only.
3. Note the account ID (`npx wrangler whoami` prints it).

A repository admin then adds both as Actions secrets (*Settings → Secrets and variables →
Actions → New repository secret*): `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`. Until
they exist, the workflow fails at its first step and says which secrets are missing. Rerun
the failed job once they're added.

## Removing it

Delete `.github/workflows/pages.yaml`, then delete the project in the Cloudflare dashboard
(*Workers & Pages → dr-zimpasta → Settings*) and revoke the token.
