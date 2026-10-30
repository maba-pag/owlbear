"""Required shaping fields contain meaningful wording without rewriting the owner's text."""

import pytest
from pydantic import ValidationError

from owlbear_delivery_next.change_flow.brief_tools import DecisionDraft

DRAFT = {"question": "Which database?", "answer": "Postgres.", "origin": "decided", "scope": "project"}


@pytest.mark.parametrize(("field", "blank"), [("question", "   "), ("answer", "\t\n")])
def test_blank_decision_fields_are_refused(field, blank):
    with pytest.raises(ValidationError):
        DecisionDraft.model_validate(DRAFT | {field: blank})


def test_meaningful_decision_wording_is_kept_as_written():
    draft = DecisionDraft.model_validate(DRAFT | {"question": " Which database? ", "answer": "Postgres.\n"})
    assert (draft.question, draft.answer) == (" Which database? ", "Postgres.\n")
