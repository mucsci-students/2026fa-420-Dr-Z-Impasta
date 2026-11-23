"""Shared wording for messages: counted nouns read the same everywhere."""


def plural(count: int, singular: str, plural_form: str | None = None) -> str:
    """``count`` and the noun that goes with it: ``"1 problem"``, ``"3 problems"``.

    Pass ``plural_form`` when adding an "s" isn't right, as in ``plural(n, "change has",
    "changes have")``. Matches ``plural()`` in ``frontend/src/format.js``.
    """
    return f"{count} {singular if count == 1 else plural_form or singular + 's'}"
