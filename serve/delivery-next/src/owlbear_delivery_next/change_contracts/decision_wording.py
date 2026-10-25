"""An archived rule's exact binding, framed independently of free-text reasons and later action notes."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from owlbear_decisions import DecisionError
from owlbear_decisions.models import STATEMENT_LIMIT

if TYPE_CHECKING:
    from owlbear_decisions import Decision

WHOLE = "Whole wording: "
FRAME = "OwlBear archived wording v1: "
CHANGE = "Change "  # the source of a rule archived from a Change; the producer sets it, never the reason text
PROMOTED = "the Decisions page: promoted"  # the source of a rule widened from another; set by promote, never a reason


class WordingError(DecisionError, ValueError):
    """The full binding cannot be established without guessing where the explanation begins."""


def _error(decision: Decision, detail: str) -> WordingError:
    return WordingError(f"{decision.id}: {detail}")


def _managed(decision: Decision) -> bool:
    """Only the producer's source makes a rationale binding: a reason typed by anyone else is plain text."""
    return decision.source.startswith(CHANGE) or decision.source == PROMOTED


def short(text: str) -> str:
    """The immutable canonical statement retained when an approved answer is longer than the core limit."""
    return text[: STATEMENT_LIMIT - 1].rstrip() + "\u2026" if len(text) > STATEMENT_LIMIT else text


def rationale(text: str, note: str, *, force: bool = False) -> str:
    """Frame both cut answers and literal terminal ellipses so neither can be mistaken for legacy metadata."""
    if not force and len(text) <= STATEMENT_LIMIT and not text.endswith("\u2026"):
        return note
    payload = json.dumps({"statement": short(text), "whole": text}, ensure_ascii=False)
    return f"{FRAME}{payload}\n\n{note}"


def whole(decision: Decision) -> str:
    """Return canonical wording or a provable expansion; never infer a delimiter inside binding paragraphs."""
    if not _managed(decision):
        return decision.statement
    first = decision.rationale.split("\n", 1)[0]
    if first.startswith(FRAME):
        try:
            payload = json.loads(first[len(FRAME) :])
        except ValueError as exc:
            raise _error(decision, "invalid archived wording frame") from exc
        if not isinstance(payload, dict) or set(payload) != {"statement", "whole"}:
            raise _error(decision, "invalid archived wording payload")
        text = payload["whole"]
        if not isinstance(text, str) or payload["statement"] != decision.statement or short(text) != decision.statement:
            raise _error(decision, "archived wording does not match its immutable statement")
        return text
    if first.startswith("OwlBear archived wording "):
        raise _error(decision, "unsupported archived wording frame")
    if not decision.statement.endswith("\u2026") or WHOLE not in decision.rationale:
        return decision.statement
    raise _error(decision, "ambiguous legacy archived wording; replace the rule with confirmed full intent")


def explanation(decision: Decision) -> str:
    """A new rule may inherit the note, never the retired rule's binding; unusable binding is dropped unvalidated."""
    if not _managed(decision):
        return decision.rationale
    first = decision.rationale.split("\n", 1)[0]
    if first.startswith(FRAME):
        return decision.rationale.partition("\n\n")[2]
    if first.startswith("OwlBear archived wording "):
        return ""
    if decision.statement.endswith("\u2026"):
        return decision.rationale.partition(WHOLE)[0].rstrip()
    return decision.rationale


def framed(decision: Decision, *, promoting: bool = False) -> str:
    """Preserve framed authority before appending notes; a promotion freezes a plain answer's binding first."""
    if promoting and not _managed(decision):
        return rationale(decision.statement, decision.rationale, force=True)
    text = whole(decision)
    return rationale(text, explanation(decision)) if text != decision.statement else decision.rationale


def problem(decision: Decision) -> str:
    """The wording fault a governing-authority preflight must expose before paying for a picker."""
    try:
        whole(decision)
    except WordingError as exc:
        return str(exc)
    return ""
