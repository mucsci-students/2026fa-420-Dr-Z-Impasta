"""The application controller: every GUI action, as one method, coordinating the Model.

A view never touches the Model directly. It asks the web API, the API calls one method
here, and the method tells the Model what to do and returns plain data for the view. That
keeps each workflow (load a file, apply an edit, run the scheduler, move the results into
the viewer, import or export schedules) in one testable place, independent of HTTP.

Methods return JSON-ready dictionaries. Expected failures are raised as the Model's own
exceptions (``WorkspaceError``, ``ScheduleError``, ``GenerationBusy``, ...); the web layer
turns them into error responses.
"""

import threading
from collections.abc import Callable, Mapping
from datetime import datetime
from pathlib import PurePath

from zimpasta.model import catalog
from zimpasta.model.generate import DEFAULT_SOLVER_TIMEOUT_MS, GenerationResult, generate_schedules
from zimpasta.model.generation_job import GenerationJob, JobStatus
from zimpasta.model.schedules import ExportedSchedules, ScheduleSet
from zimpasta.model.workspace import ConfigWorkspace, ExportedConfig


class AppController:
    """Coordinates the configuration workspace, the generation job, and the schedule set."""

    def __init__(
        self,
        *,
        generator: Callable = generate_schedules,
        clock: Callable[[], datetime] = datetime.now,
        solver_timeout_ms: int | None = DEFAULT_SOLVER_TIMEOUT_MS,
    ) -> None:
        self._clock = clock
        self._lock = threading.RLock()
        self.workspace = ConfigWorkspace(clock=clock)
        self.schedules = ScheduleSet(clock=clock)
        self.job = GenerationJob(
            generator=generator,
            on_success=self._store_results,
            clock=clock,
            solver_timeout_ms=solver_timeout_ms,
        )

    # -------------------------------------------------------------------- state

    def state(self) -> dict:
        """What the header and every mode need to render: config, generation, schedules."""
        with self._lock:
            summary = self.schedules.summary()
            return {
                "config": self.workspace.snapshot(),
                "generation": self.job.status().to_dict(self._clock()),
                "schedules": {
                    key: summary[key] for key in ("count", "source", "name", "created_at")
                },
            }

    # ------------------------------------------------------------ configuration

    def configuration(self) -> dict:
        """The configuration document with its state and section labels."""
        return {
            "state": self.workspace.snapshot(),
            "document": self.workspace.document(),
            "sections": self.workspace.section_labels(),
        }

    def schema(self) -> dict:
        return catalog.configuration_schema()

    def options(self) -> dict:
        return catalog.options()

    def new_configuration(self, *, discard_changes: bool = False) -> dict:
        self.workspace.new(discard_changes=discard_changes)
        return self.configuration()

    def load_configuration(
        self, filename: str, content: str, *, discard_changes: bool = False
    ) -> dict:
        """Load JSON text the user picked in the browser. Only the file's name is kept."""
        self.workspace.load_text(
            content, filename=_file_name(filename), discard_changes=discard_changes
        )
        return self.configuration()

    def load_configuration_file(self, path) -> dict:
        """Load a file named on the command line when the GUI starts."""
        self.workspace.load_file(path)
        return self.configuration()

    def validate_configuration(self) -> dict:
        report = self.workspace.validate()
        return {"report": report.to_dict(), "state": self.workspace.snapshot()}

    def export_configuration(self) -> ExportedConfig:
        return self.workspace.export_text()

    def mark_configuration_saved(self, revision: int, filename: str | None = None) -> dict:
        self.workspace.mark_saved(revision, _file_name(filename) if filename else None)
        return self.workspace.snapshot()

    def list_items(self, area: str) -> dict:
        items = self.workspace.items(area)
        return {"area": area, "items": items}

    def get_item(self, area: str, index: int) -> dict:
        return {"area": area, "index": index, "item": self.workspace.item(area, index)}

    def add_item(self, area: str, item: object) -> dict:
        change = self.workspace.add(area, item)
        return {
            **self.configuration(),
            "change": change.to_dict(),
            "index": len(self.workspace.items(area)) - 1,
        }

    def replace_item(self, area: str, index: int, item: object) -> dict:
        change = self.workspace.replace(area, index, item)
        return {**self.configuration(), "change": change.to_dict(), "index": index}

    def delete_impact(self, area: str, index: int) -> dict:
        return self.workspace.delete_impact(area, index).to_dict()

    def delete_item(self, area: str, index: int) -> dict:
        change, impact = self.workspace.remove(area, index)
        return {**self.configuration(), "change": change.to_dict(), "impact": impact.to_dict()}

    def update_time_slots(self, values: Mapping) -> dict:
        change = self.workspace.update_time_slots(values)
        return {**self.configuration(), "change": change.to_dict()}

    def update_settings(self, values: Mapping) -> dict:
        change = self.workspace.update_settings(values)
        return {**self.configuration(), "change": change.to_dict()}

    # --------------------------------------------------------------- generation

    def start_generation(self, *, limit: object = None, optimizer_flags: object = None) -> dict:
        """Run the scheduler on the last valid configuration with per-run overrides.

        Open drafts in the editor never reach the Model, so the run always uses the
        configuration as last applied and validated.
        """
        with self._lock:
            config = self.workspace.require_valid()
            status = self.job.start(
                config,
                limit=limit,
                optimizer_flags=optimizer_flags,
                config_name=self.workspace.name,
                config_revision=self.workspace.revision,
            )
            return status.to_dict(self._clock())

    def generation_status(self) -> dict:
        return self.job.status().to_dict(self._clock())

    def cancel_generation(self) -> dict:
        return self.job.cancel().to_dict(self._clock())

    def _store_results(self, result: GenerationResult, status: JobStatus) -> None:
        """Called by the job on success: the new schedules become the viewer's schedules."""
        with self._lock:
            self.schedules.replace_generated(result, config_name=status.config_name)

    # ---------------------------------------------------------------- schedules

    def schedule_summary(self) -> dict:
        with self._lock:
            return self.schedules.summary()

    def schedule_view(self, number: int, group: str = "room") -> dict:
        with self._lock:
            return self.schedules.view(number, group)

    def import_schedules(self, filename: str, content: str) -> dict:
        with self._lock:
            self.schedules.import_text(content, filename=_file_name(filename))
            return self.schedules.summary()

    def export_schedules(self, which: str | int = "all", fmt: str = "json") -> ExportedSchedules:
        with self._lock:
            return self.schedules.export(which, fmt)

    def clear_schedules(self) -> dict:
        with self._lock:
            self.schedules.clear()
            return self.schedules.summary()


def _file_name(name: str) -> str:
    """Just the file name, whatever path a browser or client sent along with it."""
    return PurePath(name.replace("\\", "/")).name or "untitled.json"
