"""The design detector in the visual check (TD-77, design skill research §3.5 slice 4): evidence, never a fail.

Each state is scanned in the page Delivery rendered, after its screenshot. Where the page's Content-Security-Policy
refuses the detector, a state without steps is scanned by the engine's own browser at its address; a state with
steps is reached only in Delivery's page, so it is recorded as not scanned. The Change's UI sources are scanned in
its worktree, and the same paths in the "before" capture's checkout of the merge-base. Each finding is new,
existing or unknown against "before".
"""

from __future__ import annotations

import contextlib
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any

import psutil

from owlbear_delivery_next import design_pack, detector, tools
from owlbear_delivery_next.visual_records import DetectorFinding, DetectorScan

if TYPE_CHECKING:
    from collections.abc import Sequence

    from owlbear_delivery_next.design_pack import Installed
    from owlbear_delivery_next.design_tools import ScanDesign
    from owlbear_delivery_next.models import VisualState
    from owlbear_delivery_next.visual_records import Freshness, VisualResult

SOURCES = frozenset(  # the UI files the engine reads (its SCANNABLE_EXTENSIONS)
    {".html", ".htm", ".css", ".scss", ".sass", ".less", ".jsx", ".tsx", ".js", ".ts", ".vue", ".svelte", ".astro"}
)
SOURCE_STATE = "sources"
NO_PACK = "not scanned: the design pack is not installed (owlbear-next design-pack --install)"
DETAIL = 300
SHOWN = 60  # findings one scan_design reply lists
PAGE_SECONDS = detector.PAGE_MS / 1000 + 15  # the in-page timer, plus injecting the bundle


def pack() -> Installed | None:
    """The verified design pack on this machine, if installed."""
    return design_pack.installed()


def builder_scan(root: Path, args: ScanDesign) -> str:
    """The builder's scan (``scan_design``): its worktree's UI sources, offline; the findings as hints.

    No page scan: the engine's own browser is not guarded, so a page the builder made could reach outside.
    """
    installed, root = pack(), root.resolve()
    if installed is None:
        return "The design detector is not installed on this machine; go on without it."
    errors = [
        f"paths: {p} is not a UI file of the worktree"
        for p in args.paths
        if not (tools.relative(p) and Path(p).suffix.lower() in SOURCES and _inside(root, p))
    ]
    if errors or not args.paths:
        lines = [f"- {e}" for e in errors or ["paths: name the UI files to scan"]]
        return "Rejected. Fix each field, then call again:\n" + "\n".join(lines)
    try:
        found = detector.scan_source(installed, [root / p for p in args.paths], root)
    except detector.DetectorError as exc:
        return f"The design detector failed ({exc}); go on without it."
    lines = [f"- {f.rule} at {f.where.removeprefix(f'{root}/')}: {f.detail or f.name}" for f in found]
    head = f"{len(lines)} design detector findings (hints to weigh, never a verdict):"
    return "\n".join([head, *lines[:SHOWN]]) if lines else "No design detector findings."


def _inside(root: Path, path: str) -> bool:
    target = (root / path).resolve()
    return target.is_relative_to(root) and target.is_file()


def _kept(findings: Sequence[detector.Finding], root: Path | None = None) -> list[DetectorFinding]:
    return [
        DetectorFinding(
            rule=f.rule,
            category=f.category,
            advisory=f.advisory,
            where=f.where.removeprefix(f"{root}/") if root else f.where,
            detail=(f.detail or f.name)[:DETAIL],
        )
        for f in findings
    ]


