"""Visual check: render the brief's page states in headless Chromium and judge the screenshots (B23, B24).

UI detection reads paths only: markup rendered from plain JS/TS modules outside the UI directories is not
seen here; the brief's ``ui`` flag covers that residual.
"""

from __future__ import annotations

import dataclasses
import hashlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.failures import cause_key
from owlbear_delivery_next.change_contracts.models import VISUAL, Decision, ErrorKind, Exit, Option, StepKind
from owlbear_delivery_next.change_contracts.visual_records import PageError, VisualResult
from owlbear_delivery_next.change_flow import worktree
from owlbear_delivery_next.change_flow.loop import StepResult
from owlbear_delivery_next.workflow_steps import browse, check, decision, design, engine
from owlbear_delivery_next.workflow_steps.browse import root

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from datetime import datetime

    from owlbear_delivery_next.change_contracts import tools
    from owlbear_delivery_next.change_contracts.models import Change, VisualState
    from owlbear_delivery_next.change_contracts.visual_records import DetectorScan, VisualRound
    from owlbear_delivery_next.design_packs.design_pack import Installed

UI_SUFFIXES = frozenset(
    {".html", ".htm", ".css", ".scss", ".sass", ".less", ".tsx", ".jsx", ".vue", ".svelte", ".astro"}
    | {".hbs", ".handlebars", ".ejs", ".njk", ".twig", ".erb", ".jinja", ".jinja2", ".j2", ".liquid"}
    | {".mdx", ".svg"}
)
UI_DIRS = frozenset({"components", "pages", "views", "templates", "layouts", "styles", "static", "public"})
HEIGHT = 800  # px of each desktop viewport; the widths come from the settings (TD-49, R7)
MAX_HEIGHT = 6000  # px per capture; the width is the viewport's
MAX_BYTES = 12 * 2**20  # screenshot bytes attached to one review
MAX_SHOTS = 24  # images one agent-host message was measured to take within MAX_BYTES (item 9)
SETTLE_MS = 15_000
INSTALL = "uv run playwright install chromium"
CHANNELS = ("chrome", "msedge", None)  # the installed browser first; None is Playwright's own Chromium
MISSING = ("playwright install", "Executable doesn't exist", "is not found at")  # Playwright's launch errors
FILE = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}-\d{3,4}\.png$")
NOT_UI = "not-ui"
_SHOWN = 5
_HTTP_ERROR = 400


class BrowserMissingError(RuntimeError):
    """Neither Chrome, Edge nor Playwright's Chromium is available."""


@dataclass(frozen=True)
class Shot:
    """One state rendered at one viewport width: a screenshot file, or the error that prevented it."""

    state: str
    width: int
    file: str = ""
    error: str = ""
    errors: tuple[PageError, ...] = ()  # console and page errors seen from navigation to the screenshot
    design: DetectorScan | None = None  # the design detector's evidence on the screenshot's page (TD-77)


type Capturer = Callable[..., list[Shot]]


