import os

import pytest
from playwright.sync_api import Page, expect

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not os.environ.get("OPENAI_API_KEY", "").strip(),
        reason="OPENAI_API_KEY is not set, so the live OpenAI test is skipped.",
    ),
]


def test_undo_button(loaded_config_page: Page):
    # get the number of rooms appearing on the screen before editing
    room_section = loaded_config_page.locator("section.editor-row").filter(
        has=loaded_config_page.get_by_role("heading", level=2, name="Rooms")
    )
    room_count_locator = room_section.locator(".editor-row__meta")
    number_of_rooms_before = int(room_count_locator.inner_text())

    # get the number of faculty appearing on the screen before adding a faculty
    faculty_section = loaded_config_page.locator("section.editor-row").filter(
        has=loaded_config_page.get_by_role("heading", level=2, name="Faculty")
    )
    fac_count_locator = faculty_section.locator(".editor-row__meta")
    number_of_fac_before = int(fac_count_locator.inner_text())

    # open AI chatbot & put in a request
    loaded_config_page.get_by_role("button", name="Ask Dr. ZImpasta").click()
    loaded_config_page.get_by_role("textbox", name="Message to Dr. ZImpasta").fill(
        "Add a room named Room 201 with a capacity of 30."
    )

    loaded_config_page.get_by_role("button", name="Send").click()
    loaded_config_page.get_by_role("button", name="Close chat").click()

    expect(room_count_locator).to_have_text(str(number_of_rooms_before + 1), timeout=10000)

    button = loaded_config_page.get_by_role("button", name="Undo")
    expect(button).to_be_visible()
    expect(button).to_be_enabled(timeout=10000)

    button.click()
    expect(room_count_locator).to_have_text(str(number_of_rooms_before), timeout=10000)
    expect(button).to_be_disabled(timeout=10000)

    # open AI chatbot & put in a batch request
    loaded_config_page.get_by_role("button", name="Ask Dr. ZImpasta").click()
    loaded_config_page.get_by_role("textbox", name="Message to Dr. ZImpasta").fill(
        """Add 2 things: Add a room named Room 202 with a capacity of 30 and 
          Add a faculty named Dr. Aaron, 3 minimum credits, 5 maximum credits, 
          1 different course, and 0 teaching days."""
    )

    loaded_config_page.get_by_role("button", name="Send").click()
    loaded_config_page.get_by_role("button", name="Close chat").click()

    expect(room_count_locator).to_have_text(str(number_of_rooms_before + 1), timeout=10000)
    expect(fac_count_locator).to_have_text(str(number_of_fac_before + 1), timeout=10000)

    button = loaded_config_page.get_by_role("button", name="Undo")
    expect(button).to_be_visible()
    expect(button).to_be_enabled(timeout=10000)

    button.click()
    expect(room_count_locator).to_have_text(str(number_of_rooms_before), timeout=10000)
    expect(fac_count_locator).to_have_text(str(number_of_fac_before), timeout=10000)
    expect(button).to_be_disabled(timeout=10000)

    # test a deletion
    loaded_config_page.get_by_role("button", name="Ask Dr. ZImpasta").click()
    loaded_config_page.get_by_role("textbox", name="Message to Dr. ZImpasta").fill(
        "Add a room named 203 with a capacity of 30."
    )

    loaded_config_page.get_by_role("button", name="Send").click()
    loaded_config_page.get_by_role("textbox", name="Message to Dr. ZImpasta").fill(
        "Delete room 203."
    )

    loaded_config_page.get_by_role("button", name="Send").click()
    loaded_config_page.get_by_role("button", name="Confirm").click()
    loaded_config_page.get_by_role("button", name="Close chat").click()

    expect(room_count_locator).to_have_text(str(number_of_rooms_before), timeout=10000)

    button = loaded_config_page.get_by_role("button", name="Undo")
    expect(button).to_be_visible()
    expect(button).to_be_enabled(timeout=10000)

    button.click()
    expect(room_count_locator).to_have_text(str(number_of_rooms_before + 1), timeout=10000)
    expect(button).to_be_disabled(timeout=10000)


