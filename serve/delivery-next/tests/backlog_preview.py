"""The machine host's Backlog page on fixture data only, for the visual check: ``backlog_preview.py <port>``.

Launch recipe for the visual check: directory ``serve/delivery-next``, command
``uv run python tests/backlog_preview.py {port}``, ready URL ``http://127.0.0.1:{port}/backlog``; state paths open
without ``#token=`` because ``metrics_preview.SEED`` supplies the token.

It never reads the owner's data: ``main`` replaces HOME with a fresh temporary folder (``metrics_preview._isolate``)
before loading HOME-sensitive application state, drops ``OWLBEAR_DATA`` and ``COPILOT_HOME``, and keeps Git from
reaching GitHub (D-01M68Z8Q740BSN13D1R06JX6DW); importing this file changes nothing. It makes no ``gh`` call either:
an in-memory issue store replaces ``backlog_issues.RUNNER``, the write account is chosen offline, the readiness check
is skipped, a ``gh`` that only fails comes first on PATH, and the shared data repository is a local checkout in that
HOME whose origin names ``github.com/preview/owlbear-data`` and pushes to a local bare repository.

The fixture is written through ``Backlog``: the owner's ideas and a question, two audit defects, several untriaged
suppression reviews found in the registered clone ``shop-site``, and suppression reviews triaged open and dropped.
``/backlog?reviews=open`` shows the Suppression reviews section unfolded: a script only this preview adds opens it;
the page itself has no such parameter. The script does nothing where the page has no such section.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qsl

import uvicorn
from metrics_preview import SEED, TOKEN, _isolate, seed_pages

__all__ = ["OPEN", "SEED", "TOKEN"]

DATA = "https://github.com/preview/owlbear-data.git"
CLONE = ("shop-site", "https://github.com/preview/shop-site.git")
OPEN = """<script>
if (new URLSearchParams(location.search).get("reviews") === "open") {
  new MutationObserver(() => {
    const section = document.getElementById("suppression-reviews");
    if (section && !section.dataset.previewOpened) { section.dataset.previewOpened = "1"; section.open = true; }
  }).observe(document.documentElement, { childList: true, subtree: true });
}
</script>"""
OWNER = (  # (title, text, kind): untriaged stays in the Inbox
    ("Show the build date in the footer", "So I can tell which version a screenshot shows.", "untriaged"),
    ("Group the runs by week", "", "idea"),
    ("Should drafts expire after a month?", "Old drafts pile up on the Changes page.", "question"),
)
DEFECTS = (  # (title, text, kind), found by the audit
    ("Stale lock file survives a crashed launch", "The next launch waits for a lock nobody holds.", "untriaged"),
    ("Retry count resets when the host restarts", "A step may then retry without bound.", "defect"),
)
REVIEWS = (  # (directive, place, status): inbox ones fold into the Suppression reviews section
    ("# noqa: SLF001", "serve/shop/src/cart.py", "inbox"),
    ("# noqa: PLR0913", "serve/shop/src/checkout.py", "inbox"),
    ("# type: ignore[attr-defined]", "serve/shop/src/pricing.py", "inbox"),
    ("# noqa: S603", "serve/shop/src/deploy.py", "inbox"),
    ("// biome-ignore lint/style/noNonNullAssertion", "web/shop/basket.mjs", "inbox"),
    ("# noqa: BLE001", "serve/shop/src/payments.py", "open"),
    ("# noqa: C901", "serve/shop/src/search.py", "dropped"),
)


def _title(rule: str, place: str, group: str) -> str:
    """The Suppression review's title; a merge-base without ``backlog.suppression_title`` gets the same literal."""
    try:
        from owlbear_delivery_next.state_store.backlog import suppression_title  # noqa: PLC0415
    except ImportError:
        return f"Review {rule[:80]} in {place[:60]} [{group}]"
    return suppression_title(rule, place, group)