def capture(  # noqa: C901, PLR0913 - one finding per failure of the nested shot; the pack is optional
    base: str,
    states: Sequence[VisualState],
    out: Path,
    widths: Sequence[int],
    timeout_ms: int = SETTLE_MS,
    *,
    pack: Installed | None = None,
) -> list[Shot]:
    """Render every state at each width, full page after network idle; an unanswered URL is a failed shot.

    With a design pack, each screenshot's page is then scanned by the design detector (``design.rendered``).

    Raises:
        BrowserMissingError: no installed Chrome or Edge, and Playwright's Chromium is not installed.
    """
    from playwright.sync_api import Error, sync_playwright  # noqa: PLC0415 - optional browser runtime

    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser, missing = None, ""
        for channel in CHANNELS:
            try:
                browser = pw.chromium.launch(headless=True, channel=channel)
                break
            except Error as exc:
                if not any(m in str(exc) for m in MISSING):
                    raise
                missing = str(exc)
        if browser is None:
            raise BrowserMissingError(missing)
        engine_browser = pw.chromium.executable_path if Path(pw.chromium.executable_path).is_file() else ""

        def shot(s: VisualState, width: int, height: int) -> Shot:
            page, origin, left = browser.new_page(viewport={"width": width, "height": height}), root(base), []
            seen: list[PageError] = []

            def away() -> Shot | None:
                gone = left[0] if left else root(page.url) if root(page.url) != origin else ""
                return Shot(s.name, width, error=f"state {s.name} left the preview ({gone})") if gone else None

            def rendered() -> Shot:
                try:
                    response = page.goto(base + s.path, wait_until="networkidle", timeout=timeout_ms)
                    if failed := away():
                        return failed
                    if response is None or response.status >= _HTTP_ERROR:
                        answered = response.status if response else "nothing"
                        return Shot(s.name, width, error=f"{s.path} answered {answered}")
                    if why := browse.steps(page, s, timeout_ms):
                        return away() or Shot(s.name, width, error=why)
                    tall = page.evaluate("() => document.documentElement.scrollHeight")
                    if tall > MAX_HEIGHT:
                        return Shot(
                            s.name, width, error=f"state {s.name} is {tall}px tall, over the {MAX_HEIGHT}px cap"
                        )
                    name, clip = f"{s.name}-{width}.png", {"x": 0, "y": 0, "width": width, "height": max(tall, height)}
                    page.screenshot(path=str(out / name), full_page=True, clip=clip, timeout=timeout_ms)
                except Error as exc:
                    first = str(exc).splitlines()[0][:200]
                    return away() or Shot(s.name, width, error=f"{s.path} did not answer: {first}")
                return away() or Shot(s.name, width, file=name)

            browse.listen(page, s, width, seen)  # before navigation, so load-time errors count
            browse.confine(page, origin, left, stepped=bool(s.steps))  # before navigation, like the listeners
            try:
                result = dataclasses.replace(rendered(), errors=tuple(seen))  # what was seen up to the screenshot
                if result.file:  # after the errors are taken: the scan's own refusals are not the page's
                    scan = design.rendered(
                        page, pack, s, width=width, url=base + s.path, browser=engine_browser, cwd=out
                    )
                    result = dataclasses.replace(result, design=scan)
                return result
            finally:
                page.close()

        try:
            return [shot(s, w, HEIGHT) for s in states for w in widths]
        finally:
            browser.close()


CAPTURE: Capturer = capture


def oversize(out: Path, shots: Sequence[Shot]) -> list[Shot]:
    """A screenshot larger than one review takes becomes a finding naming its state; the rest are judged in batches."""
    cap = f"over the {MAX_BYTES // 2**20} MB one review takes"
    return [
        dataclasses.replace(s, file="", error=f"state {s.state} at {s.width}px is {cap}")
        if s.file and (out / s.file).stat().st_size > MAX_BYTES
        else s
        for s in shots
    ]


def classify(errors: Sequence[PageError], before: VisualResult | None) -> tuple[list[PageError], list[PageError]]:
    """New and existing errors: existing only if a good before shot of that state version and width had it (R8).

    A missing or failed before shot is never a clean baseline, so its errors are all new.
    """

    def key(e: PageError) -> tuple[str, int, int, str, str]:
        return e.state, e.version, e.width, e.kind, e.text

    good = set(before.files) if before else set()
    seen = {key(e) for e in before.errors if f"{e.state}-{e.width}.png" in good} if before else set()
    new = [e for e in errors if key(e) not in seen]
    return new, [e for e in errors if key(e) in seen]


def tree(path: Path, head: str) -> str:
    """The tree of *head*: a visual result holds for exactly this content."""
    return worktree.git(path, "rev-parse", f"{head}^{{tree}}").strip()


def is_ui(path: str) -> bool:
    """A path with a UI suffix or under a UI directory."""
    p = Path(path.lower())
    return p.suffix in UI_SUFFIXES or any(part in UI_DIRS for part in p.parts[:-1])


def ui_paths(c: Change, head: str) -> list[str]:
    """UI paths the Change's diff touches, both ends of a rename; an unreadable diff counts as UI (fail-closed)."""
    try:
        diff = [worktree.GIT, "diff", "--name-status", "-z", "-M", f"origin/{c.names.target}...{head}"]
        done = subprocess.run(diff, cwd=c.names.worktree, capture_output=True, check=True, timeout=60)  # noqa: S603
        fields = done.stdout.decode("utf-8").split("\0")  # bytes: no newline in a name is translated
    except subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError, UnicodeDecodeError:
        return ["(the diff could not be read)"]
    paths, i = set(), 0
    while i < len(fields) and fields[i]:  # a status, then one path, or two for a rename or copy
        n = 2 if fields[i][:1] in {"R", "C"} else 1
        paths.update(fields[i + 1 : i + 1 + n])
        i += 1 + n
    return sorted(p for p in paths if is_ui(p))


