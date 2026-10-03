"""Constants and pure helpers shared by the Delivery application."""

from __future__ import annotations

import hashlib
import html
import json
import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from markdown_it import MarkdownIt

from owlbear_delivery.delivery_runtime import (
    DeliveryChangePublicationIdentity,
    DeliveryCheckpointTrigger,
    DeliveryCheckpointTriggerKind,
    DeliveryPendingCheckpoint,
    DeliveryRuntime,
    DeliveryStage,
)
from owlbear_delivery.portfolio_operating import (
    DeliveryHealthDiagnostic,
    PortfolioWorkScope,
)
from owlbear_delivery.publication_provider import (
    PublicationCheck,
    PublicationCheckSnapshot,
    failed_required_publication_checks,
)
from owlbear_delivery.work_items import (
    WorkItemScope,
)

if TYPE_CHECKING:
    from pydantic import BaseModel

    from owlbear_delivery.design_package import (
        VerifiedDesignPackage,
    )
    from owlbear_delivery.draft_pull_request import (
        DraftPullRequestPublicationReceipt,
    )


def _timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        message = "Delivery claim timestamps must include a timezone"
        raise ValueError(message)
    return parsed.astimezone(UTC)


def _health_detail(detail: str | None, fallback: str) -> str:
    compact = " ".join((detail or "").split())
    return (compact or fallback)[:_MAX_HEALTH_DETAIL_LENGTH]


def _health_diagnostic_key(diagnostic: DeliveryHealthDiagnostic) -> tuple[object, ...]:
    return (
        diagnostic.source,
        diagnostic.code,
        diagnostic.detail,
        diagnostic.change_id,
        diagnostic.path,
        diagnostic.retry_safe,
        diagnostic.reason,
        diagnostic.resolution,
        diagnostic.expected_head,
        diagnostic.observed_head,
        diagnostic.observed_local_head,
        diagnostic.head_relation,
    )


