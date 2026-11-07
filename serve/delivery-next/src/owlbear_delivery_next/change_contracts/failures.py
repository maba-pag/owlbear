"""Failure identity: cause keys, error classes and the normalised signature budgets count (D3 §3.6)."""

from __future__ import annotations

import hashlib
import re
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.models import ErrorKind

if TYPE_CHECKING:
    from collections.abc import Iterable

    from owlbear_delivery_next.change_contracts.models import StepKind

ENVIRONMENT = frozenset({ErrorKind.NETWORK, ErrorKind.CAPACITY})  # waits; never budget
DEFECT = frozenset({ErrorKind.TOOLING, ErrorKind.STATE, ErrorKind.RESULT})  # Delivery's adapter, store, tools
# work failures a smaller task can get past; the one alternative before asking is a re-plan that splits the work
SPLITTABLE = frozenset(
    {ErrorKind.CHECKS, ErrorKind.REVIEW, ErrorKind.SCOPE, ErrorKind.COMMIT_POLICY, ErrorKind.CONFLICT}
)
QUOTA = "quota"  # the cause subject of an exhausted Copilot quota: waited out, never asked about
UNREAD = "usage-unread"  # the cause subject of a step whose model could not be proven from its usage (TD-54, TD-94)
WRONG_MODEL = "wrong-model"  # the cause subject of a step a turn or call on another model voided (TD-94)
VISUAL_MODEL = "visual-model"  # the cause subject of a visual round whose judge's model is unknown (TD-94)
READ_ONLY = "read-only-write"  # the cause subject of a read-only session that changed the shared repository's refs
READ_ONLY_UNREAD = "read-only-unread"  # shared Git settings could not be inspected after the read-only session
RO_WORKTREE = "read-only-worktree"  # the cause subject of a read-only worktree Delivery could not prepare
_QUOTA = re.compile(r"quota|premium requests?|credits", re.IGNORECASE)
_CAPACITY = re.compile(r"\b429\b|rate.?limit|capacity|overloaded|quota|credits", re.IGNORECASE)
_LIMITED = re.compile(r"\b429\b|rate.?limit|too many requests|overloaded", re.IGNORECASE)  # in a check's output
_PROGRESS = re.compile(r"::|^[\s=]*\d+ (?:passed|failed|errors?|skipped|deselected|xfailed|xpassed|warnings?)\b")
_NETWORK = re.compile(  # any runtime or provider failure text
    r"\b(?:status|http|code|error)\W{0,3}5\d\d\b|\b5\d\d (?:internal|bad gateway|service unavailable|gateway)"
    r"|timed? ?out|timeout|connection|unreachable|temporar|runtime start|network|could not resolve",
    re.IGNORECASE,
)
_REMOTE = re.compile(  # a check's output that names the network itself: temporary even there (#1065)
    r"\b(?:status|http|code|error)\W{0,3}5\d\d\b|\b5\d\d (?:internal|bad gateway|service unavailable|gateway)"
    r"|connection ?(?:refused|reset|closed|aborted|error|timed? ?out)|(?:host|network) (?:is )?unreachable"
    r"|network error|could not resolve|name resolution|gaierror|nodename nor servname"
    r"|\b(?:ETIMEDOUT|ECONNRESET|ECONNREFUSED|EAI_AGAIN|ENOTFOUND)\b|\b(?:connect|read) timed? ?out",
    re.IGNORECASE,
)
CHECK = "check"  # the subject prefix of a step's own check that cannot finish: setup, never temporary (#1065)
SETUP = "setup"  # the subject prefix of a worker's premise about something outside the brief and plan (#1065)
_NOISE = (
    (re.compile(r"(/private)?/(tmp|var/folders)/\S*"), "<tmp>"),
    (re.compile(r"\b[0-9a-f]{7,40}\b"), "<sha>"),
    (re.compile(r"\d+"), "<n>"),
    (re.compile(r"\s+"), " "),
)


def signature(kind: str, step: str, message: str) -> str:
    """Stable identity of one failure: numbers, commit ids and temporary paths do not distinguish it."""
    text = message.lower()
    for pattern, mark in _NOISE:
        text = pattern.sub(mark, text)
    return hashlib.sha256(f"{kind}:{step}:{text.strip()}".encode()).hexdigest()[:16]


def transient(text: str, *, local: bool = False) -> ErrorKind | None:
    """Classify a runtime or provider failure text as capacity, network or neither.

    *local* is a step's own check: its timeout or interruption is the check not finishing, so only a diagnostic of the
    network or a rate limit counts, never a word such as a test's name.
    """
    if local:  # a check's own progress (test ids, counts) is no diagnostic
        text = "\n".join(line for line in text.splitlines() if not _PROGRESS.search(line))
    if (_LIMITED if local else _CAPACITY).search(text):
        return ErrorKind.CAPACITY
    return ErrorKind.NETWORK if (_REMOTE if local else _NETWORK).search(text) else None


def quota(text: str) -> bool:
    """Whether a capacity failure text is the Copilot quota, not a provider rate limit."""
    return bool(_QUOTA.search(text))


def kind_of(cause: str | None) -> str:
    """The error kind a cause key starts with."""
    return (cause or "").split(":", 1)[0]


def cause_key(kind: ErrorKind, step: StepKind, subject: str | Iterable[str] = "") -> str:
    """Return ``kind:step:subject``; the task id is never part of it, so a cause survives re-planning."""
    text = subject if isinstance(subject, str) else ",".join(sorted(subject))
    return f"{kind}:{step}:{text}"
