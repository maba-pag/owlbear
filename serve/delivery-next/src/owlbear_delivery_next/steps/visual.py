"""Visual check: render the brief's page states in headless Chromium and judge the screenshots (B23, B24)."""

from __future__ import annotations

import base64
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from owlbear_delivery_next.loop import StepResult, cause_key
from owlbear_delivery_next.models import VISUAL, Decision, ErrorKind, Exit, Option, StepKind, VisualResult
from owlbear_delivery_next.steps import check, engine, review, worktree

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from datetime import datetime

    from owlbear_delivery_next import tools
    from owlbear_delivery_next.models import Change, VisualState

UI_SUFFIXES = frozenset(
    {".html", ".htm", ".css", ".scss", ".sass", ".less", ".tsx", ".jsx", ".vue", ".svelte", ".astro"}
)
VIEWPORTS = ((1280, 800), (390, 844))
SETTLE_MS = 15_000
INSTALL = "uv run playwright install chromium"
FILE = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}-\d{3,4}\.png$")
NOT_UI = "not-ui"
_SHOWN = 5
_HTTP_ERROR = 400


class BrowserMissingError(RuntimeError):
    """Chromium for Playwright is not installed."""


@dataclass(frozen=True)
class Shot:
    """One state rendered at one viewport width: a screenshot file, or the error that prevented it."""

    state: str
    width: int
    file: str = ""
    error: str = ""


type Capturer = Callable[[str, Sequence[VisualState], Path], list[Shot]]


def capture(base: str, states: Sequence[VisualState], out: Path, timeout_ms: int = SETTLE_MS) -> list[Shot]:
    """Render every state at each viewport, full page after network idle; an unanswered URL is a failed shot.

    Raises:
        BrowserMissingError: Playwright's Chromium is not installed.
    """
    from playwright.sync_api import Error, sync_playwright  # noqa: PLC0415 - optional browser runtime

    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(headless=True)
        except Error as exc:
            if "playwright install" in str(exc) or "Executable doesn't exist" in str(exc):
                raise BrowserMissingError(str(exc)) from exc
            raise

        def shot(s: VisualState, width: int, height: int) -> Shot:
            page = browser.new_page(viewport={"width": width, "height": height})
            try:
                response = page.goto(base + s.path, wait_until="networkidle", timeout=timeout_ms)
                if response is None or response.status >= _HTTP_ERROR:
                    return Shot(s.name, width, error=f"{s.path} answered {response.status if response else 'nothing'}")
                name = f"{s.name}-{width}.png"
                page.screenshot(path=str(out / name), full_page=True, timeout=timeout_ms)
            except Error as exc:
                return Shot(s.name, width, error=f"{s.path} did not answer: {str(exc).splitlines()[0][:200]}")
            finally:
                page.close()
            return Shot(s.name, width, file=name)

        try:
            return [shot(s, w, h) for s in states for w, h in VIEWPORTS]
        finally:
            browser.close()


CAPTURE: Capturer = capture


def root(ready_url: str) -> str:
    """The preview root (scheme and host) under which every state's path is opened."""
    parts = urlsplit(ready_url)
    return f"{parts.scheme}://{parts.netloc}"


def tree(path: Path, head: str) -> str:
    """The tree of *head*: a visual result holds for exactly this content."""
    return worktree.git(path, "rev-parse", f"{head}^{{tree}}").strip()


def ui_paths(c: Change, head: str) -> list[str]:
    """Paths with a UI suffix the Change's diff touches; an unreadable diff counts as UI (fail-closed)."""
    try:
        out = worktree.git(Path(c.names.worktree), "diff", "--name-only", f"origin/{c.names.target}...{head}")
    except subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError:
        return ["(the diff could not be read)"]
    return [p for p in out.splitlines() if any(p.lower().endswith(s) for s in UI_SUFFIXES)]


def _cause(c: Change) -> str:
    return cause_key(ErrorKind.GATE, StepKind.MERGE, f"visual-v{c.brief.version}")


def _decision(c: Change) -> str:
    return f"Not a UI change (brief v{c.brief.version})"


def not_ui(c: Change) -> bool:
    """The owner decided this brief version is not a UI change."""
    return any(d.text == _decision(c) and d.origin == "decided" for d in c.decisions)


