"""Change notifications for Model objects (the Observer pattern).

A :class:`Subject` keeps a list of observers and calls each one, with no arguments, after
it changes. The configuration workspace and the schedule set are subjects; the account
service observes both to save the open state to the user's account after every change,
whichever path made it (an editor form, the AI assistant, an import, a finished run).

Observers are called after the change is complete and must not raise: a failure in one
observer is caught and logged so it can never undo or block the change itself.
"""

import logging
from collections.abc import Callable

logger = logging.getLogger("zimpasta.model")

Observer = Callable[[], None]


class Subject:
    """Something observers can subscribe to."""

    def __init__(self) -> None:
        self._observers: list[Observer] = []

    def subscribe(self, observer: Observer) -> Callable[[], None]:
        """Call ``observer`` after every change. Returns a function that unsubscribes it."""
        self._observers.append(observer)

        def unsubscribe() -> None:
            if observer in self._observers:
                self._observers.remove(observer)

        return unsubscribe

    def _notify(self) -> None:
        for observer in list(self._observers):
            try:
                observer()
            except Exception:
                logger.exception("An observer of %s failed", type(self).__name__)
