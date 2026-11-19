"""End-to-end test: play the web app in a real headless browser."""
import json

import pytest

from conftest import WEB, SHOTS


def _answer_of(page):
    """Look up the right answer for the question on screen from the bank."""
    lines = page.evaluate("() => [...document.querySelectorAll('.ln code')].map(c => c.textContent)")
    code = "\n".join(line.rstrip() for line in lines)
    bank = json.loads((WEB / "bank.json").read_text())
    return next(q for q in bank["questions"] if q["code"] == code)


def test_play_through(browser, url):
    SHOTS.mkdir(exist_ok=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(url)
    page.wait_for_selector(".opt")
    assert "Teacher Agent" in page.inner_text("#tcard")
    page.screenshot(path=str(SHOTS / "1_question.png"), full_page=True)

    # hint
    page.click("#hint")
    assert "Hint:" in page.inner_text("#tcard")

    # wrong answer -> misconception feedback + step-through
    q = _answer_of(page)
    wrong = next(i for i, o in enumerate(q["options"]) if o != q["answer"])
    page.locator(".opt").nth(wrong).click()
    tc = page.inner_text("#tcard")
    assert "Not quite" in tc and q["misconceptions"][q["options"][wrong]] in tc
    assert page.locator(".ln.on").count() == 1
    page.click("#nxt")
    page.screenshot(path=str(SHOTS / "2_feedback.png"), full_page=True)

    # three right answers in a row -> level up, agents talk
    for _ in range(3):
        page.click("#next")
        page.wait_for_selector(".opt:not([disabled])")
        q = _answer_of(page)
        page.locator(".opt").nth(q["options"].index(q["answer"])).click()
        assert "Correct!" in page.inner_text("#tcard")
    level = int(page.inner_text("#sLevel"))
    log = page.inner_text("#log")
    assert "Question Agent" in log and "Teacher" in log and "level" in log
    # streak is per topic, so level-up depends on topic mix; with mixed topics the focus topic repeats
    assert level >= 1 and int(page.inner_text("#sXp").split()[0]) > 0
    page.screenshot(path=str(SHOTS / "3_progress.png"), full_page=True)

    # topic chip + keyboard play
    page.click(".chip[data-t='loops']")
    assert page.inner_text(".qhead .tag >> nth=0") == "loops"
    page.keyboard.press("1")
    page.wait_for_selector("#next")
    assert not errors, errors


def test_level_up_on_one_topic(browser, url):
    page = browser.new_page()
    page.goto(url)
    page.wait_for_selector(".opt")
    page.click(".chip[data-t='strings']")
    for _ in range(3):
        page.wait_for_selector(".opt:not([disabled])")
        q = _answer_of(page)
        page.locator(".opt").nth(q["options"].index(q["answer"])).click()
        page.click("#next")
    assert page.inner_text("#sLevel") == "2"
    assert page.inner_text(".qhead .lvl") == "Level 2"


@pytest.mark.parametrize("theme,width", [("dark", 390), ("light", 390), ("dark", 1280)])
def test_layout_no_overflow(browser, url, theme, width):
    page = browser.new_page(viewport={"width": width, "height": 860}, color_scheme=theme)
    page.goto(url)
    page.wait_for_selector(".opt")
    page.locator(".opt").first.click()
    assert page.evaluate("document.documentElement.scrollWidth") <= width
    page.screenshot(path=str(SHOTS / f"layout_{theme}_{width}.png"), full_page=True)
