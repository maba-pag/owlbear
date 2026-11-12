"""The missing-tool report's cases (TD-36), in order.

A guard denial, missing executable setup, one of the step's own checks that cannot finish (setup for repair, unless its
text names the network: #1065), a temporary failure, a tool only a VS Code window has, nowhere. Delivery never grants a
tool, and a window-only tool is asked of the owner, naming it, never run elsewhere (D-01M5WG7TB1292KJ05CH0R11WE0).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.failures import CHECK, ENVIRONMENT, cause_key, transient
from owlbear_delivery_next.change_contracts.models import ErrorKind, Exit, Option, Question, StepKind
from owlbear_delivery_next.change_flow.loop import StepResult

if TYPE_CHECKING:
    from datetime import datetime

    from owlbear_delivery_next.change_contracts.tools import MissingTool
    from owlbear_delivery_next.runtimes.session_result import Run

PAUSE = Option(id="pause", label="Pause", next="pause")
# Setup texts that name the tool itself, so "npm: ENOENT package.json" never reads as "npm is not installed".
_ABSENT = (
    r"command not found:\s*{n}(?![\w.-])",
    r"(?<![\w.-]){n}: (?:command )?not found",
    r"spawn {n} ENOENT",
    r"No such file or directory: '(?:[^']*/)?{n}'",
    r"Failed to spawn:?\s*`?{n}`?(?![\w.-])",
    r"(?<![\w.-]){n}(?:\s+\w+)?\s+(?:(?:is|are|was|were)\s+)?not (?:installed|running)",
    r"Executable doesn't exist at \S*{n}",
    r"(?:Cannot connect to|Is) the {n} daemon",
)
# The categories and tools only a VS Code window offers (runtime research P15 to P19). Delivery steps run only through
# the SDK (D-01M5WG8RGCBKADW6XPGP0E2FAP), so a step that needs one is asked of the owner.
WINDOW_ONLY = (
    "browser", "problems", "tasks",
    "openBrowserPage", "readPage", "screenshotPage", "navigatePage", "clickElement", "typeInPage", "hoverElement",
    "dragElement", "handleDialog", "runPlaywrightCode", "get_errors", "runTask", "getTaskOutput", "createAndRunTask",
)  # fmt: skip


def _key(name: str) -> str:
    """One spelling for a tool name: ``open_browser_page`` and ``openBrowserPage`` are the same tool."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def window_only(found: set[str]) -> bool:
    """Whether one of *found* is a tool, or a category of tools, that only a VS Code window has."""
    keys = {_key(n) for n in found}
    return any(_key(name) in keys for name in WINDOW_ONLY)


def names(tool: str) -> set[str]:
    """The report's tool as Delivery matches it: its whole name and its program, lower case."""
    words = tool.strip().lower().split()
    return {" ".join(words), words[0].rsplit("/", 1)[-1]} if words else set()


def absent(tool: str, error: str) -> bool:
    """Whether *error* says this very tool is not installed or not running on the machine."""
    return any(re.search(p.format(n=re.escape(n)), error, re.IGNORECASE) for n in names(tool) for p in _ABSENT if n)


def slug(tool: str) -> str:
    """The tool's part of a cause key."""
    return re.sub(r"[^a-z0-9]+", "-", tool.lower()).strip("-")[:40] or "unknown"


def checked(tool: str, checks: tuple[str, ...]) -> bool:
    """Whether the reported *tool* is one of the step's resolved *checks*, or a command run inside one.

    c1's builder reported `uv run test --changed`, part of its check `uv run test --changed && uv run lint --no-fix`.
    """
    said = re.escape(" ".join(tool.split()))
    found = re.compile(rf"(?<![^\s;&|(){{}}]){said}(?![^\s;&|(){{}}])")  # bounded by blanks or shell operators
    return bool(said) and any(found.search(" ".join(c.split())) for c in checks)


def setup(cause: str, reason: str) -> StepResult:
    """A setup problem: never retried as temporary and never back to the brief; it goes to repair (#1065)."""
    return StepResult(exit=Exit.RETRY, cause=cause, reason=reason, setup=True, operational=True)


def _without(enclosing: StepKind, tool: str) -> list[Option]:
    """Go on without the tool: the plan or the brief changes, whichever the step's work comes from.

    A brief challenge offers none: the brief it challenges changes only in chat (its step back is its finding).
    """
    if enclosing == StepKind.SHAPE:
        return []
    if enclosing == StepKind.PLAN:
        return [Option(id="revise", label=f"Revise the brief without {tool}", next=StepKind.SHAPE)]
    return [Option(id="replan", label=f"Plan again without {tool}", next=StepKind.PLAN)]


def _ask(enclosing: StepKind, text: str, cause: str, options: list[Option]) -> StepResult:
    question = Question(step=enclosing, text=text, options=options, cause=cause)
    return StepResult(exit=Exit.ASK, reason=text, cause=cause, question=question, operational=True)


def classify(run: Run, p: MissingTool, enclosing: StepKind, now: datetime) -> StepResult:
    """The step result for one missing-tool report; *enclosing* is the step the session ran for."""
    tool, subject = p.tool.strip(), f"tool-{slug(p.tool)}"
    said = f"{tool} for {p.need}: {p.error}"
    if denied := next((run.denied[n] for n in names(tool) if n in run.denied), None):
        reason = f"{tool} was denied by Delivery's guard, which grants nothing: {denied}"
        cause = cause_key(ErrorKind.POLICY, enclosing, subject)
        return StepResult(exit=Exit.RETRY, cause=cause, reason=reason, denial=denied, operational=True)
    if absent(tool, p.error):
        return setup(
            cause_key(ErrorKind.PROJECT_ENV, enclosing, subject), f"needs {said}; it is not installed or running"
        )
    own = checked(tool, run.checks)
    if (kind := transient(p.error, local=own)) not in ENVIRONMENT and own:
        cause = cause_key(ErrorKind.PROJECT_ENV, enclosing, f"{CHECK}-{slug(tool)}")
        return setup(cause, f"the check {tool} cannot finish: {p.error}")
    if kind in ENVIRONMENT:
        return StepResult(
            exit=Exit.RETRY,
            cause=cause_key(kind, enclosing, subject),
            reason=f"{tool} failed temporarily",
            detail=p.error,
            wake_at=now,
            operational=True,
        )
    if window_only(names(tool)):
        text = f"{tool} exists only in a VS Code window; Delivery steps run only through the SDK. The step needs {said}"
        options = [*_without(enclosing, tool), PAUSE]
        return _ask(enclosing, text, cause_key(ErrorKind.PROJECT_ENV, enclosing, subject), options)
    return _nowhere(tool, said, enclosing, subject)


def _nowhere(tool: str, said: str, enclosing: StepKind, subject: str) -> StepResult:
    """No runtime here has it: a plan, build or review has a setup problem for repair (#1066).

    A brief challenge's step back becomes its round's finding (``steps.brief_round``); the brief changes in chat.
    """
    reason = f"needs {said}, which no runtime here provides"
    cause = cause_key(ErrorKind.SCOPE, enclosing, subject)
    if enclosing in {StepKind.PLAN, StepKind.BUILD, StepKind.REVIEW}:
        return setup(cause, f"the {enclosing} {reason}")
    if enclosing == StepKind.SHAPE:
        return StepResult(exit=Exit.BACK, back_to=StepKind.SHAPE, cause=cause, reason=reason, operational=True)
    return _ask(enclosing, f"The step {reason}.", cause, [*_without(enclosing, tool), PAUSE])
