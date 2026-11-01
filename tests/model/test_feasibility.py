"""Warnings for valid configurations that can't have any schedule (model.feasibility)."""

import pytest

from tests.helpers import EXAMPLE_CONFIG
from zimpasta.model import feasibility
from zimpasta.model import references as refs
from zimpasta.model.feasibility import schedule_problems
from zimpasta.model.workspace import ConfigStatus, ConfigWorkspace, EditRejected

WEDNESDAY_LAB = "4 credits: MON, WED (lab), FRI"
"""The only enabled pattern that puts Hogg, Xie, and Yang on their mandatory Wednesday."""


@pytest.fixture
def example_workspace() -> ConfigWorkspace:
    ws = ConfigWorkspace()
    ws.load_text(EXAMPLE_CONFIG.read_text(encoding="utf-8"), filename="sample_config.json")
    return ws


def set_disabled(ws, label: str, disabled: bool = True, *, force: bool = False) -> None:
    labels = [refs.pattern_label(pattern) for pattern in ws.items("patterns")]
    index = labels.index(label)
    item = {**ws.item("patterns", index), "disabled": disabled}
    ws.replace("patterns", index, item, force=force)


def test_the_example_has_no_warnings(example_workspace):
    assert example_workspace.warnings == ()
    assert example_workspace.snapshot()["warnings"] == []


def test_disabling_a_needed_pattern_warns_without_blocking(example_workspace):
    ws = example_workspace

    set_disabled(ws, WEDNESDAY_LAB)

    assert ws.status is ConfigStatus.VALID
    messages = [warning.message for warning in ws.warnings]
    assert any("Hogg on mandatory day WED" in message for message in messages)
    hogg = next(w for w in ws.warnings if "Hogg" in w.message)
    assert (hogg.area, ws.item("faculty", hogg.index)["name"]) == ("faculty", "Hogg")
    assert ws.snapshot()["warnings"][0]["message"] == messages[0]

    set_disabled(ws, WEDNESDAY_LAB, disabled=False)
    assert ws.warnings == ()


def test_one_unavailable_candidate_is_not_a_warning_but_the_only_one_is(example_workspace):
    ws = example_workspace
    for label in (
        "4 credits: MON (lab), WED",
        "4 credits: TUE (lab), THU",
        "4 credits: TUE, THU (lab)",
        "4 credits: MON, TUE (lab), FRI",
        WEDNESDAY_LAB,
    ):
        set_disabled(ws, label)

    messages = [warning.message for warning in ws.warnings]
    # Rogers can't teach CMSC 161.02 any more, but Zoppetti still can.
    assert not any("Rogers" in message for message in messages)
    # Hobbs is the only candidate for CMSC 420.01.
    assert "Hobbs has no available compatible meeting pattern for CMSC 420.01" in messages


def test_a_library_failure_never_blocks_an_edit(example_workspace, monkeypatch):
    def broken(config):
        raise RuntimeError("library changed")

    monkeypatch.setattr(feasibility.SchedulingProblem, "from_config", broken)

    assert schedule_problems(example_workspace.config) == ()


@pytest.mark.parametrize(
    ("pointers", "where"),
    [
        (("/config/courses/14",), ("courses", 14, None)),
        (("/config/faculty/2/times",), ("faculty", 2, "times")),
        (("/time_slot_config/classes/3",), ("patterns", 3, None)),
        (("/limit",), (None, None, None)),
    ],
)
def test_findings_are_located_at_the_first_item(pointers, where):
    issue = feasibility._issue("code", "message", pointers)
    assert (issue.area, issue.index, issue.field) == where


def test_a_forced_toggle_can_turn_off_a_pattern_courses_need(example_workspace):
    ws = example_workspace
    only_without_lab = "4 credits: MON, WED"

    with pytest.raises(EditRejected):
        set_disabled(ws, only_without_lab)

    set_disabled(ws, only_without_lab, force=True)

    assert ws.status is ConfigStatus.INVALID
    assert any("no enabled class pattern with no lab meeting" in i.message for i in ws.issues)
    assert ws.warnings == ()  # only checked once the library accepts the configuration

    set_disabled(ws, only_without_lab, disabled=False)
    assert ws.status is ConfigStatus.VALID
