"""In-session storage for the most recent set of generated schedules."""

from zimpasta.generate import GenerationResult, Schedule


class ScheduleStore:
    """Holds one :class:`GenerationResult` at a time. Schedule numbers are 1-based."""

    def __init__(self) -> None:
        self._result: GenerationResult | None = None

    @property
    def result(self) -> GenerationResult | None:
        return self._result

    @property
    def schedules(self) -> list[Schedule]:
        return list(self._result.schedules) if self._result is not None else []

    def is_empty(self) -> bool:
        return self._result is None or self._result.count == 0

    def __len__(self) -> int:
        return 0 if self._result is None else self._result.count

    def replace(self, result: GenerationResult) -> None:
        """Discard whatever is stored and keep ``result`` instead."""
        self._result = result

    def clear(self) -> None:
        self._result = None

    def get(self, number: int) -> Schedule:
        """Return schedule ``number`` (1-based).

        Raises:
            LookupError: nothing has been generated.
            IndexError: ``number`` is outside ``1..len(self)``.
        """
        if self._result is None:
            raise LookupError("No generated schedules in the session.")
        if not 1 <= number <= self._result.count:
            raise IndexError(f"Schedule number must be between 1 and {self._result.count}.")
        return self._result.schedules[number - 1]
