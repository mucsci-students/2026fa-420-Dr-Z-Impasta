import pytest

from tests.helpers import ScriptedConsole
from zimpasta.command import (
    NOT_IMPLEMENTED,
    CommandError,
    CommandSpec,
    Invocation,
    Option,
    Positional,
    Registry,
    UnknownCommand,
    evaluate,
    tokenize,
)
from zimpasta.prompts import INVALID_CHOICE
from zimpasta.session import Session

KINDS = ("course", "room", "lab", "faculty")


def modify_spec(**overrides) -> CommandSpec:
    return CommandSpec(
        "modify",
        positionals=(
            Positional("kind", choices=KINDS),
            Positional("id"),
            Positional("field"),
            Positional("value", required=False),
        ),
        description="Change one field",
        **overrides,
    )


def run_spec(**overrides) -> CommandSpec:
    return CommandSpec(
        "run",
        "schedule",
        options=(
            Option("config"),
            Option("limit", required=True),
            Option("format", required=True, choices=("csv", "json")),
            Option("overwrite", flag=True),
        ),
        **overrides,
    )


def test_tokenize_keeps_quoted_ids_together():
    assert tokenize('modify course "CS 101" name') == ["modify", "course", "CS 101", "name"]
    assert tokenize("  ") == []


def test_tokenize_reports_unbalanced_quotes():
    with pytest.raises(CommandError):
        tokenize('modify course "CS 101')


def test_parse_positionals_normalizes_choices():
    invocation = modify_spec().parse(["Course", "CS 101", "name"])

    assert invocation.positionals == {"kind": "course", "id": "CS 101", "field": "name"}
    assert invocation.complete
    assert invocation.get("id") == "CS 101"
    assert invocation.get("value") is None


def test_parse_rejects_bad_choice_and_extra_arguments():
    with pytest.raises(CommandError, match="kind must be one of"):
        modify_spec().parse(["building", "x", "name"])
    with pytest.raises(CommandError, match="Too many arguments"):
        modify_spec().parse(["course", "x", "name", "value", "extra"])


def test_parse_options_flags_and_inline_values():
    invocation = run_spec().parse(["--limit", "5", "--format=CSV", "--overwrite"])

    assert invocation.options == {"limit": "5", "format": "csv", "overwrite": True}
    assert invocation.complete
    assert invocation.to_line() == "run schedule --limit 5 --format csv --overwrite"


def test_parse_option_errors():
    with pytest.raises(CommandError, match="Unknown option --speed"):
        run_spec().parse(["--speed", "9"])
    with pytest.raises(CommandError, match="--limit needs a value"):
        run_spec().parse(["--limit"])
    with pytest.raises(CommandError, match="--overwrite takes no value"):
        run_spec().parse(["--overwrite=yes"])
    with pytest.raises(CommandError, match="--format must be one of"):
        run_spec().parse(["--format", "xml"])


def test_missing_lists_required_positionals_and_options():
    assert modify_spec().parse(["course"]).missing() == ("id", "field")
    assert run_spec().parse([]).missing() == ("--limit", "--format")
    assert run_spec().parse(["--limit", "1", "--format", "json"]).missing() == ()


def test_with_values_and_to_line_quote_ids_with_spaces():
    partial = modify_spec().parse(["course"])
    full = partial.with_values({"id": "CS 101", "field": "name", "value": "Intro"})

    assert full.complete
    assert full.to_line() == "modify course 'CS 101' name Intro"
    assert partial.positionals == {"kind": "course"}


def test_usage_strings():
    assert modify_spec().usage == "modify <course|room|lab|faculty> <id> <field> [<value>]"
    assert run_spec().usage == (
        "run schedule [--config CONFIG] --limit LIMIT --format csv|json [--overwrite]"
    )


def test_registry_rejects_duplicates_and_lists_specs():
    registry = Registry([modify_spec(), run_spec()])

    assert len(registry) == 2
    assert [spec.name for spec in registry] == ["modify", "run schedule"]
    with pytest.raises(ValueError):
        registry.register(modify_spec())


