# Dr. ZImpasta

An interactive shell for building course-scheduling configurations, generating schedules,
and exporting the results. All scheduling logic comes from the
[course-constraint-scheduler](https://github.com/mucsci/scheduler) library (PyPI
`course-constraint-scheduler`, import name `scheduler`). This repo only adds the shell.

## Setup

1. Install [uv](https://docs.astral.sh/uv/) (`brew install uv` on macOS).
2. From the repo root:

```bash
uv sync
```

That creates `.venv` with Python 3.12 (uv downloads it if needed), the library, and the dev
tools. You never need to activate the venv; prefix commands with `uv run`.

## Run

```bash
uv run zimpasta
```

`examples/sample_config.json` is a small valid configuration for trying things out.

## Check before you push

CI runs exactly these on Linux, macOS, and Windows:

```bash
uv run ruff format --check .
uv run ruff check .
uv run pytest
```

`uv run ruff format .` fixes formatting in place.

## Layout

```
src/zimpasta/
  cli.py            entry point: banner, main menu, dispatch (replace your MENU line)
  session.py        Session: state shared by every command (config, config_path, ...)
  console.py        Console protocol (ask / say) and the stdin/stdout implementation
  prompts.py        validated prompts: ask_int, ask_yes_no, ask_menu, fixed messages
  commands/         one module per feature; each exposes (console, session) -> None
tests/
  conftest.py       fixtures: config_data, config, config_file (all from the sample)
  helpers.py        ScriptedConsole for driving a command from a list of answers
examples/
  sample_config.json
```

## Adding your feature

1. Branch from `develop`: `git switch -c feat/<your-feature> develop`.
2. Put your command in `src/zimpasta/commands/<feature>.py` as a function
   `def <feature>(console: Console, session: Session) -> None`. Read and update the
   `Session`; talk to the user only through the `Console`; use `zimpasta.prompts` so
   invalid input re-prompts instead of raising. Add fields to `Session` if your feature
   needs state between commands.
3. Replace your placeholder line in `MENU` in `src/zimpasta/cli.py`.
4. Test it with `ScriptedConsole` from `tests/helpers.py`: pass the answers a user would
   type, then assert on `console.output`. The `config` and `config_file` fixtures give you a
   valid configuration to start from.
5. Use the library, do not copy it: `CombinedConfig` and its nested models, their
   validation, `Scheduler`, and `scheduler.writers` are the source of truth.
   `CombinedConfig.edit_mode()` applies a group of changes atomically and rolls back on a
   validation error.

## Conventions

- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/):
  `feat:`, `fix:`, `test:`, `docs:`, `chore:`.
- Open pull requests against `develop` and fill in `.github/PULL_REQUEST_TEMPLATE.md`.
- Keep `uv.lock` committed and run `uv sync` after pulling.

## Feature notes

- [docs/run-scheduler.md](docs/run-scheduler.md): schedule generation, in-session results,
  and JSON/CSV export.
