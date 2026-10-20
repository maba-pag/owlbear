from __future__ import annotations

from datetime import UTC, datetime

import pytest

from owlbear_decisions.models import Applicability, Decision, Origin, OwnerWords, Scope, State, new_id

AT = datetime(2026, 10, 20, tzinfo=UTC)


def build(**changes) -> Decision:
    fields = {
        "id": new_id(AT, seed="one"),
        "aliases": ("TD-417",),
        "title": "Lint once",
        "topic": "C-28 Code and tool rules",
        "statement": "The builder's code is linted once, at submission.",
        "rationale": "Why: **speed**.\n\nSecond paragraph.",
        "applies_to": Applicability(paths=("serve/**/*.py",), roles=("builder",)),
        "scope": Scope.PROJECT,
        "project": "owlbear",
        "origin": Origin.DECIDED,
        "actor": "owner",
        "source": "chat 2026-10-20",
        "owner_words": (OwnerWords(text="lint once — “quoted” … cut", date="2026-10-14", alias="TD-87"),),
        "state": State.IN_FORCE,
        "read_back": "2026-10-20",
        "created_at": AT,
    }
    return Decision(**{**fields, **changes})


@pytest.fixture
def make():
    """A valid in-force project decision; keyword arguments override fields."""
    return build
