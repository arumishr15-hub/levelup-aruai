"""Shared browser-test setup.

Browser tests need Playwright (pip install playwright && playwright install chromium)
and Pyodide for the live-mode tests (npm install). Set CHROME_PATH to use an installed
Chrome instead of Playwright's Chromium, and SHOTS_DIR to keep screenshots.
"""
import functools
import http.server
import os
import pathlib
import tempfile
import threading

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
SHOTS = pathlib.Path(os.environ.get("SHOTS_DIR", pathlib.Path(tempfile.gettempdir()) / "levelup_shots"))
PYODIDE_LOCAL = pathlib.Path(os.environ.get("PYODIDE_DIR", ROOT / "node_modules" / "pyodide"))


def serve_pyodide(route):
    """Serve Pyodide from node_modules instead of the CDN, so tests run offline."""
    name = route.request.url.split("/full/")[-1].split("?")[0]
    path = PYODIDE_LOCAL / name
    if not path.exists():
        return route.fulfill(status=404, body="")
    ctype = {".js": "text/javascript", ".wasm": "application/wasm", ".json": "application/json",
             ".zip": "application/zip"}.get(path.suffix, "application/octet-stream")
    route.fulfill(status=200, body=path.read_bytes(), headers={"content-type": ctype, "access-control-allow-origin": "*"})


@pytest.fixture(scope="session")
def url():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(WEB))
    handler.log_message = lambda *a: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}/index.html"
    srv.shutdown()


@pytest.fixture(scope="session")
def browser():
    pw = pytest.importorskip("playwright.sync_api")
    SHOTS.mkdir(parents=True, exist_ok=True)
    with pw.sync_playwright() as p:
        kwargs = {"args": ["--no-sandbox"]}
        if os.environ.get("CHROME_PATH"):
            kwargs["executable_path"] = os.environ["CHROME_PATH"]
        try:
            b = p.chromium.launch(**kwargs)
        except Exception as exc:  # no browser installed
            pytest.skip(f"no browser available: {exc}")
        yield b
        b.close()
