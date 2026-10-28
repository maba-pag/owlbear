"""A Retro run's paid calls (#715, Improvement design §5): one batch each, kept before anything is derived from it.

The job (``machine_host.retro_job``) gives a run its paid call (``Ask``): admission, the lease and the ``inflight``
line come before the session, which charges the run's meter. Each call is a batch under a deterministic key; its raw
answer is kept, then ``settled`` is written, so a retry or a re-run of the revision replays a kept answer instead of
asking again. An answer that is empty, cut off at the limit or not valid against its batch's schema is kept only as an
attempt, never reused or derived from, and ends the run ``stopped``, its work still due.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.improvement import retro_store as store
from owlbear_delivery_next.improvement.retro_segments import cut

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from owlbear_delivery_next.improvement.retro_segments import Prepared


@dataclass(frozen=True)
class Paid:
    """One paid call's answer and spend, as the job's ``Ask`` returns it."""

    answer: str
    call: float  # credits this call spent
    total: float  # the run's spend so far, this call included
    known: bool = True  # whether every spend so far is known
    cut: bool = False  # the run's meter closed during the call: the answer may be cut off


type Ask = Callable[[str, str, str], Paid]  # (batch key, message, agent) -> the paid call's answer


class StoppedError(Exception):
    """The run ends now with *result* (``stopped: ...``); what it did is kept and its unit's work stays due."""

    def __init__(self, result: str) -> None:
        super().__init__(result)
        self.result = result


class WaitingError(Exception):
    """No call may start now (pause, fence, stop): the run waits at its cursor with *why*."""

    def __init__(self, why: str) -> None:
        super().__init__(why)
        self.why = why


@dataclass
class Work:
    """One run's unit revision: what it reads, what it grades and how it asks."""

    run: str
    uid: str
    rev: Mapping[str, Any]
    unit: Mapping[str, Any]
    records: list[dict[str, Any]]
    prepared: Prepared
    ask: Ask
    provenance: str = "real"
    grade_only: bool = False
    found: dict[str, int] = field(default_factory=lambda: {"findings": 0, "grades": 0})


def answer(text: str) -> dict[str, Any] | None:
    """The JSON object *text* holds, if any."""
    hit = re.search(r"\{.*\}", text or "", re.DOTALL)
    try:
        said = json.loads(hit.group(0)) if hit else None
    except ValueError:
        return None
    return said if isinstance(said, dict) else None


def strings(value: object) -> bool:
    """Whether *value* is a list of strings, as an answer's lists must be."""
    return isinstance(value, list) and all(isinstance(x, str) for x in value)


def key(w: Work, phase: str, message: str) -> str:
    """The batch key of *message* in *phase* of *w*'s revision."""
    return f"b-{store.digest([w.uid, w.rev.get('rev', ''), phase, store.digest(message, 32)])}"


def paid(
    w: Work, phase: str, message: str, valid: Callable[[dict[str, Any]], bool], agent: str = "retro"
) -> dict[str, Any]:
    """The answer of batch (*phase*, *message*): the kept one, else asked, kept, then settled.

    Raises:
        StoppedError: The answer is unusable; it is kept as an attempt and nothing is derived from it. A saved
            answer no longer valid stops the run too: nothing is derived from it, and it is never asked again.
    """
    batch = key(w, phase, message)
    if (kept := store.saved(batch)) is not None:
        if isinstance(kept["answer"], dict) and valid(kept["answer"]):
            return kept["answer"]
        msg = "stopped: a saved answer is not valid against its schema"
        raise StoppedError(msg)
    got = w.ask(batch, message, agent)
    said = answer(got.answer)
    why = (
        "cut off at the credit limit"
        if got.cut
        else "empty"
        if not got.answer.strip()
        else ""
        if said is not None and valid(said)
        else "not valid against its schema"
    )
    kept_as = said if not why else cut(got.answer, 2_000)
    store.keep(batch, w.run, kept_as, got.call, attempt=why, total=got.total, phase=phase, unit=w.uid)
    store.run_event(w.run, "settled", batch=batch, phase=phase, spent=got.total, known=got.known)
    if why:
        msg = f"stopped: an answer was {why}"
        raise StoppedError(msg)
    return said
