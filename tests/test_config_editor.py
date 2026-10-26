import re
import subprocess
import time
import urllib.request

import pytest
from playwright.sync_api import Page, expect
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from tests.helpers import EXAMPLE_CONFIG

LOCAL_URL = "http://localhost:8000"

# commands to start up server from here, rather than manually doing it
RUN_SERVER = ["uv", "run", "zimpasta", "--gui"]


@pytest.fixture(scope="session", autouse=True)
def start_website():

    # start website in the background
    server = subprocess.Popen(
        RUN_SERVER,
        # stdout=subprocess.DEVNULL,
        # stderr=subprocess.DEVNULL,
    )

    try:
        # give some time for the server to respond & start up
        overtime = time.time() + 30

        while time.time() < overtime:
            if server.poll() is not None:
                raise RuntimeError("Server stopped before it became ready.")

            try:
                with urllib.request.urlopen(LOCAL_URL, timeout=1):
                    break
            except Exception:
                time.sleep(0.5)
        else:
            raise RuntimeError(f"Website did not start within 30 seconds: {LOCAL_URL}")

        # run pytests while the server is running
        yield

    finally:
        # shut down server when testing finishes
        if server.poll() is None:
            server.terminate()

            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()


@pytest.fixture
def loaded_config_page(page: Page) -> Page:
    # loads a config file into the website

    page.goto("http://localhost:8000")

    page.get_by_role("button", name="Load JSON...").click()
    page.locator('input[type="file"]').set_input_files(EXAMPLE_CONFIG)

    if page.get_by_role("button", name="Discard and load").is_visible():
        page.get_by_role("button", name="Discard and load").click()

    expect(
        page.get_by_role("heading", level=2, name="No configuration loaded", exact=True)
    ).not_to_be_visible(timeout=10000)

    return page


def test_init_page_load(page: Page):

    page.goto("http://localhost:8000")

    expect(page.get_by_role("heading", level=1, name="Configuration", exact=True)).to_be_visible()
    expect(page.get_by_role("button", name="New")).to_be_visible()
    expect(page.get_by_role("button", name="Load JSON...")).to_be_visible()


def test_config_editor_page(loaded_config_page: Page):

    # load new config for this test function & discard previous, unsaved edits
    discardBtn = loaded_config_page.get_by_role("button", name="Discard and load")
    try:
        discardBtn.wait_for(state="visible", timeout=5000)
        discardBtn.click()
    except PlaywrightTimeoutError:
        pass

    expect(loaded_config_page.get_by_role("heading", level=1, name="Configuration")).to_be_visible()
    expect(loaded_config_page.get_by_role("heading", name="Faculty")).to_be_visible()
    expect(loaded_config_page.get_by_role("heading", name="Courses")).to_be_visible()
    expect(loaded_config_page.get_by_role("heading", name="Rooms")).to_be_visible()
    expect(loaded_config_page.get_by_role("heading", name="Labs")).to_be_visible()
    expect(loaded_config_page.get_by_role("heading", name="Class Patterns")).to_be_visible()
    expect(loaded_config_page.get_by_role("heading", name="Time Slots")).to_be_visible()
    expect(loaded_config_page.get_by_role("heading", name="Global Settings")).to_be_visible()


