"""Worker tools: one fixed schema each, and validators whose errors name the field (D4 §3.3, T3-T5)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

INVALID_LIMIT = 3
LOCAL_URL = re.compile(r"http://(127\.0\.0\.1|localhost):\d{1,5}(/\S*)?")


class Args(BaseModel):
    """Strict tool arguments: unknown fields are an error the agent sees."""

    model_config = ConfigDict(extra="forbid")


def _f(limit: int, description: str, example: object, least: int = 1) -> Any:  # noqa: ANN401 - a pydantic FieldInfo
    """A bounded field with its description and one example (T5)."""
    return Field(min_length=least, max_length=limit, description=description, examples=[example])


class CheckRun(Args):
    """One check command the agent ran and its exit code."""

    command: str = _f(300, "The command as listed in the task", "npm test")
    exit_code: int = Field(description="Its exit code; 0 means it passed", examples=[0])


class BuildResult(Args):
    """``submit_result`` for the build step."""

    summary: str = _f(2000, "What you changed and why, in a few sentences", "Added greet(name), with a test.")
    changed_paths: list[str] = _f(200, "Repository-relative paths your commit changes", ["packages/app/src/greet.ts"])
    checks: list[CheckRun] = _f(
        20, "Every task check you ran on your final commit", [{"command": "npm test", "exit_code": 0}]
    )


class AskOption(Args):
    """One answer the owner can choose and where it leads."""

    label: str = _f(200, "The answer as the owner picks it", "German")
    effect: str = _f(300, "What you will do if it is chosen", "greet() returns 'Hallo, <name>!'")


class AskQuestion(Args):
    """``ask_question``: one question for the owner; the step ends and resumes with the answer."""

    question: str = _f(500, "One question", "Which language should greet() use?")
    why: str = _f(500, "Why you cannot decide it yourself", "The brief calls the greeting language a product decision.")
    options: list[AskOption] = _f(
        5,
        "Two to five distinct answers, each leading somewhere",
        [{"label": "German", "effect": "Hallo"}, {"label": "English", "effect": "Hello"}],
        least=2,
    )


class WrongPremise(Args):
    """``report_wrong_premise``: the brief or plan cannot be built as written."""

    stage: Literal["brief", "plan"] = Field(description="Which document is wrong", examples=["plan"])
    reason: str = _f(1000, "What is wrong", "greet() already exists with another signature.")
    evidence: list[str] = _f(10, "Paths, lines or command output that show it", ["src/greet.ts:3 exports greet(a, b)"])


class Finding(Args):
    """One problem the change must fix."""

    place: str = _f(300, "File and line or area", "src/greet.ts:4")
    problem: str = _f(500, "What is wrong, naming the criterion", "AC-1: English")
    fix: str = _f(500, "The change that resolves it", "Use Hallo")


class ReviewResult(Args):
    """``submit_result`` for the review step."""

    verdict: Literal["pass", "fix"] = Field(
        description="pass when every criterion holds and nothing must change, else fix", examples=["pass"]
    )
    findings: list[Finding] = Field(
        default_factory=list,
        max_length=20,
        description="Each problem that must be fixed; empty for pass",
        examples=[[{"place": "src/greet.ts:4", "problem": "AC-1: English", "fix": "Use Hallo"}]],
    )
    covered_paths: list[str] = _f(
        200, "Every repository path you read, including files outside the diff", ["packages/app/src/greet.ts"]
    )


class CheckRecipe(Args):
    """``submit_result`` for check preparation: how the host starts the environment the owner checks."""

    command: str = _f(200, "One allowed launch command", "npm run preview")
    directory: str = _f(300, "Repository-relative directory to run it in", "packages/app")
    ready_url: str = _f(300, "Local URL that answers once the environment is ready", "http://127.0.0.1:4173/")
    summary: str = _f(1000, "How you verified it", "Ran it, fetched the page, stopped it")


@dataclass(frozen=True)
class Spec:
    """One tool's name, description, argument model and the step ending an accepted call causes."""

    name: str
    description: str
    model: type[Args]
    ending: Literal["result", "ask", "premise"]


SUBMIT = Spec(
    "submit_result",
    "Submit this step's result once: after committing your work and running every task check on that commit. "
    "Delivery reads the commit from the worktree HEAD.",
    BuildResult,
    "result",
)
ASK = Spec(
    "ask_question",
    "Ask the owner one question when a decision is theirs or something you need is missing. Your step ends; "
    "it resumes with the answer.",
    AskQuestion,
    "ask",
)
PREMISE = Spec(
    "report_wrong_premise",
    "Report that the brief or plan is wrong, with evidence. Your step ends.",
    WrongPremise,
    "premise",
)
SPECS = (SUBMIT, ASK, PREMISE)
REVIEW = Spec("submit_result", "Submit your review verdict once, after reading the diff.", ReviewResult, "result")
RECIPE = Spec(
    "submit_result",
    "Submit the verified launch recipe once, after you stopped everything you started.",
    CheckRecipe,
    "result",
)


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
    """Return field errors for a build result against the worktree HEAD the runner derives and the task's checks."""
    errors = []
    if tree.head == tree.base:
        errors.append(
            f"changes: no commit since the task's base {tree.base[:12]}; commit your changes, then submit again"
        )
    if tree.dirty:
        errors.append(f"changes: uncommitted files ({_few(tree.dirty)}); commit them, then submit again")
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


def check_review(review: ReviewResult, tree: Worktree) -> list[str]:
    """Return field errors for a verdict that does not match its findings or skips a changed path."""
    errors = []
    if review.verdict == "fix" and not review.findings:
        errors.append("findings: empty - a fix verdict names each problem with place, problem and fix")
    if review.verdict == "pass" and review.findings:
        errors.append("verdict: pass with findings - use fix, or drop findings that need no change")
    if missing := sorted(set(tree.changed) - set(review.covered_paths)):
        errors.append(f"covered_paths: missing {_few(missing)} - read every changed path and list it")
    return errors


def check_recipe(recipe: CheckRecipe, tree: Worktree, launch: Sequence[str], root: Path) -> list[str]:
    """Return field errors for a recipe the host could not run: outside the worktree, unlisted or not local."""
    errors = [f"changes: uncommitted files ({_few(tree.dirty)}); commit or revert them"] if tree.dirty else []
    where = (root / recipe.directory).resolve()
    if not (where.is_relative_to(root.resolve()) and where.is_dir()):
        errors.append(f'directory: {recipe.directory} is not a directory in the worktree - e.g. "packages/app"')
    if not any(recipe.command.split()[: len(c.split())] == c.split() for c in launch):
        errors.append(f"command: not an allowed launch command - use one of {', '.join(launch) or 'none'}")
    if not LOCAL_URL.fullmatch(recipe.ready_url):
        errors.append('ready_url: must be local with a port, e.g. "http://127.0.0.1:4173/"')
    return errors


def check_result(args: Args, tree: Worktree, checks: Sequence[str], root: Path) -> list[str]:
    """Return the field errors of one ``submit_result`` against the worktree the runner observed."""
    match args:
        case BuildResult():
            return check_build(args, tree, checks)
        case ReviewResult():
            return check_review(args, tree)
        case CheckRecipe():
            return check_recipe(args, tree, checks, root)
    return []