def test_redo_button(loaded_config_page: Page):
    # get the number of rooms appearing on the screen before editing
    room_section = loaded_config_page.locator("section.editor-row").filter(
        has=loaded_config_page.get_by_role("heading", level=2, name="Rooms")
    )
    room_count_locator = room_section.locator(".editor-row__meta")
    number_of_rooms_before = int(room_count_locator.inner_text())

    # get the number of faculty appearing on the screen before adding a faculty
    faculty_section = loaded_config_page.locator("section.editor-row").filter(
        has=loaded_config_page.get_by_role("heading", level=2, name="Faculty")
    )
    fac_count_locator = faculty_section.locator(".editor-row__meta")
    number_of_fac_before = int(fac_count_locator.inner_text())

    # open AI chatbot & put in a request
    loaded_config_page.get_by_role("button", name="Ask Dr. ZImpasta").click()
    loaded_config_page.get_by_role("textbox", name="Message to Dr. ZImpasta").fill(
        "Add a room named Room 201 with a capacity of 30."
    )

    loaded_config_page.get_by_role("button", name="Send").click()
    loaded_config_page.get_by_role("button", name="Close chat").click()

    expect(room_count_locator).to_have_text(str(number_of_rooms_before + 1), timeout=10000)

    # undo
    undoBtn = loaded_config_page.get_by_role("button", name="Undo")
    expect(undoBtn).to_be_visible()
    expect(undoBtn).to_be_enabled(timeout=10000)

    undoBtn.click()
    expect(room_count_locator).to_have_text(str(number_of_rooms_before), timeout=10000)
    expect(undoBtn).to_be_disabled(timeout=10000)

    # redo
    redoBtn = loaded_config_page.get_by_role("button", name="Redo")
    expect(redoBtn).to_be_visible()
    expect(redoBtn).to_be_enabled(timeout=10000)

    redoBtn.click()
    expect(room_count_locator).to_have_text(str(number_of_rooms_before + 1), timeout=10000)
    expect(redoBtn).to_be_disabled(timeout=10000)

    # open AI chatbot & put in a batch request
    loaded_config_page.get_by_role("button", name="Ask Dr. ZImpasta").click()
    loaded_config_page.get_by_role("textbox", name="Message to Dr. ZImpasta").fill(
        """Add 2 things: Add a room named Room 202 with a capacity of 30 and 
          Add a faculty named Dr. Aaron, 3 minimum credits, 5 maximum credits, 
          1 different course, and 0 teaching days."""
    )

    loaded_config_page.get_by_role("button", name="Send").click()
    loaded_config_page.get_by_role("button", name="Close chat").click()

    expect(room_count_locator).to_have_text(str(number_of_rooms_before + 2), timeout=10000)
    expect(fac_count_locator).to_have_text(str(number_of_fac_before + 1), timeout=10000)

    # undo
    undoBtn = loaded_config_page.get_by_role("button", name="Undo")
    expect(undoBtn).to_be_visible()
    expect(undoBtn).to_be_enabled(timeout=10000)

    undoBtn.click()
    expect(room_count_locator).to_have_text(str(number_of_rooms_before + 1), timeout=10000)
    expect(fac_count_locator).to_have_text(str(number_of_fac_before), timeout=10000)
    expect(undoBtn).to_be_enabled(timeout=10000)

    # redo
    redoBtn = loaded_config_page.get_by_role("button", name="Redo")
    expect(redoBtn).to_be_visible()
    expect(redoBtn).to_be_enabled(timeout=10000)

    redoBtn.click()
    expect(room_count_locator).to_have_text(str(number_of_rooms_before + 2), timeout=10000)
    expect(fac_count_locator).to_have_text(str(number_of_fac_before + 1), timeout=10000)
    expect(redoBtn).to_be_disabled(timeout=10000)

    # test a deletion
    loaded_config_page.get_by_role("button", name="Ask Dr. ZImpasta").click()
    loaded_config_page.get_by_role("textbox", name="Message to Dr. ZImpasta").fill(
        "Add a room named 203 with a capacity of 30."
    )

    loaded_config_page.get_by_role("button", name="Send").click()
    loaded_config_page.get_by_role("textbox", name="Message to Dr. ZImpasta").fill(
        "Delete room 203."
    )

    loaded_config_page.get_by_role("button", name="Send").click()
    loaded_config_page.get_by_role("button", name="Confirm").click()
    loaded_config_page.get_by_role("button", name="Close chat").click()

    expect(room_count_locator).to_have_text(str(number_of_rooms_before + 2), timeout=10000)

    # undo
    undoBtn = loaded_config_page.get_by_role("button", name="Undo")
    expect(undoBtn).to_be_visible()
    expect(undoBtn).to_be_enabled(timeout=10000)

    undoBtn.click()
    expect(room_count_locator).to_have_text(str(number_of_rooms_before + 3), timeout=10000)
    expect(undoBtn).to_be_enabled(timeout=10000)

    # redo
    redoBtn = loaded_config_page.get_by_role("button", name="Redo")
    expect(redoBtn).to_be_visible()
    expect(redoBtn).to_be_enabled(timeout=10000)

    redoBtn.click()
    expect(room_count_locator).to_have_text(str(number_of_rooms_before + 2), timeout=10000)
    expect(redoBtn).to_be_disabled(timeout=10000)