def test_add_faculty_buttons(loaded_config_page: Page):

    # load new config for this test function & discard previous, unsaved edits
    discardBtn = loaded_config_page.get_by_role("button", name="Discard and load")
    try:
        discardBtn.wait_for(state="visible", timeout=5000)
        discardBtn.click()
    except PlaywrightTimeoutError:
        pass

    # test '+ Add faculty' button
    loaded_config_page.get_by_role("button", name="Add faculty").click()
    popup = loaded_config_page.get_by_role("dialog")

    expect(popup).to_be_visible()
    expect(popup.get_by_role("heading", level=2, name="Add faculty member")).to_be_visible()

    # test 'Cancel' button with unsaved input
    name_field = popup.get_by_label("Name")
    name_field.fill("Betty")
    expect(name_field).to_be_visible()

    loaded_config_page.get_by_role("button", name="Cancel").click()
    popup2 = loaded_config_page.get_by_role("dialog")

    expect(popup2.get_by_text("Discard changes?")).to_be_visible()
    expect(
        popup2.get_by_text("Your changes to this faculty member haven't been saved.")
    ).to_be_visible()

    popup2.get_by_role("button", name="Keep editing").click()
    popup = loaded_config_page.get_by_role("dialog")
    expect(popup.get_by_text("Discard changes?")).not_to_be_visible()

    # test 'Cancel' button with no inputs
    name_field.fill("")
    loaded_config_page.get_by_role("button", name="Cancel").click()

    expect(
        loaded_config_page.get_by_role("heading", level=2, name="Add faculty member")
    ).not_to_be_visible()

    # test 'Discard' button
    faculty_section = loaded_config_page.locator("section.editor-row").filter(
        has=loaded_config_page.get_by_role("heading", name="Faculty")
    )

    # get the number of faculty appearing on the screen before clicking '+ Add faculty'
    number_of_fac_before = faculty_section.locator(".editor-row__meta").inner_text()

    loaded_config_page.get_by_role("button", name="Add faculty").click()
    loaded_config_page.get_by_label("Name").fill("Test")
    loaded_config_page.get_by_role("button", name="Cancel").click()
    popup2 = loaded_config_page.get_by_role("dialog")

    expect(popup2.get_by_text("Discard changes?")).to_be_visible()

    popup2.get_by_role("button", name="Discard").click()
    expect(
        loaded_config_page.get_by_role("heading", level=2, name="Add faculty member")
    ).not_to_be_visible()

    number_of_fac_after = faculty_section.locator(".editor-row__meta").inner_text()

    # test that the number of faculty on the screen stayed the same
    assert number_of_fac_after == number_of_fac_before


def test_adding_a_faculty_member(loaded_config_page: Page):

    # load new config for this test function & discard previous, unsaved edits
    discardBtn = loaded_config_page.get_by_role("button", name="Discard and load")
    try:
        discardBtn.wait_for(state="visible", timeout=5000)
        discardBtn.click()
    except PlaywrightTimeoutError:
        pass

    # get the number of faculty appearing on the screen before adding a faculty
    faculty_section = loaded_config_page.locator("section.editor-row").filter(
        has=loaded_config_page.get_by_role("heading", level=2, name="Faculty")
    )
    fac_count_locator = faculty_section.locator(".editor-row__meta")
    number_of_fac_before = int(fac_count_locator.inner_text())

    # add a faculty
    loaded_config_page.get_by_role("button", name="Add faculty").click()
    popup = loaded_config_page.get_by_role("dialog")

    popup.get_by_label("Name").fill("Dr. Not-Zoppetti")
    popup.get_by_label("Minimum credits").fill(str(3))
    popup.get_by_label("Maximum credits").fill(str(12))
    popup.get_by_label("Different courses").fill(str(3))

    loaded_config_page.get_by_role("button", name="Add faculty member").click()

    expect(popup).not_to_be_visible()

    # test that the number of faculty on the screen incremented after an addition
    expect(fac_count_locator).to_have_text(str(number_of_fac_before + 1))


def test_adding_a_course(loaded_config_page: Page):

    # load new config for this test function & discard previous, unsaved edits
    discardBtn = loaded_config_page.get_by_role("button", name="Discard and load")
    try:
        discardBtn.wait_for(state="visible", timeout=5000)
        discardBtn.click()
    except PlaywrightTimeoutError:
        pass

    # get the number of courses appearing on the screen before adding a course
    course_section = loaded_config_page.locator("section.editor-row").filter(
        has=loaded_config_page.get_by_role("heading", level=2, name="Courses")
    )

    course_count_locator = course_section.locator(".editor-row__meta")
    number_of_courses_before = int(course_count_locator.inner_text().split(" ")[0])

    # add a course
    loaded_config_page.get_by_role("button", name="Add course").click()
    popup = loaded_config_page.get_by_role("dialog")

    popup.get_by_label("Course ID").fill("CMSC 144")
    popup.get_by_label("Credits").fill(str(4))
    popup.get_by_label("Capacity").fill(str(30))
    popup.get_by_label("Specific").click()
    popup.get_by_label("Zoppetti").click()
    popup.get_by_label("Roddy 136").click()
    popup.get_by_label("Linux").click()

    popup.get_by_role("button", name="Add course").click()

    # test that the number of courses on the screen incremented after an addition
    expect(course_count_locator).to_have_text(str(number_of_courses_before + 1) + " sections")


