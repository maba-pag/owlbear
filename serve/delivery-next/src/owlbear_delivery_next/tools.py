"""Worker tools: one fixed schema each, and validators whose errors name the field (D4 §3.3, T3-T5)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from owlbear_delivery_next.models import ItemRef

INVALID_LIMIT = 3
LOCAL_URL = re.compile(r"http://(127\.0\.0\.1|localhost):\d{1,5}(/\S*)?")


class Args(BaseModel):
    """Strict tool arguments: unknown fields are an error the agent sees."""

    model_config = ConfigDict(extra="forbid")


def _f(limit: int, description: str, example: object, least: int = 1) -> Any:  # noqa: ANN401 - a pydantic FieldInfo
    """A bounded field with its description and one example (T5)."""
    return Field(min_length=least, max_length=limit, description=description, examples=[example])


bounded = _f  # the same helper for the owner chat's brief schema (brief_tools)


class CheckRun(Args):
    """One check command the agent ran and its exit code."""

    command: str = _f(300, "The command as listed in the task", "npm test")
    exit_code: int = Field(description="Its exit code; 0 means it passed", examples=[0])


class Response(Args):
    """How a pull-request conversation task was handled and the text Delivery posts for it."""

    how: Literal["fixed", "answered", "no-action"] = Field(
        description="fixed: your commit changes the code; answered: a reply without a code change; "
        "no-action: nothing to do (not for review threads)",
        examples=["answered"],
    )
    text: str = _f(3000, "The reply Delivery posts, or the reason no action is needed", "greet() trims the name.")


class BuildResult(Args):
    """``submit_result`` for the build step."""

    summary: str = _f(2000, "What you changed and why, in a few sentences", "Added greet(name), with a test.")
    changed_paths: list[str] = _f(
        200, "Repository-relative paths your commit changes", ["packages/app/src/greet.ts"], least=0
    )
    checks: list[CheckRun] = _f(
        20, "Every task check you ran on your final commit", [{"command": "npm test", "exit_code": 0}], least=0
    )
    response: Response | None = Field(
        default=None,
        description="Only for a pull-request conversation task: how you handled it and the text to post",
        examples=[{"how": "answered", "text": "greet() trims the name."}],
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
    """``report_wrong_premise``: the brief or plan cannot be built as written, or the target has what is missing."""

    stage: Literal["brief", "plan", "target"] = Field(
        description="Which document is wrong; target when the task needs a commit or API that is on the target "
        "branch but not in this branch yet",
        examples=["plan"],
    )
    reason: str = _f(1000, "What is wrong", "greet() already exists with another signature.")
    evidence: list[str] = _f(10, "Paths, lines or command output that show it", ["src/greet.ts:3 exports greet(a, b)"])


class MissingTool(Args):
    """``report_missing_tool``: a tool, command or capability the step needs is missing or keeps failing."""

    tool: str = _f(100, "The tool, command or capability, by the name you tried", "docker")
    need: str = _f(300, "What you need it for", "Run the integration tests the task's checks name")
    error: str = _f(1000, "The exact error, or what happened when you tried", "zsh: command not found: docker")


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
    covered_paths: list[str] = Field(
        default_factory=list,
        max_length=200,
        description="Paths you read, as reading evidence; for a visual review every screenshot file name",
        examples=[["packages/app/src/greet.ts"]],
    )


class Doubt(Args):
    """One screenshot the reviewer cannot judge, and what only the owner can decide about it."""

    place: str = _f(300, "The screenshot file name", "home-1280.png")
    question: str = _f(500, "What you cannot decide from the brief", "Is the greeting meant to wrap at 1280px?")


class VisualReviewResult(ReviewResult):
    """``submit_result`` for the visual review: a reviewer who cannot decide says so (N6)."""

    verdict: Literal["pass", "fix", "unsure"] = Field(  # type: ignore[assignment]
        description="pass, fix for a definite problem, or unsure when only the owner can decide", examples=["pass"]
    )
    doubts: list[Doubt] = Field(
        default_factory=list,
        max_length=10,
        description="For unsure: each screenshot you cannot judge and why; empty otherwise",
        examples=[[{"place": "home-1280.png", "question": "Is the greeting meant to wrap at 1280px?"}]],
    )


class CheckRecipe(Args):
    """``submit_result`` for check preparation: how the host starts the environment the owner checks."""

    command: str = _f(200, "The command that starts it", "npm run preview")
    directory: str = _f(300, "Repository-relative directory to run it in", "packages/app")
    ready_url: str = _f(300, "Local URL that answers once the environment is ready", "http://127.0.0.1:4173/")
    summary: str = _f(1000, "How you verified it", "Ran it, fetched the page, stopped it")


class PlanTask(Args):
    """One ordered task of the plan."""

    title: str = _f(200, "What the task delivers", "Add farewell(name) with a test")
    goal: str = _f(3000, "The criteria it meets and how the Builder knows it is done", "AC-1: farewell('Ada')")
    scope: list[str] = _f(20, "Repository-relative paths or directories it may change", ["packages/app"])
    checks: list[str] = _f(5, "Check commands from the project profile the Builder runs", ["npm test"])


class PlanResult(Args):
    """``submit_result`` for the plan step."""

    tasks: list[PlanTask] = _f(
        8,
        "Ordered tasks, each small enough for one Builder session",
        [{"title": "Add farewell", "goal": "AC-1", "scope": ["packages/app"], "checks": ["npm test"]}],
    )


def relative(path: str) -> bool:
    """Whether *path* is repository-relative and stays inside the repository."""
    p = PurePosixPath(path)
    return bool(path.strip()) and not p.is_absolute() and ".." not in p.parts and not path.startswith("~")


def within(path: str, scope: Sequence[str]) -> bool:
    """Whether *path* is one of the *scope* paths or lies under one; an empty or root scope holds every path."""
    parts = PurePosixPath(path).parts
    return not scope or any(parts[: len(s := PurePosixPath(p).parts)] == s for p in scope)


def check_plan(plan: PlanResult, tree: Worktree, checks: Sequence[str], scope: Sequence[str] = ()) -> list[str]:
    """Return field errors for task checks outside the profile and scopes outside the repository or the brief."""
    errors = [f"changes: uncommitted files ({_few(tree.dirty)}); planning changes nothing"] if tree.dirty else []
    listed = ", ".join(f'"{c}"' for c in checks) or "none - ask the owner which command checks this package"
    brief = ", ".join(scope)
    for i, task in enumerate(plan.tasks):
        errors += [
            f'tasks[{i}].checks: "{c}" is not a check of the project profile - use one of {listed}'
            for c in task.checks
            if c not in checks
        ]
        errors += [f"tasks[{i}].scope: {p} is not repository-relative" for p in task.scope if not relative(p)]
        errors += [
            f"tasks[{i}].scope: {p} is outside the approved brief scope {brief}; keep to the brief or "
            "report_wrong_premise to widen it"
            for p in task.scope
            if relative(p) and not within(p, scope)
        ]
    return errors


@dataclass(frozen=True)
class Spec:
    """One tool's name, description, argument model and the step ending an accepted call causes."""

    name: str
    description: str
    model: type[Args]
    ending: Literal["result", "ask", "premise", "missing-tool"]