def _canonical_model_bytes(model: BaseModel) -> bytes:
    return (json.dumps(model.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n").encode()


_MAX_PULL_REQUEST_TITLE_LENGTH = 256


_MAX_ACCEPTANCE_RECONCILIATION_CHANGES = 8


_ACCEPTANCE_RECONCILIATION_CURSOR_FILE = "cursor.json"


_ATTENTION_RESOLUTION_LOCK_TIMEOUT_SECONDS = 2.0


_ATTENTION_RESOLUTION_LOCK_RETRY_SECONDS = 0.05


_MAX_REQUIRED_CHECK_DIAGNOSTICS = 8


_MAX_CHECK_DIAGNOSTIC_VALUE_LENGTH = 160


_MAX_AUTOMATION_PATHS = 32


_MAX_AUTOMATION_PATH_LENGTH = 240


_MAX_PR_OUTCOMES = 24


_MAX_PR_GOAL_LENGTH = 1_200


_MAX_PR_INTENT_LENGTH = 1_600


_MAX_PR_OUTCOME_TITLE_LENGTH = 180


_MAX_PR_OUTCOME_PROMISE_LENGTH = 480


_CHECKPOINT_RETRY_BASE_SECONDS = 5


_CHECKPOINT_RETRY_MAX_SECONDS = 5 * 60


_CHECKPOINT_RETRY_ERROR_CODE = "ERR_DELIVERY_CHECKPOINT_RECONCILIATION"


_CHECKPOINT_REVIEW_ERROR_CODE = "ERR_DELIVERY_CHECKPOINT_AWAITS_REVIEW"


_CHECKPOINT_MISSING_HEAD_ERROR_CODE = "ERR_DELIVERY_CHECKPOINT_HEAD_MISSING"


_MAX_CHECKPOINT_ERROR_DETAIL_LENGTH = 240


_MAX_CONTINUATION_JOURNAL_BYTES = 65_536


_PUBLICATION_OBSERVATION_CACHE_SECONDS = 15


_PUBLICATION_READBACK_FAILURE_CODES = frozenset(
    {
        "unavailable",
        "authentication_required",
        "rate_limited",
        "timeout",
        "conflict",
        "not_found",
        "invalid_response",
        "response_unknown",
    }
)


_MAX_HEALTH_DETAIL_LENGTH = 240


_MAX_HEALTH_DIAGNOSTICS = 64


_INTENT_SUMMARY_HEADING = "Problem And Product Promise"


_logger = logging.getLogger("owlbear_delivery.portfolio_application")


def _failed_required_publication_checks(snapshot: PublicationCheckSnapshot) -> tuple[PublicationCheck, ...]:
    """Return provider-marked required checks with terminal non-success evidence."""
    return failed_required_publication_checks(snapshot)


def _check_diagnostic_value(value: str | None) -> str:
    """Bound provider-controlled values embedded in durable attention diagnostics."""
    if value is None:
        return "<missing>"
    printable = "".join(character if character.isprintable() else " " for character in value)
    compact = " ".join(printable.split())
    return (compact or "<empty>")[:_MAX_CHECK_DIAGNOSTIC_VALUE_LENGTH]


def _required_check_diagnostics(
    snapshot: PublicationCheckSnapshot,
    observation_id: str,
    failures: tuple[PublicationCheck, ...],
) -> tuple[str, ...]:
    """Build deterministic bounded attention diagnostics for one check observation."""
    ordered = tuple(sorted(failures, key=lambda check: (check.name.casefold(), check.check_id)))
    diagnostics = [
        "required-publication-check-failure",
        f"exact-head:{snapshot.head_sha}",
        f"check-observation:{observation_id}",
        f"failing-required-checks:{len(ordered)}",
    ]
    diagnostics.extend(
        "required-check:"
        f"{_check_diagnostic_value(check.check_id)}:"
        f"name={_check_diagnostic_value(check.name)}:"
        f"status={_check_diagnostic_value(check.status)}:"
        f"conclusion={_check_diagnostic_value(check.conclusion)}"
        for check in ordered[:_MAX_REQUIRED_CHECK_DIAGNOSTICS]
    )
    if len(ordered) > _MAX_REQUIRED_CHECK_DIAGNOSTICS:
        diagnostics.append(f"required-checks-truncated:{len(ordered) - _MAX_REQUIRED_CHECK_DIAGNOSTICS}")
    return tuple(diagnostics)


def _operating_scope(scope: WorkItemScope) -> PortfolioWorkScope:
    if scope == WorkItemScope.CHANGE_PUBLICATION:
        return PortfolioWorkScope.PUBLICATION
    return PortfolioWorkScope.OUTCOME


def _checkpoint_operation_id(kind: str, *parts: str) -> str:
    payload = json.dumps((kind, *parts), separators=(",", ":"))
    return f"checkpoint-{kind}-{hashlib.sha256(payload.encode()).hexdigest()}"


def _checkpoint_retry_ready(pending: DeliveryPendingCheckpoint, now: datetime) -> bool:
    """Return whether a failed checkpoint has waited its bounded retry delay."""
    if pending.last_attempted_at is None or pending.attempt_count == 0:
        return True
    exponent = min(max(pending.attempt_count - 1, 0), 6)
    delay_seconds = min(_CHECKPOINT_RETRY_MAX_SECONDS, _CHECKPOINT_RETRY_BASE_SECONDS * 2**exponent)
    return now >= pending.last_attempted_at + timedelta(seconds=delay_seconds)


def _checkpoint_error_detail(value: str, fallback: str) -> str:
    """Bound provider or Git text retained in checkpoint diagnostics."""
    printable = "".join(character if character.isprintable() else " " for character in value)
    return (" ".join(printable.split()) or fallback)[:_MAX_CHECKPOINT_ERROR_DETAIL_LENGTH]


def _checkpoint_error_code(exc: BaseException) -> str:
    """Return a stable bounded code for one checkpoint reconciliation failure."""
    value = getattr(exc, "code", None)
    return value[:120] if isinstance(value, str) and value else _CHECKPOINT_RETRY_ERROR_CODE


def _checkpoint_awaits_review(runtime: DeliveryRuntime) -> bool:
    """Return whether target synchronization requires fresh finalization before publication."""
    target_sync = runtime.target_sync_receipt()
    return target_sync is not None and target_sync.review_required and runtime.finalization() is None


def _dirty_recovery_operation_id(change_id: str, outcome_id: str, attempt_id: str, claim_id: str) -> str:
    payload = json.dumps(
        ("dirty-worktree-recovery", change_id, outcome_id, attempt_id, claim_id),
        separators=(",", ":"),
    )
    return f"recover-dirty-{hashlib.sha256(payload.encode()).hexdigest()}"


def _checkpoint_summary(  # noqa: PLR0913 - summary binds semantic and checkpoint publication inputs.
    runtime: DeliveryRuntime,
    package: VerifiedDesignPackage,
    pending: DeliveryPendingCheckpoint | None,
    head: str,
    automation_paths: tuple[str, ...],
    *,
    supersedes_publication_id: str | None = None,
) -> str:
    goal, intent = _intent_summary(package.intent_bytes, runtime)
    bindings = {binding.outcome_id: binding for binding in runtime.bindings()}
    completed_outcomes = sum(binding.stage == DeliveryStage.COMPLETED for binding in bindings.values())
    lines = [
        "> **OwlBear-managed pull request:**",
        "> Do not manually change this PR's draft/ready state or push to its branch.",
        "> Use Delivery controls so provider state and Delivery evidence stay synchronized.",
        "",
        "## Goal",
        "",
        f"> {_summary_text(goal, _MAX_PR_GOAL_LENGTH)}",
        "",
        "## Intent",
        "",
        f"> {_summary_text(intent, _MAX_PR_INTENT_LENGTH)}",
        "",
        "## Promised Outcomes",
        "",
    ]
    visible_outcomes = runtime.contract.outcomes[:_MAX_PR_OUTCOMES]
    for outcome in visible_outcomes:
        binding = bindings[outcome.outcome_id]
        complete = binding.stage == DeliveryStage.COMPLETED
        state = "complete" if complete else binding.stage.value
        checkbox = "x" if complete else " "
        outcome_line = (
            f"- [{checkbox}] **{_summary_text(outcome.title, _MAX_PR_OUTCOME_TITLE_LENGTH)}** "
            f"(`{outcome.outcome_id}`; {state})"
        )
        lines.extend(
            (
                outcome_line,
                f"  Promised result: {_summary_text(outcome.promise, _MAX_PR_OUTCOME_PROMISE_LENGTH)}",
            )
        )
    omitted_outcomes = len(runtime.contract.outcomes) - len(visible_outcomes)
    if omitted_outcomes:
        lines.append(f"- {omitted_outcomes} additional Outcome(s) omitted from this summary")
    lines.extend(
        (
            "",
            "## Delivery Status",
            "",
            f"As of reviewed checkpoint `{head}`:",
            "",
            f"- Outcomes complete: {completed_outcomes} of {len(runtime.contract.outcomes)}",
        )
    )
    if pending is not None:
        lines.append(
            f"- Checkpoint includes: {', '.join(_checkpoint_trigger_label(trigger) for trigger in pending.triggers)}"
        )
    finalization = runtime.finalization()
    if finalization is not None and finalization.exact_head == head:
        lines.extend(
            (
                "- Delivery finalization: recorded for this checkpoint",
                "- Independent exact-commit review: passed for this checkpoint",
            )
        )
    if supersedes_publication_id is not None:
        lines.append(f"- Publication supersedes provider publication `{supersedes_publication_id}`")
    lines.extend(_automation_summary(automation_paths))
    if finalization is not None and finalization.exact_head == head:
        lines.extend(
            (
                "",
                "## Review And Merge",
                "",
                (
                    "- To evaluate and address reviewer feedback, run "
                    f"`/address-pr-feedback {runtime.contract.change_id}`."
                ),
                (
                    "- When satisfied with the review, merge this pull request in GitHub; "
                    "Delivery records acceptance afterward."
                ),
            )
        )
    return "\n".join(lines)


def _checkpoint_trigger_label(trigger: DeliveryCheckpointTrigger) -> str:
    if trigger.kind == DeliveryCheckpointTriggerKind.ADMITTED_DESIGN:
        return "admitted Design package"
    if trigger.kind == DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK:
        return "first promoted Task result"
    if trigger.kind == DeliveryCheckpointTriggerKind.VERIFIED_TASK:
        return "verified Task result"
    if trigger.kind == DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME:
        return f"Outcome `{trigger.outcome_id}` verified"
    if trigger.kind == DeliveryCheckpointTriggerKind.FINALIZATION:
        return "finalization recorded"
    return "explicit publication request"


def _intent_summary(intent_bytes: bytes, runtime: DeliveryRuntime) -> tuple[str, str]:
    paragraphs = _intent_summary_paragraphs(intent_bytes)
    if paragraphs:
        goal = paragraphs[0]
        intent = " ".join(paragraphs[1:]).strip() or "Deliver the promised Outcomes below."
        return goal, intent
    fallback = next(
        (
            commitment.statement
            for commitment in runtime.contract.commitments
            if commitment.commitment_class.value in {"dealbreaker", "protected-request"}
        ),
        runtime.contract.title,
    )
    return fallback, "Deliver the promised Outcomes below."


def _intent_summary_paragraphs(intent_bytes: bytes) -> tuple[str, ...]:
    text = intent_bytes.decode("utf-8", errors="replace")
    tokens = MarkdownIt("commonmark").parse(text)
    in_summary_section = False
    in_paragraph = False
    paragraphs: list[str] = []
    for index, token in enumerate(tokens):
        if token.type == "heading_open":
            heading = ""
            if index + 1 < len(tokens) and tokens[index + 1].type == "inline":
                heading = tokens[index + 1].content
            if token.tag == "h2" and heading == _INTENT_SUMMARY_HEADING:
                in_summary_section = True
            elif token.tag in {"h1", "h2"}:
                in_summary_section = False
            in_paragraph = False
        elif token.type == "paragraph_open":
            in_paragraph = in_summary_section
        elif token.type == "paragraph_close":
            in_paragraph = False
        elif token.type == "inline" and in_paragraph and token.content.strip():
            paragraphs.append(token.content)
    return tuple(paragraphs)


def _summary_text(value: str, max_length: int) -> str:
    normalized = " ".join("".join(character if character.isprintable() else " " for character in value).split())
    if not normalized:
        return "Not provided."
    escaped = _escape_summary_text(normalized)
    if len(escaped) <= max_length:
        return escaped
    suffix = "..."
    low = 0
    high = len(normalized)
    while low < high:
        midpoint = (low + high + 1) // 2
        candidate = normalized[:midpoint].rstrip() + suffix
        if len(_escape_summary_text(candidate)) <= max_length:
            low = midpoint
        else:
            high = midpoint - 1
    return _escape_summary_text(normalized[:low].rstrip() + suffix)


def _escape_summary_text(value: str) -> str:
    escaped = html.escape(value, quote=False)
    replacements = {
        ord(character): replacement
        for character, replacement in (
            ("\\", "&#92;"),
            ("`", "&#96;"),
            ("@", "&#64;"),
            ("#", "&#35;"),
            (":", "&#58;"),
            ("/", "&#47;"),
            ("*", "&#42;"),
            ("_", "&#95;"),
            ("[", "&#91;"),
            ("]", "&#93;"),
            ("~", "&#126;"),
            ("|", "&#124;"),
        )
    }
    return escaped.translate(replacements)


def _automation_summary(paths: tuple[str, ...]) -> tuple[str, ...]:
    """Render bounded repository automation paths for a generated PR summary."""
    if not paths:
        return ()
    lines = ["", "### Repository automation changed"]
    visible = paths[:_MAX_AUTOMATION_PATHS]
    lines.extend(f"- {_automation_path_markup(path)}" for path in visible)
    omitted = len(paths) - len(visible)
    if omitted:
        lines.append(f"- {omitted} additional automation path(s) omitted")
    return tuple(lines)


def _automation_path_markup(path: str) -> str:
    """Escape and bound one repository-controlled path for Markdown HTML."""
    printable = []
    for character in path:
        if character == "\n":
            printable.append(r"\n")
        elif character == "\r":
            printable.append(r"\r")
        elif character == "\t":
            printable.append(r"\t")
        elif character.isprintable():
            printable.append(character)
        else:
            printable.append(f"\\u{ord(character):04x}")
    bounded = "".join(printable)
    if len(bounded) > _MAX_AUTOMATION_PATH_LENGTH:
        bounded = f"{bounded[: _MAX_AUTOMATION_PATH_LENGTH - 3]}..."
    escaped = html.escape(bounded, quote=True).replace("`", "&#96;")
    return f"<code>{escaped}</code>"


def _checkpoint_pull_request_title(runtime: DeliveryRuntime) -> str:
    printable = "".join(character if character.isprintable() else " " for character in runtime.contract.title)
    title = " ".join(printable.split()) or f"Delivery Change {runtime.contract.change_id}"
    if len(title) <= _MAX_PULL_REQUEST_TITLE_LENGTH:
        return title
    return f"{title[: _MAX_PULL_REQUEST_TITLE_LENGTH - 3]}..."


def _publication_identity(
    publication: DraftPullRequestPublicationReceipt,
) -> DeliveryChangePublicationIdentity:
    return DeliveryChangePublicationIdentity(
        change_id=publication.change_id,
        repository=publication.repository,
        number=publication.number,
        node_id=publication.node_id,
        head_sha=publication.head_sha,
    )
