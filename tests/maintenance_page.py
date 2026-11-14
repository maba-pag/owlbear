"""The native project Maintenance page, with test-owned server and Chromium lifetimes."""

import socket
import threading
import time
from contextlib import contextmanager

import uvicorn

from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.state_store.store import Store


@contextmanager
def opened(root, pds, *, startup=None):
    from playwright.sync_api import sync_playwright  # noqa: PLC0415 - optional browser runtime

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        server = uvicorn.Server(uvicorn.Config(api.create_app(Store(root), "tok", None), log_level="warning"))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + startup if startup is not None else None
            while not server.started:
                assert thread.is_alive(), "the owned page server stopped before startup"
                assert deadline is None or time.monotonic() < deadline, "the owned page server did not start"
                time.sleep(0.05)
            base = f"http://127.0.0.1:{sock.getsockname()[1]}"
            with sync_playwright() as pw:
                browser = pw.chromium.launch()
                try:
                    page = browser.new_page()
                    pds.only(page, base)
                    yield page, base
                finally:
                    browser.close()
        finally:
            server.should_exit = True
            thread.join(5)
            assert not thread.is_alive(), "the owned page server did not stop"