def digest(ui: Sequence[str]) -> str:
    """The identity of one sorted set of UI paths; NUL never occurs in a path, so no two sets share it."""
    return hashlib.sha256("\0".join(sorted(set(ui))).encode()).hexdigest()[:12]


def _cause(c: Change, ui: Sequence[str]) -> str:
    return cause_key(ErrorKind.GATE, StepKind.MERGE, f"visual-v{c.brief.version}-{digest(ui)}")


def not_ui(c: Change, ui: Sequence[str]) -> bool:
    """The owner decided this brief version is not a UI change for a set of UI paths holding every current one."""
    prefix = f"Not a UI change (brief v{c.brief.version},"
    return any(d.origin == "decided" and d.text.startswith(prefix) and set(ui) <= set(d.paths) for d in c.decisions)


def decide(c: Change, ui: Sequence[str], now: datetime) -> Change:
    """Record the owner's "Not a UI change" answer for this brief version and these UI paths, once."""
    cause = _cause(c, ui)
    if any(q.cause == cause and q.answer and q.answer.option == NOT_UI for q in c.questions) and not not_ui(c, ui):
        text = f"Not a UI change (brief v{c.brief.version}, UI paths {digest(ui)})"
        c.decisions.append(Decision(text=text, origin="decided", at=now, paths=sorted(set(ui))))
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
    return engine.ask(StepKind.MERGE, text, _cause(c, ui), options)


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
    c: Change,
    head: str,
    tree_id: str,
    shots: Sequence[Shot],
    *,
    verdict: tools.ReviewResult | None,
    now: datetime,
    scans: Sequence[DetectorScan] = (),
    kept: VisualRound | None = None,
) -> tuple[Change, StepResult]:
    """Record the visual result and end the round by the verdict matrix (``decision.route``; B23, TD-78).

    A failed shot, a new browser error or a correctness fail always goes back (R8). The detector's scans are recorded
    as evidence only (TD-77).
    """
    failed = [f"{s.state} at {s.width}px: {s.error}" for s in shots if s.error or not s.file]
    if not shots:
        failed.append("no screenshot was captured")
    errors = [e for s in shots for e in s.errors]
    new, _old = classify(errors, c.before)
    raised = [f"{e.state} at {e.width}px: new {e.kind} error: {e.text[:300]}" for e in new]
    found = [*failed, *raised]  # a failed shot does not hide the errors the others raised
    if not failed and verdict is not None and verdict.verdict == "fix":  # an unsure judge's findings are the owner's
        found += [f"{f.place}: {f.problem} - fix: {f.fix}" for f in verdict.findings]
        if not verdict.findings:
            found.append("the reviewer did not accept the screenshots")
    elif not failed and verdict is None:
        found.append("the screenshots were not judged")
    ends, sent = decision.route(kept, found, verdict, broken=bool(failed or raised))
    files = [s.file for s in shots if s.file]
    states, criteria = {s.name: s.version for s in c.brief.visual}, {k.id: k.version for k in c.brief.criteria}
    c.visual = VisualResult(
        head=head, tree=tree_id, states=states, criteria=criteria, files=files, passed=ends == "merge",
        findings=sent, errors=errors, doubts=decision.doubts(ends, verdict, kept), design=list(scans), at=now,
    )  # fmt: skip
    if kept is not None and ends != "again":
        kept.outcome = ends
    if ends == "model" and kept is not None:  # TD-94: the owner accepts the whole round or runs it again
        return c, decision.unknown(head, kept)
    if ends == "merge":
        reason = f"visual check of {head[:7]} passed: {len(files)} screenshots"
        return c, StepResult(exit=Exit.DONE, reason=reason, paths=check.declared(c))
    if ends == "again":
        return c, decision.again(kept)
    if ends == "ask" and kept is not None:  # nothing is definitely wrong, or the setting asks: the owner decides
        return c, decision.ask(head, kept)
    shot = next((s for s in shots if s.error), None) or next((s for s in shots if s.file), None)
    named = f" (see {shot.file or f'{shot.state} at {shot.width}px'})" if shot else ""
    lines = sent or found or ["the screenshots were not judged"]
    return c, decision.repair(c, f"Fix: the visual check of {head[:7]} failed: {lines[0][:200]}{named}", lines)
