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

The shell is a REPL with a command prompt. A complete command runs immediately:

```
> modify course "CS 101" credits 4
> run schedule --limit 5 --optimize yes --format csv --output out
```

A bare verb, or a command missing required parts, starts that command's interactive
prompts for whatever is missing, shows the command it constructed, and runs it:

```
> run
Config file to use [none]: examples/sample_config.json
Maximum number of schedules [3]: 5
...
Running: run schedule --config examples/sample_config.json --limit 5 --optimize yes --format csv --output out
```

`help` lists every command with its usage, `help <verb>` shows one, and `quit` leaves.
Identifiers with spaces are quoted shell-style (`"CS 101"`). Backslashes are ordinary
characters, so Windows paths need no quoting or escaping.
`examples/sample_config.json` is a small valid configuration for trying things out.

## Commands

| Command | Purpose |
| --- | --- |
| `load <path>` | Load a configuration file |
| `add <course\|room\|lab\|faculty> <id> ...` | Add an item (owner defines its fields) |
| `modify <course\|room\|lab\|faculty> <id> <field> [<value>]` | Change one field of an item |
| `delete <course\|room\|lab\|faculty> <id> [--section N]` | Remove an item |
| `run schedule [--config PATH] --limit N --optimize yes\|no --format csv\|json --output FILE [--overwrite]` | Generate schedules and export them |
| `schedules summary` / `show <n>` / `export <n>\|all --format F --output FILE [--overwrite]` / `clear` | Work with the generated set |
| `display ...` | Display schedules (owner defines the arguments) |
| `help [<command>]`, `quit` | Shell |

Options are `--name value` (or `--name=value`); flags like `--overwrite` take no value.
Verbs, nouns, and choice values are case-insensitive.

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
  cli.py            entry point: welcome page, command prompt, PLACEHOLDERS (swap yours in)
  command.py        CommandSpec / Invocation / Registry and evaluate(), the one execution path
  session.py        Session: state shared by every command (config, config_path, ...)
  console.py        Console protocol (ask / say) and the stdin/stdout implementation
  prompts.py        validated prompts: ask_int, ask_yes_no, ask_choice, ask_menu, fixed messages
  welcome_page.py   the welcome banner
  commands/         one module per feature exposing SPECS; help.py is the help command
tests/
  conftest.py       fixtures: config_data, config, config_file (all from the sample)
  helpers.py        ScriptedConsole for driving a command from a list of answers
examples/
  sample_config.json
```

## Adding your feature

1. Branch from `develop`: `git switch -c feat/<your-feature> develop`.
2. Create `src/zimpasta/commands/<feature>.py` with a `SPECS` tuple of `CommandSpec`s.
   Each spec declares the grammar (positionals and options), a **handler**
   `(console, session, invocation) -> None` that does the work for a complete command and
   never prompts for arguments, and a **builder** `(console, session, invocation) ->
   Invocation | None` that asks for whatever required values are missing (use
   `invocation.missing()` and `invocation.with_values(...)`) and returns `None` if the
   user cancels. Read values with `invocation.get("name")`.
3. In `src/zimpasta/cli.py`, replace your placeholder in `PLACEHOLDERS` with your `SPECS`.
   Keep the grammar the placeholder shows unless the team agrees to change it.
4. Test with `ScriptedConsole` from `tests/helpers.py`: call `evaluate(console, session,
   "your command line", Registry(SPECS))` for the direct path and a bare verb for the
   builder path, then assert on `console.output` and the `Session`. The `config` and
   `config_file` fixtures give you a valid configuration to start from.
5. Use the library, do not copy it: `CombinedConfig` and its nested models, their
   validation, `Scheduler`, and `scheduler.writers` are the source of truth.
   `CombinedConfig.edit_mode()` applies a group of changes atomically and rolls back on a
   validation error. Never read `examples/sample_config.json` from a command; work on
   `session.config`.

## Conventions

- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/):
  `feat:`, `fix:`, `test:`, `docs:`, `chore:`.
- Open pull requests against `develop` and fill in `.github/PULL_REQUEST_TEMPLATE.md`.
- Keep `uv.lock` committed and run `uv sync` after pulling.

## Feature notes

- [docs/run-scheduler.md](docs/run-scheduler.md): schedule generation, in-session results,
  and JSON/CSV export.
