import subprocess
import time
import urllib.request

import pytest
from playwright.sync_api import Page, expect

from tests.helpers import EXAMPLE_CONFIG
HOSTED_URL = "https://dr-zimpasta.pages.dev/editor"

LOCAL_URL = "http://localhost:8000"

# commands to start up server from here, rather than manually doing it
RUN_SERVER = ["uv", "run", "zimpasta", "--gui"]


@pytest.fixture(scope="session", autouse=True)
def start_website():
    # runs 'uv run zimpasta --gui' upon the running of this file

    subprocess.run(["npm", "ci"], cwd="frontend", check=True)
    subprocess.run(["npm", "run", "build"], cwd="frontend", check=True)

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

    expect(loaded_config_page.get_by_role("heading", level=1, name="Configuration")).to_be_visible()
    expect(loaded_config_page.get_by_role("heading", name="Faculty")).to_be_visible()
    expect(loaded_config_page.get_by_role("heading", name="Courses")).to_be_visible()
    expect(loaded_config_page.get_by_role("heading", name="Rooms")).to_be_visible()
    expect(loaded_config_page.get_by_role("heading", name="Labs")).to_be_visible()
    expect(loaded_config_page.get_by_role("heading", name="Class Patterns")).to_be_visible()
    expect(loaded_config_page.get_by_role("heading", name="Time Slots")).to_be_visible()
    expect(loaded_config_page.get_by_role("heading", name="Global Settings")).to_be_visible()


def test_add_faculty_buttons(loaded_config_page: Page):

    if loaded_config_page.get_by_role("button", name="Discard and load").is_visible():
        loaded_config_page.get_by_role("button", name="Discard and load").click()

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

    if loaded_config_page.get_by_role("button", name="Discard and load").is_visible():
        loaded_config_page.get_by_role("button", name="Discard and load").click()

    faculty_section = loaded_config_page.locator("section.editor-row").filter(
        has=loaded_config_page.get_by_role("heading", level=2, name="Faculty")
    )
    fac_count_locator = faculty_section.locator(".editor-row__meta")
    number_of_fac_before = int(fac_count_locator.inner_text())

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

    if loaded_config_page.get_by_role("button", name="Discard and load").is_visible():
        loaded_config_page.get_by_role("button", name="Discard and load").click()

    loaded_config_page.get_by_role("button", name="Add course").click()
    popup = loaded_config_page.get_by_role("dialog")

    popup.get_by_label("Course ID").fill("CMSC 144")
    popup.get_by_label("Credits").fill(str(4))
    popup.get_by_label("Capacity").fill(str(30))
    popup.get_by_label("Specific").click()
    popup.get_by_label("Who can teach it").click()
    popup.get_by_label("Zoppetti").click()
    popup.get_by_label("Roddy 136").click()
    popup.get_by_label("Linux").click()


# def test_page_load_with_file(page: Page):
#  page.goto("http://localhost:8000/editor")

#  expect(page.get_by_role("heading", level=1, name="Configuration", exact=True)).to_be_visible()
