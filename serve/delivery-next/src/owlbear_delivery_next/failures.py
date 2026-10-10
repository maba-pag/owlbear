"""Failure identity: cause keys, error classes and the normalised signature budgets count (D3 §3.6)."""

from __future__ import annotations

import hashlib
import re
from typing import TYPE_CHECKING

from owlbear_delivery_next.models import ErrorKind

if TYPE_CHECKING:
    from collections.abc import Iterable

    from owlbear_delivery_next.models import StepKind

ENVIRONMENT = frozenset({ErrorKind.NETWORK, ErrorKind.CAPACITY})  # waits; never budget
DEFECT = frozenset({ErrorKind.TOOLING, ErrorKind.STATE, ErrorKind.RESULT})  # Delivery's adapter, store, tools
# work failures a smaller task can get past; the one alternative before asking is a re-plan that splits the work
SPLITTABLE = frozenset(
    {ErrorKind.CHECKS, ErrorKind.REVIEW, ErrorKind.SCOPE, ErrorKind.COMMIT_POLICY, ErrorKind.CONFLICT}
)
QUOTA = "quota"  # the cause subject of an exhausted Copilot quota: waited out, never asked about
_QUOTA = re.compile(r"quota|premium requests?|credits", re.IGNORECASE)
_CAPACITY = re.compile(r"\b429\b|rate.?limit|capacity|overloaded|quota|credits", re.IGNORECASE)
_NETWORK = re.compile(
    r"\b(?:status|http|code|error)\W{0,3}5\d\d\b|\b5\d\d (?:internal|bad gateway|service unavailable|gateway)"
    r"|timed? ?out|timeout|connection|unreachable|temporar|runtime start|network|could not resolve",
    re.IGNORECASE,
)
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


def transient(text: str) -> ErrorKind | None:
    """Classify a runtime or provider failure text as capacity, network or neither."""
    if _CAPACITY.search(text):
        return ErrorKind.CAPACITY
    return ErrorKind.NETWORK if _NETWORK.search(text) else None


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
