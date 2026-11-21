"""Export PDF in the Schedule Viewer, end to end in a real browser.

Starts ``zimpasta --gui`` on its own port, loads schedules the way a user would (Load
JSON, or a real generation run), exports PDFs from the dialog, and reads the downloaded
files. The PDFs are not compressed, so the text in them can be searched directly.

Needs the built GUI (``npm run build`` in ``frontend/``); skipped when it is missing.
"""

import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

from tests.helpers import FIXTURE_CONFIG

PORT = 8791
URL = f"http://127.0.0.1:{PORT}"
ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "src" / "zimpasta" / "web" / "index.html"
SCHEDULES = ROOT / "tests" / "fixtures" / "pdf_export_schedules.json"
LONG_NAME = "Dr. Maximiliana Alexandrovna Featherstonehaugh-Montgomery-Vanderbilt III"
FAILED = "PDF export failed. Your existing schedule has not been changed. Please try again."
LOAD_FAILED = (
    "The PDF exporter couldn't be loaded. Your existing schedule has not been changed. "
    "Check your connection and try again. If it keeps failing, export the schedules as "
    "JSON, then reload the page."
)

pytestmark = pytest.mark.skipif(not WEB.exists(), reason="the GUI is not built (npm run build)")


@pytest.fixture(scope="module", autouse=True)
def server():
    process = subprocess.Popen(
        [sys.executable, "-m", "zimpasta.cli", "--gui", "--no-browser", "--port", str(PORT)],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.time() + 30
        while True:
            if process.poll() is not None:
                raise RuntimeError("The server stopped before it was ready.")
            try:
                with urllib.request.urlopen(f"{URL}/api/state", timeout=1):
                    break
            except Exception:
                if time.time() > deadline:
                    raise RuntimeError(
                        f"The server did not start within 30 seconds: {URL}"
                    ) from None
                time.sleep(0.3)
        yield
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def api(page: Page, method: str, path: str, body=None):
    """Call the API from the page, as the GUI does; returns ``(status, text)``."""
    return page.evaluate(
        """async ([method, path, body]) => {
            const init = { method, headers: { Accept: "application/json" } };
            if (body !== null) {
                init.headers["Content-Type"] = "application/json";
                init.body = JSON.stringify(body);
            }
            const response = await fetch(path, init);
            return [response.status, await response.text()];
        }""",
        [method, path, body],
    )


def exported_json(page: Page) -> str:
    status, text = api(page, "GET", "/api/schedules/export?which=all&format=json")
    assert status == 200
    return text


@pytest.fixture
def viewer(page: Page) -> Page:
    """The Schedule Viewer showing the three imported fixture schedules."""
    # Without the Save As dialog (Chrome only), saving is a plain download we can catch.
    page.add_init_script("window.showSaveFilePicker = undefined;")
    page.goto(f"{URL}/viewer")
    api(page, "DELETE", "/api/schedules")
    page.reload()
    page.locator('input[type="file"]').set_input_files(SCHEDULES)
    expect(page.get_by_text("3 schedules", exact=True)).to_be_visible()
    return page


def open_dialog(page: Page):
    page.get_by_role("button", name="Export PDF…").click()
    dialog = page.get_by_role("dialog", name="Export schedule as PDF")
    expect(dialog).to_be_visible()
    return dialog


def export(page: Page, dialog) -> tuple[str, bytes]:
    """Click Export PDF in the dialog; returns the download's name and bytes."""
    with page.expect_download() as download:
        dialog.get_by_role("button", name="Export PDF", exact=True).click()
    path = download.value.path()
    data = Path(path).read_bytes()
    assert data.startswith(b"%PDF-") and b"%%EOF" in data
    return download.value.suggested_filename, data


def heading(text: str) -> bytes:
    """How a line of text is stored in the PDF; parentheses are escaped there."""
    escaped = text.replace("(", "\\(").replace(")", "\\)")
    return f"({escaped}) Tj".encode("latin-1")


def test_export_all_rooms_and_labs_of_an_imported_schedule(viewer: Page):
    before = exported_json(viewer)
    dialog = open_dialog(viewer)

    # The schedule on screen is preselected, grouped by room and lab, everything, US Letter.
    expect(dialog.get_by_label("Schedule", exact=True)).to_have_value("1")
    expect(dialog.get_by_label("Room / Lab")).to_be_checked()
    expect(dialog.get_by_label("All rooms and labs")).to_be_checked()
    expect(dialog.get_by_label("US Letter")).to_be_checked()
    # The review says what will be exported and where it goes.
    expect(dialog.get_by_text("All rooms and labs (6)")).to_be_visible()
    expect(dialog.get_by_text("schedule_1_room_lab.pdf")).to_be_visible()
    expect(dialog.get_by_text("downloads folder")).to_be_visible()

    name, pdf = export(viewer, dialog)

    assert name == "schedule_1_room_lab.pdf"
    for section in ["ROOM: Annex 12", "ROOM: Roddy 140", "ROOM: Roddy 147"]:
        assert heading(section) in pdf
    for section in ["LAB: Annex 12", "LAB: Linux", "LAB: Mac"]:
        assert heading(section) in pdf
    assert heading("Schedule 1 of 3") in pdf and heading("Room / Lab") in pdf
    assert b"(Page 1 of " in pdf
    assert b"/MediaBox [0 0 612. 792.]" in pdf  # US Letter
    # The dialog closes and a message confirms the file, as for JSON and CSV.
    expect(dialog).not_to_be_visible()
    expect(
        viewer.get_by_text("schedule_1_room_lab.pdf is in your browser's downloads folder.")
    ).to_be_visible()
    # Nothing about the schedules changed.
    assert exported_json(viewer) == before
    expect(viewer.get_by_text("3 schedules", exact=True)).to_be_visible()


def test_export_one_lab_of_another_schedule_after_a_missing_selection(viewer: Page):
    dialog = open_dialog(viewer)
    dialog.get_by_label("Schedule", exact=True).select_option("2")
    dialog.get_by_label("Specific room or lab").check()
    chooser = dialog.get_by_role("combobox", name="Room or lab")

    # Only schedule 2's rooms and labs are offered.
    expect(chooser.locator("option")).to_have_text(
        ["Choose…", "Roddy 140 (Room)", "Roddy 147 (Room)", "Mac (Lab)"]
    )
    # Exporting without choosing one explains what is missing and downloads nothing.
    dialog.get_by_role("button", name="Export PDF", exact=True).click()
    expect(dialog.get_by_text("Choose a room or lab to export.")).to_be_visible()
    expect(dialog).to_be_visible()

    chooser.select_option(label="Mac (Lab)")
    expect(dialog.get_by_text("Choose a room or lab to export.")).not_to_be_visible()
    dialog.get_by_label("A4").check()
    name, pdf = export(viewer, dialog)

    assert name == "schedule_2_lab_mac.pdf"
    assert heading("LAB: Mac") in pdf and heading("Lab: Mac") in pdf
    assert heading("Schedule 2 of 3") in pdf
    assert b"Roddy 147" not in pdf and b"ROOM:" not in pdf
    assert b"/MediaBox [0 0 595." in pdf  # A4
    # The viewer still shows the schedule it showed before.
    expect(viewer.get_by_label("Schedule", exact=True)).to_have_value("0")


def test_export_one_room(viewer: Page):
    dialog = open_dialog(viewer)
    dialog.get_by_label("Specific room or lab").check()
    dialog.get_by_role("combobox", name="Room or lab").select_option(label="Annex 12 (Room)")

    name, pdf = export(viewer, dialog)

    assert name == "schedule_1_room_annex_12.pdf"
    assert heading("ROOM: Annex 12") in pdf
    assert heading("LAB: Annex 12") not in pdf and b"CMSC 453" not in pdf
    assert heading("CMSC 420") in pdf


def test_export_all_faculty_and_one_faculty_member(viewer: Page):
    dialog = open_dialog(viewer)
    dialog.get_by_label("Faculty", exact=True).check()
    expect(dialog.get_by_text("All faculty members (4)")).to_be_visible()

    name, pdf = export(viewer, dialog)

    assert name == "schedule_1_faculty.pdf"
    for person in ["Dr. Brown", "Dr. Jones", "Dr. Smith"]:
        assert heading(person) in pdf
    assert LONG_NAME.encode() in pdf
    # A meeting with no room says so; the text wraps inside its cell.
    assert b"(No physical resource) Tj" in pdf and b"(assigned) Tj" in pdf
    assert heading("Linux (Lab)") in pdf and heading("Online") in pdf

    dialog = open_dialog(viewer)
    dialog.get_by_label("Faculty", exact=True).check()
    dialog.get_by_label("Specific faculty member").check()
    dialog.get_by_role("combobox", name="Faculty member").select_option(label="Dr. Jones")
    name, pdf = export(viewer, dialog)

    assert name == "schedule_1_faculty_dr_jones.pdf"
    assert heading("Dr. Jones") in pdf and heading("Faculty member: Dr. Jones") in pdf
    assert b"Dr. Smith" not in pdf and b"Dr. Brown" not in pdf


def test_the_dialog_starts_from_what_the_viewer_shows(viewer: Page):
    picker = viewer.get_by_label("Schedule", exact=True)
    # The picker follows the app state, which is polled; wait until it knows all three.
    for _ in range(20):
        picker.select_option("1")
        if picker.input_value() == "1":
            break
        viewer.wait_for_timeout(300)
    expect(picker).to_have_value("1")
    viewer.get_by_role("button", name="Faculty", exact=True).click()

    dialog = open_dialog(viewer)

    expect(dialog.get_by_label("Schedule", exact=True)).to_have_value("2")
    expect(dialog.get_by_label("Faculty", exact=True)).to_be_checked()
    expect(dialog.get_by_text("schedule_2_faculty.pdf")).to_be_visible()
    dialog.get_by_role("button", name="Cancel").click()
    expect(dialog).not_to_be_visible()


def test_a_schedule_with_nothing_to_export_says_so(viewer: Page):
    dialog = open_dialog(viewer)
    dialog.get_by_label("Schedule", exact=True).select_option("3")

    # Schedule 3 is a single online section: no room or lab to list.
    expect(dialog.get_by_text("Schedule 3 has no meetings in a room or lab")).to_be_visible()
    expect(dialog.get_by_role("button", name="Export PDF", exact=True)).to_be_disabled()

    dialog.get_by_label("Faculty", exact=True).check()
    name, pdf = export(viewer, dialog)
    assert name == "schedule_3_faculty.pdf"
    assert heading("Dr. Brown") in pdf and heading("Online") in pdf


def test_a_failed_export_shows_an_error_and_keeps_the_schedules(viewer: Page):
    before = exported_json(viewer)
    # The PDF code is loaded on the first export; make that fail.
    viewer.route("**/assets/schedulePdfDocument-*.js", lambda route: route.abort())
    dialog = open_dialog(viewer)

    dialog.get_by_role("button", name="Export PDF", exact=True).click()

    expect(dialog.get_by_text("Couldn't export.")).to_be_visible()
    expect(dialog.get_by_text(LOAD_FAILED)).to_be_visible()
    expect(dialog.get_by_role("button", name="Export PDF", exact=True)).to_be_enabled()
    dialog.get_by_role("button", name="Cancel").click()
    expect(viewer.get_by_text("3 schedules", exact=True)).to_be_visible()
    assert exported_json(viewer) == before

    # After a reload the schedules are still there and the export works.
    viewer.unroute("**/assets/schedulePdfDocument-*.js")
    viewer.reload()
    expect(viewer.get_by_text("3 schedules", exact=True)).to_be_visible()
    name, _ = export(viewer, open_dialog(viewer))
    assert name == "schedule_1_room_lab.pdf"


def test_an_error_while_saving_shows_the_general_message(viewer: Page):
    before = exported_json(viewer)
    # A browser with a Save As dialog that refuses to write the file.
    viewer.evaluate(
        """() => {
            window.showSaveFilePicker = async () => {
                throw new DOMException("The request is not allowed", "NotAllowedError");
            };
        }"""
    )
    dialog = open_dialog(viewer)
    expect(dialog.get_by_text("Your browser will ask where to save the file")).to_be_visible()

    dialog.get_by_role("button", name="Export PDF", exact=True).click()

    expect(dialog.get_by_text(FAILED)).to_be_visible()
    assert exported_json(viewer) == before


def test_json_and_csv_export_still_work_next_to_pdf(viewer: Page):
    export(viewer, open_dialog(viewer))
    menu = viewer.get_by_label("Export schedules")

    with viewer.expect_download() as download:
        menu.select_option("all:json")
    saved = json.loads(Path(download.value.path()).read_text(encoding="utf-8"))
    assert download.value.suggested_filename.endswith(".json")
    assert saved == json.loads(SCHEDULES.read_text(encoding="utf-8"))

    with viewer.expect_download() as download:
        menu.select_option("current:csv")
    lines = Path(download.value.path()).read_text(encoding="utf-8").splitlines()
    assert download.value.suggested_filename.endswith(".csv")
    assert any(line.startswith("CMSC 161.01,Dr. Smith,Roddy 140") for line in lines)


def test_export_a_generated_schedule_without_generating_again(page: Page):
    page.add_init_script("window.showSaveFilePicker = undefined;")
    page.goto(f"{URL}/viewer")
    api(page, "DELETE", "/api/schedules")
    config = FIXTURE_CONFIG.read_text(encoding="utf-8")
    status, text = api(
        page,
        "POST",
        "/api/config/load",
        {"filename": "minimal.json", "content": config, "discard_changes": True},
    )
    assert status == 200, text
    status, text = api(page, "POST", "/api/generation", {"limit": 2, "optimizer_flags": None})
    assert status in (200, 202), text
    for _ in range(100):
        state = json.loads(api(page, "GET", "/api/state")[1])
        if state["generation"]["state"] != "running":
            break
        time.sleep(0.2)
    assert state["generation"]["state"] == "succeeded", state["generation"]
    assert state["schedules"]["count"] == 2
    before = exported_json(page)
    page.reload()
    expect(page.get_by_text("2 schedules", exact=True)).to_be_visible()

    dialog = open_dialog(page)
    dialog.get_by_label("Schedule", exact=True).select_option("2")
    dialog.get_by_label("Faculty", exact=True).check()
    name, pdf = export(page, dialog)

    assert name == "schedule_2_faculty.pdf"
    generated = json.loads(before)[1]
    for assignment in generated:
        assert heading(assignment["faculty"]) in pdf
        assert heading(assignment["course"].rpartition(".")[0]) in pdf
    # Exporting read the schedules; it did not start a run or change them.
    after = json.loads(api(page, "GET", "/api/state")[1])
    assert after["generation"] == state["generation"]
    assert after["schedules"] == state["schedules"]
    assert exported_json(page) == before
