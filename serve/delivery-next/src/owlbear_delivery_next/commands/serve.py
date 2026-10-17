"""The host command's process: one host per clone, its scheduler and readiness threads, and the HTTP server."""

from __future__ import annotations

import contextlib
import os
import secrets
import socket
import sys
import threading
from typing import TYPE_CHECKING

import uvicorn

from owlbear_delivery_next.local_system.storage_io import atomic_write, open_lock
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import Host, running
from owlbear_delivery_next.runtimes import readiness
from owlbear_delivery_next.state_store.store import Store

if TYPE_CHECKING:
    from pathlib import Path


def serve(repo: Path) -> int:
    """Start the one host of this clone, or print the running host's URL and exit 0."""
    store = Store.open(repo)
    dir_fd = os.open(store.root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        lock_fd = open_lock(dir_fd, blocking=False, name="host.lock")
    except BlockingIOError:
        found = running(store)
        sys.stdout.write(f"Delivery is already running: {api.link(found) or '(starting)'}\n")
        return 0
    finally:
        os.close(dir_fd)
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    url, token = f"http://127.0.0.1:{sock.getsockname()[1]}/", secrets.token_urlsafe(32)
    host = Host(store, repo)
    host.record = host.record.model_copy(update={"url": url, "token": token})
    atomic_write(store.root / "host.json", host.record.model_dump_json())
    (store.root / "host.json").chmod(0o600)
    host.say(f"Delivery host {os.getpid()} on {api.link(host.record)}")

    def ready() -> None:
        failed = [f"{c.name}: {c.detail} · fix: {c.fix}" for c in readiness.ready(store, repo) if not c.ok]
        host.record = host.record.model_copy(update={"ready": failed})
        if not host.stopped.is_set():
            atomic_write(store.root / "host.json", host.record.model_dump_json())
        host.say("readiness: " + ("; ".join(failed) or "ok"))

    threading.Thread(target=ready, daemon=True, name="readiness").start()
    threading.Thread(target=host.run, daemon=True, name="scheduler").start()
    server = uvicorn.Server(uvicorn.Config(api.create_app(store, token, host), log_level="warning"))
    try:
        with contextlib.suppress(KeyboardInterrupt):
            server.run(sockets=[sock])
    finally:
        host.stopped.set()
        (store.root / "host.json").unlink(missing_ok=True)
        os.close(lock_fd)
    return 0
