"""Desktop launcher: starts the local FastAPI server and opens it in the
default browser. This is the entry point PyInstaller packages into the
.exe (see build_exe.py) -- it does not contain any pipeline logic itself,
it only boots competitor_analysis_agent.gui.server.
"""

from __future__ import annotations

import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

HOST = "127.0.0.1"
PORT = 8756


def _app_base_dir() -> Path:
    """Directory the .env file / output folder should live next to.

    When frozen by PyInstaller, sys.executable is the .exe itself; in dev,
    it's this script's own directory (the project root)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _port_is_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) != 0


def _open_browser_when_ready(url: str) -> None:
    for _ in range(100):
        if not _port_is_free(HOST, PORT):
            webbrowser.open(url)
            return
        time.sleep(0.1)


def _ensure_streams_for_frozen_gui(base_dir: Path) -> None:
    """A PyInstaller --noconsole/windowed build (i.e. launched by double-
    clicking the .exe, with no console attached at all) has sys.stdout and
    sys.stderr set to None -- but uvicorn's default logging setup (and
    click/colorama underneath it) call methods like .isatty() on those
    streams, which crashes with `AttributeError: 'NoneType' object has no
    attribute 'isatty'` the moment the server starts. Redirecting them to a
    real file (instead of leaving them None) fixes that, and as a bonus
    gives a place to see what happened if double-clicking the .exe ever
    fails silently (there's no console window to show a traceback in)."""
    if sys.stdout is not None and sys.stderr is not None:
        return
    log_file = open(base_dir / "app.log", "a", buffering=1, encoding="utf-8")
    if sys.stdout is None:
        sys.stdout = log_file
    if sys.stderr is None:
        sys.stderr = log_file


def _fix_playwright_browsers_path() -> None:
    """When frozen by PyInstaller, Playwright's own path heuristics mistake
    the bundle's extraction directory for a vendored install and look for
    Chromium there instead of the normal per-user cache -- point it at the
    same cache `playwright install chromium` (run outside the .exe) already
    populates, so Live Run's pricing/review scraping doesn't need the
    browser bundled into the .exe itself."""
    if os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
        return
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(Path(local_app_data) / "ms-playwright")


def main() -> int:
    base_dir = _app_base_dir()
    os.chdir(base_dir)  # so Settings' env_file=".env" and output_dir="output" resolve next to the exe
    _ensure_streams_for_frozen_gui(base_dir)
    _fix_playwright_browsers_path()

    if not _port_is_free(HOST, PORT):
        webbrowser.open(f"http://{HOST}:{PORT}/")
        print(f"Uygulama zaten çalışıyor: http://{HOST}:{PORT}/")
        return 0

    import uvicorn

    from competitor_analysis_agent.gui.server import app

    threading.Thread(target=_open_browser_when_ready, args=(f"http://{HOST}:{PORT}/",), daemon=True).start()

    print(f"Rakip ve Pazar Analizi Ajanı başlatılıyor: http://{HOST}:{PORT}/")
    # log_config=None: skip uvicorn's own logging.config.dictConfig setup
    # entirely -- it's unneeded (the GUI's live log panel is fed by our own
    # queue-based logging.Handler in gui/job_manager.py, not by uvicorn's
    # access/error loggers) and its default formatter is one more thing that
    # can trip over a None/non-console stream in a frozen --noconsole build.
    uvicorn.run(app, host=HOST, port=PORT, log_level="info", log_config=None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