class Issues:
    """GitHub's issue and label REST API for one repository, in memory, behind the ``gh api`` runner."""

    def __init__(self) -> None:
        self.issues: dict[int, dict] = {}
        self.labels: dict[str, dict] = {}
        self.tick = 0

    def __call__(self, argv, data, _timeout, _cwd, _env) -> subprocess.CompletedProcess[bytes]:
        method = argv[argv.index("--method") + 1]
        path, _, query = next(a for a in argv if a.startswith("repos/")).partition("?")
        status, out = self._answer(method, path.split("/")[3:], dict(parse_qsl(query)), json.loads(data or "null"))
        if status:
            return subprocess.CompletedProcess(argv, 1, b"", f"gh: {out} (HTTP {status})\n".encode())
        return subprocess.CompletedProcess(argv, 0, json.dumps(out).encode(), b"")

    def _answer(self, method: str, parts: list[str], params: dict, body: dict | None) -> tuple[int, object]:  # noqa: PLR0911
        if not parts:
            return 0, {"full_name": "preview/owlbear-data", "private": True, "visibility": "private"}
        if parts == ["labels"]:
            if method == "GET":
                return 0, _page(list(self.labels.values()), params)
            self.labels.setdefault(body["name"], {"name": body["name"], "color": body["color"]})
            return 0, self.labels[body["name"]]
        if parts == ["issues"] and method == "GET":
            return 0, _page(sorted(self.issues.values(), key=lambda i: -i["number"]), params)
        if parts == ["issues"]:
            number = len(self.issues) + 1
            url = f"https://github.com/preview/owlbear-data/issues/{number}"
            self.issues[number] = {"number": number, "state": "open", "state_reason": None, "html_url": url}
            return 0, self._edit(self.issues[number], body)
        number = int(parts[1])
        if number not in self.issues:
            return 404, "Not Found"
        if parts[2:] == ["comments"]:
            return 0, [] if method == "GET" else {"id": 1, "html_url": self.issues[number]["html_url"]}
        return 0, self.issues[number] if method == "GET" else self._edit(self.issues[number], body)

    def _edit(self, issue: dict, body: dict) -> dict:
        issue |= {k: v for k, v in body.items() if k != "labels"}
        if "labels" in body:
            issue["labels"] = [{"name": n} for n in body["labels"]]
        if body.get("state") == "open":
            issue["state_reason"] = None
        self.tick += 1
        issue["updated_at"] = f"{datetime.now(UTC):%Y-%m-%dT%H:%M}:{self.tick % 60:02d}Z"
        return issue


def _page(items: list, params: dict) -> list:
    size, page = int(params.get("per_page", 30)), int(params.get("page", 1))
    return items[(page - 1) * size : page * size]


def _git(cwd: Path, *args: str) -> None:
    who = ("-c", "user.name=preview", "-c", "user.email=preview@example.invalid")
    subprocess.run(["git", *who, *args], cwd=cwd, check=True, capture_output=True)  # noqa: S603, S607


def _checkout(path: Path, origin: str, remote: Path | None = None) -> Path:
    """A local repository with one commit whose ``origin`` names *origin*; Git reaches *remote* for it, or nothing."""
    path.mkdir(parents=True)
    _git(path, "init", "-q", "-b", "main")
    _git(path, "remote", "add", "origin", origin)
    _git(path, "commit", "-q", "--allow-empty", "-m", "start")
    if remote:  # the longer insteadOf wins over HOME's rule that keeps GitHub unreachable
        _git(path.parent, "init", "-q", "--bare", "-b", "main", str(remote))
        _git(path, "config", f"url.{remote}.insteadOf", origin)
        _git(path, "push", "-q", "-u", "origin", "HEAD")
    return path.resolve()


def _offline(home: Path) -> None:
    """In *home*: a Git identity for the fixture's commits, and a ``gh`` first on PATH that never reaches GitHub."""
    with (home / ".gitconfig").open("a") as config:
        config.write("[user]\n\tname = preview\n\temail = preview@example.invalid\n")
    tools = home / "bin"
    tools.mkdir()
    (tools / "gh").write_text('#!/bin/sh\necho "gh is offline in the Backlog preview" >&2\nexit 1\n')
    (tools / "gh").chmod(0o755)
    os.environ["PATH"] = f"{tools}{os.pathsep}{os.environ.get('PATH', '')}"


