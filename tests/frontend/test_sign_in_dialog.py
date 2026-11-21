import json

from playwright.sync_api import Page, expect
from server import site

def open_sign_in(page: Page, site: str):
    page.goto(site)

    page.get_by_role("button", name="Account", exact=True).click()

    page.get_by_role("button", name="Sign in").click()

    expect(
        page.get_by_role("heading", name="Sign in")
    ).to_be_visible()


def open_sign_up(page: Page, site: str):
    page.goto(site)

    page.get_by_role("button", name="Account", exact=True).click()

    page.get_by_role("button", name="Create account").click()

    expect(
        page.get_by_role("heading", name="Create account")
    ).to_be_visible()


def test_sign_in_dialog_opens(page: Page, site: str):
    open_sign_in(page, site)

    expect(page.get_by_label("Username")).to_be_visible()
    expect(page.get_by_label("Password")).to_be_visible()


def test_sign_in_dialog_closes(page: Page, site: str):
    open_sign_in(page, site)

    page.get_by_role("button", name="Close").click()

    expect(
        page.get_by_role("heading", name="Sign in")
    ).not_to_be_visible()


def test_sign_in_submits_credentials(page: Page, site: str):
    requests = []

    open_sign_in(page, site)

    def login(route):
        requests.append(route.request.post_data_json)

        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({})
        )

    page.route("**/api/account/login", login)

    page.get_by_role("textbox", name="Username").fill("testuser")
    page.get_by_label("Password").fill("password123")

    page.get_by_role("button", name="Sign in").click()

    expect(
        page.get_by_role("heading", name="Sign in")
    ).not_to_be_visible()

    assert requests[0]["username"] == "testuser"
    assert requests[0]["password"] == "password123"


def test_sign_in_shows_error_for_invalid_credentials(
    page: Page, site: str
):
    open_sign_in(page, site)

    def login(route):
        route.fulfill(
            status=401,
            content_type="application/json",
            body=json.dumps({
                "error": {
                    "code": "invalid_credentials",
                    "message": "Invalid credentials."
                }
            })
        )

    page.route("**/api/account/login", login)

    page.get_by_role("textbox", name="Username").fill("wronguser")
    page.get_by_label("Password").fill("wrongpassword")

    page.get_by_role("button", name="Sign in").click()

    expect(
            page.get_by_text("Invalid login.")
        ).to_have_text("Invalid login.")


def test_sign_up_shows_requirements(page: Page, site: str):
    open_sign_up(page, site)

    expect(
        page.get_by_role("region", name="Account requirements")
    ).to_be_visible()

    expect(
        page.get_by_text("Username is 3 to 32 characters")
    ).to_be_visible()

    expect(
        page.get_by_text("Password is 8 to 128 characters")
    ).to_be_visible()


def test_sign_up_updates_username_requirements(
    page: Page, site: str
):
    open_sign_up(page, site)

    username = page.get_by_role("textbox", name="Username")

    username.fill("ab")

    expect(
        page.get_by_role(
            "listitem",
            name="Username is 3 to 32 characters: not met"
        )
    ).to_be_visible()

    username.fill("testuser")

    expect(
        page.get_by_role(
            "listitem",
            name="Username is 3 to 32 characters: met"
        )
    ).to_be_visible()
