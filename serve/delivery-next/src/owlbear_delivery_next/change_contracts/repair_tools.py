"""The repairer's result: why the step stopped, every fix it tried, and what it proved (#1066)."""

from typing import Literal

from pydantic import Field, model_validator

from owlbear_delivery_next.change_contracts.repair_records import PreparationProposal
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
        max_length=20, description="Every attempted remedy in order; empty only for retry, never invent a fix",
        examples=[[{"fix": "Route web/vendor/ like pages", "outcome": "passed in 212 s"}]],
    )  # fmt: skip
    fix: Literal["none", "patch", "profile-check", "retry", "preparation"] = Field(
        description="patch: your edits in this copy make the checks pass; profile-check: the step needs a project "
        "check the profile lacks, proven here; retry: the cause no longer reproduces, no change needed; "
        "none: you tried remedies but none worked",
        examples=["patch"],
    )
    package: str = Field(default="", max_length=300, description="profile-check only: its package", examples=["."])
    command: str = Field(
        default="", max_length=500, description="profile-check only: its command", examples=["uv run pytest -q"]
    )
    defect: Defect | None = Field(default=None, description="Only when the cause is in OwlBear's own code")
    preparation: PreparationProposal | None = Field(
        default=None, description="preparation only: exact option, source, cleanup, isolation and seeded-state check"
    )

    @model_validator(mode="after")
    def _check(self) -> RepairResult:
        if self.fix != "retry" and not self.tried:
            msg = "tried: list the remedies actually attempted; only retry may report no attempted fix"
            raise ValueError(msg)
        if self.fix == "profile-check" and not (self.package.strip() and self.command.strip()):
            msg = "package and command: a profile-check needs both, e.g. package '.' and command 'uv run pytest -q'"
            raise ValueError(msg)
        if (self.fix == "preparation") != isinstance(self.preparation, PreparationProposal):
            msg = "preparation: supply exactly one proposal with fix=preparation, and none for other fixes"
            raise ValueError(msg)
        return self


class PreparationResult(RepairResult):
    """A missing or unsafe test copy needs a synthetic setup proposal, not an unrelated code patch."""

    fix: Literal["none", "preparation"]


class AttemptResult(RepairResult):
    """The diagnostic or real rerun failed: reproduce that operation and try remedies, not another no-change retry."""

    fix: Literal["none", "patch", "profile-check", "retry", "preparation"] = Field(
        description="patch: a proven edit; profile-check: a proven missing project check; none: remedies failed",
        json_schema_extra={"enum": ["none", "patch", "profile-check", "preparation"]},
    )
    tried: list[Try] = Field(min_length=1, max_length=20, description="Actual attempted remedies, never diagnostics")

    @model_validator(mode="after")
    def _attempted(self) -> AttemptResult:
        if self.fix == "retry":
            msg = "fix: retry did not recover the step; reproduce its reported failure and try a remedy before ending"
            raise ValueError(msg)
        return self


SUBMIT = Spec("submit_result", "Submit once, after trying fixes in this copy.", RepairResult, "result")
ATTEMPT = Spec(
    "submit_result", "Submit after trying remedies; another no-change retry is not recovery.", AttemptResult, "result"
)
PREPARATION = Spec(
    "submit_result",
    "Propose one proven synthetic preparation; Delivery asks before saving it.",
    PreparationResult,
    "result",
)
