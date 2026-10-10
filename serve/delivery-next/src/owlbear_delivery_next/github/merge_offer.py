# Adapted from serve/delivery/src/owlbear_delivery/merge_offer.py at ab9cfc6cb.
"""One merge decision from fresh provider facts: block reasons, consent state and attempt readback (D3, D4 §3.2)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Literal

from owlbear_delivery_next.git.remote_git import classify_write_readback

if TYPE_CHECKING:
    from owlbear_delivery_next.git.remote_git import WriteReadback
    from owlbear_delivery_next.github.provider import CiState, MergeMethod, PullRequest, Rules

MERGED = "merged"
_REVIEW = re.compile(r"\breview", re.IGNORECASE)


class Block(StrEnum):
    """Known reasons the merge is not sent now."""

    CLOSED = "closed"
    WRONG_BASE = "wrong-base"
    DRAFT = "draft"
    CHECKS_FAILED = "checks-failed"
    CHECKS_RUNNING = "checks-running"
    RULES_UNKNOWN = "rules-unknown"
    NO_PERMISSION = "no-permission"
    METHOD_NOT_ALLOWED = "method-not-allowed"
    CONFLICTS = "conflicts"
    BEHIND = "behind"
    CHECKING = "checking"
    PROTECTION = "protection"
    QUEUE = "queue"
    REVIEW_REQUIRED = "review-required"


@dataclass(frozen=True)
class Decision:
    """Merge directly, or block with a reason and detail."""

    action: Literal["merge", "block"]
    block: Block | None = None
    detail: str = ""


def _blocked(block: Block, detail: str = "") -> Decision:
    return Decision("block", block, detail)


def decide(  # noqa: C901, PLR0911, PLR0912, PLR0913 - one ordered row per block reason
    pr: PullRequest,
    *,
    target: str,
    ci: CiState,
    rules: Rules,
    rules_confirmed: bool,
    method: MergeMethod,
    methods: tuple[MergeMethod, ...],
    can_push: bool,
) -> Decision:
    """Classify one open pull request at its current head; unknown rules make merging human-assisted."""
    state = (pr.merge_state or "").casefold()
    if pr.merged or pr.state != "open":
        return _blocked(Block.CLOSED)
    if pr.base_branch != target:
        return _blocked(Block.WRONG_BASE, f"base {pr.base_branch}")
    if pr.draft:
        return _blocked(Block.DRAFT)
    if ci.failed:
        return _blocked(Block.CHECKS_FAILED, ", ".join(c.name for c in ci.failed))
    if ci.running or ci.missing:
        return _blocked(Block.CHECKS_RUNNING, ", ".join((*ci.running, *ci.missing)))
    if rules.state == "unknown" and not rules_confirmed:
        return _blocked(Block.RULES_UNKNOWN, rules.evidence)
    if not can_push:
        return _blocked(Block.NO_PERMISSION)
    if method not in methods:
        return _blocked(Block.METHOD_NOT_ALLOWED, f"{method} is not allowed")
    if rules.queue_required:
        return _blocked(Block.QUEUE, "merge queue not supported (TD-22)")
    if pr.mergeable is False or state == "dirty":
        return _blocked(Block.CONFLICTS)
    if state == "behind":
        return _blocked(Block.BEHIND)
    if pr.mergeable is None or state in {"", "unknown"}:
        return _blocked(Block.CHECKING)
    if state == "blocked":
        return _blocked(Block.PROTECTION, "GitHub reports the merge blocked by reviews or rules")
    return Decision("merge")


def review_required(decision: str | None, refusal: str | None = None) -> bool:
    """GitHub waits for a human review: ``REVIEW_REQUIRED``, or a merge refusal that names reviews."""
    return decision == "REVIEW_REQUIRED" or bool(refusal and _REVIEW.search(refusal))


def consent(head: str | None, pr_head: str) -> Literal["missing", "valid", "void"]:
    """Consent holds only for the exact head it names; any other PR head voids it (M2)."""
    if head is None:
        return "missing"
    return "valid" if head == pr_head else "void"


def readback(pr: PullRequest, consented_head: str) -> WriteReadback:
    """Classify the PR read after an unknown merge result: merged, still open at the sent head, or moved."""
    observed = MERGED if pr.merged else pr.head_sha if pr.state == "open" else "closed"
    return classify_write_readback(observed, intended=MERGED, expected_old=consented_head)