def rendered(  # noqa: PLR0913 - one rendered state and where else to reach it
    page: Any,  # noqa: ANN401 - a Playwright page
    pack: Installed | None,
    state: VisualState,
    *,
    width: int,
    url: str,
    browser: str,
    cwd: Path,
) -> DetectorScan:
    """Scan one state Delivery rendered, after its screenshot; a refused state without steps by the engine."""
    if pack is None:
        return DetectorScan(state=state.name, width=width, kind="page", scanned=False, reason=NO_PACK)
    try:
        found = _in_page(page, pack)
    except detector.DetectorError as exc:
        refused = str(exc)
    else:
        return DetectorScan(state=state.name, width=width, kind="page", scanned=True, findings=_kept(found))
    if state.steps:
        reason = f"not scanned: {refused}; a state with steps is reached only in Delivery's page"
        return DetectorScan(state=state.name, width=width, kind="page", scanned=False, reason=reason[:DETAIL])
    try:
        found = detector.scan_url(pack, url, width, browser, cwd)
    except detector.DetectorError as exc:
        reason = f"not scanned: {refused}; the engine's own browser: {exc}"
        return DetectorScan(state=state.name, width=width, kind="url", scanned=False, reason=reason[:DETAIL])
    return DetectorScan(state=state.name, width=width, kind="url", scanned=True, findings=_kept(found))


def _in_page(page: Any, pack: Installed) -> list[detector.Finding]:  # noqa: ANN401 - a Playwright page
    """The in-page scan under a deadline the page cannot hold up: past it, the page's renderer is ended.

    The watchdog is joined before returning, so it never reaches into the next shot.
    """
    done = threading.Event()
    watchdog = threading.Thread(target=lambda: done.wait(PAGE_SECONDS) or _end_renderers(), daemon=True)
    watchdog.start()
    try:
        return detector.scan_page(page, pack)  # a crashed page is a refused scan
    finally:
        done.set()
        watchdog.join()


def _end_renderers() -> None:
    """End this runner's browser renderers; one capture page is open at a time, the one whose scan hangs."""
    for p in psutil.Process().children(recursive=True):
        with contextlib.suppress(psutil.Error):
            if "--type=renderer" in p.cmdline():
                p.kill()


def sources(root: Path, paths: Sequence[str], pack: Installed | None) -> DetectorScan | None:
    """The UI sources among *paths* in the tree at *root*; ``covered`` names each path asked about, present or not."""
    root = root.resolve()
    asked = sorted({p for p in paths if Path(p).suffix.lower() in SOURCES})
    if not asked:
        return None
    if pack is None:
        return DetectorScan(state=SOURCE_STATE, kind="source", scanned=False, reason=NO_PACK)
    try:
        files = [root / p for p in asked if (root / p).is_file()]
        found = detector.scan_source(pack, files, root) if files else []
    except (detector.DetectorError, OSError) as exc:
        return DetectorScan(state=SOURCE_STATE, kind="source", scanned=False, reason=str(exc)[:DETAIL])
    return DetectorScan(state=SOURCE_STATE, kind="source", scanned=True, covered=asked, findings=_kept(found, root))


def marked(scans: Sequence[DetectorScan], before: VisualResult | None, states: dict[str, int]) -> list[DetectorScan]:
    """Mark each finding new or existing against the same kind of scan in "before", else unknown.

    A rendered state compares only at the same state version and width, by rule and element; a source finding by
    rule and file, for a file "before" asked about.
    """
    seen: dict[tuple[str, int | None], DetectorScan] = {}
    for s in before.design if before else []:
        if s.scanned and before and (s.kind == "source" or before.states.get(s.state) == states.get(s.state)):
            seen[s.state, s.width] = s

    def fresh(s: DetectorScan, f: DetectorFinding) -> Freshness:
        old = seen.get((s.state, s.width))
        if old is None or old.kind != s.kind or (s.kind == "source" and _file(f) not in old.covered):
            return "unknown"
        return "existing" if _key(s, f) in {_key(old, g) for g in old.findings} else "new"

    return [
        s.model_copy(update={"findings": [f.model_copy(update={"freshness": fresh(s, f)}) for f in s.findings]})
        for s in scans
    ]


def _file(f: DetectorFinding) -> str:
    head, _, line = f.where.rpartition(":")
    return head if head and line.isdigit() else f.where


def _key(s: DetectorScan, f: DetectorFinding) -> tuple[str, str]:
    return f.rule, _file(f) if s.kind == "source" else f.where
