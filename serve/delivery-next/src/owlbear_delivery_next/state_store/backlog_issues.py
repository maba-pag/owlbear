"""The backlog's GitHub issues (TD-103): one issue per entry in the shared repository, read and written through ``gh``.

The issue's title is the entry's title; its body shows the entry's fields as Markdown, with a Repeats line, and ends
in a hidden JSON block that round-trips them. Labels carry the scope, the project and the class; the open or closed
state carries done and dropped. Every label OwlBear creates is tawny brown.
"""

from __future__ import annotations

import json
import re
import time
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.github import gh_client
from owlbear_delivery_next.github.gh_client import GhClient, Json, Missing, repo
from owlbear_delivery_next.github.provider import FailureCode, ProviderError
from owlbear_delivery_next.local_system import data_repo

if TYPE_CHECKING:
    from datetime import datetime

    from owlbear_delivery_next.local_system.data_repo import DataRepo

RUNNER = gh_client.run  # tests replace it: they never reach GitHub
MARK = "owlbear-backlog"
COLOUR = "A67C52"
PAGE = 100
LONGEST = 65000  # GitHub refuses an issue body over 65536 characters
SCOPES = ("project", "cross-project", "global", "unassigned")
KINDS = ("untriaged", "defect", "improvement", "idea", "question")
OURS = ("scope:", "project:", "class:")
VISIBILITY = "repo_visibility"  # the operation whose failure refuses a write: the repository is not known private
PRIVATE_SECONDS = 600.0  # how long GitHub's word that the repository is private is reused
_BLOCK = re.compile(rf"(?:\A|\n)<!-- {MARK} (\{{[^\n]*\}}) -->\s*\Z")  # the body's last line, never a pasted one
_private: dict[str, float] = {}  # host/owner/name -> when GitHub last said it is private


class Issues(GhClient):
    """The fixed issue and label operations on one ``owner/name`` repository."""

    def __init__(self, shared: DataRepo) -> None:
        """The GitHub repository the shared checkout's ``origin`` names; a ValueError when it names none."""
        parts = data_repo.identity(shared.root).split("/")
        if len(parts) != 3 or "." not in parts[0]:  # noqa: PLR2004 - host/owner/name
            msg = f"the shared repository {shared.root} has no GitHub origin remote"
            raise ValueError(msg)
        super().__init__(shared.root, host=parts[0], runner=RUNNER)
        self.repository = f"{parts[1]}/{parts[2]}"
        self._labels: set[str] | None = None

    def issues(self) -> list[Json]:
        """Every issue, open or closed, that holds a backlog block; pull requests aside."""
        found, page = [], 1
        while True:
            got = self._api(
                "list_issues", "GET", f"{repo(self.repository)}/issues?state=all&per_page={PAGE}&page={page}"
            )
            found += [i for i in got if "pull_request" not in i and f"<!-- {MARK} " in (i.get("body") or "")]
            if len(got) < PAGE:
                return found
            page += 1

    def issue(self, number: int) -> Json | None:
        """One issue as GitHub holds it now, however its listing lags; None when there is none."""
        got = self._api("get_issue", "GET", f"{repo(self.repository)}/issues/{number}", absent={404, 410})
        return None if isinstance(got, Missing) or "pull_request" in got else got

    def private(self) -> None:
        """Refuse a write unless GitHub says the repository is private (TD-103: no public reports)."""
        where = f"{self.host}/{self.repository}"
        if time.monotonic() - _private.get(where, -PRIVATE_SECONDS) < PRIVATE_SECONDS:
            return
        try:
            got = self._api(VISIBILITY, "GET", repo(self.repository))
        except ProviderError as exc:
            why = f"its visibility is unknown ({exc}); the backlog is written only to a private repository"
            raise ProviderError(exc.code, VISIBILITY, why, retry_safe=True) from exc
        facts = got if isinstance(got, dict) else {}
        if facts.get("private") is not True or facts.get("visibility", "private") != "private":
            seen = facts.get("visibility") or "of unknown visibility"
            why = f"it is {seen}, not private; the backlog is written only to a private repository"
            raise ProviderError(FailureCode.CONFLICT, VISIBILITY, why, retry_safe=True)
        _private[where] = time.monotonic()

    def create(self, title: str, body: str, labels: list[str]) -> Json:
        """Open one issue."""
        self.private()
        payload = {"title": title, "body": body, "labels": labels}
        return self._api("create_issue", "POST", f"{repo(self.repository)}/issues", body=payload, write=True)

    def edit(self, number: int, fields: dict[str, Any]) -> Json:
        """Set an issue's title, body, labels or state."""
        self.private()
        endpoint = f"{repo(self.repository)}/issues/{number}"
        return self._api("edit_issue", "PATCH", endpoint, body=fields, write=True)

    def comment(self, number: int, body: str) -> None:
        """Add one comment to an issue."""
        self.private()
        endpoint = f"{repo(self.repository)}/issues/{number}/comments"
        self._api("comment_issue", "POST", endpoint, body={"body": body}, write=True)

    def ensure_labels(self, names: list[str]) -> None:
        """Create the labels the repository lacks, in OwlBear's colour; one already there stays as it is."""
        if self._labels is None:
            self._labels, page = set(), 1
            while True:
                got = self._api("list_labels", "GET", f"{repo(self.repository)}/labels?per_page={PAGE}&page={page}")
                self._labels |= {label["name"] for label in got}
                if len(got) < PAGE:
                    break
                page += 1
        for name in [n for n in names if n not in self._labels]:
            self.private()
            payload = {"name": name, "color": COLOUR, "description": "OwlBear backlog"}
            endpoint = f"{repo(self.repository)}/labels"
            self._api("create_label", "POST", endpoint, body=payload, write=True, absent={422})  # 422: made meanwhile
            self._labels.add(name)


