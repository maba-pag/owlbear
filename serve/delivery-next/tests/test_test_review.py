"""A test review's roles and result schemas (TD-339, TD-112): a removal names its bug and still-catching test."""

import pytest
from pydantic import ValidationError

from owlbear_delivery_next.change_contracts.curation_tools import TestCurationResult, TestReviewResult
from owlbear_delivery_next.settings import roles
from owlbear_delivery_next.settings.config import Layer, resolve

MEASURE = {"command": "uv run pytest -q", "commit": "abc1234", "tests": 10, "seconds": 1.5}


def test_the_reviewer_and_curator_roles_default_as_the_owner_chose():
    agents = resolve(None, Layer()).agents
    reviewer, curator = agents["test-reviewer"], agents["test-curator"]
    assert (reviewer.model, reviewer.effort, reviewer.context) == ("gpt-6.1-sol", "medium", "default")
    assert (curator.model, curator.effort, curator.context) == ("claude-opus-5.5", "high", "long")
    assert (roles.SESSIONS["test-review"], roles.SESSIONS["test-curation"]) == ("test-reviewer", "test-curator")


@pytest.mark.parametrize("action", ["retire", "merge"])
@pytest.mark.parametrize("missing", ["bug", "caught_by"])
def test_a_removal_without_its_bug_or_still_catching_test_is_refused(action, missing):
    verdict = {"test": "t.py::a", "action": action, "behaviour": "b", "bug": "x", "caught_by": "t.py::b"} | {
        missing: " "
    }
    with pytest.raises(ValidationError, match="needs bug and caught_by"):
        TestReviewResult.model_validate({"verdicts": [verdict], "kept": 3, "covered_paths": ["t.py"]})
    note = {"test": "t.py::a", "action": "rewrite-lower", "behaviour": "b"}  # a note for later needs neither
    assert TestReviewResult.model_validate({"verdicts": [note], "kept": 3, "covered_paths": ["t.py"]}).verdicts


def test_applied_edits_are_measured_again_with_the_same_command_and_nothing_applied_is_not():
    applied = [{"test": "t.py::a", "action": "retire", "change": "removed"}]
    with pytest.raises(ValidationError, match="same command"):
        TestCurationResult.model_validate({"applied": applied, "before": MEASURE, "summary": "s"})
    other = MEASURE | {"command": "pytest -x"}
    with pytest.raises(ValidationError, match="same command"):
        TestCurationResult.model_validate({"applied": applied, "before": MEASURE, "after": other, "summary": "s"})
    with pytest.raises(ValidationError, match="none applied"):
        TestCurationResult.model_validate({"before": MEASURE, "after": MEASURE, "summary": "s"})
    assert TestCurationResult.model_validate({"before": MEASURE, "summary": "nothing held"}).after is None