SUBMIT = Spec(
    "submit_result",
    "Submit this step's result once: after committing your work and running every task check on that commit. "
    "Delivery reads the commit from the worktree HEAD.",
    BuildResult,
    "result",
)
ASK = Spec(
    "ask_question",
    "Ask the owner one question when a decision is theirs. Your step ends; it resumes with the answer.",
    AskQuestion,
    "ask",
)
PREMISE = Spec(
    "report_wrong_premise",
    "Report that the brief or plan is wrong, or that the task needs target-branch work this branch lacks, with "
    "evidence. Your step ends.",
    WrongPremise,
    "premise",
)
MISSING = Spec(
    "report_missing_tool",
    "Report a tool, command or capability you need that is missing or keeps failing, with the exact error. "
    "Delivery retries it, asks the owner to set it up, or plans without it. Your step ends.",
    MissingTool,
    "missing-tool",
)
SPECS = (SUBMIT, ASK, PREMISE, MISSING)
FIRST_LOOK = "submit_first_look"  # the design judge's own verdict, before the detector's findings reach it
SCAN_DESIGN = "scan_design"  # the builder's design detector on a UI Change (slice 7)
JUDGES = frozenset({"challenger", "designer"})  # they answer with a verdict, never a question (TD-108)


def asks(role: str) -> bool:
    """Whether the role may ask the owner with ``ask_question``; a judge's session always names its role."""
    return role not in JUDGES