def test_adding_a_room(loaded_config_page: Page):

    # load new config for this test function & discard previous, unsaved edits
    discardBtn = loaded_config_page.get_by_role("button", name="Discard and load")
    try:
        discardBtn.wait_for(state="visible", timeout=5000)
        discardBtn.click()
    except PlaywrightTimeoutError:
        pass

    # get the number of rooms appearing on the screen before adding a room
    room_section = loaded_config_page.locator("section.editor-row").filter(
        has=loaded_config_page.get_by_role("heading", level=2, name="Rooms")
    )

    room_count_locator = room_section.locator(".editor-row__meta")
    number_of_rooms_before = int(room_count_locator.inner_text())

    # add a room
    loaded_config_page.get_by_role("button", name="Add room").click()
    popup = loaded_config_page.get_by_role("dialog")

    popup.get_by_label("Name").fill("Roddy 101")
    popup.get_by_label("Capacity").fill(str(30))

    popup.get_by_role("button", name="Add room").click()

    # test that the number of rooms on the screen incremented after an addition
    expect(room_count_locator).to_have_text(str(number_of_rooms_before + 1))


def test_adding_a_lab(loaded_config_page: Page):

    # load new config for this test function & discard previous, unsaved edits
    discardBtn = loaded_config_page.get_by_role("button", name="Discard and load")
    try:
        discardBtn.wait_for(state="visible", timeout=5000)
        discardBtn.click()
    except PlaywrightTimeoutError:
        pass

    # get the number of labs appearing on the screen before adding a lab
    lab_section = loaded_config_page.locator("section.editor-row").filter(
        has=loaded_config_page.get_by_role("heading", level=2, name="Labs")
    )

    lab_count_locator = lab_section.locator(".editor-row__meta")
    number_of_labs_before = int(lab_count_locator.inner_text())

    # add a lab
    loaded_config_page.get_by_role("button", name="Add lab").click()
    popup = loaded_config_page.get_by_role("dialog")

    popup.get_by_label("Name").fill("Opera")
    popup.get_by_label("Capacity").fill(str(30))

    popup.get_by_role("button", name="Add lab").click()

    # test that the number of labs on the screen incremented after an addition
    expect(lab_count_locator).to_have_text(str(number_of_labs_before + 1))


def test_adding_a_class_pattern(loaded_config_page: Page):

    # load new config for this test function & discard previous, unsaved edits
    discardBtn = loaded_config_page.get_by_role("button", name="Discard and load")
    try:
        discardBtn.wait_for(state="visible", timeout=5000)
        discardBtn.click()
    except PlaywrightTimeoutError:
        pass

    # get the number of rooms appearing on the screen before adding a room
    pattern_section = loaded_config_page.locator("section.editor-row").filter(
        has=loaded_config_page.get_by_role("heading", level=2, name="Class Patterns")
    )

    pattern_count_locator = pattern_section.locator(".editor-row__meta")
    number_of_patterns_before = int(pattern_count_locator.inner_text().split(" ")[2])

    # add a pattern
    loaded_config_page.get_by_role("button", name="Add pattern").click()
    popup = loaded_config_page.get_by_role("dialog")

    popup.get_by_label("Credits").fill(str(3))

    popup.get_by_role("button", name="Add pattern").click()

    # test that the number of patterns on the screen incremented after an addition
    loaded_config_page.wait_for_timeout(1000)
    assert pattern_count_locator.inner_text().split(" ")[2] == str(number_of_patterns_before + 1)


