# Run the scheduler

Owner: Sean Funk. Covers sprint requirement sections 8 (schedule generation), 9 (in-session
schedule management), and 10 (export).

## Commands

```
run schedule [--config PATH] --limit N --optimize yes|no --format csv|json --output FILE [--overwrite]
schedules summary
schedules show <number>
schedules export <number|all> --format csv|json --output FILE [--overwrite]
schedules clear
```

A complete command line runs immediately. `run` alone (or any line missing a required
option) goes through the builder, which asks the acceptance-scenario prompts for whatever
was left out, echoes the command it constructed, and runs it:

```
> run
Config file to use [none]: examples/sample_config.json
Maximum number of schedules [100]: 5
Optimize? (yes/no): yes
Output format (csv/Json): csv
Output file name: out
Running: run schedule --config examples/sample_config.json --limit 5 --optimize yes --format csv --output /abs/path/out.csv
Generating up to 5 schedule(s) with optimization...
  schedule 1 of 5 found
  ...
Generated 5 schedule(s).
Wrote 5 schedule(s) to /abs/path/out.csv
```

`run --limit 5 --format csv` asks only for the config, optimize, and output answers.
`schedules show` and `schedules export` have builders too; `schedules summary` and
`schedules clear` take no arguments.

## Modules

| Module | Responsibility |
| --- | --- |
| `zimpasta/generate.py` | Builds a validated run copy of the config, drives `Scheduler.get_models()`, classifies the outcome. |
| `zimpasta/results.py` | `ScheduleStore`: the generated set kept in the session (replace, get, clear). |
| `zimpasta/view.py` | Plain-text summary and per-schedule table. The display feature may replace it. |
| `zimpasta/export.py` | JSON and CSV export through `scheduler.writers`, with overwrite protection. |
| `zimpasta/prompts.py` | `ask_format` and `ask_output_path` alongside the shared prompt helpers. |
| `zimpasta/commands/run.py` | `run schedule`: handler, builder, and `make_specs()` for test injection. |
| `zimpasta/commands/results.py` | The four `schedules` commands. |
| `zimpasta/commands/export_flow.py` | The export step shared by both, with overwrite confirmation and write-failure re-prompts. |

Nothing here duplicates library models or validation. The library is the source of truth for
`CombinedConfig`, `CourseInstance`, the writers, and every validation rule.

## Seams with other features

**Config loading (Foster).** `zimpasta/config_loader.py` holds one stub function,
`load_config(path) -> CombinedConfig`, wrapping the library's `load_config_from_file`. Replace
the body and keep the signature and the documented exceptions (`OSError`,
`json.JSONDecodeError`, `pydantic.ValidationError`). `run schedule` stores a successfully
loaded config on `Session.config` and `Session.config_path`; on any failure the session is
untouched. `--config` is optional: without it the loaded configuration is used.

**Display (Mohamed).** `Session.results` is a `ScheduleStore` holding one `GenerationResult`:
`schedules` (a list of `list[CourseInstance]`), `limit`, `optimizer_flags`, `completion_reason`,
`generated_at`, and `config_path`. `view.summarize()` and `view.format_schedule()` are the
minimal renderers the commands use; richer display can consume the same objects.

**Shell.** Both modules expose `SPECS`; `zimpasta/cli.py` registers them in place of the
`run schedule` and `schedules` placeholders.

## Fixed messages

From the acceptance scenarios, used verbatim in the builder prompts:

| Situation | Message |
| --- | --- |
| Unknown command | `Invalid choice.` then the command list is shown again |
| Non-numeric schedule limit | `Please enter numerical characters only.` |
| Unsupported output format | `Unsupported format. Choose csv or Json` |
| Unwritable output file name | `Cannot make a scheduler to that file name`, then the prompt `Type a valid filename.` |
| Invalid optimization choice | `Invalid option. Please choose yes or no.` |

Format and yes/no answers are case-insensitive (`csv`, `CSV`, `Json`, `JSON`, `y`, `YES`, `n`),
and so are the `--format` and `--optimize` values. No invalid input ends the session; Ctrl-D or
Ctrl-C inside the prompts prints `Run cancelled.` and returns to the command prompt.

On a complete command line the same problems are reported as one-line errors instead of
prompts: `--limit must be a whole number of 1 or more.`, `--format must be one of: csv, json.`,
`No configuration is loaded. Pass --config PATH, or load one first.`, and the config-file
messages below.

### Optimization

`--optimize yes` uses the configuration's `optimizer_flags`, or every flag when the
configuration lists none. `--optimize no` runs with no optimizer flags. Either way the session's
configuration is not changed: the run uses a validated deep copy.

### Limit

The prompt defaults to the configuration's `limit`; `--limit` or a typed number overrides it for
this run only.

### Outcomes

| Outcome | What the user sees | Session |
| --- | --- | --- |
| Success | `Generated N schedule(s).` then `Wrote N schedule(s) to <path>` | results replaced |
| Fewer than requested | `Generated N of M requested schedule(s); the solution space is exhausted.` | results replaced |
| No feasible schedule | `No feasible schedule exists for this configuration.` and `Nothing was written to <path>.` | unchanged |
| Solver timeout | `The solver timed out before finding a schedule. Try a simpler configuration.` | unchanged |
| Invalid configuration | `Invalid configuration. Nothing was generated.` plus one line per error | unchanged |
| Unreadable or invalid config file | `Cannot read config file ...`, `... is not valid JSON ...`, or `... is not a valid configuration:` plus one line per error | unchanged |
| Unexpected runtime error | `Unexpected error while generating schedules: <type>: <message>` | unchanged |

Every solver check runs with a 60-second Z3 timeout (`DEFAULT_SOLVER_TIMEOUT_MS`) so a hard
problem reports a timeout instead of hanging, and each schedule prints a progress line as it
arrives.

## Export and overwrite protection

Both formats go through the library's `JSONWriter` and `CSVWriter` and are written as UTF-8.
A name without the chosen format's extension gets it appended (`out` becomes `out.csv`).
The reported location is the absolute path.

Overwrite protection is confirm-or-refuse:

1. In the prompts, an existing file asks `File '<path>' already exists. Overwrite?
   (yes/no):`. `no` returns to the file-name prompt; `yes` adds `--overwrite` to the
   constructed command.
2. On a complete command line, `--overwrite` replaces the file without asking; without it, an
   existing file triggers the same confirmation.
3. `export_schedules()` itself refuses to replace a file unless told to. It claims the path with
   an exclusive create, so a file that appeared between the prompt and the write is still
   caught and the user is asked again.
4. A write failure removes the claimed empty file, prints `Cannot make a scheduler to that file
   name`, and re-prompts with `Type a valid filename.`. Generated results stay in the session,
   so the export can be retried with `schedules export`.

## Testing

```
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

Command tests drive `evaluate()` with `ScriptedConsole`: bare `run` for every prompt path and
complete command lines for the direct path. The suite runs one real solve on the small fixture in `tests/fixtures/` and reuses its
schedules as canned output for a fake scheduler everywhere else; the shipped example is solved
once at limit 1 in `tests/test_examples.py`.
