"""A test review's record on its Change (TD-373, TD-390): the pinned commit, its shares and the curator's report."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from owlbear_delivery_next.change_contracts.curation_tools import TestCurationResult, TestReviewResult


class _Record(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Share(_Record):
    """One reviewer's test files and, once it ended, its verdicts."""

    paths: list[str]
    lines: int
    review: TestReviewResult | None = None
    ended: Literal["reviewed", "not-reviewed"] | None = None  # not reviewed: the owner went on without it


class TestReview(_Record):
    """The review of one project's tests: every share is judged at ``commit``, then the curator applies what holds."""

    __test__ = False  # not a pytest class

    commit: str
    packages: list[str]
    shares: list[Share]
    report: TestCurationResult | None = None
    unchanged: bool = False  # the curation applied nothing at the pinned commit: the Change ends without a PR
