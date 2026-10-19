"""A test review's results (TD-339, TD-390): each reviewer's verdicts on its share, then the curator's report."""

from __future__ import annotations

from typing import Literal, Self

from pydantic import Field, model_validator

from owlbear_delivery_next.change_contracts import tools

REVIEW_LABEL = "test-review"  # a share's reviewer session
CURATION_LABEL = "test-curation"  # the curator's build session


class TestVerdict(tools.Args):
    """One test you would not keep as it is, and why; a test in doubt is kept and not listed."""

    __test__ = False  # not a pytest class

    test: str = tools.bounded(300, "The test: its file and node", "tests/test_greet.py::test_trims")
    action: Literal["retire", "merge", "rewrite-lower"] = Field(
        description="retire: it protects nothing another test does not; merge: it and caught_by protect the same "
        "behaviour; rewrite-lower: the behaviour matters but a cheaper test at a lower layer would protect it"
    )
    behaviour: str = tools.bounded(500, "The behaviour, interface or risk it protects", "greet() trims the name")
    bug: str = Field(
        default="",
        max_length=500,
        description="For retire and merge: a plausible bug this test would catch",
        examples=["greet() stops trimming a trailing space"],
    )
    caught_by: str = Field(
        default="",
        max_length=500,
        description="For retire and merge: the remaining test and its assertion that still catches that bug",
        examples=["tests/test_greet.py::test_names asserts greet(' Ada ') == 'Hallo Ada'"],
    )

    @model_validator(mode="after")
    def _evidence(self) -> Self:
        """A removal names the bug and the test that still catches it (TD-112, TD-339)."""
        if self.action != "rewrite-lower" and not (self.bug.strip() and self.caught_by.strip()):
            msg = f"{self.action} needs bug and caught_by; a test you cannot name them for is kept"
            raise ValueError(msg)
        return self


class TestReviewResult(tools.Args):
    """``submit_result`` for a test reviewer: its share's verdicts; every test not listed is kept."""

    __test__ = False  # not a pytest class

    verdicts: list[TestVerdict] = Field(
        default_factory=list,
        max_length=200,
        description="Each test of your share you would retire, merge or rewrite lower; none when all stay",
    )
    kept: int = Field(ge=0, description="How many tests of your share stay as they are", examples=[42])
    covered_paths: list[str] = Field(
        min_length=1, max_length=500, description="Every file of your share you read", examples=[["tests/test_a.py"]]
    )


class Applied(tools.Args):
    """One verdict you applied."""

    test: str = tools.bounded(300, "The test as the verdict names it", "tests/test_greet.py::test_trims")
    action: Literal["retire", "merge"] = Field(description="What you did")
    change: str = tools.bounded(500, "What changed", "Removed; test_names keeps the assertion")


class Refused(tools.Args):
    """One retire or merge verdict that does not hold."""

    test: str = tools.bounded(300, "The test as the verdict names it", "tests/test_greet.py::test_trims")
    reason: str = tools.bounded(1000, "Why it stays, with evidence", "Only it covers the empty name")


class Measure(tools.Args):
    """One run of the suite, before or after your edits."""

    command: str = tools.bounded(300, "The command you ran", "uv run pytest -q tests")
    commit: str = tools.bounded(40, "The commit it ran on", "3d090f3ad")
    tests: int = Field(ge=0, description="Tests collected", examples=[1697])
    seconds: float = Field(ge=0, description="Its wall time in seconds", examples=[106.4])
    failures: list[str] = Field(default_factory=list, max_length=100, description="Tests that failed")
    preexisting: list[str] = Field(
        default_factory=list, max_length=100, description="After only: failures that also failed before"
    )


class TestCurationResult(tools.Args):
    """``submit_result`` for the curator: what held and what did not, and the suite before and after."""

    __test__ = False  # not a pytest class

    applied: list[Applied] = Field(default_factory=list, max_length=300, description="The verdicts you applied")
    refused: list[Refused] = Field(default_factory=list, max_length=300, description="The verdicts that do not hold")
    before: Measure = Field(description="The suite before your edits")
    after: Measure | None = Field(default=None, description="The same command after your edits; none if none applied")
    summary: str = tools.bounded(1000, "What changed, in two sentences", "Retired 12 duplicated tests; 1697 remain")

    @model_validator(mode="after")
    def _measured(self) -> Self:
        """Applied edits are measured again with the same command; none applied, nothing to measure (TD-311)."""
        if self.applied and (self.after is None or self.after.command != self.before.command):
            msg = "after: run the same command as before on your last commit"
            raise ValueError(msg)
        if not self.applied and self.after is not None:
            msg = "after: none applied, so leave it out"
            raise ValueError(msg)
        return self


TEST_REVIEW = tools.Spec(
    "submit_result", "Submit your share's verdicts once, after reading each of its tests.", TestReviewResult, "result"
)
TEST_CURATION = tools.Spec(
    "submit_result",
    "Submit once: after committing what holds and measuring the suite on that commit, or with nothing applied.",
    TestCurationResult,
    "result",
)
