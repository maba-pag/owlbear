"""The browser gate of a PDS update (#777): delivery-next's browser tests run on a worktree, in their own process.

The candidate's code comes first on the import path, so its pages and served PDS files are the ones tested. A pass
needs tests that ran, none failed or errored, not all skipped, and a clean exit: anything else is a failure or a stop.
A test that fails on the candidate is run again on the base; failing there too, it is not the update's to fix. Passing
there, it runs once more on the candidate: passing on both, it is a flake the gate names and lets pass
(D-01M6BFK5YF5GYYN7QCDDPBEZH2).
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

TESTS = "serve/delivery-next/tests"
SOURCE = "serve/delivery-next/src"
REPORT = "browser-junit.xml"
CDN = "PDS CDN fetch of"  # the tests' own words when the PDS CDN did not answer (tests/conftest.py)
SECONDS = 1800
SUMMARY = re.compile(r"^(?:FAILED|ERROR) (\S+)", re.MULTILINE)
TRUST = ("NODE_EXTRA_CA_CERTS", "SSL_CERT_FILE", "SSL_CERT_DIR")  # a proxy intercepting TLS needs its CA
PROXY = tuple(n for v in ("HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY") for n in (v, v.lower()))
KEPT = ("PATH", "LANG", "LC_ALL", "TMPDIR", "PLAYWRIGHT_BROWSERS_PATH", *TRUST, *PROXY)  # the rest stays out
type Runner = Callable[..., subprocess.CompletedProcess[str]]


class Unrunnable(Exception):  # noqa: N818 - says why the gate cannot run, never a page failure
    """The browser tests cannot run here: no browsers, a CDN that did not answer, or no report."""


@dataclass(frozen=True)
class Result:
    """One run: tests counted, failing node ids, the exit code, the output's tail and what each failure said."""

    tests: int
    failures: int
    errors: int
    skipped: int
    failed: tuple[str, ...]
    code: int
    output: str
    told: str = ""  # each failing case's message and traceback from the report, never the output's warnings
    flaked: tuple[str, ...] = ()  # tests that failed, then passed on a rerun on the candidate and on main

    @property
    def passed(self) -> bool:
        """Tests ran, none failed or errored, not all were skipped, and the process exited cleanly."""
        bad = self.failures or self.errors or self.failed
        return self.code == 0 and self.tests > self.skipped and not bad

    def said(self) -> str:
        """The run in a line."""
        ran = self.tests - self.skipped
        said = f"{ran} browser test(s) ran, {self.failures} failed, {self.errors} errored, {self.skipped} skipped"
        if self.flaked:
            said += f"; passed on a rerun on the candidate and on main: {', '.join(self.flaked)}"
        return said

    def flake(self) -> Result:
        """This run, its failures having passed a rerun on the candidate and on main: a pass that names them."""
        return replace(self, failures=0, errors=0, failed=(), code=0, flaked=self.failed)


def browsers() -> Path:
    """Where Playwright's browsers are installed for this user."""
    if found := os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
        return Path(found)
    return Path.home() / ("Library/Caches" if sys.platform == "darwin" else ".cache") / "ms-playwright"


def run(at: Path, ids: tuple[str, ...] = (), *, runner: Runner = subprocess.run) -> Result:
    """The browser tests, or only *ids*, on the worktree *at*, with its code first on the import path.

    Raises:
        Unrunnable: Playwright's browsers are missing, the PDS CDN did not answer, or the run left no report.
    """
    where = browsers()
    if not any(where.glob("chromium*")):
        msg = (f"Playwright's browsers are not installed at {where}, so the browser tests cannot run; install them "
               "with `uv run playwright install chromium` and run the update again")  # fmt: skip
        raise Unrunnable(msg)
    report = at / ".pds" / REPORT
    report.parent.mkdir(parents=True, exist_ok=True)
    report.unlink(missing_ok=True)
    env = {k: os.environ[k] for k in KEPT if k in os.environ} | {
        "HOME": str(Path.home()), "PYTHONPATH": str(at / SOURCE), "PLAYWRIGHT_BROWSERS_PATH": str(where),
    }  # fmt: skip
    args = [sys.executable, "-m", "pytest", *(ids or (TESTS,)), "-m", "browser", f"--junitxml={report}", "-q",
            "-rfE", "--color=no", "-p", "no:cacheprovider"]  # fmt: skip
    try:
        done = runner(args, cwd=at, env=env, capture_output=True, text=True, timeout=SECONDS, check=False)
    except subprocess.TimeoutExpired as exc:
        msg = f"the browser tests did not finish in {SECONDS} s"
        raise Unrunnable(msg) from exc
    output = f"{done.stdout or ''}\n{done.stderr or ''}"
    if CDN in output:
        line = next(x for x in output.splitlines() if CDN in x)
        msg = f"the PDS CDN did not answer, so the browser tests prove nothing: {line.strip()[:300]}"
        raise Unrunnable(msg)
    return _read(report, done.returncode, output)


def _read(report: Path, code: int, output: str) -> Result:
    try:
        root = ET.parse(report).getroot()  # noqa: S314 - the run's own report
    except (OSError, ET.ParseError) as exc:
        tail = output.strip()[-600:]
        msg = f"the browser tests left no report (exit {code}): {exc}; {tail}"
        raise Unrunnable(msg[:1200]) from exc
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    count = {k: sum(int(s.get(k, "0")) for s in suites) for k in ("tests", "failures", "errors", "skipped")}
    failed = tuple(dict.fromkeys(SUMMARY.findall(output)))
    return Result(**count, failed=failed, code=code, output=output.strip()[-4000:], told=_told(root))


def _told(root: ET.Element) -> str:
    """What the report says of each failing or erroring case, each cut to its last lines."""
    said = []
    for case in root.iter("testcase"):
        for bad in (*case.iter("failure"), *case.iter("error")):
            text = f"{bad.get('message', '')}\n{(bad.text or '').strip()}".strip()
            said.append(f"{case.get('classname', '')}::{case.get('name', '')}\n{text[-1500:]}")
    return "\n\n".join(said)[:6000]
