import json

from playwright.sync_api import Page, expect


def open_add_state_dialog(page: Page, site: str):
    # Simulate a logged-in account.
    page.route(
        "**/api/account",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "available": True,
                    "user": {"username": "testuser"},
                    "state": None,
                    "sync": {"status": "saved", "saved_at": None, "error": None},
                }
            ),
        ),
    )

    page.route(
        "**/api/states",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"states": [], "account": {}}),
        ),
    )

    page.goto(site)

    page.get_by_role("button", name="Account", exact=True).click()

    page.get_by_role("button", name="Add State").click()

    expect(page.get_by_role("heading", name="Add a State")).to_be_visible()


def test_add_state_dialog_opens(page: Page, site: str):
    open_add_state_dialog(page, site)

    expect(page.get_by_label("Title")).to_be_visible()

    expect(page.get_by_role("button", name="Create State")).to_be_visible()


def test_add_state_dialog_closes(page: Page, site: str):
    open_add_state_dialog(page, site)

    page.get_by_role("button", name="Close").click()

    expect(page.get_by_role("heading", name="Add a State")).not_to_be_visible()


def test_create_state(page: Page, site: str):
    requests = []

    open_add_state_dialog(page, site)

    def create_state(route):
        requests.append(route.request.post_data_json)

        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"states": [], "state": {"id": 1, "name": "Test State"}}),
        )

    page.route("**/api/states", create_state)

    page.get_by_label("Title").fill("Test State")

    page.get_by_role("button", name="Create State").click()

    expect(page.get_by_role("heading", name="Add a State")).not_to_be_visible()

    assert requests[0]["name"] == "Test State"
    assert requests[0]["copy_current"] is False


def test_create_state_with_copy(page: Page, site: str):
    requests = []

    open_add_state_dialog(page, site)

    def create_state(route):
        requests.append(route.request.post_data_json)

        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"states": [], "state": {"id": 2, "name": "Copied State"}}),
        )

    page.route("**/api/states", create_state)

    page.get_by_label("Title").fill("Copied State")

    page.get_by_label("Copy Current State?").check()

    page.get_by_role("button", name="Create State").click()

    expect(page.get_by_role("heading", name="Add a State")).not_to_be_visible()

    assert requests[0]["name"] == "Copied State"
    assert requests[0]["copy_current"] is True
