"""Issues in OwlBear's own public repository (#716): what an accepted proposal about OwlBear itself becomes.

An issue is found again by a marker its body carries, so a lost response never makes a second one. No label is set:
none is created in the public repository.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from owlbear_delivery_next.github.gh_client import GhClient, invalid, repo

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.github.gh_client import Json, Runner

PAGE, PAGES = 100, 10  # issues a page reads; pages a search reads, newest first


@dataclass(frozen=True)
class Issue:
    """One issue: its number, link and state (``open`` or ``closed``)."""

    number: int
    url: str
    state: str


def _issue(found: Json, operation: str) -> Issue:
    try:
        return Issue(int(found["number"]), str(found["html_url"]), str(found["state"]))
    except (KeyError, TypeError, ValueError) as exc:
        invalid(operation, "an issue without its number, link or state", exc)


class OwlbearIssues(GhClient):
    """The issues of one public repository given by name (``owner/name``)."""

    def __init__(self, repository: str, cwd: Path, *, runner: Runner | None = None) -> None:
        super().__init__(cwd, **({"runner": runner} if runner else {}))
        self.repository = repository

    def find(self, marker: str) -> Issue | None:
        """The newest issue whose body carries *marker*, pull requests left out; None when none of the newest has it."""
        query = f"state=all&sort=created&direction=desc&per_page={PAGE}"
        for page in range(1, PAGES + 1):
            found = self._api("find_issue", "GET", f"{repo(self.repository)}/issues?{query}&page={page}")
            if not isinstance(found, list):
                invalid("find_issue", "the issues are not a list")
            for item in found:
                if "pull_request" not in item and marker in str(item.get("body") or ""):
                    return _issue(item, "find_issue")
            if len(found) < PAGE:
                return None
        return None

    def create(self, title: str, body: str) -> Issue:
        """Open one issue; an unknown outcome is found again by its marker before it is made again."""
        payload = {"title": title, "body": body}
        made = self._api("create_issue", "POST", f"{repo(self.repository)}/issues", body=payload, write=True)
        return _issue(made, "create_issue")

    def close(self, number: int) -> Issue:
        """Close one issue as not planned."""
        payload = {"state": "closed", "state_reason": "not_planned"}
        endpoint = f"{repo(self.repository)}/issues/{number}"
        return _issue(self._api("close_issue", "PATCH", endpoint, body=payload, write=True), "close_issue")
