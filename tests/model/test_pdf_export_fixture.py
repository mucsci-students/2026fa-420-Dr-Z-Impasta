"""The PDF export's fixtures stay in step with the Model.

The Schedule Viewer makes PDFs in the browser from the views ``ScheduleSet.view`` returns.
Its JavaScript tests (``tests/test_schedule_pdf_export.js``) can't call Python, so the views
of ``tests/fixtures/pdf_export_schedules.json`` are saved in ``pdf_export_views.json``. This
test fails if the saved views no longer match what the Model returns; regenerate them with::

    uv run python -m tests.model.test_pdf_export_fixture
"""

import json
from pathlib import Path

from zimpasta.model.schedules import GROUPINGS, ScheduleSet

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
SCHEDULES = FIXTURES / "pdf_export_schedules.json"
VIEWS = FIXTURES / "pdf_export_views.json"


def current_views() -> dict:
    schedules = ScheduleSet()
    count = schedules.import_text(SCHEDULES.read_text(encoding="utf-8"), filename=SCHEDULES.name)
    return {
        str(number): {group: schedules.view(number, group) for group in GROUPINGS}
        for number in range(1, count + 1)
    }


def test_saved_views_match_the_model():
    saved = json.loads(VIEWS.read_text(encoding="utf-8"))

    assert saved == json.loads(json.dumps(current_views()))


def test_the_fixture_covers_the_cases_the_pdf_tests_rely_on():
    room = current_views()["1"]["room"]["groups"]

    kinds = {(group["kind"], group["name"]) for group in room}
    # A room and a lab that share a name, an online meeting, and a meeting with no room.
    assert {("room", "Annex 12"), ("lab", "Annex 12")} <= kinds
    assert {("online", "Online"), ("unassigned", "No room")} <= kinds
    held = [m for group in room for m in group["meetings"] if m["room_held_for_lab"]]
    assert {m["course"] for m in held} == {"CMSC 162.01", "CMSC 453.01"}


if __name__ == "__main__":
    VIEWS.write_text(json.dumps(current_views(), separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {VIEWS}")
