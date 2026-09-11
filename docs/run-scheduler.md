# Run the scheduler

Owner: Sean Funk. Covers sprint requirement sections 8 (schedule generation), 9 (in-session
schedule management), and 10 (export).

## Modules

| Module | Responsibility |
| --- | --- |
| `zimpasta/generate.py` | Builds a validated run copy of the config, drives `Scheduler.get_models()`, classifies the outcome. |
| `zimpasta/results.py` | `ScheduleStore`: the generated set kept in the session (replace, get, clear). |
| `zimpasta/view.py` | Plain-text summary and per-schedule table. The display feature may replace it. |
| `zimpasta/export.py` | JSON and CSV export through `scheduler.writers`, with overwrite protection. |
| `zimpasta/prompts.py` | Validated prompts and the fixed message strings. |
| `zimpasta/commands/run.py` | The "Run Schedule" flow. |
| `zimpasta/commands/results.py` | Summary, inspect, export, clear for the current results. |
| `zimpasta/cli.py` | Wires `Run Schedule` and `Generated schedules` into the shared main menu. |

Nothing here duplicates library models or validation. The library is the source of truth for
`CombinedConfig`, `CourseInstance`, the writers, and every validation rule.

## Seams with other features

**Config loading (Foster).** `zimpasta/config_loader.py` holds one stub function,
`load_config(path) -> CombinedConfig`, wrapping the library's `load_config_from_file`. Replace
the body and keep the signature and the documented exceptions (`OSError`,
`json.JSONDecodeError`, `pydantic.ValidationError`). The run command stores a successfully
loaded config on `Session.config` and `Session.config_path`; on any failure the session is
untouched.

**Display (Mohamed).** `Session.results` is a `ScheduleStore` holding one `GenerationResult`:
`schedules` (a list of `list[CourseInstance]`), `limit`, `optimizer_flags`, `completion_reason`,
`generated_at`, and `config_path`. `view.summarize()` and `view.format_schedule()` are the
minimal renderers the commands use; richer display can consume the same objects.

**Shell dispatch.** `run_schedule(console, session)` and `manage_results(console, session)` are
plain functions wired into `MENU` in `zimpasta/cli.py`. `Console` is a two-method protocol (`ask`, `say`), so the shell can host them
however it likes and tests script them.

## The "Run Schedule" flow

```
Config file to use [none]:                 <- Enter keeps the loaded config, if any
Maximum number of schedules [10]:          <- Enter keeps the config's limit
Optimize? (yes/no):
Output format (csv/Json):
Output file name:
Generating up to 10 schedule(s) with optimization...
  schedule 1 of 10 found
  ...
Generated 10 schedule(s).
Wrote 10 schedule(s) to /abs/path/out.csv
```

Fixed messages from the acceptance scenarios, used verbatim:

| Situation | Message |
| --- | --- |
| Invalid menu option | `Invalid choice.` then the menu is shown again |
| Non-numeric schedule limit | `Please enter numerical characters only.` |
| Unsupported output format | `Unsupported format. Choose csv or Json` |
| Unwritable output file name | `Cannot make a scheduler to that file name`, then the prompt `Type a valid filename.` |
| Invalid optimization choice | `Invalid option. Please choose yes or no.` |

Format and yes/no answers are case-insensitive (`csv`, `CSV`, `Json`, `JSON`, `y`, `YES`, `n`).
No invalid input ends the session; Ctrl-D or Ctrl-C inside the flow prints `Run cancelled.` and
returns to the menu.

### Optimization

"yes" uses the configuration's `optimizer_flags`, or every flag when the configuration lists
none. "no" runs with no optimizer flags. Either way the session's configuration is not changed:
the run uses a validated deep copy.

### Limit

The prompt defaults to the configuration's `limit`; typing a number overrides it for this run only.

### Outcomes

| Outcome | What the user sees | Session |
| --- | --- | --- |
| Success | `Generated N schedule(s).` then `Wrote N schedule(s) to <path>` | results replaced |
| Fewer than requested | `Generated N of M requested schedule(s); the solution space is exhausted.` | results replaced |
| No feasible schedule | `No feasible schedule exists for this configuration.` and `Nothing was written to <path>.` | unchanged |
| Solver timeout | `The solver timed out before finding a schedule. Try a simpler configuration.` | unchanged |
| Invalid configuration | `Invalid configuration. Nothing was generated.` plus one line per error | unchanged |
| Unexpected runtime error | `Unexpected error while generating schedules: <type>: <message>` | unchanged |

Every solver check runs with a 60-second Z3 timeout (`DEFAULT_SOLVER_TIMEOUT_MS`) so a hard
problem reports a timeout instead of hanging, and each schedule prints a progress line as it
arrives.

## Export and overwrite protection

Both formats go through the library's `JSONWriter` and `CSVWriter` and are written as UTF-8.
A name without the chosen format's extension gets it appended (`out` becomes `out.csv`).
The reported location is the absolute path.

Overwrite protection is confirm-or-refuse:

1. At the file-name prompt, an existing file asks `File '<path>' already exists. Overwrite?
   (yes/no):`. `no` returns to the file-name prompt.
2. `export_schedules()` refuses to replace a file unless `overwrite=True`. Without it, the path
   is claimed with an exclusive create, so a file that appeared between the prompt and the
   write is still caught and the user is asked again.
3. A write failure removes the claimed empty file, prints `Cannot make a scheduler to that file
   name`, and re-prompts with `Type a valid filename.`. Generated results stay in the session,
   so the export can be retried from the "Generated schedules" menu.

## Generated schedules menu

```
Generated schedules
  1) View summary
  2) Inspect a schedule
  3) Export schedules
  4) Clear results
  5) Back
```

Inspecting shows course, faculty, room, lab, and meeting times per section, with the lab
meeting marked `(lab)`. Export offers the whole set or one schedule, then the same format,
file-name, and overwrite prompts as the run flow.

## Testing

```
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

The suite runs one real solve on a two-course fixture (well under a second) and reuses its
schedules as canned output for a fake scheduler everywhere else.