def test_undo_button(loaded_config_page: Page):
    # load new config for this test function & discard previous, unsaved edits
    discardBtn = loaded_config_page.get_by_role("button", name="Discard and load")
    try:
        discardBtn.wait_for(state="visible", timeout=5000)
        discardBtn.click()
    except PlaywrightTimeoutError:
        pass

    # get the number of patterns appearing on the screen before editing
    pattern_section = loaded_config_page.locator("section.editor-row").filter(
        has=loaded_config_page.get_by_role("heading", level=2, name="Class Patterns")
    )
    pattern_count_locator = pattern_section.locator(".editor-row__meta")
    init_text = pattern_count_locator.inner_text()
    number_of_patterns_before = int(init_text.split(" ")[2])

    # get the number of labs appearing on the screen before editing
    lab_section = loaded_config_page.locator("section.editor-row").filter(
        has=loaded_config_page.get_by_role("heading", level=2, name="Labs")
    )
    lab_count_locator = lab_section.locator(".editor-row__meta")
    number_of_labs_before = int(lab_count_locator.inner_text())

    # get the number of rooms appearing on the screen before editing
    room_section = loaded_config_page.locator("section.editor-row").filter(
        has=loaded_config_page.get_by_role("heading", level=2, name="Rooms")
    )
    room_count_locator = room_section.locator(".editor-row__meta")
    number_of_rooms_before = int(room_count_locator.inner_text())

    # get the number of courses appearing on the screen before editing
    course_section = loaded_config_page.locator("section.editor-row").filter(
        has=loaded_config_page.get_by_role("heading", level=2, name="Courses")
    )
    course_count_locator = course_section.locator(".editor-row__meta")
    number_of_courses_before = int(course_count_locator.inner_text().split(" ")[0])

    # get the number of faculty appearing on the screen before editing
    faculty_section = loaded_config_page.locator("section.editor-row").filter(
        has=loaded_config_page.get_by_role("heading", level=2, name="Faculty")
    )
    fac_count_locator = faculty_section.locator(".editor-row__meta")
    number_of_fac_before = int(fac_count_locator.inner_text())

    # test faculty un-doing

    # add a faculty
    loaded_config_page.get_by_role("button", name="Add faculty").click()
    popup = loaded_config_page.get_by_role("dialog")

    popup.get_by_label("Name").fill("Dr. Not-Zoppetti")
    popup.get_by_label("Minimum credits").fill(str(3))
    popup.get_by_label("Maximum credits").fill(str(12))
    popup.get_by_label("Different courses").fill(str(3))

    loaded_config_page.get_by_role("button", name="Add faculty member").click()
    expect(fac_count_locator).to_have_text(str(number_of_fac_before + 1), timeout=5000)

    # undo
    loaded_config_page.get_by_role("button", name="Undo").click()
    expect(fac_count_locator).to_have_text(str(number_of_fac_before), timeout=5000)

    # test course un-doing

    # add a course
    loaded_config_page.get_by_role("button", name="Add course").click()
    popup = loaded_config_page.get_by_role("dialog")

    popup.get_by_label("Course ID").fill("CMSC 144")
    popup.get_by_label("Credits").fill(str(4))
    popup.get_by_label("Capacity").fill(str(30))
    popup.get_by_label("Specific").click()
    popup.get_by_label("Zoppetti").click()
    popup.get_by_label("Roddy 136").click()
    popup.get_by_label("Linux").click()

    popup.get_by_role("button", name="Add course").click()
    expect(course_count_locator).to_have_text(
        str(number_of_courses_before + 1) + " sections", timeout=5000
    )

    # undo
    loaded_config_page.get_by_role("button", name="Undo").click()
    expect(course_count_locator).to_have_text(
        str(number_of_courses_before) + " sections", timeout=5000
    )

    # test room un-doing

    # add a room
    loaded_config_page.get_by_role("button", name="Add room").click()
    popup = loaded_config_page.get_by_role("dialog")

    popup.get_by_label("Name").fill("Roddy 101")
    popup.get_by_label("Capacity").fill(str(30))

    popup.get_by_role("button", name="Add room").click()
    expect(room_count_locator).to_have_text(str(number_of_rooms_before + 1), timeout=5000)

    # undo
    loaded_config_page.get_by_role("button", name="Undo").click()
    expect(room_count_locator).to_have_text(str(number_of_rooms_before), timeout=5000)

    # test lab un-doing

    # add a lab
    loaded_config_page.get_by_role("button", name="Add lab").click()
    popup = loaded_config_page.get_by_role("dialog")

    popup.get_by_label("Name").fill("Opera")
    popup.get_by_label("Capacity").fill(str(30))

    popup.get_by_role("button", name="Add lab").click()
    expect(lab_count_locator).to_have_text(str(number_of_labs_before + 1), timeout=5000)

    # undo
    loaded_config_page.get_by_role("button", name="Undo").click()
    expect(lab_count_locator).to_have_text(str(number_of_labs_before), timeout=5000)

    # test pattern un-doing

    # add a pattern
    loaded_config_page.get_by_role("button", name="Add pattern").click()
    popup = loaded_config_page.get_by_role("dialog")

    popup.get_by_label("Credits").fill(str(3))

    popup.get_by_role("button", name="Add pattern").click()
    #expect(pattern_count_locator).to_have_text(
    #    re.compile(rf"\d+ of {number_of_patterns_before + 1} enabled"), timeout=5000
    #)

    # undo
    loaded_config_page.get_by_role("button", name="Undo").click()
    expect(pattern_count_locator).to_have_text(
        re.compile(rf"\d+ of {number_of_patterns_before} enabled"), timeout=5000
    )


