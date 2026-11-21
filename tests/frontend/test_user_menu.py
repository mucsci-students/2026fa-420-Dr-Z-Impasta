from playwright.sync_api import Page, expect


def test_user_menu_opens(page: Page, site: str):
    page.goto(site)

    account_button = page.get_by_role("button", name="Account", exact=True)

    account_button.click()

    expect(account_button).to_have_attribute("aria-expanded", "true")

    expect(page.get_by_text("Guest User")).to_be_visible()


def test_user_menu_closes_when_clicked_again(page: Page, site: str):
    page.goto(site)

    account_button = page.get_by_role("button", name="Account", exact=True)

    account_button.click()
    account_button.click()

    expect(account_button).to_have_attribute("aria-expanded", "false")


def test_guest_can_open_sign_in_dialog(page: Page, site: str):
    page.goto(site)

    page.get_by_role("button", name="Account", exact=True).click()

    page.get_by_role("button", name="Sign in").click()

    expect(page.get_by_role("heading", name="Sign in")).to_be_visible()


def test_guest_can_open_sign_up_dialog(page: Page, site: str):
    page.goto(site)

    page.get_by_role("button", name="Account", exact=True).click()

    page.get_by_role("button", name="Create account").click()

    expect(page.get_by_role("heading", name="Create account")).to_be_visible()


def test_clicking_outside_closes_menu(page: Page, site: str):
    page.goto(site)

    page.get_by_role("button", name="Account", exact=True).click()

    expect(page.get_by_text("Guest User")).to_be_visible()

    page.locator("body").click(position={"x": 10, "y": 10})

    expect(page.get_by_text("Guest User")).not_to_be_visible()
