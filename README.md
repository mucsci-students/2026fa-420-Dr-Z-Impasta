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
> load examples/sample_config.json
> delete course "CMSC 476"
> run schedule --limit 5 --optimize yes --format csv --output out
```

A bare verb, or a command missing required parts, starts that command's interactive
prompts for whatever is missing, shows the command it constructed, and runs it:

```
> run
Config file to use [none]: examples/sample_config.json
Maximum number of schedules [100]: 5
...
Running: run schedule --config examples/sample_config.json --limit 5 --optimize yes --format csv --output out
```

`help` lists every command with its usage, `help <verb>` shows one, and `quit` leaves.
Identifiers with spaces are quoted shell-style (`"CS 101"`). Backslashes are ordinary
characters, so Windows paths need no quoting or escaping.
`examples/sample_config.json` is the scheduler library's own department example (17 course
sections, 9 faculty). Its limit is 100, so give `run` a small limit the first time; each
schedule takes a second or two.

A typical session: `load` a configuration, `print` it, edit it with `delete` (and `add` and
`modify` once they land), `save` it, `run schedule` to generate and export, then `display`
the exported file. `display` looks for `.csv` and `.json` files in the directory the shell
was started from, so export there.

## Commands

| Command | Purpose |
| --- | --- |
| `load <path>` | Load and validate a configuration file (bare `load` asks until a file loads) |
| `save <path>` | Save the loaded configuration as JSON (bare `save` offers the loaded file's path) |
| `print` | Show the loaded configuration in readable form |
| `add <course\|room\|lab\|faculty> <id>` | Not implemented yet; the placeholder keeps the agreed grammar |
| `modify <course\|room\|lab\|faculty> <id> <field> [<value>]` | Not implemented yet; the placeholder keeps the agreed grammar |
| `delete <course\|room\|lab\|faculty> <id> [--section N]` | Remove an item after a yes/no confirmation and strip references to it. `--section` picks between entries that share a name, such as two sections of one course. Bare `delete` offers menus |
| `run schedule [--config PATH] --limit N --optimize yes\|no --format csv\|json --output FILE [--overwrite]` | Generate schedules and export them (bare `run` asks for each value) |
| `schedules summary` / `show <n>` / `export <n>\|all --format F --output FILE [--overwrite]` / `clear` | Work with the schedules generated in this session |
| `display` | List the `.csv` and `.json` schedule files in the current directory and show the chosen one as tables |
| `help [<command>]`, `quit`, `exit` | Shell |

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
  cli.py            entry point: welcome page, command prompt, the command registry
  command.py        CommandSpec / Invocation / Registry and evaluate(), the one execution path
  session.py        Session: state shared by every command (config, config_path, results)
  console.py        Console protocol (ask / say) and the stdin/stdout implementation
  prompts.py        validated prompts (ask_int, ask_yes_no, ask_choice, ask_menu, ask_format,
                    ask_output_path) and the fixed acceptance-scenario messages
  welcome_page.py   the welcome banner
  config_loader.py  load_config(path): the one place a configuration file is read
  config_finder.py  ConfigFinder: look up courses, faculty, rooms, and labs by id or name
  generate.py       schedule generation through the library's Scheduler
  results.py        ScheduleStore: the generated schedules kept in the session
  view.py           text summary and table for the in-session schedules
  export.py         JSON and CSV export with overwrite protection
  commands/         one module per command, each exposing SPECS
    load_config.py, save_config.py, print_config.py    load, save, print
    delete.py                                          delete
    run.py, results.py, export_flow.py                 run schedule, schedules ...
    display_schedules.py                               display
    help.py                                            help
tests/
  conftest.py       fixtures: config_data, config, config_file (from tests/fixtures/)
  fixtures/         minimal_config.json: two courses, solved in milliseconds
  helpers.py        ScriptedConsole and a fake scheduler for driving commands in tests
examples/
  sample_config.json   the library's department example
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
3. In `src/zimpasta/cli.py`, replace your placeholder in `PLACEHOLDERS` with your `SPECS`
   (only `add` and `modify` are still placeholders). Keep the grammar the placeholder shows
   unless the team agrees to change it. `commands/delete.py` is a good model to follow.
4. Test with `ScriptedConsole` from `tests/helpers.py`: call `evaluate(console, session,
   "your command line", Registry(SPECS))` for the direct path and a bare verb for the
   builder path, then assert on `console.output` and the `Session`. The `config` and
   `config_file` fixtures give you a small valid configuration to start from. Keep tests on
   that fixture rather than `examples/sample_config.json` so the suite stays fast.
5. Use the library, do not copy it: `CombinedConfig` and its nested models, their
   validation, `Scheduler`, and `scheduler.writers` are the source of truth.
   `CombinedConfig.edit_mode()` applies a group of changes atomically and rolls back on a
   validation error. Never read `examples/sample_config.json` from a command; work on
   `session.config`, and leave writing it to disk to `save`.
6. A `course_id` is not unique: a configuration lists one entry per section, so the example
   has `CMSC 140` twice. Look items up with `ConfigFinder`, which returns every match, and
   decide how your command picks one (`delete` uses `--section`).

## Conventions

- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/):
  `feat:`, `fix:`, `test:`, `docs:`, `chore:`.
- Open pull requests against `develop` and fill in `.github/PULL_REQUEST_TEMPLATE.md`.
- Keep `uv.lock` committed and run `uv sync` after pulling.

## Feature notes

- [docs/run-scheduler.md](docs/run-scheduler.md): schedule generation, in-session results,
  and JSON/CSV export.
- The other commands are documented in their module docstrings: `commands/delete.py`
  (sections and reference stripping), `commands/display_schedules.py` (the CSV and JSON
  layouts it reads), and `commands/load_config.py`, `save_config.py`, `print_config.py`.
