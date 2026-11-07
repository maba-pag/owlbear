"""The repairer's result: why the step stopped, every fix it tried, and what it proved (#1066)."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from owlbear_delivery_next.change_contracts.tools import Args, Spec, bounded


class Try(Args):
    """One fix you tried and what happened when you ran the checks."""

    fix: str = bounded(500, "What you changed or tried", "Route web/vendor/ like page files in testing.py")
    outcome: str = bounded(1000, "What the checks did then, with their output's telling lines", "passed in 212 s")


class Defect(Args):
    """A defect in OwlBear's own code, as it holds for any project: never this project's names or files."""

    title: str = bounded(120, "The issue's title", "uv run test --changed runs the full suite for vendored .js files")
    text: str = bounded(3000, "What is wrong and how it shows, for any project", "_python_scope sends web/vendor/ ...")
    paths: list[str] = Field(
        min_length=1, max_length=10, description="OwlBear paths, repository-relative, with lines",
        examples=[["serve/tools/src/owlbear_tools/testing.py:216"]],
    )  # fmt: skip


class RepairResult(Args):
    """``submit_result`` for the repairer of a stuck step."""

    cause: str = bounded(3000, "Why the step stopped, with the evidence", "The diff's .pre-commit-config.yaml ...")
    tried: list[Try] = Field(
        min_length=1, max_length=20, description="Every fix in the order you tried it",
        examples=[[{"fix": "Route web/vendor/ like pages", "outcome": "passed in 212 s"}]],
    )  # fmt: skip
    fix: Literal["none", "patch", "profile-check"] = Field(
        description="patch: your edits in this copy make the checks pass; profile-check: the step needs a project "
        "check the profile lacks, proven here; none: nothing worked or the cause is temporary",
        examples=["patch"],
    )
    package: str = Field(default="", max_length=300, description="profile-check only: its package", examples=["."])
    command: str = Field(
        default="", max_length=500, description="profile-check only: its command", examples=["uv run pytest -q"]
    )
    defect: Defect | None = Field(default=None, description="Only when the cause is in OwlBear's own code")

    @model_validator(mode="after")
    def _check(self) -> RepairResult:
        if self.fix == "profile-check" and not (self.package.strip() and self.command.strip()):
            msg = "package and command: a profile-check needs both, e.g. package '.' and command 'uv run pytest -q'"
            raise ValueError(msg)
        return self


SUBMIT = Spec("submit_result", "Submit once, after trying fixes in this copy.", RepairResult, "result")