def test_resolve_direct_verb_noun_and_case():
    registry = Registry([modify_spec(), run_spec()])

    spec, rest = registry.resolve(["MODIFY", "course", "x"])
    assert spec.name == "modify" and rest == ["course", "x"]

    spec, rest = registry.resolve(["run", "Schedule", "--limit", "2"])
    assert spec.name == "run schedule" and rest == ["--limit", "2"]

    spec, rest = registry.resolve(["run", "--limit", "2"])
    assert spec.name == "run schedule" and rest == ["--limit", "2"]


def test_resolve_unknown_verb_and_empty_line():
    registry = Registry([modify_spec()])

    with pytest.raises(UnknownCommand):
        registry.resolve(["frobnicate"])
    with pytest.raises(CommandError):
        registry.resolve([])


def test_resolve_asks_which_noun_when_several_exist():
    registry = Registry(
        [
            CommandSpec("schedules", "summary"),
            CommandSpec("schedules", "show", positionals=(Positional("number"),)),
        ]
    )
    console = ScriptedConsole(["nope", "show"])

    spec, rest = registry.resolve(["schedules"], console)

    assert spec.name == "schedules show" and rest == []
    assert console.prompts == ["schedules what? (summary/show): "] * 2
    assert INVALID_CHOICE in console.output

    with pytest.raises(CommandError, match="needs one of"):
        registry.resolve(["schedules", "bogus"], console)
    with pytest.raises(CommandError, match="needs one of"):
        registry.resolve(["schedules"])


def test_evaluate_runs_a_complete_command_without_the_builder():
    calls = []
    builder_calls = []
    spec = modify_spec(
        handler=lambda console, session, inv: calls.append(inv),
        builder=lambda console, session, inv: builder_calls.append(inv) or inv,
    )
    console = ScriptedConsole()

    evaluate(console, Session(), 'modify course "CS 101" name Intro', Registry([spec]))

    assert len(calls) == 1 and calls[0].get("id") == "CS 101"
    assert builder_calls == []
    assert console.output == []


def test_evaluate_uses_the_builder_for_a_partial_command():
    calls = []

    def builder(console, session, invocation):
        assert invocation.positionals == {"kind": "course"}
        return invocation.with_values({"id": console.ask("Course id: "), "field": "name"})

    spec = modify_spec(handler=lambda console, session, inv: calls.append(inv), builder=builder)
    console = ScriptedConsole(["CS 102"])

    evaluate(console, Session(), ["modify", "course"], Registry([spec]))

    assert calls[0].get("id") == "CS 102"
    assert console.output == ["Running: modify course 'CS 102' name"]


def test_evaluate_builder_cancel_skips_the_handler():
    calls = []
    spec = modify_spec(
        handler=lambda console, session, inv: calls.append(inv),
        builder=lambda console, session, inv: None,
    )

    evaluate(ScriptedConsole(), Session(), ["modify"], Registry([spec]))

    assert calls == []


def test_evaluate_without_builder_reports_missing_parts():
    spec = run_spec(handler=lambda console, session, inv: None)

    with pytest.raises(CommandError, match=r"Missing --limit, --format\. Usage: run schedule"):
        evaluate(ScriptedConsole(), Session(), "run schedule --config x", Registry([spec]))


def test_evaluate_builder_that_leaves_gaps_is_an_error():
    spec = run_spec(
        handler=lambda console, session, inv: None,
        builder=lambda console, session, inv: inv.with_values(options={"limit": "3"}),
    )

    with pytest.raises(CommandError, match="Still missing --format"):
        evaluate(ScriptedConsole(), Session(), "run", Registry([spec]))


def test_evaluate_placeholder_says_not_implemented():
    console = ScriptedConsole()

    evaluate(console, Session(), "modify course x name", Registry([modify_spec()]))

    assert console.output == [NOT_IMPLEMENTED.format(name="modify")]


def test_invocation_get_returns_flag_values():
    invocation = Invocation(run_spec(), options={"overwrite": True})

    assert invocation.get("overwrite") is True
    assert invocation.get("limit", "10") == "10"
