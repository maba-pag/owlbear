"""Issues in OwlBear's own public repository (#716): what an accepted proposal about OwlBear itself becomes.

An issue is found again by its body marker. Machine-local filing records prevent another POST when a recent issue
is not yet listed, including after a lost response. Only audit publication explicitly retries an old pending filing
after a complete listing proves absence; ordinary callers' pending and known records never expire.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal, NoReturn

from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.github.account import AccountMissing, Origin, Writer
from owlbear_delivery_next.github.gh_client import GhClient, invalid, repo
from owlbear_delivery_next.github.provider import FailureCode, ProviderError

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from owlbear_delivery_next.github.gh_client import Json, Runner

PAGE = 100
AUDIT_RECENT_SECONDS = 120.0


def _unavailable(operation: str, path: Path, exc: OSError) -> NoReturn:
    raise ProviderError(FailureCode.UNAVAILABLE, operation, f"{path}: {failure(exc)}", retry_safe=True) from exc


def _present(path: Path, operation: str) -> bool:
    try:
        path.stat()
    except FileNotFoundError:
        return False
    except OSError as exc:
        _unavailable(operation, path, exc)
    return True


def _claim(path: Path, operation: str) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            path.touch(mode=0o600, exist_ok=False)
        except FileExistsError:
            return False
    except OSError as exc:
        _unavailable(operation, path, exc)
    return True


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
        """*cwd* holds machine-local filing records; writes use TD-402's account for *repository*."""
        writer = Writer.rule(Origin("github.com", *repository.split("/", 1)))
        super().__init__(cwd, writer=writer, **({"runner": runner} if runner else {}))
        self.repository = repository

    def find(self, marker: str) -> Issue | None:
        """Find the newest marked issue, recording it locally; None only when absence permits a first filing.

        Raises:
            ProviderError: A page or filing record cannot be read, or an earlier filing is not yet listed.
        """
        issue = self.listed(marker)
        if issue is None and _present(self._intent(marker, "pending"), "find_issue"):
            self._unconfirmed("find_issue", marker)
        return issue

    def listed(self, marker: str) -> Issue | None:
        """Read all issue pages until found or absent, ignoring pending intents but never a known issue's absence."""
        query = f"state=all&sort=created&direction=desc&per_page={PAGE}"
        page = 1
        while True:
            found = self._api("find_issue", "GET", f"{repo(self.repository)}/issues?{query}&page={page}")
            if not isinstance(found, list):
                invalid("find_issue", "the issues are not a list")
            for item in found:
                body = str(item.get("body") or "")
                matches = (
                    re.search(re.escape(marker) + r"(?![\w:-])", body)
                    if marker.startswith("audit:")
                    else marker in body
                )
                if "pull_request" not in item and matches:
                    issue = _issue(item, "find_issue")
                    _claim(self._intent(marker, "known"), "find_issue")
                    return issue
            if len(found) < PAGE:
                if _present(self._intent(marker, "known"), "find_issue"):
                    self._unconfirmed("find_issue", marker)
                return None
            page += 1

    def _intent(self, marker: str, kind: Literal["pending", "known"]) -> Path:
        key = hashlib.sha256(f"{self.repository.casefold()}\n{marker}".encode()).hexdigest()
        return self.cwd / "issue-filings" / f"{key}.{kind}"

    def _unconfirmed(self, operation: str, marker: str) -> NoReturn:
        detail = f"an earlier filing of {marker} in {self.repository} may exist; read its marker again before creating"
        raise ProviderError(FailureCode.RESPONSE_UNKNOWN, operation, detail, retry_safe=False)

    def create(self, title: str, body: str, *, marker: str, labels: Iterable[str] = ()) -> Issue:
        """Record a pending filing before POST; an unknown outcome can only be recovered by finding its marker."""
        pending = self._intent(marker, "pending")
        if not _claim(pending, "create_issue"):
            self._unconfirmed("create_issue", marker)
        payload = {"title": title, "body": body}
        if names := list(dict.fromkeys(labels)):
            payload["labels"] = names
        try:
            if _present(self._intent(marker, "known"), "create_issue"):
                self._unconfirmed("create_issue", marker)
            made = self._api("create_issue", "POST", f"{repo(self.repository)}/issues", body=payload, write=True)
        except (ProviderError, AccountMissing) as exc:
            if isinstance(exc, AccountMissing) or exc.code != FailureCode.RESPONSE_UNKNOWN:
                try:
                    pending.unlink()
                except OSError as removal:
                    exc.add_note(f"filing intent {pending} could not be cleared: {failure(removal)}")
            raise
        # A successful POST with an unreadable receipt is still a write.
        issue = _issue(made, "create_issue")
        _claim(self._intent(marker, "known"), "create_issue")
        return issue

    def retry_audit(
        self,
        title: str,
        body: str,
        *,
        marker: str,
        pending_since: datetime,
        labels: Iterable[str] = (),
    ) -> Issue:
        """Recover an audit filing; only an old pending intent absent from a complete listing permits another POST.

        Persist the new attempt's pending time in the audit record before calling, passing the previous time here.
        A known issue is never recreated, even when GitHub stops listing it.
        """
        if not marker.startswith("audit:"):
            msg = "only an audit identity may retry a pending filing"
            raise ValueError(msg)
        if issue := self.listed(marker):
            return issue
        if (datetime.now(UTC) - pending_since).total_seconds() < AUDIT_RECENT_SECONDS:
            self._unconfirmed("retry_audit", marker)
        pending = self._intent(marker, "pending")
        try:
            pending.unlink(missing_ok=True)
        except OSError as exc:
            _unavailable("retry_audit", pending, exc)
        return self.create(title, body, marker=marker, labels=labels)

    def close(self, number: int) -> Issue:
        """Close one issue as not planned."""
        payload = {"state": "closed", "state_reason": "not_planned"}
        endpoint = f"{repo(self.repository)}/issues/{number}"
        return _issue(self._api("close_issue", "PATCH", endpoint, body=payload, write=True), "close_issue")
