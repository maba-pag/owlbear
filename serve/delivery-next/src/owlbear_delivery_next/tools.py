"""Worker tools: one fixed schema each, and validators whose errors name the field (D4 §3.3, T3-T5)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

if TYPE_CHECKING:
    from collections.abc import Sequence

INVALID_LIMIT = 3


class Args(BaseModel):
    """Strict tool arguments: unknown fields are an error the agent sees."""

    model_config = ConfigDict(extra="forbid")


class CheckRun(Args):
    """One check command the agent ran and its exit code."""

    command: str = Field(min_length=1, description="The command as listed in the task", examples=["npm test"])
    exit_code: int = Field(description="Its exit code; 0 means it passed", examples=[0])


class BuildResult(Args):
    """``submit_result`` for the build step."""

    summary: str = Field(
        min_length=1,
        max_length=2000,
        description="What you changed and why, in a few sentences",
        examples=["Added greet(name) returning a German greeting, with a test."],
    )
    changed_paths: list[str] = Field(
        min_length=1,
        max_length=200,
        description="Repository-relative paths your commit changes",
        examples=[["packages/app/src/greet.ts"]],
    )
    commit: str = Field(
        pattern=r"^[0-9a-f]{7,40}$",
        description="SHA of the commit you created; it must be the worktree HEAD",
        examples=["3f2c1ab"],
    )
    checks: list[CheckRun] = Field(
        min_length=1,
        max_length=20,
        description="Every task check you ran on that commit",
        examples=[[{"command": "npm test", "exit_code": 0}]],
    )


class AskOption(Args):
    """One answer the owner can choose and where it leads."""

    label: str = Field(
        min_length=1, max_length=200, description="The answer as the owner picks it", examples=["German"]
    )
    effect: str = Field(
        min_length=1,
        max_length=300,
        description="What you will do if it is chosen",
        examples=["greet() returns 'Hallo, <name>!'"],
    )


class AskQuestion(Args):
    """``ask_question``: one question for the owner; the step ends and resumes with the answer."""

    question: str = Field(
        min_length=1, max_length=500, description="One question", examples=["Which language should greet() use?"]
    )
    why: str = Field(
        min_length=1,
        max_length=500,
        description="Why you cannot decide it yourself",
        examples=["The brief calls the greeting language a product decision."],
    )
    options: list[AskOption] = Field(
        min_length=2,
        max_length=5,
        description="Two to five distinct answers, each leading somewhere",
        examples=[[{"label": "German", "effect": "Hallo"}, {"label": "English", "effect": "Hello"}]],
    )


class WrongPremise(Args):
    """``report_wrong_premise``: the brief or plan cannot be built as written."""

    stage: Literal["brief", "plan"] = Field(description="Which document is wrong", examples=["plan"])
    reason: str = Field(
        min_length=1,
        max_length=1000,
        description="What is wrong",
        examples=["greet() already exists with another signature."],
    )
    evidence: list[str] = Field(
        min_length=1,
        max_length=10,
        description="Paths, lines or command output that show it",
        examples=[["packages/app/src/greet.ts:3 exports greet(name, lang)"]],
    )


@dataclass(frozen=True)
class Spec:
    """One tool's name, description and argument model."""

    name: str
    description: str
    model: type[Args]


SUBMIT = Spec(
    "submit_result",
    "Submit this step's result once: after committing your work and running every task check on that commit.",
    BuildResult,
)
ASK = Spec(
    "ask_question",
    "Ask the owner one question when a decision is theirs or something you need is missing. Your step ends; "
    "it resumes with the answer.",
    AskQuestion,
)
PREMISE = Spec(
    "report_wrong_premise", "Report that the brief or plan is wrong, with evidence. Your step ends.", WrongPremise
)
SPECS = (SUBMIT, ASK, PREMISE)


def _inline(node: object, defs: dict[str, Any]) -> object:
    if isinstance(node, dict):
        if "$ref" in node:
            return _inline(defs[node["$ref"].rsplit("/", 1)[-1]], defs)
        return {k: _inline(v, defs) for k, v in node.items() if k != "$defs"}
    return [_inline(v, defs) for v in node] if isinstance(node, list) else node


def schema(spec: Spec) -> dict[str, Any]:
    """Return the tool's JSON schema with every reference inlined."""
    raw = spec.model.model_json_schema()
    inlined = _inline(raw, raw.get("$defs", {}))
    return inlined if isinstance(inlined, dict) else raw


def _loc(loc: Sequence[int | str]) -> str:
    out = ""
    for part in loc:
        out += f"[{part}]" if isinstance(part, int) else (f".{part}" if out else str(part))
    return out or "arguments"


def parse[T: Args](model: type[T], arguments: object) -> tuple[T | None, list[str]]:
    """Validate tool arguments; return the instance, or one error per field with an example."""
    try:
        data = json.loads(arguments) if isinstance(arguments, str) else arguments
        return model.model_validate(data), []
    except ValidationError as exc:
        errors = []
        for err in exc.errors():
            field = model.model_fields.get(str(err["loc"][0])) if err["loc"] else None
            example = f" - e.g. {json.dumps(field.examples[0])}" if field and field.examples else ""
            errors.append(f"{_loc(err['loc'])}: {err['msg']}{example}")
        return None, errors
    except ValueError:
        return None, ["arguments: not a JSON object - send the fields as one object"]


@dataclass(frozen=True)
class Worktree:
    """What git shows in the worktree when a result arrives."""

    head: str
    base: str
    dirty: tuple[str, ...] = ()
    changed: tuple[str, ...] = ()


def _few(paths: Sequence[str]) -> str:
    return ", ".join(paths[:5]) + (f" and {len(paths) - 5} more" if len(paths) > 5 else "")  # noqa: PLR2004


def check_build(result: BuildResult, tree: Worktree, checks: Sequence[str]) -> list[str]:
    """Return field errors for a build result against the observed worktree and the task's checks."""
    errors = []
    if tree.head == tree.base:
        errors.append(
            f"commit: HEAD of the worktree is {tree.head[:12]}, the task's base; commit your changes, then submit again"
        )
    elif not tree.head.startswith(result.commit):
        errors.append(
            f"commit: HEAD of the worktree is {tree.head[:12]}, not {result.commit}; "
            "commit your changes, then submit again with the HEAD SHA"
        )
    if tree.dirty:
        errors.append(
            f"commit: the worktree has uncommitted changes ({_few(tree.dirty)}); commit them, then submit again"
        )
    if tree.head != tree.base:
        if missing := sorted(set(tree.changed) - set(result.changed_paths)):
            errors.append(f"changed_paths: missing {_few(missing)} - list every path your commit changes")
        if extra := sorted(set(result.changed_paths) - set(tree.changed)):
            errors.append(f"changed_paths: {_few(extra)} not changed by the commits since the base - remove them")
    errors.extend(
        f"checks[{i}].exit_code: {c.exit_code} - fix the failure, commit, run it again, then submit"
        for i, c in enumerate(result.checks)
        if c.exit_code != 0
    )
    errors.extend(
        f'checks: "{cmd}" missing - run it on your commit and report it, e.g. {{"command": "{cmd}", "exit_code": 0}}'
        for cmd in checks
        if not any(cmd in c.command for c in result.checks)
    )
    return errors


def check_question(question: AskQuestion) -> list[str]:
    """Return field errors for a question whose options do not lead to distinct answers."""
    labels = [o.label.strip().lower() for o in question.options]
    if len(set(labels)) < len(labels):
        return ["options: labels repeat - give each option a distinct answer"]
    return []