def seed(home: Path) -> None:
    """The shared data checkout, the registered clone, and the backlog's entries written through ``Backlog``."""
    from owlbear_delivery_next.git.access import Access  # noqa: PLC0415 - imported once HOME is the fixture's
    from owlbear_delivery_next.github import account  # noqa: PLC0415
    from owlbear_delivery_next.local_system.data_repo import DataRepo  # noqa: PLC0415
    from owlbear_delivery_next.machine_host import project  # noqa: PLC0415
    from owlbear_delivery_next.state_store import backlog_issues, registry  # noqa: PLC0415
    from owlbear_delivery_next.state_store.backlog import Backlog  # noqa: PLC0415

    def offline(setting: str, origin: account.Origin, *, until: float | None = None) -> Access:
        del until
        if origin == account.Origin.LOCAL:
            return Access.LOCAL
        login = account.FALLBACK if setting == account.REPOSITORY_OWNER else setting
        return Access(login, "chosen offline in the preview", origin.host, f"preview-{login}", "gh")

    _offline(home)
    backlog_issues.RUNNER = Issues()
    account.resolve = offline
    project.readiness.ready = lambda _store, _repo, **_kwargs: []  # its checks ask GitHub
    shared = DataRepo(_checkout(home / ".owlbear" / "data", DATA, home / "remotes" / "owlbear-data.git"))
    name, origin = CLONE
    registry.register(_checkout(home / "projects" / name, origin))
    book = Backlog(shared, name)
    for title, text, kind in OWNER:
        entry, _ = book.add(title, text, source="owner")
        if kind != "untriaged":
            book.update(entry.id, {"kind": kind})
    for title, text, kind in DEFECTS:
        entry, _ = book.add(title, text, source="audit")
        if kind != "untriaged":
            book.update(entry.id, {"kind": kind})
    for n, (rule, place, status) in enumerate(REVIEWS, 1):
        entry, _ = book.add(_title(rule, place, f"{n:016x}"), "Refused in the pinned inventory.", source="audit")
        if status == "open":
            book.update(entry.id, {"kind": "improvement"})
        elif status != "inbox":
            book.update(entry.id, {"status": status})


def open_reviews(pages) -> None:
    """The Backlog page *pages* serves gets ``OPEN`` after ``<head>``: ``?reviews=open`` unfolds its reviews."""
    served = pages.pages
    pages.pages = lambda: {p: h.replace("<head>", "<head>" + OPEN, 1) if p == "/backlog" else h
                           for p, h in served().items()}  # fmt: skip


def main() -> None:
    port = int(sys.argv[1])
    home = _isolate()
    from owlbear_delivery_next.local_system import codebase  # noqa: PLC0415
    from owlbear_delivery_next.machine_host import app  # noqa: PLC0415
    from owlbear_delivery_next.machine_host.machine import Machine  # noqa: PLC0415
    from owlbear_delivery_next.project_host import pages  # noqa: PLC0415
    from owlbear_delivery_next.project_host.host import HostRecord  # noqa: PLC0415

    def gone() -> None:
        shutil.rmtree(home, ignore_errors=True)

    try:
        seed(home)
        open_reviews(pages)
        seed_pages(pages)  # last: the token's seed comes first in <head>, before any other script
        base = f"http://127.0.0.1:{port}"
        record = HostRecord(url=f"{base}/", token=TOKEN, pid=os.getpid(), started_at=datetime.now(UTC),
                            code=codebase.CURRENT)  # fmt: skip
        machine = Machine(record)
        machine.load_all()  # the registered clone, so the page lists its backlog
        print(f"Backlog preview: {base}/backlog#token={TOKEN}", flush=True)  # noqa: T201 - the recipe's address
        try:
            uvicorn.run(app.create(machine, gone), host="127.0.0.1", port=port, log_level="warning")
        finally:
            machine.stop_all()
    finally:  # Uvicorn replays a stop signal once it returns: the app's own end removes HOME
        gone()


if __name__ == "__main__":
    main()
