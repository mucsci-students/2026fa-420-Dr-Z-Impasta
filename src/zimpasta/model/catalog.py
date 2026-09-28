"""Choices and help text for form controls, read from the scheduler library.

Dropdowns and checkboxes need the allowed values (weekdays, modalities, delivery modes,
optimizer flags) and the generator needs a sentence per optimizer flag. All of it comes
from the library so nothing drifts: enum values from its types, flag descriptions from
the docstrings it writes under each ``OptimizerFlags`` member. The full field-by-field
constraints are in the library's JSON Schema (``CombinedConfig.model_json_schema()``).
"""

import ast
import inspect
import textwrap
import typing
from functools import cache

from scheduler import CombinedConfig, CourseModality, Day, DeliveryMode, OptimizerFlags


@cache
def configuration_schema() -> dict:
    """The library's published JSON Schema for a complete configuration."""
    return CombinedConfig.model_json_schema()


@cache
def weekdays() -> tuple[str, ...]:
    """``("MON", ..., "FRI")``, from the library's ``Day`` type."""
    literal = typing.get_args(Day.__value__)[0]
    return typing.get_args(literal)


@cache
def optimizer_flag_descriptions() -> dict[str, str]:
    """One sentence per optimizer flag, from the library's member docstrings."""
    fallback = {flag.value: flag.value.replace("_", " ").capitalize() for flag in OptimizerFlags}
    try:
        tree = ast.parse(textwrap.dedent(inspect.getsource(OptimizerFlags)))
    except (OSError, TypeError, SyntaxError):
        return fallback
    body = tree.body[0].body
    descriptions = dict(fallback)
    for statement, following in zip(body, body[1:], strict=False):
        if not (isinstance(statement, ast.Assign) and isinstance(following, ast.Expr)):
            continue
        target = statement.targets[0]
        text = getattr(following.value, "value", None)
        if (
            isinstance(target, ast.Name)
            and isinstance(text, str)
            and hasattr(OptimizerFlags, target.id)
        ):
            first_paragraph = inspect.cleandoc(text).split("\n\n")[0]
            descriptions[getattr(OptimizerFlags, target.id).value] = " ".join(
                first_paragraph.split()
            )
    return descriptions


def options() -> dict:
    """Every choice list a form needs, in display order."""
    descriptions = optimizer_flag_descriptions()
    return {
        "weekdays": list(weekdays()),
        "modalities": [modality.value for modality in CourseModality],
        "delivery_modes": [mode.value for mode in DeliveryMode],
        "optimizer_flags": [
            {"value": flag.value, "description": descriptions[flag.value]}
            for flag in OptimizerFlags
        ],
    }
