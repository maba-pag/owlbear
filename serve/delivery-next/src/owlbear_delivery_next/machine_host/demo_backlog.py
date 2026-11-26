"""The demo's Backlog scenario: its entries live in an in-memory copy of GitHub's issue API, never on GitHub.

``seed`` installs one ``Issues`` as ``backlog_issues.RUNNER`` for the life of the process, then writes through
``Backlog``: the owner's ideas and a question, two audit defects, several untriaged suppression reviews found in
the example shop, and suppression reviews triaged open and dropped. The page's own reads reach the same entries.
``OPEN`` is the script only the demo's Backlog page carries: ``/backlog?reviews=open`` unfolds its Suppression reviews
section; the page itself has no such parameter, and the script does nothing where the page has no such section.
"""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qsl

from owlbear_delivery_next.state_store import backlog_issues
from owlbear_delivery_next.state_store.backlog import Backlog, suppression_title

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from owlbear_delivery_next.local_system.data_repo import DataRepo

REPOSITORY = "example/owlbear-data"
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


class Issues:
    """GitHub's issue and label REST API for one repository, in memory, behind the ``gh api`` runner."""

    def __init__(self) -> None:
        """No issues and no labels yet."""
        self.issues: dict[int, dict[str, Any]] = {}
        self.labels: dict[str, dict[str, Any]] = {}
        self.tick = 0

    def __call__(
        self,
        argv: tuple[str, ...],
        data: bytes | None,
        _timeout: float,
        _cwd: Path | None,
        _env: Mapping[str, str] | None,
    ) -> subprocess.CompletedProcess[bytes]:
        """Answer one ``gh api`` call as GitHub would, from memory."""
        method = argv[argv.index("--method") + 1]
        path, _, query = next(a for a in argv if a.startswith("repos/")).partition("?")
        status, out = self._answer(method, path.split("/")[3:], dict(parse_qsl(query)), json.loads(data or "null"))
        if status:
            return subprocess.CompletedProcess(argv, 1, b"", f"gh: {out} (HTTP {status})\n".encode())
        return subprocess.CompletedProcess(argv, 0, json.dumps(out).encode(), b"")

    def _answer(self, method: str, parts: list[str], params: dict, body: dict | None) -> tuple[int, object]:
        if not parts:
            return 0, {"full_name": REPOSITORY, "private": True, "visibility": "private"}
        if parts == ["labels"]:
            if method != "GET":
                self.labels.setdefault(body["name"], {"name": body["name"], "color": body["color"]})
                return 0, self.labels[body["name"]]
            return 0, _page(list(self.labels.values()), params)
        if parts == ["issues"]:
            return 0, self._listed(params) if method == "GET" else self._opened(body)
        return self._issue(method, int(parts[1]), parts[2:], body)

    def _listed(self, params: dict) -> list:
        return _page(sorted(self.issues.values(), key=lambda i: -i["number"]), params)

    def _opened(self, body: dict) -> dict:
        number = len(self.issues) + 1
        url = f"https://github.com/{REPOSITORY}/issues/{number}"
        self.issues[number] = {"number": number, "state": "open", "state_reason": None, "html_url": url}
        return self._edit(self.issues[number], body)

    def _issue(self, method: str, number: int, rest: list[str], body: dict | None) -> tuple[int, object]:
        if number not in self.issues:
            return 404, "Not Found"
        if rest == ["comments"]:
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


def seed(shared: DataRepo, project: str) -> None:
    """The in-memory issues installed for good, and the backlog's entries written through ``Backlog`` in *project*."""
    backlog_issues.RUNNER = Issues()
    book = Backlog(shared, project)
    for title, text, kind in OWNER:
        entry, _ = book.add(title, text, source="owner")
        if kind != "untriaged":
            book.update(entry.id, {"kind": kind})
    for title, text, kind in DEFECTS:
        entry, _ = book.add(title, text, source="audit")
        if kind != "untriaged":
            book.update(entry.id, {"kind": kind})
    for n, (rule, place, status) in enumerate(REVIEWS, 1):
        entry, _ = book.add(
            suppression_title(rule, place, f"{n:016x}"), "Refused in the pinned inventory.", source="audit"
        )
        if status == "open":
            book.update(entry.id, {"kind": "improvement"})
        elif status != "inbox":
            book.update(entry.id, {"status": status})