def labels(fields: dict[str, Any]) -> list[str]:
    """The entry's labels: its scope, its class, and its project when the scope is a project."""
    named = [f"scope:{fields['scope']}", f"class:{fields['kind']}"]
    return named + ([f"project:{fields['project']}"] if fields["scope"] == "project" and fields["project"] else [])


def kept_labels(issue: Json) -> list[str]:
    """The issue's labels OwlBear does not own, kept on every edit."""
    return [n for n in (label["name"] for label in issue.get("labels", [])) if not n.startswith(OURS)]


def state(status: str) -> dict[str, str]:
    """The issue state for an entry's status: done and dropped close it."""
    if status in {"done", "dropped"}:
        return {"state": "closed", "state_reason": "completed" if status == "done" else "not_planned"}
    return {"state": "open"}


def _when(at: datetime) -> str:
    return f"{at:%Y-%m-%d %H:%M} UTC"


def _line(text: str) -> str:
    return " ".join(text.split())


def _shown(text: str) -> str:
    """The owner's text as Markdown shows it: a pasted comment opener hides nothing after it."""
    return text.replace("<!--", "&lt;!--")


def body(fields: dict[str, Any]) -> str:
    """The issue body: the entry's fields as Markdown, the Repeats line, and the block that round-trips them."""
    f = fields
    where = f" ({f['project']})" if f["project"] else ""
    head = f"**Class:** {f['kind']} · **Scope:** {f['scope']}{where} · **Source:** {f['source']}"
    head += f" · **State:** {f['status']}"
    parts = [_shown(f["text"]), head] if f["text"] else [head]
    if f["notes"]:
        parts.append(f"### Owner's notes\n\n{_shown(f['notes'])}")
    if f["evidence"]:
        parts.append("### Evidence\n\n" + "\n".join(f"- {_shown(_line(r))}" for r in f["evidence"]))
    if f["change"] or f["launch"]:
        launch = f" (launch {f['launch']})" if f["launch"] else ""
        parts.append(f"### Change\n\n{f['change'] or 'not named yet'}{launch}")
    if f["links"]:
        parts.append("### Connected entries\n\n" + "\n".join(f"- #{i}" for i in f["links"]))
    times = "time" if f["count"] == 1 else "times"
    seen = f"**Repeats:** seen {f['count']} {times} · first {_when(f['first_seen'])} · last {_when(f['last_seen'])}"
    block = json.dumps({k: v for k, v in _jsonable(f).items() if k not in {"id", "title"}}, ensure_ascii=False)
    hidden = block.replace("<", "\\u003c").replace(">", "\\u003e")  # nothing in it can close the comment
    return "\n\n".join([*parts, seen, f"<!-- {MARK} {hidden} -->"]) + "\n"


def _jsonable(fields: dict[str, Any]) -> dict[str, Any]:
    return {k: v.isoformat() if hasattr(v, "isoformat") else v for k, v in fields.items()}


def fields(issue: Json) -> dict[str, Any] | None:
    """An issue's entry fields: its block, with the title, labels and state GitHub holds; None without a block."""
    found = _BLOCK.search(issue.get("body") or "")
    try:
        data = json.loads(found.group(1)) if found else None
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    names = [label["name"] for label in issue.get("labels", [])]
    for prefix, key, allowed in (("scope:", "scope", SCOPES), ("class:", "kind", KINDS)):
        if len(said := [n.removeprefix(prefix) for n in names if n.startswith(prefix)]) == 1 and said[0] in allowed:
            data[key] = said[0]
    if data.get("scope") == "project" and len(said := [n for n in names if n.startswith("project:")]) == 1:
        data["project"] = said[0].removeprefix("project:")
    if issue.get("state") == "closed":  # GitHub's closing reason, as it is now: a reopened and reclosed issue too
        data["status"] = "dropped" if issue.get("state_reason") in {"not_planned", "duplicate"} else "done"
    elif data.get("status") in {"done", "dropped"}:
        data["status"] = "inbox" if data.get("kind") == "untriaged" else "open"
    return data | {"id": str(issue["number"]), "title": issue["title"]}