def decide(c: Change, now: datetime) -> Change:
    """Record the owner's "Not a UI change" answer for this brief version as a decided Decision, once."""
    cause = _cause(c)
    if any(q.cause == cause and q.answer and q.answer.option == NOT_UI for q in c.questions) and not not_ui(c):
        c.decisions.append(Decision(text=_decision(c), origin="decided", at=now))
    return c


def held(c: Change, head: str, ui: Sequence[str]) -> StepResult:
    """Why the merge waits on the visual check: capture again, or ask once whether this is a UI change."""
    if c.brief.visual:
        reason = f"no passed visual check of {head[:7]} for the current states"
        return StepResult(
            exit=Exit.BACK,
            back_to=StepKind.FOLLOW,
            cause=cause_key(ErrorKind.GATE, StepKind.MERGE, VISUAL),
            reason=reason,
        )
    shown = ", ".join(ui[:_SHOWN]) or "the brief marks it as UI"
    options = [
        Option(id="brief", label="Revise the brief", next=StepKind.SHAPE),
        Option(id=NOT_UI, label="Not a UI change", next=StepKind.MERGE),
        Option(id="pause", label="Pause", next="pause"),
    ]
    text = f"This Change touches UI files ({shown}) but its brief has no visual check"
    return engine.ask(StepKind.MERGE, text, _cause(c), options)


def attachments(out: Path, shots: Sequence[Shot]) -> tuple[dict[str, str], ...]:
    """Each screenshot as a base64 PNG blob attachment for the reviewer session."""
    return tuple(
        {"type": "blob", "data": base64.b64encode((out / s.file).read_bytes()).decode(), "mimeType": "image/png"}
        | {"displayName": s.file}
        for s in shots
        if s.file
    )


def missing_browser(reason: str) -> StepResult:
    """B24: the owner installs Chromium; the check never passes without it."""
    text = f"The visual check needs Chromium for Playwright; run `{INSTALL}`, then continue ({reason[:200]})"
    return engine.ask(
        StepKind.CHECK,
        text,
        cause_key(ErrorKind.PROJECT_ENV, StepKind.CHECK, VISUAL),
        [
            Option(id="done", label="Installed, continue", next=StepKind.CHECK),
            Option(id="pause", label="Pause", next="pause"),
        ],
    )


def broken(reason: str) -> StepResult:
    """The capture itself failed: never a pass; the check is prepared and captured again within its budget."""
    return StepResult(
        exit=Exit.RETRY,
        cause=cause_key(ErrorKind.PROJECT_ENV, StepKind.CHECK, VISUAL),
        reason=f"capture failed: {reason}",
    )


def judged(  # noqa: PLR0913 - one result from every visual input
    c: Change, head: str, tree_id: str, shots: Sequence[Shot], *, verdict: tools.ReviewResult | None, now: datetime
) -> tuple[Change, StepResult]:
    """Record the visual result; a pass moves on, a failed shot or a fix verdict becomes a repair task (B23)."""
    found = [f"{s.state} at {s.width}px: {s.error}" for s in shots if s.error or not s.file]
    if not shots:
        found.append("no screenshot was captured")
    if not found and verdict is not None:
        found = [f"{f.place}: {f.problem} - fix: {f.fix}" for f in verdict.findings]
        if verdict.verdict != "pass" and not found:
            found = ["the reviewer did not accept the screenshots"]
    elif not found:
        found = ["the screenshots were not judged"]
    passed = not found and verdict is not None and verdict.verdict == "pass"
    files = [s.file for s in shots if s.file]
    states = {s.name: s.version for s in c.brief.visual}
    c.visual = VisualResult(head=head, tree=tree_id, states=states, files=files, passed=passed, findings=found, at=now)
    if passed:
        reason = f"visual check of {head[:7]} passed: {len(files)} screenshots"
        return c, StepResult(exit=Exit.DONE, reason=reason, paths=check.declared(c))
    shot = next((s for s in shots if s.error), None) or next((s for s in shots if s.file), None)
    named = f" (see {shot.file or f'{shot.state} at {shot.width}px'})" if shot else ""
    title = f"Fix: the visual check of {head[:7]} failed: {found[0][:200]}{named}"
    detail = review.findings(verdict) if verdict and verdict.findings else "\n".join(f"- {f}" for f in found)[:4000]
    fix = engine.task(c, title, "review", detail)
    cause = cause_key(ErrorKind.CHECKS, StepKind.CHECK, VISUAL)
    return c, StepResult(exit=Exit.BACK, back_to=StepKind.BUILD, cause=cause, reason=title, fix_task=fix)