def results(role: str, *, ui: bool = False) -> list[str]:
    """Delivery's tools a role's agent is offered: every step's own, the design judge's first look, the UI scan."""
    extra = [FIRST_LOOK] if role == "designer" else [SCAN_DESIGN] if role == "builder" and ui else []
    return [*(s.name for s in SPECS if s is not ASK or asks(role)), *extra]


REVIEW = Spec("submit_result", "Submit your review verdict once, after reading the diff.", ReviewResult, "result")
VISUAL_REVIEW = Spec(
    "submit_result", "Submit your verdict once, after looking at each screenshot.", VisualReviewResult, "result"
)
RECIPE = Spec(
    "submit_result",
    "Submit the verified launch recipe once, after you stopped everything you started.",
    CheckRecipe,
    "result",
)
PLAN = Spec("submit_result", "Submit the ordered plan once, after reading the code it touches.", PlanResult, "result")


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


def _response(result: BuildResult, item: ItemRef | None) -> list[str]:
    """Errors of the ``response`` field: required for a conversation task answering *item*, refused otherwise."""
    r = result.response
    if item is None:
        return ["response: only for a pull-request conversation task - remove it"] if r else []
    if r is None:
        return ['response: required for this conversation task - e.g. {"how": "answered", "text": "..."}']
    if r.how == "no-action" and not item.notice:
        return ["response.how: no-action is only for a bot's comment or review - fix it or answer it"]
    return []


def check_build(result: BuildResult, tree: Worktree, checks: Sequence[str], item: ItemRef | None = None) -> list[str]:
    """Return field errors for a build result against the worktree HEAD the runner derives and the task's checks.

    *item* is the conversation item the task answers, if any; an answer or no-action needs no commit.
    """
    errors = _response(result, item)
    reply = result.response is not None and result.response.how != "fixed"
    if reply and tree.head == tree.base and not tree.dirty:
        return errors
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


def check_review(review: ReviewResult, tree: Worktree, *, visual: bool = False) -> list[str]:
    """Return field errors for a verdict that does not match its findings or, visual, skips a screenshot.

    A code review's coverage is the engine's own diff; its ``covered_paths`` is only logged evidence.
    """
    errors = []
    if review.verdict == "fix" and not review.findings:
        errors.append("findings: empty - a fix verdict names each problem with place, problem and fix")
    if review.verdict == "pass" and review.findings:
        errors.append("verdict: pass with findings - use fix, or drop findings that need no change")
    if review.verdict == "unsure" and not getattr(review, "doubts", None):
        errors.append("doubts: empty - an unsure verdict names each screenshot and what you cannot decide")
    if visual and (missing := sorted(set(tree.changed) - set(review.covered_paths))):
        errors.append(f"covered_paths: missing {_few(missing)} - look at every screenshot and list it")
    places = [f.place for f in review.findings] + [d.place for d in getattr(review, "doubts", [])]
    if visual and (unknown := sorted({p for p in places if p not in tree.changed})):
        errors.append(f"place: {_few(unknown)} is not a screenshot - name the screenshot file it is seen in")
    return errors


def check_recipe(recipe: CheckRecipe, tree: Worktree, root: Path) -> list[str]:
    """Return field errors for a recipe the host could not run: uncommitted, outside the worktree or not local."""
    errors = [f"changes: uncommitted files ({_few(tree.dirty)}); commit or revert them"] if tree.dirty else []
    where = (root / recipe.directory).resolve()
    if not (where.is_relative_to(root.resolve()) and where.is_dir()):
        errors.append(f'directory: {recipe.directory} is not a directory in the worktree - e.g. "packages/app"')
    if not LOCAL_URL.fullmatch(recipe.ready_url):
        errors.append('ready_url: must be local with a port, e.g. "http://127.0.0.1:4173/"')
    return errors


def check_result(  # noqa: PLR0913, PLR0917 - the result, its worktree and four bounds
    args: Args,
    tree: Worktree,
    checks: Sequence[str],
    root: Path,
    scope: Sequence[str] = (),
    item: ItemRef | None = None,
    *,
    visual: bool = False,
) -> list[str]:
    """Return the field errors of one ``submit_result`` against the worktree the runner observed and the brief scope."""
    match args:
        case BuildResult():
            return check_build(args, tree, checks, item)
        case ReviewResult():
            return check_review(args, tree, visual=visual)
        case CheckRecipe():
            return check_recipe(args, tree, root)
        case PlanResult():
            return check_plan(args, tree, checks, scope)
    return []
