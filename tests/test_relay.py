"""Free-AI mode: the relay Worker (unit tests in Node) and the full app through it in a browser."""
import json
import pathlib
import shutil
import subprocess

import pytest

from conftest import PYODIDE_LOCAL, SHOTS, serve_pyodide

ROOT = pathlib.Path(__file__).resolve().parent.parent
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(not NODE, reason="node not installed")


def test_relay_worker_unit_tests():
    r = subprocess.run([NODE, "--test", "relay/test/worker.test.mjs"], cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    assert "# fail 0" in r.stdout


@pytest.fixture(scope="module")
def relay_url():
    proc = subprocess.Popen([NODE, "relay/test/e2e-servers.mjs"], cwd=ROOT, stdout=subprocess.PIPE, text=True)
    url = json.loads(proc.stdout.readline())["relay"]
    yield url
    proc.terminate()


def test_free_ai_mode_end_to_end(browser, url, relay_url):
    if not PYODIDE_LOCAL.exists():
        pytest.skip("local pyodide not installed")
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.add_init_script(f"window.LEVELUP_RELAY = {json.dumps(relay_url)};")
    page.route("https://cdn.jsdelivr.net/pyodide/**", serve_pyodide)
    sent, errors = [], []
    page.on("request", lambda r: sent.append((r.url, r.headers.get("authorization"), r.post_data or "")))
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(url)
    page.wait_for_selector("#goLive:not([disabled])", timeout=20000)
    assert "Free live AI is connected" in page.inner_text("#log")

    page.click("#goLive")
    page.wait_for_selector(".opt", timeout=60000)
    assert page.inner_text("#sMode") == "Live AI"
    assert "Free AI" in page.inner_text("#tcard")
    log = page.inner_text("#log")
    assert "The AI's draft said ka3" in log and "Python printed kakaka" in log      # wrong key fixed by Python
    assert "fixed by Python" in page.inner_text("#qcard")

    opts = page.locator(".opt")
    idx = [opts.nth(i).inner_text().split("\n")[-1].strip() for i in range(4)].index("ka3")
    opts.nth(idx).click()
    page.wait_for_function("document.querySelector('#explain') && document.querySelector('#explain').textContent.includes('repeats the text')")
    assert "secret thoughts" not in page.inner_text("#tcard")

    page.fill("#chatIn", "Why do lists start at 0?")
    page.press("#chatIn", "Enter")
    page.wait_for_function("[...document.querySelectorAll('.cm.ai')].some(e => e.textContent.includes('index counts steps'))")
    page.screenshot(path=str(SHOTS / "relay_mode.png"), full_page=True)

    relay_calls = [s for s in sent if s[0].startswith(relay_url)]
    assert {u.rsplit("/", 1)[-1] for u, _, _ in relay_calls} >= {"health", "question", "explain", "chat"}
    assert all("test-key" not in (a or "") + body for _, a, body in sent)              # the key never touches the browser
    assert not errors, errors
