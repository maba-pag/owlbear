from __future__ import annotations

from datetime import UTC, datetime

import pytest

from owlbear_decisions.models import Decision, Origin, Scope, State, new_id

AT = datetime(2026, 10, 20, tzinfo=UTC)


def build(**changes) -> Decision:
    fields = {
        "id": new_id(AT, seed="one"),
        "aliases": ("TD-417",),
        "title": "Lint once",
        "topic": "C-28 Code and tool rules",
        "statement": "The builder's code is linted once, at submission.",
        "rationale": "Why: **speed**.\n\nSecond paragraph.",
        "scope": Scope.PROJECT,
        "project": "owlbear",
        "origin": Origin.DECIDED,
        "actor": "owner",
        "source": "chat 2026-10-20",
        "state": State.IN_FORCE,
        "read_back": "2026-10-20",
        "created_at": AT,
    }
    return Decision(**{**fields, **changes})


@pytest.fixture
def make():
    """A valid in-force project decision; keyword arguments override fields."""
    return build
