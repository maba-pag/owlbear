"""Impeccable's design detector, run by Delivery (TD-77): its findings are evidence for the judges, never a fail.

Three scans: source files through the engine, a URL through the engine's own headless browser, and a page Delivery
already rendered through the in-page detector, which also reaches states that need clicks or typing.
"""

from __future__ import annotations

import contextlib
import json
import os
import signal
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.design_pack import PackError

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from owlbear_delivery_next.design_pack import Installed

QUIET = {"IMPECCABLE_NO_UPDATE_CHECK": "1", "IMPECCABLE_NO_TELEMETRY": "1", "DO_NOT_TRACK": "1"}
SECONDS = 120.0  # one engine scan
PAGE_MS = 60_000  # one in-page scan; evaluate itself has no timeout
PAGE = (
    "async ms => await Promise.race([window.impeccableDetectAsync(),"
    " new Promise((_, no) => setTimeout(() => no(new Error(`no answer within ${ms} ms`)), ms))])"
)


class DetectorError(RuntimeError):
    """The scan did not complete: the engine failed, timed out or answered unreadably, or the page refused it."""


@dataclass(frozen=True)
class Finding:
    """One detector finding: its rule, the rule's category, and where it was found."""

    rule: str
    category: str
    advisory: bool
    name: str
    where: str  # file and line, or the element's CSS selector
    detail: str


def _from_engine(raw: dict[str, Any], *, by_file: bool) -> Finding:
    line = raw.get("line") or 0
    at = f"{raw.get('file', '')}:{line}" if line else str(raw.get("file", ""))
    return Finding(
        rule=str(raw.get("antipattern", "")),
        category=str(raw.get("category", "")),
        advisory=raw.get("severity") == "advisory",
        name=str(raw.get("name", "")),
        where=at if by_file else str(raw.get("selector") or at),
        detail=str(raw.get("snippet", "")),
    )


def _run(command: list[str], cwd: Path, env: dict[str, str]) -> tuple[int, str, str]:
    """Run the engine in its own process group; on timeout the whole group ends, a browser it started included."""
    try:
        proc = subprocess.Popen(  # noqa: S603 - the pack's engine, verified just before
            command, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True
        )
    except OSError as exc:
        msg = f"the design detector did not start: {exc}"
        raise DetectorError(msg) from exc
    try:
        out, err = proc.communicate(timeout=SECONDS)
    except subprocess.TimeoutExpired as exc:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        msg = f"the design detector did not finish within {SECONDS:.0f} s"
        raise DetectorError(msg) from exc
    return proc.returncode, out, err


def _engine(
    pack: Installed, args: Sequence[str], cwd: Path, browser: str | None = None, *, by_file: bool = False
) -> list[Finding]:
    env = os.environ | QUIET | ({"IMPECCABLE_BROWSER": browser} if browser else {})
    try:
        engine = pack.verified_engine()
    except (PackError, OSError) as exc:  # a changed, missing or unreadable engine is never run
        msg = f"the design detector cannot be verified: {exc}"
        raise DetectorError(msg) from exc
    code, out, err = _run([str(engine), "detect", "--json", "--no-config", *args], cwd, env)
    if code not in {0, 2}:  # 2 means findings; anything else, a target was not scanned
        msg = f"the design detector failed ({code}): {err.strip()[-300:]}"
        raise DetectorError(msg)
    try:
        raw = json.loads(out)
    except ValueError as exc:
        msg = "the design detector's answer is not JSON"
        raise DetectorError(msg) from exc
    if not isinstance(raw, list) or not all(isinstance(f, dict) for f in raw):
        msg = "the design detector's answer is not a list of findings"
        raise DetectorError(msg)
    return [_from_engine(f, by_file=by_file) for f in raw]


def scan_source(pack: Installed, paths: Sequence[Path], cwd: Path) -> list[Finding]:
    """The detector's rules over UI source files (HTML, CSS, JSX, TSX, Vue, Svelte), offline; found by file."""
    if relative := [p for p in paths if not p.is_absolute()]:
        msg = f"source scans take absolute paths, not {relative[0]}"
        raise DetectorError(msg)
    return _engine(pack, [str(p) for p in paths], cwd, by_file=True) if paths else []


def scan_url(pack: Installed, url: str, width: int, browser: str, cwd: Path) -> list[Finding]:
    """The detector over a page the engine opens itself, headless, at one width (height 800, R7)."""
    if not url.startswith(("http://", "https://")):  # anything else would be read as an option or a path
        msg = f"not a web address: {url[:80]}"
        raise DetectorError(msg)
    return _engine(pack, ["--viewport", f"{width}x800", url], cwd, browser)


def scan_page(page: Any, pack: Installed) -> list[Finding]:  # noqa: ANN401 - a Playwright page
    """The detector inside a page Delivery rendered: call it after the screenshot, which it leaves unchanged.

    A page whose Content-Security-Policy forbids WebAssembly refuses it.
    """
    try:
        page.evaluate("window.__IMPECCABLE_CONFIG__ = {autoScan: false}")  # no overlay
        page.add_script_tag(content=pack.bundle)  # the verified text, not a path that could change
        groups = page.evaluate(PAGE, PAGE_MS)
    except Exception as exc:  # Playwright's own errors: the page refused the detector
        msg = f"the page refused the design detector: {str(exc)[:300]}"
        raise DetectorError(msg) from exc
    shaped = isinstance(groups, list) and all(
        isinstance(g, dict)
        and isinstance(g.get("findings", []), list)
        and all(isinstance(f, dict) for f in g.get("findings", []))
        for g in groups
    )
    if not shaped:
        msg = "the in-page detector's answer is not a list of findings by element"
        raise DetectorError(msg)
    return [
        Finding(
            rule=str(f.get("type", "")),
            category=str(f.get("category", "")),
            advisory=bool(f.get("advisory")),
            name=str(f.get("name", "")),
            where=str(group.get("selector", "")),
            detail=str(f.get("detail", "")),
        )
        for group in groups
        for f in group.get("findings", [])
    ]