def test_redo_button(loaded_config_page: Page):
    # load new config for this test function & discard previous, unsaved edits
    discardBtn = loaded_config_page.get_by_role("button", name="Discard and load")
    try:
        discardBtn.wait_for(state="visible", timeout=5000)
        discardBtn.click()
    except PlaywrightTimeoutError:
        pass

    # get the number of patterns appearing on the screen before editing
    pattern_section = loaded_config_page.locator("section.editor-row").filter(
        has=loaded_config_page.get_by_role("heading", level=2, name="Class Patterns")
    )
    pattern_count_locator = pattern_section.locator(".editor-row__meta")
    init_text = pattern_count_locator.inner_text()
    number_of_patterns_before = int(init_text.split(" ")[2])

    print(f"Initial pattern text: {init_text}")
    print(f"Initial total patterns: {number_of_patterns_before}")

    # get the number of labs appearing on the screen before editing
    lab_section = loaded_config_page.locator("section.editor-row").filter(
        has=loaded_config_page.get_by_role("heading", level=2, name="Labs")
    )
    lab_count_locator = lab_section.locator(".editor-row__meta")
    number_of_labs_before = int(lab_count_locator.inner_text())

    # get the number of rooms appearing on the screen before editing
    room_section = loaded_config_page.locator("section.editor-row").filter(
        has=loaded_config_page.get_by_role("heading", level=2, name="Rooms")
    )
    room_count_locator = room_section.locator(".editor-row__meta")
    number_of_rooms_before = int(room_count_locator.inner_text())

    # get the number of courses appearing on the screen before editing
    course_section = loaded_config_page.locator("section.editor-row").filter(
        has=loaded_config_page.get_by_role("heading", level=2, name="Courses")
    )
    course_count_locator = course_section.locator(".editor-row__meta")
    number_of_courses_before = int(course_count_locator.inner_text().split(" ")[0])

    # get the number of faculty appearing on the screen before editing
    faculty_section = loaded_config_page.locator("section.editor-row").filter(
        has=loaded_config_page.get_by_role("heading", level=2, name="Faculty")
    )
    fac_count_locator = faculty_section.locator(".editor-row__meta")
    number_of_fac_before = int(fac_count_locator.inner_text())

    # test faculty re-doing

    # add a faculty
    loaded_config_page.get_by_role("button", name="Add faculty").click()
    popup = loaded_config_page.get_by_role("dialog")

    popup.get_by_label("Name").fill("Dr. Not-Zoppetti")
    popup.get_by_label("Minimum credits").fill(str(3))
    popup.get_by_label("Maximum credits").fill(str(12))
    popup.get_by_label("Different courses").fill(str(3))

    loaded_config_page.get_by_role("button", name="Add faculty member").click()

    # undo-redo
    undo_button = loaded_config_page.get_by_role("button", name="Undo")
    redo_button = loaded_config_page.get_by_role("button", name="Redo")

    expect(fac_count_locator).to_have_text(str(number_of_fac_before + 1), timeout=5000)

    undo_button.click()
    expect(fac_count_locator).to_have_text(str(number_of_fac_before), timeout=5000)

    redo_button.click()
    expect(fac_count_locator).to_have_text(str(number_of_fac_before + 1), timeout=5000)

    # test course re-doing

    # add a course
    loaded_config_page.get_by_role("button", name="Add course").click()
    popup = loaded_config_page.get_by_role("dialog")

    popup.get_by_label("Course ID").fill("CMSC 144")
    popup.get_by_label("Credits").fill(str(4))
    popup.get_by_label("Capacity").fill(str(30))
    popup.get_by_label("Specific").click()
    popup.get_by_label(text="Zoppetti", exact=True).click()
    popup.get_by_label("Roddy 136").click()
    popup.get_by_label("Linux").click()

    popup.get_by_role("button", name="Add course").click()

    # undo-redo
    undo_button = loaded_config_page.get_by_role("button", name="Undo")
    redo_button = loaded_config_page.get_by_role("button", name="Redo")

    expect(course_count_locator).to_have_text(
        str(number_of_courses_before + 1) + " sections", timeout=5000
    )

    undo_button.click()
    expect(course_count_locator).to_have_text(
        str(number_of_courses_before) + " sections", timeout=5000
    )

    redo_button.click()
    expect(course_count_locator).to_have_text(
        str(number_of_courses_before + 1) + " sections", timeout=5000
    )

    # test room re-doing

    # add a room
    loaded_config_page.get_by_role("button", name="Add room").click()
    popup = loaded_config_page.get_by_role("dialog")

    popup.get_by_label("Name").fill("Roddy 101")
    popup.get_by_label("Capacity").fill(str(30))

    popup.get_by_role("button", name="Add room").click()

    # undo-redo
    undo_button = loaded_config_page.get_by_role("button", name="Undo")
    redo_button = loaded_config_page.get_by_role("button", name="Redo")

    expect(room_count_locator).to_have_text(str(number_of_rooms_before + 1), timeout=5000)

    undo_button.click()
    expect(room_count_locator).to_have_text(str(number_of_rooms_before), timeout=5000)

    redo_button.click()
    expect(room_count_locator).to_have_text(str(number_of_rooms_before + 1), timeout=5000)

    # test lab re-doing

    # add a lab
    loaded_config_page.get_by_role("button", name="Add lab").click()
    popup = loaded_config_page.get_by_role("dialog")

    popup.get_by_label("Name").fill("Opera")
    popup.get_by_label("Capacity").fill(str(30))

    popup.get_by_role("button", name="Add lab").click()

    # undo-redo
    undo_button = loaded_config_page.get_by_role("button", name="Undo")
    redo_button = loaded_config_page.get_by_role("button", name="Redo")

    expect(lab_count_locator).to_have_text(str(number_of_labs_before + 1), timeout=5000)

    undo_button.click()
    expect(lab_count_locator).to_have_text(str(number_of_labs_before), timeout=5000)

    redo_button.click()
    expect(lab_count_locator).to_have_text(str(number_of_labs_before + 1), timeout=5000)

    # test pattern re-doing

    # add a pattern
    loaded_config_page.get_by_role("button", name="Add pattern").click()
    popup = loaded_config_page.get_by_role("dialog")

    popup.get_by_label("Credits").fill(str(3))

    popup.get_by_role("button", name="Add pattern").click()
    expect(pattern_count_locator).to_have_text(
        re.compile(rf"\d+ of {number_of_patterns_before + 1} enabled"), timeout=5000
    )

    # undo-redo
    loaded_config_page.get_by_role("button", name="Undo").click()
    expect(pattern_count_locator).to_have_text(
        re.compile(rf"\d+ of {number_of_patterns_before} enabled"), timeout=5000
    )

    loaded_config_page.get_by_role("button", name="Redo").click()
    expect(pattern_count_locator).to_have_text(
        re.compile(rf"\d+ of {number_of_patterns_before + 1} enabled"), timeout=5000
    )
