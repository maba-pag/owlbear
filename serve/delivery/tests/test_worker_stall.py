# ruff: noqa: SLF001

from __future__ import annotations

import contextlib
import dataclasses
import itertools
import json
import os
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import psutil
import pytest
from pydantic import ValidationError
from serve.delivery.tests.test_portfolio_application import (
    _acquire_planning_claim,
    _builder_retry_history,
    _continuation_request,
    _finalization_request,
    _git,
    _policies,
    _portfolio,
    _requestless_builder_settlement,
    _task_result,
    _workspace_content_snapshot,
)

from owlbear_delivery import (
    CompletedHistoryCatalog,
    DeliveryActionSelectionConflictError,
    DeliveryBuilderInvocationSettlement,
    DeliveryPlanningRetrySettlement,
    DeliveryRuntimeConflictError,
    DeliveryStage,
    FinalizationReportError,
    FinalizerSettlementReceipt,
    PortfolioApplication,
    PortfolioApplicationConfig,
    PortfolioApplicationDependencies,
    PortfolioApplicationError,
    PortfolioApplicationHooks,
    PublishDeliveryResult,
    RetryDelivery,
    change_workspace,
)
from owlbear_delivery.delivery_runtime import DeliveryEngineBuilderSettlement, DeliveryEnginePlanningSettlement
from owlbear_delivery.diagnostics import DeliveryFailureCategory, classify_delivery_failure
from owlbear_delivery.finalization_reports import (
    FinalizationFailureCode,
    FinalizerEngineSettlement,
    ReportFinalizationFailure,
)
from owlbear_delivery.portfolio_application import DeliveryActionBusyError
from owlbear_delivery.recovery import RetryLedger
from owlbear_delivery.worker_stall import (
    DEFAULT_WORKER_QUIET_PERIOD,
    DeliveryWorkerActiveError,
    ObservedProcess,
    ProcessObservationError,
    ProcessTableWorktreeProbe,
    ProcessVanishedError,
    ProcessWindowLivenessProbe,
    WindowHostIdentity,
    WorktreeProcessScanError,
    psutil_process,
)

_WINDOW = WindowHostIdentity(pid=4242, create_time=1_700_000_000.5, name="Code Helper (Plugin)")
_HOST = _WINDOW.pid
_QUIET = timedelta(seconds=30)
_ISSUED = datetime(2026, 1, 1, tzinfo=UTC)


class _Probe:
    """Fake host environment: window liveness by pid and the worktree process table."""

    def __init__(self) -> None:
        self.states: dict[int, str] = {}
        self.processes: tuple[str, ...] = ()
        self.scan_fails = False
        self.scanned_roots: list[tuple[Path, ...]] = []
        self.issued_after: list[datetime | None] = []
        self.during_scan: Callable[[], None] | None = None

    def window_state(self, window: WindowHostIdentity) -> str:
        return self.states.get(window.pid, "alive")

    def active_processes(self, roots: tuple[Path, ...], *, issued_after: datetime | None) -> tuple[str, ...]:
        self.scanned_roots.append(roots)
        self.issued_after.append(issued_after)
        if self.during_scan is not None:
            self.during_scan()
        if self.scan_fails:
            message = "process table unavailable"
            raise WorktreeProcessScanError(message)
        return self.processes


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _real_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _stall_portfolio(
    tmp_path: Path,
    stages: dict[str, DeliveryStage],
    now: list[str],
    *,
    window: WindowHostIdentity | None = _WINDOW,
    capacity: int = 3,
):
    base, runtimes, coordinator, state_root = _portfolio(
        tmp_path, stages, execution_capacity=capacity, clock=lambda: now[0]
    )
    probe = _Probe()
    identities = (f"stall-{index:03}" for index in itertools.count(1))
    application = PortfolioApplication(
        dict(reversed(tuple(runtimes.items()))),
        PortfolioApplicationDependencies(
            target_root=state_root,
            package_store=base._package_store,
            authority_registry=base._authority_registry,
            coordinator=coordinator,
            workspace_manager=base._workspace_manager,
            completed_history_catalog=CompletedHistoryCatalog(state_root),
            issuer_window=window,
            window_liveness_probe=probe,
            worktree_process_probe=probe,
        ),
        PortfolioApplicationConfig(
            package_root=tmp_path / "packages",
            execution_capacity=capacity,
            role_policies=_policies(),
        ),
        PortfolioApplicationHooks(identity_factory=lambda: next(identities), clock=lambda: now[0]),
    )
    return application, runtimes, coordinator, state_root, probe


def _owner_failure_code(state_root: Path, change_id: str, attempt_id: str) -> str:
    path = state_root / "changes" / change_id / "retry-ledger/owner-results" / f"{attempt_id}.json"
    return json.loads(path.read_bytes())["failure_code"]


def _issuer_path(state_root: Path, change_id: str, attempt_id: str) -> Path:
    return state_root / "changes" / change_id / "claim-issuers" / f"{attempt_id}.json"


def _builder_with_workspace_changes(tmp_path: Path, now: list[str]):
    application, runtimes, coordinator, state_root, probe = _stall_portfolio(
        tmp_path, {"change-a": DeliveryStage.IMPLEMENTATION}, now, capacity=1
    )
    acquired = application.acquire_change_action(_continuation_request(application, "change-a"))
    assert acquired.launch is not None, acquired
    launch = acquired.launch
    worktree = launch.worktree_path
    (worktree / "committed.txt").write_text("committed Builder work\n", encoding="utf-8")
    _git(worktree, "add", "committed.txt")
    _git(worktree, "commit", "-m", "preserve Builder commit")
    branch_head = _git(worktree, "rev-parse", "HEAD")
    (worktree / "product.txt").write_text("staged Builder work\n", encoding="utf-8")
    _git(worktree, "add", "product.txt")
    (worktree / "product.txt").write_text("unstaged Builder work\n", encoding="utf-8")
    (worktree / "untracked.txt").write_text("untracked Builder work\n", encoding="utf-8")
    return application, runtimes["change-a"], coordinator, state_root, probe, launch, branch_head


_HIDDEN_ACTIVITY = ("ignored-file", "deleted-nested-untracked", "ignored-directory-entry", "deleted-ignored-entry")


def _hidden_activity(worktree: Path, scenario: str, touched: datetime) -> Path:
    """Create worktree activity that `git status --ignored=no` cannot attribute to a listed path."""
    (worktree / ".gitignore").write_text("*.log\nbuild/\n", encoding="utf-8")
    if scenario == "ignored-file":
        target = worktree / "debug.log"
        target.write_text("recent ignored output\n", encoding="utf-8")
    elif scenario == "ignored-directory-entry":
        target = worktree / "build"
        target.mkdir()
        (target / "artifact.bin").write_bytes(b"artifact")
    elif scenario == "deleted-ignored-entry":
        target = worktree / "build"
        target.mkdir()
        (target / "gone.txt").write_text("deleted\n", encoding="utf-8")
        (target / "gone.txt").unlink()
    else:
        target = worktree / "work" / "nested"
        target.mkdir(parents=True)
        (target / "keep.txt").write_text("kept\n", encoding="utf-8")
        (target / "gone.txt").write_text("deleted\n", encoding="utf-8")
        (target / "gone.txt").unlink()
    if scenario != "deleted-nested-untracked":
        _git(worktree, "check-ignore", "-q", str(target.relative_to(worktree)))
    os.utime(target, (touched.timestamp(), touched.timestamp()))
    return target


_IGNORED_CONTENT = {"__pycache__/x.pyc": b"cache", ".venv/lib/x": b"environment"}


def _add_ignored_content(worktree: Path) -> None:
    (worktree / ".gitignore").write_text("__pycache__/\n.venv/\n.ruff_cache/\n", encoding="utf-8")
    for relative, content in _IGNORED_CONTENT.items():
        target = worktree / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        _git(worktree, "check-ignore", "-q", relative)


def _churn_ignored_content(worktree: Path) -> None:
    (worktree / "__pycache__" / "x.pyc").write_bytes(b"rewritten cache")
    (worktree / "__pycache__" / "y.pyc").write_bytes(b"new cache")
    (worktree / ".ruff_cache").mkdir()
    (worktree / ".ruff_cache" / "state").write_bytes(b"lint cache")
    (worktree / ".venv" / "lib" / "x").unlink()


def _lookup(*rows: ObservedProcess, denied: frozenset[int] = frozenset()):
    table = {row.pid: row for row in rows}

    def lookup(pid: int) -> ObservedProcess | None:
        if pid in denied:
            message = "denied"
            raise ProcessObservationError(message)
        return table.get(pid)

    return lookup


@pytest.mark.parametrize(
    "wrappers", [(), ("uv",), ("python3.14", "uv", "-zsh"), ("Python", "env", "uvx", "bash", "sh")]
)
def test_window_identity_capture_skips_the_server_and_launcher_wrappers(wrappers: tuple[str, ...]) -> None:
    rows = [ObservedProcess(pid=900, parent_pid=800, create_time=9.0, name="owlbear-delivery-mcp")]
    for offset, name in enumerate(wrappers):
        rows.append(ObservedProcess(pid=800 - offset, parent_pid=799 - offset, create_time=8.0, name=name))
    window_pid = 800 - len(wrappers)
    rows.append(ObservedProcess(pid=window_pid, parent_pid=1, create_time=5.5, name="Code Helper (Plugin)"))

    assert WindowHostIdentity.capture(_lookup(*rows), pid=900) == WindowHostIdentity(
        pid=window_pid, create_time=5.5, name="Code Helper (Plugin)"
    )


@pytest.mark.parametrize("case", ["launchers-to-init", "parent-gone", "parent-denied", "server-unobservable"])
def test_window_identity_capture_returns_none_without_an_identifiable_window(case: str) -> None:
    server = ObservedProcess(pid=900, parent_pid=800, create_time=9.0, name="python3")
    rows = {
        "launchers-to-init": (server, ObservedProcess(pid=800, parent_pid=1, create_time=8.0, name="zsh")),
        "parent-gone": (server,),
        "parent-denied": (server,),
        "server-unobservable": (),
    }[case]
    denied = frozenset({800} if case == "parent-denied" else {900} if case == "server-unobservable" else ())

    assert WindowHostIdentity.capture(_lookup(*rows, denied=denied), pid=900) is None


def test_window_liveness_requires_the_exact_recorded_process() -> None:
    window = WindowHostIdentity(pid=100, create_time=5.5, name="Code Helper (Plugin)")
    rows: dict[int, ObservedProcess] = {}
    probe = ProcessWindowLivenessProbe(rows.get)

    rows[100] = ObservedProcess(pid=100, parent_pid=1, create_time=5.5, name="Code Helper (Plugin)")
    assert probe.window_state(window) == "alive"
    rows[100] = ObservedProcess(pid=100, parent_pid=1, create_time=5.7, name="Code Helper (Plugin)")
    assert probe.window_state(window) == "alive"
    rows[100] = ObservedProcess(pid=100, parent_pid=1, create_time=125.5, name="Code Helper (Plugin)")
    assert probe.window_state(window) == "gone"
    del rows[100]
    assert probe.window_state(window) == "gone"
    assert ProcessWindowLivenessProbe(_lookup(denied=frozenset({100}))).window_state(window) == "unknown"


def _sleeping_python(cwd: Path, opened: Path | None = None) -> subprocess.Popen[str]:
    script = "import sys\n"
    if opened is not None:
        script += f"handle = open({str(opened)!r})\n"
    script += "print('ready', flush=True)\nsys.stdin.read()\n"
    process = subprocess.Popen(  # noqa: S603 - fixed interpreter and inline script.
        (sys.executable, "-c", script), cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True
    )
    assert process.stdout is not None
    assert process.stdout.readline().strip() == "ready"
    return process


def _stop(process: subprocess.Popen[str]) -> None:
    assert process.stdin is not None
    process.stdin.close()
    process.wait(timeout=30)


def test_real_window_liveness_tracks_process_exit(tmp_path: Path) -> None:
    process = _sleeping_python(tmp_path)
    try:
        observed = psutil_process(process.pid)
        assert observed is not None
        window = WindowHostIdentity(pid=observed.pid, create_time=observed.create_time, name=observed.name)
        assert ProcessWindowLivenessProbe().window_state(window) == "alive"
    finally:
        _stop(process)
    assert ProcessWindowLivenessProbe().window_state(window) == "gone"
    captured = WindowHostIdentity.capture()
    assert captured is None or (captured.pid != os.getpid() and not captured.name.lower().startswith("python"))


@pytest.mark.parametrize("link", ["cwd", "open-admin-file"])
def test_real_process_table_detects_a_leftover_process_until_it_exits(tmp_path: Path, link: str) -> None:
    worktree = tmp_path / "worktree"
    administration = tmp_path / "repository" / ".git" / "worktrees" / "worktree"
    elsewhere = tmp_path / "elsewhere"
    for directory in (worktree, administration, elsewhere):
        directory.mkdir(parents=True)
    (administration / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    probe = ProcessTableWorktreeProbe()
    issued = datetime.now(UTC)
    roots = (worktree, administration)
    assert probe.active_processes(roots, issued_after=issued) == ()
    opened = None if link == "cwd" else administration / "HEAD"
    process = _detached_python(worktree if opened is None else elsewhere, tmp_path / "control", opened)
    try:
        assert len(probe.active_processes(roots, issued_after=issued)) == 1
    finally:
        _stop_detached(process, tmp_path / "control")
    assert probe.active_processes(roots, issued_after=issued) == ()


def test_real_process_table_ignores_delivery_own_subprocesses(tmp_path: Path) -> None:
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    issued = datetime.now(UTC)
    process = _sleeping_python(worktree)
    try:
        assert ProcessTableWorktreeProbe().active_processes((worktree,), issued_after=issued) == ()
    finally:
        _stop(process)


def _detached_python(cwd: Path, control: Path, opened: Path | None = None) -> psutil.Process:
    """Start a sleeper reparented away from this process, as a stopped worker's leftover would be."""
    control.mkdir()
    sleeper = "import pathlib, time\n"
    if opened is not None:
        sleeper += f"handle = open({str(opened)!r})\n"
    sleeper += (
        f"control = pathlib.Path({str(control)!r})\n"
        "(control / 'ready').touch()\n"
        "while not (control / 'stop').exists():\n"
        "    time.sleep(0.05)\n"
    )
    launcher = (
        "import subprocess, sys\n"
        f"child = subprocess.Popen((sys.executable, '-c', {sleeper!r}), cwd={str(cwd)!r}, start_new_session=True,"
        " stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n"
        "print(child.pid)\n"
    )
    launched = subprocess.run(  # noqa: S603 - fixed interpreter and inline script.
        (sys.executable, "-c", launcher), capture_output=True, text=True, check=True, timeout=30
    )
    process = psutil.Process(int(launched.stdout.strip()))
    deadline = time.monotonic() + 30
    while not (control / "ready").exists():
        assert time.monotonic() < deadline
        time.sleep(0.05)
    return process


def _stop_detached(process: psutil.Process, control: Path) -> None:
    (control / "stop").touch()
    with contextlib.suppress(psutil.NoSuchProcess):
        process.wait(timeout=30)


@dataclass(frozen=True)
class _FakeProcess:
    name: str
    working: Path | None = None
    files: tuple[Path, ...] = ()
    children: bool = False
    terminal: bool | None = True
    failure: str | None = None
    create_time: float | None = _ISSUED.timestamp() - 3600

    def cwd(self) -> Path | None:
        if self.failure == "vanished":
            raise ProcessVanishedError(self.failure)
        if self.failure == "unreadable":
            raise ProcessObservationError(self.failure)
        return self.working

    def open_files(self) -> tuple[Path, ...]:
        if self.failure in {"unreadable", "files-unreadable"}:
            raise ProcessObservationError(self.failure)
        return self.files

    def has_live_children(self) -> bool:
        return self.children

    def has_terminal(self) -> bool:
        if self.terminal is None:
            message = "terminal unreadable"
            raise ProcessObservationError(message)
        return self.terminal


_NEW = _ISSUED.timestamp() + 5
_WITHIN_TOLERANCE = _ISSUED.timestamp() - 0.5
_GUARD_CASES = {
    "non-shell-cwd": (_FakeProcess("node", working=Path("W/src")), True),
    "open-admin-file": (_FakeProcess("git", working=Path("E"), files=(Path("A/index.lock"),)), True),
    "idle-shell-cwd": (_FakeProcess("zsh", working=Path("W")), False),
    "login-shell-cwd": (_FakeProcess("-bash", working=Path("W/sub")), False),
    "shell-with-child": (_FakeProcess("bash", working=Path("W"), children=True), True),
    "shell-with-open-file": (_FakeProcess("fish", working=Path("W"), files=(Path("W/notes.txt"),)), True),
    "shell-without-terminal": (_FakeProcess("sh", working=Path("W"), terminal=False), True),
    "shell-terminal-unreadable-new": (_FakeProcess("zsh", working=Path("W"), terminal=None, create_time=_NEW), True),
    "shell-terminal-unreadable-old": (_FakeProcess("zsh", working=Path("W"), terminal=None), False),
    "unrelated": (_FakeProcess("Code Helper", working=Path("E"), files=(Path("E/x"),)), False),
    "vanished": (_FakeProcess("ghost", failure="vanished", create_time=_NEW), False),
    "unreadable-started-after-claim": (_FakeProcess("worker", failure="unreadable", create_time=_NEW), True),
    "unreadable-within-tolerance": (
        _FakeProcess("worker", failure="unreadable", create_time=_WITHIN_TOLERANCE),
        True,
    ),
    "unreadable-unknown-start": (_FakeProcess("worker", failure="unreadable", create_time=None), True),
    "unreadable-started-before-claim": (_FakeProcess("lsd", failure="unreadable"), False),
    "unreadable-unknown-issue-time": (_FakeProcess("lsd", failure="unreadable"), True),
    "files-unreadable-cwd-inside-old": (_FakeProcess("node", working=Path("W"), failure="files-unreadable"), True),
    "files-unreadable-elsewhere-new": (
        _FakeProcess("node", working=Path("E"), failure="files-unreadable", create_time=_NEW),
        True,
    ),
    "files-unreadable-elsewhere-old": (_FakeProcess("node", working=Path("E"), failure="files-unreadable"), False),
}


@pytest.mark.parametrize("case", sorted(_GUARD_CASES))
def test_process_guard_classifies_leftover_processes(tmp_path: Path, case: str) -> None:
    roots = {"W": tmp_path / "worktree", "A": tmp_path / "repository/.git/worktrees/worktree", "E": tmp_path / "e"}

    def rooted(path: Path | None) -> Path | None:
        return None if path is None else roots[path.parts[0]].joinpath(*path.parts[1:])

    fake, blocks = _GUARD_CASES[case]
    process = dataclasses.replace(fake, working=rooted(fake.working), files=tuple(rooted(path) for path in fake.files))
    probe = ProcessTableWorktreeProbe(lambda: iter((process,)))
    issued_after = None if case.endswith("unknown-issue-time") else _ISSUED

    assert probe.active_processes((roots["W"], roots["A"]), issued_after=issued_after) == (
        (fake.name,) if blocks else ()
    )


class _FakePsutilProcess:
    def __init__(self, info: dict[str, object], failure: Exception | None, cwd: Path) -> None:
        self.info = info
        self._failure = failure
        self._cwd = cwd

    def cwd(self) -> str:
        if self._failure is not None:
            raise self._failure
        return str(self._cwd)

    def open_files(self) -> list[object]:
        if self._failure is not None:
            raise self._failure
        return []

    def terminal(self) -> str | None:
        return None

    def children(self) -> list[object]:
        return []


_PSUTIL_CASES = {
    "owner-unknown-new": (None, None, _NEW, True),
    "owner-unknown-old": (None, None, _ISSUED.timestamp() - 3600, False),
    "denied-new": ("own", psutil.AccessDenied(9_001), _NEW, True),
    "denied-unknown-start": ("own", psutil.AccessDenied(9_001), None, True),
    "denied-old": ("own", psutil.AccessDenied(9_001), _ISSUED.timestamp() - 3600, False),
    "vanished-new": ("own", psutil.NoSuchProcess(9_001), _NEW, False),
    "zombie-new": ("own", psutil.ZombieProcess(9_001), _NEW, False),
    "other-user-new": ("other", psutil.AccessDenied(9_001), _NEW, False),
}


@pytest.mark.parametrize("case", sorted(_PSUTIL_CASES))
def test_psutil_process_table_blocks_unreadable_processes_started_after_the_claim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    owner, failure, created, blocks = _PSUTIL_CASES[case]
    uids = None if owner is None else SimpleNamespace(real=os.getuid() + (owner == "other"))
    info = {"pid": 9_001, "name": "sandboxed", "uids": uids, "create_time": created}
    row = _FakePsutilProcess(info, failure, tmp_path / "elsewhere")
    monkeypatch.setattr(psutil, "process_iter", lambda _attrs: iter((row,)))

    names = ProcessTableWorktreeProbe().active_processes((tmp_path / "worktree",), issued_after=_ISSUED)

    assert names == (("sandboxed",) if blocks else ())


@pytest.mark.parametrize("failure", [OSError("denied"), WorktreeProcessScanError("unavailable")])
def test_process_guard_fails_closed_when_the_table_cannot_be_scanned(tmp_path: Path, failure: Exception) -> None:
    def source():
        raise failure

    with pytest.raises(WorktreeProcessScanError):
        ProcessTableWorktreeProbe(source).active_processes((tmp_path,), issued_after=_ISSUED)


def _restart(application: PortfolioApplication, now: list[str], probe: _Probe) -> PortfolioApplication:
    """Model a fresh Delivery process over the same state: no window of its own, real window liveness."""
    identities = (f"restart-{index:03}" for index in itertools.count(1))
    return PortfolioApplication(
        application._runtimes,
        PortfolioApplicationDependencies(
            target_root=application._target_root,
            package_store=application._package_store,
            authority_registry=application._authority_registry,
            coordinator=application._coordinator,
            workspace_manager=application._workspace_manager,
            completed_history_catalog=application._completed_history_catalog,
            worktree_process_probe=probe,
        ),
        PortfolioApplicationConfig(
            package_root=application._package_root,
            execution_capacity=application._execution_capacity,
            role_policies=_policies(),
        ),
        PortfolioApplicationHooks(identity_factory=lambda: next(identities), clock=lambda: now[0]),
    )


def test_delivery_restart_with_live_window_keeps_claim_until_that_window_exits(tmp_path: Path) -> None:
    window_process = _sleeping_python(tmp_path)
    observed = psutil_process(window_process.pid)
    assert observed is not None
    window = WindowHostIdentity(pid=observed.pid, create_time=observed.create_time, name=observed.name)
    start = _real_now()
    now = [_iso(start)]
    try:
        application, runtimes, _coordinator, state_root, probe = _stall_portfolio(
            tmp_path, {"change-a": DeliveryStage.PLANNING}, now, window=window
        )
        claim = _acquire_planning_claim(application)
        issuer = json.loads(_issuer_path(state_root, "change-a", claim.attempt_id).read_bytes())
        assert issuer["window"] == window.model_dump(mode="json")
        restarted = _restart(application, now, probe)
        now[0] = _iso(start + timedelta(minutes=30))
        frontier_before = runtimes["change-a"].frontier_bytes()

        restarted.acquire_frontier_work()

        assert runtimes["change-a"].frontier_bytes() == frontier_before
        readiness = restarted.show_work_item_view("change-a", "outcome:OUT-001").readiness
        assert readiness is not None
        assert (readiness.status, readiness.reason_code) == ("running", "active-custody")
    finally:
        _stop(window_process)

    restarted.acquire_frontier_work()

    assert runtimes["change-a"].show_binding("OUT-001").active_claim is None
    assert _owner_failure_code(state_root, "change-a", claim.attempt_id) == "worker-host-lost"


def test_leftover_process_blocks_window_loss_settlement_without_a_retry_time(tmp_path: Path) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, runtimes, _coordinator, state_root, probe = _stall_portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING}, now
    )
    claim = _acquire_planning_claim(application)
    worktree = application._workspace_manager.show("change-a").worktree_path
    probe.states[_HOST] = "gone"
    probe.processes = ("node", "node", "pytest-helper")
    now[0] = _iso(start + timedelta(minutes=30))
    runtime = runtimes["change-a"]
    frontier_before = runtime.frontier_bytes()
    ledger_before = runtime.retry_ledger().read()

    application.acquire_frontier_work()
    application.acquire_change_action(_continuation_request(application, "change-a"))

    assert runtime.frontier_bytes() == frontier_before
    assert runtime.retry_ledger().read() == ledger_before
    roots = probe.scanned_roots[-1]
    assert roots[0] == worktree
    assert roots[1].parent.name == "worktrees"
    assert probe.issued_after[-1] == datetime.fromisoformat(claim.started_at)
    for readiness in (
        application.get_change("change-a").readiness,
        application.show_work_item_view("change-a", "outcome:OUT-001").readiness,
    ):
        assert readiness is not None
        assert (readiness.status, readiness.reason_code) == ("waiting", "worker-stall-wait")
        assert readiness.next_eligible_at is None
        assert readiness.prompt is not None
        assert "3 processes (node, pytest-helper) are still active" in readiness.prompt
        assert str(worktree) not in readiness.prompt

    probe.processes = ()
    application.acquire_frontier_work()

    assert runtime.show_binding("OUT-001").active_claim is None
    assert _owner_failure_code(state_root, "change-a", claim.attempt_id) == "worker-host-lost"


@pytest.mark.parametrize("role", ["planner", "builder", "finalizer"])
def test_leftover_process_blocks_confirmed_release_without_a_retry_time(tmp_path: Path, role: str) -> None:
    start = _real_now()
    now = [_iso(start)]
    if role == "builder":
        application, runtime, _coordinator, state_root, probe, launch, _head = _builder_with_workspace_changes(
            tmp_path, now
        )
        identity = (launch.outcome_id, launch.claim.attempt_id, launch.claim.claim_id)
        issued = launch.claim.started_at
    else:
        stage = DeliveryStage.PLANNING if role == "planner" else DeliveryStage.COMPLETED
        application, runtimes, _coordinator, state_root, probe = _stall_portfolio(tmp_path, {"change-a": stage}, now)
        runtime = runtimes["change-a"]
        if role == "planner":
            claim = _acquire_planning_claim(application)
            identity = ("OUT-001", claim.attempt_id, claim.claim_id)
            issued = claim.started_at
        else:
            acquired = application.acquire_change_action(_continuation_request(application))
            assert acquired.finalization is not None
            writer = acquired.finalization.attempt.writer
            identity = (None, writer.attempt_id, writer.claim_id)
            issued = writer.claimed_at
    worktree = application._workspace_manager.show("change-a").worktree_path
    probe.processes = ("node",)
    now[0] = _iso(start + timedelta(minutes=30))
    frontier_before = runtime.frontier_bytes()
    ledger_before = runtime.retry_ledger().read()

    with pytest.raises(DeliveryWorkerActiveError) as raised:
        application.release_stuck_worker("change-a", *identity)

    assert probe.issued_after[-1] == datetime.fromisoformat(issued)
    assert raised.value.code == "ERR_DELIVERY_WORKER_ACTIVE"
    assert raised.value.retry_after is None
    assert raised.value.active_processes == ("node",)
    assert "1 process (node) is still active in the worker's worktree" in str(raised.value)
    assert "Retry at or after" not in str(raised.value)
    assert str(worktree) not in str(raised.value)
    classification = classify_delivery_failure(raised.value)
    assert classification is not None
    assert classification.retry_safe is True
    assert runtime.frontier_bytes() == frontier_before
    assert runtime.retry_ledger().read() == ledger_before
    assert application._read_finalizer_settlement_receipt("change-a", identity[1]) is None

    probe.processes = ()
    application.release_stuck_worker("change-a", *identity)

    if role == "finalizer":
        assert application._read_finalizer_settlement_receipt("change-a", identity[1]) is not None
    else:
        assert runtime.show_binding(identity[0]).active_claim is None
    assert _owner_failure_code(state_root, "change-a", identity[1]) in {
        "worker-released-stuck",
        "finalizer-ended-without-report",
    }


@pytest.mark.parametrize("entry", ["release", "window-lost-sweep"])
def test_process_scan_failure_fails_closed(tmp_path: Path, entry: str) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, runtimes, _coordinator, state_root, probe = _stall_portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING}, now
    )
    claim = _acquire_planning_claim(application)
    probe.scan_fails = True
    probe.states[_HOST] = "gone"
    now[0] = _iso(start + timedelta(minutes=30))
    runtime = runtimes["change-a"]
    frontier_before = runtime.frontier_bytes()

    if entry == "release":
        with pytest.raises(DeliveryWorkerActiveError) as raised:
            application.release_stuck_worker("change-a", "OUT-001", claim.attempt_id, claim.claim_id)
        assert raised.value.retry_after is None
        assert "could not be observed safely" in str(raised.value)
    else:
        application.acquire_frontier_work()
        readiness = application.show_work_item_view("change-a", "outcome:OUT-001").readiness
        assert readiness is not None
        assert (readiness.reason_code, readiness.next_eligible_at) == ("worker-stall-wait", None)

    assert runtime.frontier_bytes() == frontier_before
    assert not (state_root / "changes/change-a/retry-ledger/owner-results" / f"{claim.attempt_id}.json").exists()


@pytest.mark.parametrize("recorded", ["earlier", "unparseable"])
def test_window_loss_scan_uses_the_issuer_record_issue_time(tmp_path: Path, recorded: str) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, runtimes, _coordinator, state_root, probe = _stall_portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING}, now
    )
    claim = _acquire_planning_claim(application)
    path = _issuer_path(state_root, "change-a", claim.attempt_id)
    record = json.loads(path.read_bytes())
    issued = start - timedelta(hours=1)
    record["issued_at"] = _iso(issued) if recorded == "earlier" else "not-a-time"
    path.write_text(json.dumps(record), encoding="utf-8")
    probe.states[_HOST] = "gone"
    probe.processes = ("node",)
    now[0] = _iso(start + timedelta(minutes=30))
    frontier_before = runtimes["change-a"].frontier_bytes()

    application.acquire_frontier_work()

    assert probe.issued_after
    assert set(probe.issued_after) == {issued if recorded == "earlier" else None}
    assert runtimes["change-a"].frontier_bytes() == frontier_before


@pytest.mark.parametrize("entry", ["release", "window-lost-sweep"])
def test_write_during_process_scan_keeps_worker_claim(tmp_path: Path, entry: str) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, runtimes, _coordinator, state_root, probe = _stall_portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING}, now
    )
    claim = _acquire_planning_claim(application)
    runtime = runtimes["change-a"]
    written = application._workspace_manager.show("change-a").worktree_path / "late-output.txt"
    current = start + timedelta(minutes=10)
    now[0] = _iso(current)

    def write_now() -> None:
        written.write_text("late worker output\n", encoding="utf-8")
        os.utime(written, (current.timestamp(), current.timestamp()))

    probe.during_scan = write_now
    frontier_before = runtime.frontier_bytes()
    ledger_before = runtime.retry_ledger().read()

    if entry == "release":
        with pytest.raises(DeliveryWorkerActiveError) as raised:
            application.release_stuck_worker("change-a", "OUT-001", claim.attempt_id, claim.claim_id)
        assert raised.value.retry_after == current + _QUIET
    else:
        probe.states[_HOST] = "gone"
        application.acquire_frontier_work()
        readiness = application.show_work_item_view("change-a", "outcome:OUT-001").readiness
        assert readiness is not None
        assert (readiness.reason_code, readiness.next_eligible_at) == ("worker-stall-wait", _iso(current + _QUIET))

    assert written.exists()
    assert runtime.show_binding("OUT-001").active_claim is not None
    assert runtime.frontier_bytes() == frontier_before
    assert runtime.retry_ledger().read() == ledger_before
    probe.during_scan = None
    now[0] = _iso(current + _QUIET)
    if entry == "release":
        settled = application.release_stuck_worker("change-a", "OUT-001", claim.attempt_id, claim.claim_id)
        assert settled.active_claim is None
    else:
        application.acquire_frontier_work()
        assert runtime.show_binding("OUT-001").active_claim is None
        assert _owner_failure_code(state_root, "change-a", claim.attempt_id) == "worker-host-lost"


@pytest.mark.parametrize("ignored_content", ["no-ignored", "ignored-caches"])
def test_host_lost_quiet_builder_settles_and_resumes_same_task_with_preserved_work(
    tmp_path: Path, ignored_content: str
) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, runtime, coordinator, state_root, probe, launch, branch_head = _builder_with_workspace_changes(
        tmp_path, now
    )
    if ignored_content == "ignored-caches":
        _add_ignored_content(launch.worktree_path)
    issuer = json.loads(_issuer_path(state_root, "change-a", launch.claim.attempt_id).read_bytes())
    assert issuer == {
        "schema_version": 1,
        "change_id": "change-a",
        "outcome_id": launch.outcome_id,
        "attempt_id": launch.claim.attempt_id,
        "claim_id": launch.claim.claim_id,
        "role": "builder",
        "window": {"pid": _WINDOW.pid, "create_time": _WINDOW.create_time, "name": _WINDOW.name},
        "issued_at": launch.claim.started_at,
    }
    before_workspace = _workspace_content_snapshot(launch.worktree_path)
    probe.states[_HOST] = "gone"
    now[0] = _iso(start + timedelta(minutes=10))

    application.acquire_change_action(_continuation_request(application, "change-a"))

    settled = runtime.show_binding(launch.outcome_id)
    assert settled.active_claim is None
    assert settled.block is None
    assert settled.builder_handoff_context is not None
    assert settled.builder_handoff_context.route == "same-task"
    assert settled.builder_handoff_context.branch_head == branch_head
    assert coordinator.show("change-a").builder_handoff is not None
    assert _workspace_content_snapshot(launch.worktree_path) == before_workspace
    assert _owner_failure_code(state_root, "change-a", launch.claim.attempt_id) == "worker-host-lost"
    late_result = _task_result(
        "RESULT-LATE-HOST-LOST",
        "change-a",
        runtime.authority_digest,
        settled.tasks[0],
        branch_head,
    )
    with pytest.raises(DeliveryRuntimeConflictError):
        runtime.publish_result(
            PublishDeliveryResult(outcome_id=launch.outcome_id, claim_id=launch.claim.claim_id, result=late_result)
        )
    with pytest.raises(DeliveryRuntimeConflictError):
        application.settle_worker_invocation(
            DeliveryBuilderInvocationSettlement(
                change_id="change-a",
                outcome_id=launch.outcome_id,
                claim_id=launch.claim.claim_id,
                attempt_id=launch.claim.attempt_id,
                task_id=launch.task_id,
                expected_last_reviewed_commit=launch.last_reviewed_commit,
                disposition="ended-without-result",
            ),
            host_id=launch.claim.owner_id,
            session_id=launch.claim.process_id,
        )

    probe.states[_HOST] = "alive"
    now[0] = _iso(start + timedelta(hours=2))
    resumed_result = application.acquire_change_action(_continuation_request(application, "change-a"))
    assert resumed_result.launch is not None, resumed_result
    resumed = resumed_result.launch
    assert resumed.claim.task_id == launch.task_id
    assert resumed.claim.attempt_id != launch.claim.attempt_id
    assert resumed.builder_handoff_context == settled.builder_handoff_context
    assert _workspace_content_snapshot(resumed.worktree_path) == before_workspace
    context = application.show_build_context(
        resumed.change_id, resumed.outcome_id, resumed.claim.attempt_id, resumed.claim.claim_id
    )
    assert _builder_retry_history(context.prior_attempts) == [(1, "original", "failed", "worker-host-lost")]


def test_host_lost_recent_worktree_change_waits_until_exact_quiet_boundary(tmp_path: Path) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, runtimes, _coordinator, state_root, probe = _stall_portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING}, now
    )
    claim = _acquire_planning_claim(application)
    runtime = runtimes["change-a"]
    worktree = application._workspace_manager.show("change-a").worktree_path
    touched = start + timedelta(minutes=5)
    activity = worktree / "planner-notes.txt"
    activity.write_text("recent\n", encoding="utf-8")
    os.utime(activity, (touched.timestamp(), touched.timestamp()))
    probe.states[_HOST] = "gone"
    assert DEFAULT_WORKER_QUIET_PERIOD == _QUIET
    eligible = touched + _QUIET
    now[0] = _iso(eligible - timedelta(seconds=1))
    frontier_before = runtime.frontier_bytes()
    ledger_before = runtime.retry_ledger().read()

    result = application.acquire_frontier_work()

    assert result.launch_packages == ()
    assert runtime.frontier_bytes() == frontier_before
    assert runtime.retry_ledger().read() == ledger_before
    for readiness in (
        application.get_change("change-a").readiness,
        application.show_work_item_view("change-a", "outcome:OUT-001").readiness,
    ):
        assert readiness is not None
        assert readiness.status == "waiting"
        assert readiness.reason_code == "worker-stall-wait"
        assert readiness.executable is False
        assert readiness.next_eligible_at == _iso(eligible)
    application.acquire_change_action(_continuation_request(application, "change-a"))
    assert runtime.frontier_bytes() == frontier_before

    now[0] = _iso(eligible)
    application.acquire_frontier_work()

    assert runtime.show_binding("OUT-001").active_claim is None
    assert _owner_failure_code(state_root, "change-a", claim.attempt_id) == "worker-host-lost"


@pytest.mark.parametrize("case", ["live-window", "unknown-window", "no-issuer-record", "no-window-identity"])
def test_stall_sweep_leaves_claims_without_window_loss_evidence(tmp_path: Path, case: str) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, runtimes, _coordinator, state_root, probe = _stall_portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
        now,
        window=None if case == "no-window-identity" else _WINDOW,
    )
    claim = _acquire_planning_claim(application)
    if case == "unknown-window":
        probe.states[_HOST] = "unknown"
    elif case == "no-issuer-record":
        _issuer_path(state_root, "change-a", claim.attempt_id).unlink()
        probe.states[_HOST] = "gone"
    elif case == "no-window-identity":
        assert json.loads(_issuer_path(state_root, "change-a", claim.attempt_id).read_bytes())["window"] is None
        probe.states[_HOST] = "gone"
    now[0] = _iso(start + timedelta(minutes=30))
    runtime = runtimes["change-a"]
    frontier_before = runtime.frontier_bytes()

    application.acquire_frontier_work()
    application.acquire_change_action(_continuation_request(application, "change-a"))

    assert runtime.frontier_bytes() == frontier_before
    readiness = application.show_work_item_view("change-a", "outcome:OUT-001").readiness
    assert readiness is not None
    assert readiness.status == "running"
    assert readiness.reason_code == "active-custody"


def test_stall_sweep_isolates_an_unreadable_issuer_record_to_its_change(tmp_path: Path) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, runtimes, _coordinator, state_root, probe = _stall_portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING, "change-b": DeliveryStage.PLANNING}, now
    )
    launches = {launch.change_id: launch for launch in application.acquire_frontier_work().launch_packages}
    assert set(launches) == {"change-a", "change-b"}
    _issuer_path(state_root, "change-a", launches["change-a"].claim.attempt_id).write_bytes(b"{not-json")
    probe.states[_HOST] = "gone"
    now[0] = _iso(start + timedelta(minutes=30))
    blocked_before = runtimes["change-a"].frontier_bytes()

    result = application.acquire_frontier_work()

    assert runtimes["change-a"].frontier_bytes() == blocked_before
    assert runtimes["change-b"].show_binding("OUT-001").active_claim is None
    assert _owner_failure_code(state_root, "change-b", launches["change-b"].claim.attempt_id) == "worker-host-lost"
    assert any(failure.change_id == "change-a" for failure in result.failures)


def test_release_stuck_worker_settles_quiet_planner_and_replays(tmp_path: Path) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, runtimes, _coordinator, state_root, _probe = _stall_portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING}, now
    )
    claim = _acquire_planning_claim(application)
    now[0] = _iso(start + timedelta(minutes=10))

    settled = application.release_stuck_worker("change-a", "OUT-001", claim.attempt_id, claim.claim_id)

    assert settled.active_claim is None
    assert runtimes["change-a"].show_binding("OUT-001").active_claim is None
    assert _owner_failure_code(state_root, "change-a", claim.attempt_id) == "worker-released-stuck"
    frontier = runtimes["change-a"].frontier_bytes()
    assert application.release_stuck_worker("change-a", "OUT-001", claim.attempt_id, claim.claim_id) == settled
    assert runtimes["change-a"].frontier_bytes() == frontier
    with pytest.raises(DeliveryRuntimeConflictError):
        application.settle_worker_invocation(
            DeliveryPlanningRetrySettlement(
                change_id="change-a",
                outcome_id="OUT-001",
                claim_id=claim.claim_id,
                attempt_id=claim.attempt_id,
                disposition="ended-without-result",
            )
        )


def test_release_stuck_worker_refuses_active_worktree_without_mutation(tmp_path: Path) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, runtime, coordinator, _state_root, _probe, launch, _head = _builder_with_workspace_changes(
        tmp_path, now
    )
    touched = start + timedelta(minutes=5)
    os.utime(launch.worktree_path / "untracked.txt", (touched.timestamp(), touched.timestamp()))
    now[0] = _iso(touched + timedelta(seconds=10))
    frontier_before = runtime.frontier_bytes()
    ledger_before = runtime.retry_ledger().read()
    coordination_before = coordinator.show("change-a")
    workspace_before = _workspace_content_snapshot(launch.worktree_path)

    with pytest.raises(DeliveryWorkerActiveError) as raised:
        application.release_stuck_worker("change-a", launch.outcome_id, launch.claim.attempt_id, launch.claim.claim_id)

    assert raised.value.code == "ERR_DELIVERY_WORKER_ACTIVE"
    assert raised.value.retry_after == touched + _QUIET
    assert "unchanged" in str(raised.value)
    assert _iso(touched + _QUIET) in str(raised.value)
    classification = classify_delivery_failure(raised.value)
    assert classification is not None
    assert classification.code == "ERR_DELIVERY_WORKER_ACTIVE"
    assert classification.category is DeliveryFailureCategory.CONFLICT
    assert classification.retry_safe is True
    assert runtime.frontier_bytes() == frontier_before
    assert runtime.retry_ledger().read() == ledger_before
    assert coordinator.show("change-a") == coordination_before
    assert _workspace_content_snapshot(launch.worktree_path) == workspace_before


@pytest.mark.parametrize("scenario", _HIDDEN_ACTIVITY)
def test_release_stuck_worker_refuses_recent_activity_hidden_from_status(tmp_path: Path, scenario: str) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, runtime, coordinator, _state_root, _probe, launch, _head = _builder_with_workspace_changes(
        tmp_path, now
    )
    touched = start + timedelta(minutes=5)
    target = _hidden_activity(launch.worktree_path, scenario, touched)
    now[0] = _iso(touched + timedelta(seconds=10))
    target_times = target.lstat().st_mtime_ns, target.lstat().st_ctime_ns
    before = (
        runtime.frontier_bytes(),
        runtime.retry_ledger().read(),
        coordinator.show("change-a"),
        _workspace_content_snapshot(launch.worktree_path),
    )

    with pytest.raises(DeliveryWorkerActiveError) as raised:
        application.release_stuck_worker("change-a", launch.outcome_id, launch.claim.attempt_id, launch.claim.claim_id)

    assert raised.value.code == "ERR_DELIVERY_WORKER_ACTIVE"
    assert raised.value.retry_after == touched + _QUIET
    assert (target.lstat().st_mtime_ns, target.lstat().st_ctime_ns) == target_times
    assert (
        runtime.frontier_bytes(),
        runtime.retry_ledger().read(),
        coordinator.show("change-a"),
        _workspace_content_snapshot(launch.worktree_path),
    ) == before


@pytest.mark.parametrize("scenario", _HIDDEN_ACTIVITY)
def test_release_stuck_worker_settles_planner_once_hidden_activity_is_quiet(tmp_path: Path, scenario: str) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, runtimes, _coordinator, state_root, _probe = _stall_portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING}, now
    )
    claim = _acquire_planning_claim(application)
    touched = start + timedelta(minutes=5)
    _hidden_activity(application._workspace_manager.show("change-a").worktree_path, scenario, touched)
    now[0] = _iso(touched + _QUIET - timedelta(seconds=1))
    with pytest.raises(DeliveryWorkerActiveError):
        application.release_stuck_worker("change-a", "OUT-001", claim.attempt_id, claim.claim_id)
    now[0] = _iso(touched + _QUIET)

    settled = application.release_stuck_worker("change-a", "OUT-001", claim.attempt_id, claim.claim_id)

    assert settled.active_claim is None
    assert runtimes["change-a"].show_binding("OUT-001").active_claim is None
    assert _owner_failure_code(state_root, "change-a", claim.attempt_id) == "worker-released-stuck"


def test_release_stuck_worker_hands_off_builder_once_deleted_nested_path_is_quiet(tmp_path: Path) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, runtime, _coordinator, state_root, _probe, launch, branch_head = _builder_with_workspace_changes(
        tmp_path, now
    )
    touched = start + timedelta(minutes=5)
    _hidden_activity(launch.worktree_path, "deleted-nested-untracked", touched)
    now[0] = _iso(touched + _QUIET)

    application.release_stuck_worker("change-a", launch.outcome_id, launch.claim.attempt_id, launch.claim.claim_id)

    settled = runtime.show_binding(launch.outcome_id)
    assert settled.active_claim is None
    assert settled.builder_handoff_context is not None
    assert settled.builder_handoff_context.route == "same-task"
    assert settled.builder_handoff_context.branch_head == branch_head
    assert _owner_failure_code(state_root, "change-a", launch.claim.attempt_id) == "worker-released-stuck"


@pytest.mark.parametrize("bound", ["entries", "time"])
def test_release_stuck_worker_refuses_when_activity_walk_exceeds_its_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bound: str
) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, runtimes, _coordinator, _state_root, _probe = _stall_portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING}, now
    )
    claim = _acquire_planning_claim(application)
    worktree = application._workspace_manager.show("change-a").worktree_path
    (worktree / "build").mkdir()
    (worktree / "build" / "old.bin").write_bytes(b"old")
    now[0] = _iso(start + timedelta(minutes=10))
    runtime = runtimes["change-a"]
    frontier_before = runtime.frontier_bytes()
    ledger_before = runtime.retry_ledger().read()
    if bound == "entries":
        monkeypatch.setattr(change_workspace, "_ACTIVITY_WALK_MAX_ENTRIES", 1)
    else:
        monkeypatch.setattr(change_workspace, "_ACTIVITY_WALK_SECONDS", 0.0)

    with pytest.raises(DeliveryWorkerActiveError) as raised:
        application.release_stuck_worker("change-a", "OUT-001", claim.attempt_id, claim.claim_id)

    assert raised.value.retry_after is None
    assert runtime.frontier_bytes() == frontier_before
    assert runtime.retry_ledger().read() == ledger_before
    monkeypatch.undo()
    settled = application.release_stuck_worker("change-a", "OUT-001", claim.attempt_id, claim.claim_id)
    assert settled.active_claim is None


_CONCURRENT_ACTIVITY = ("root-add", "nested-add", "nested-remove", "directory-replaced")


def _inject_concurrent_activity(
    monkeypatch: pytest.MonkeyPatch, worktree: Path, scenario: str, displaced: Path
) -> list[int]:
    """Mutate one directory each time the activity walk finishes listing it, as a live worker would."""
    (worktree / "work" / "nested").mkdir(parents=True)
    (worktree / "work" / "nested" / "keep.txt").write_text("kept\n", encoding="utf-8")
    target = worktree / {"root-add": "", "directory-replaced": "work"}.get(scenario, "work/nested")
    fired: list[int] = []
    real_scandir = os.scandir

    def mutate() -> None:
        index = len(fired)
        fired.append(index)
        if scenario == "directory-replaced":
            (worktree / "work").rename(displaced / f"work-{index}")
            (worktree / "work" / "nested").mkdir(parents=True)
            (worktree / "work" / "nested" / "keep.txt").write_text("kept\n", encoding="utf-8")
        elif scenario == "nested-remove":
            transient = target / f"transient-{index}.txt"
            transient.write_text("transient\n", encoding="utf-8")
            transient.unlink()
        else:
            (target / f"late-{index}.txt").write_text("late\n", encoding="utf-8")

    @contextlib.contextmanager
    def listing(path: int):
        with real_scandir(path) as entries:
            yield entries
        mutate()

    def scandir(path="."):
        if isinstance(path, int):
            listed, current = os.fstat(path), target.lstat()
            if (listed.st_dev, listed.st_ino) == (current.st_dev, current.st_ino):
                return listing(path)
        return real_scandir(path)

    monkeypatch.setattr(os, "scandir", scandir)
    return fired


@pytest.mark.parametrize("scenario", _CONCURRENT_ACTIVITY)
@pytest.mark.parametrize("entry", ["release", "host-lost-sweep"])
def test_activity_during_observation_keeps_worker_claim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, scenario: str, entry: str
) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, runtimes, _coordinator, state_root, probe = _stall_portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING}, now
    )
    claim = _acquire_planning_claim(application)
    runtime = runtimes["change-a"]
    worktree = application._workspace_manager.show("change-a").worktree_path
    displaced = tmp_path / "displaced"
    displaced.mkdir()
    # Every write is older than the quiet period by the injected clock; only its timing during the walk is live.
    now[0] = _iso(start + timedelta(minutes=10))
    fired = _inject_concurrent_activity(monkeypatch, worktree, scenario, displaced)
    frontier_before = runtime.frontier_bytes()
    ledger_before = runtime.retry_ledger().read()

    if entry == "release":
        with pytest.raises(DeliveryWorkerActiveError) as raised:
            application.release_stuck_worker("change-a", "OUT-001", claim.attempt_id, claim.claim_id)
        assert raised.value.code == "ERR_DELIVERY_WORKER_ACTIVE"
    else:
        probe.states[_HOST] = "gone"
        application.acquire_frontier_work()

    assert fired
    assert runtime.show_binding("OUT-001").active_claim is not None
    assert runtime.frontier_bytes() == frontier_before
    assert runtime.retry_ledger().read() == ledger_before
    monkeypatch.undo()
    if entry == "release":
        settled = application.release_stuck_worker("change-a", "OUT-001", claim.attempt_id, claim.claim_id)
        assert settled.active_claim is None
    else:
        application.acquire_frontier_work()
        assert runtime.show_binding("OUT-001").active_claim is None
        assert _owner_failure_code(state_root, "change-a", claim.attempt_id) == "worker-host-lost"


def _inject_overwrite_after_walk(
    monkeypatch: pytest.MonkeyPatch, target: Path, mtime: str
) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    """Rewrite one already-scanned file in place with identical bytes as soon as the walk ends."""
    content = target.read_bytes()
    real_walk = change_workspace._worktree_tree_activity_ns
    parents: list[tuple[tuple[int, int], tuple[int, int]]] = []

    def walk(worktree: Path, ignored: frozenset[str], observed: dict) -> int:
        newest = real_walk(worktree, ignored, observed)
        before, parent = target.lstat(), target.parent.lstat()
        target.write_bytes(content)
        if mtime == "restored":
            os.utime(target, ns=(before.st_atime_ns, before.st_mtime_ns))
        after = target.parent.lstat()
        parents.append(((parent.st_mtime_ns, parent.st_ctime_ns), (after.st_mtime_ns, after.st_ctime_ns)))
        return newest

    monkeypatch.setattr(change_workspace, "_worktree_tree_activity_ns", walk)
    return parents


def _overwrite_target(worktree: Path, tracked: Path, kind: str) -> Path:
    if kind == "tracked":
        _git(worktree, "ls-files", "--error-unmatch", tracked.name)
        return tracked
    (worktree / ".gitignore").write_text("*.log\n", encoding="utf-8")
    target = worktree / "debug.log"
    target.write_text("ignored output\n", encoding="utf-8")
    _git(worktree, "check-ignore", "-q", target.name)
    return target


@pytest.mark.parametrize("mtime", ["restored", "new"])
@pytest.mark.parametrize(
    ("role", "entry", "kind"),
    [
        ("planner", "release", "tracked"),
        ("planner", "release", "ignored"),
        ("planner", "host-lost-sweep", "tracked"),
        ("planner", "host-lost-sweep", "ignored"),
        ("builder", "release", "tracked"),
        ("builder", "release", "ignored"),
        ("builder", "host-lost-sweep", "tracked"),
        ("builder", "host-lost-sweep", "ignored"),
    ],
)
def test_file_overwritten_after_activity_walk_keeps_worker_claim(  # noqa: PLR0913, PLR0917 - one scenario matrix.
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, role: str, entry: str, kind: str, mtime: str
) -> None:
    start = _real_now()
    now = [_iso(start)]
    if role == "planner":
        application, runtimes, coordinator, state_root, probe = _stall_portfolio(
            tmp_path, {"change-a": DeliveryStage.PLANNING}, now
        )
        claim = _acquire_planning_claim(application)
        runtime, outcome_id = runtimes["change-a"], "OUT-001"
        worktree = application._workspace_manager.show("change-a").worktree_path
        tracked = worktree / "product.txt"
    else:
        application, runtime, coordinator, state_root, probe, launch, _head = _builder_with_workspace_changes(
            tmp_path, now
        )
        claim, outcome_id, worktree = launch.claim, launch.outcome_id, launch.worktree_path
        tracked = worktree / "committed.txt"
    target = _overwrite_target(worktree, tracked, kind)
    # Every write, including the injected overwrite, is older than the quiet period by the injected clock.
    now[0] = _iso(start + timedelta(minutes=10))
    parents = _inject_overwrite_after_walk(monkeypatch, target, mtime)
    frontier_before = runtime.frontier_bytes()
    ledger_before = runtime.retry_ledger().read()
    coordination_before = coordinator.show("change-a")

    if entry == "release":
        with pytest.raises(DeliveryWorkerActiveError) as raised:
            application.release_stuck_worker("change-a", outcome_id, claim.attempt_id, claim.claim_id)
        assert raised.value.code == "ERR_DELIVERY_WORKER_ACTIVE"
    else:
        probe.states[_HOST] = "gone"
        application.acquire_frontier_work()

    assert parents
    assert all(before == after for before, after in parents)
    binding = runtime.show_binding(outcome_id)
    assert binding.active_claim is not None
    assert binding.active_claim.attempt_id == claim.attempt_id
    assert binding.builder_handoff_context is None
    assert runtime.frontier_bytes() == frontier_before
    assert runtime.retry_ledger().read() == ledger_before
    assert coordinator.show("change-a") == coordination_before
    assert coordinator.show("change-a").builder_handoff is None
    monkeypatch.undo()
    if entry == "release":
        application.release_stuck_worker("change-a", outcome_id, claim.attempt_id, claim.claim_id)
        code = "worker-released-stuck"
    else:
        application.acquire_frontier_work()
        code = "worker-host-lost"
    assert runtime.show_binding(outcome_id).active_claim is None
    assert _owner_failure_code(state_root, "change-a", claim.attempt_id) == code


def test_host_lost_waits_for_deletion_inside_ignored_directory(tmp_path: Path) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, runtimes, _coordinator, state_root, probe = _stall_portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING}, now
    )
    claim = _acquire_planning_claim(application)
    runtime = runtimes["change-a"]
    worktree = application._workspace_manager.show("change-a").worktree_path
    touched = start + timedelta(minutes=5)
    _hidden_activity(worktree, "deleted-ignored-entry", touched)
    probe.states[_HOST] = "gone"
    now[0] = _iso(touched + timedelta(seconds=10))
    frontier_before = runtime.frontier_bytes()

    assert application.acquire_frontier_work().launch_packages == ()

    assert runtime.frontier_bytes() == frontier_before
    readiness = application.show_work_item_view("change-a", "outcome:OUT-001").readiness
    assert readiness is not None
    assert readiness.reason_code == "worker-stall-wait"
    assert readiness.next_eligible_at == _iso(touched + _QUIET)

    now[0] = _iso(touched + _QUIET)
    application.acquire_frontier_work()

    assert runtime.show_binding("OUT-001").active_claim is None
    assert _owner_failure_code(state_root, "change-a", claim.attempt_id) == "worker-host-lost"


def test_ended_builder_with_ignored_content_resumes_same_task_despite_cache_churn(tmp_path: Path) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, _runtime, coordinator, _state_root, _probe, launch, branch_head = _builder_with_workspace_changes(
        tmp_path, now
    )
    _add_ignored_content(launch.worktree_path)
    before_workspace = _workspace_content_snapshot(launch.worktree_path)

    settled = application.settle_worker_invocation(
        _requestless_builder_settlement(launch, "ended-without-result"),
        host_id=launch.claim.owner_id,
        session_id=launch.claim.process_id,
    )

    assert settled.active_claim is None
    assert settled.builder_handoff_context is not None
    assert settled.builder_handoff_context.route == "same-task"
    assert settled.builder_handoff_context.branch_head == branch_head
    assert coordinator.show("change-a").builder_handoff is not None
    assert _workspace_content_snapshot(launch.worktree_path) == before_workspace
    waiting = application.acquire_change_action(_continuation_request(application, "change-a"))
    assert waiting.launch is None
    assert waiting.reason_code == "retry-backoff"
    _churn_ignored_content(launch.worktree_path)
    after_churn = _workspace_content_snapshot(launch.worktree_path)

    now[0] = _iso(start + timedelta(hours=1))
    resumed_result = application.acquire_change_action(_continuation_request(application, "change-a"))

    assert resumed_result.launch is not None, resumed_result
    resumed = resumed_result.launch
    assert resumed.claim.task_id == launch.task_id
    assert resumed.claim.attempt_id != launch.claim.attempt_id
    assert resumed.builder_handoff_context == settled.builder_handoff_context
    assert _workspace_content_snapshot(resumed.worktree_path) == after_churn
    assert (resumed.worktree_path / ".ruff_cache" / "state").read_bytes() == b"lint cache"


def _drift_handoff_workspace(worktree: Path, drift: str) -> None:
    if drift == "tracked":
        (worktree / "committed.txt").write_text("drifted tracked work\n", encoding="utf-8")
    elif drift == "untracked":
        (worktree / "post-handoff.txt").write_text("drifted untracked work\n", encoding="utf-8")
    elif drift == "staged":
        _git(worktree, "add", "untracked.txt")
    else:
        (worktree / "committed.txt").write_text("drifted committed work\n", encoding="utf-8")
        _git(worktree, "commit", "-m", "drift head", "--", "committed.txt")


@pytest.mark.parametrize("drift", ["tracked", "untracked", "staged", "head"])
def test_builder_handoff_with_ignored_churn_still_refuses_preserved_work_drift(tmp_path: Path, drift: str) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, runtime, coordinator, _state_root, _probe, launch, _branch_head = _builder_with_workspace_changes(
        tmp_path, now
    )
    _add_ignored_content(launch.worktree_path)
    application.settle_worker_invocation(
        _requestless_builder_settlement(launch, "ended-without-result"),
        host_id=launch.claim.owner_id,
        session_id=launch.claim.process_id,
    )
    handoff = coordinator.show("change-a").builder_handoff
    assert handoff is not None
    _churn_ignored_content(launch.worktree_path)
    _drift_handoff_workspace(launch.worktree_path, drift)
    drifted = _workspace_content_snapshot(launch.worktree_path)
    now[0] = _iso(start + timedelta(hours=1))

    result = application.acquire_change_action(_continuation_request(application, "change-a"))

    assert result.launch is None, result
    assert result.kind == "unavailable", result
    assert runtime.active_claims() == ()
    assert coordinator.show("change-a").builder_handoff == handoff
    assert _workspace_content_snapshot(launch.worktree_path) == drifted


def test_release_stuck_builder_with_ignored_content_hands_off_and_resumes(tmp_path: Path) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, runtime, _coordinator, state_root, _probe, launch, branch_head = _builder_with_workspace_changes(
        tmp_path, now
    )
    _add_ignored_content(launch.worktree_path)
    before_workspace = _workspace_content_snapshot(launch.worktree_path)
    now[0] = _iso(start + timedelta(minutes=10))

    application.release_stuck_worker("change-a", launch.outcome_id, launch.claim.attempt_id, launch.claim.claim_id)

    settled = runtime.show_binding(launch.outcome_id)
    assert settled.active_claim is None
    assert settled.builder_handoff_context is not None
    assert settled.builder_handoff_context.branch_head == branch_head
    assert _owner_failure_code(state_root, "change-a", launch.claim.attempt_id) == "worker-released-stuck"
    assert _workspace_content_snapshot(launch.worktree_path) == before_workspace
    now[0] = _iso(start + timedelta(hours=2))
    resumed_result = application.acquire_change_action(_continuation_request(application, "change-a"))
    assert resumed_result.launch is not None, resumed_result
    assert resumed_result.launch.claim.task_id == launch.task_id
    assert _workspace_content_snapshot(launch.worktree_path) == before_workspace


def test_activity_ignores_deep_writes_inside_ignored_directories(tmp_path: Path) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, _runtimes, _coordinator, _state_root, _probe = _stall_portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING}, now
    )
    manager = application._workspace_manager
    worktree = manager.show("change-a").worktree_path
    (worktree / ".gitignore").write_text(".venv/\n", encoding="utf-8")
    deep = worktree / ".venv" / "lib" / "site-packages" / "pkg" / "x.py"
    deep.parent.mkdir(parents=True)
    deep.write_text("cache\n", encoding="utf-8")
    touched = start + timedelta(minutes=5)
    os.utime(deep, (touched.timestamp(), touched.timestamp()))

    # Documented limitation: tool caches and environments below an ignored directory are not observed.
    assert manager.observe_worktree_activity("change-a") < touched


def test_activity_observes_large_ignored_tree_within_entry_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, runtimes, _coordinator, state_root, _probe = _stall_portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING}, now
    )
    claim = _acquire_planning_claim(application)
    worktree = application._workspace_manager.show("change-a").worktree_path
    (worktree / ".gitignore").write_text("build/\n", encoding="utf-8")
    (worktree / "build").mkdir()
    for index in range(5_000):
        (worktree / "build" / f"{index}.bin").write_bytes(b"x")
    monkeypatch.setattr(change_workspace, "_ACTIVITY_WALK_MAX_ENTRIES", 1_000)
    now[0] = _iso(start + timedelta(minutes=10))

    settled = application.release_stuck_worker("change-a", "OUT-001", claim.attempt_id, claim.claim_id)

    assert settled.active_claim is None
    assert runtimes["change-a"].show_binding("OUT-001").active_claim is None
    assert _owner_failure_code(state_root, "change-a", claim.attempt_id) == "worker-released-stuck"


def test_release_stuck_worker_requires_exact_active_identity(tmp_path: Path) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, runtimes, _coordinator, _state_root, _probe = _stall_portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING}, now
    )
    claim = _acquire_planning_claim(application)
    now[0] = _iso(start + timedelta(minutes=10))
    runtime = runtimes["change-a"]
    frontier_before = runtime.frontier_bytes()
    ledger_before = runtime.retry_ledger().read()
    for outcome_id, attempt_id, claim_id in (
        ("OUT-001", "foreign-attempt", claim.claim_id),
        ("OUT-001", claim.attempt_id, "foreign-claim"),
        ("OUT-002", claim.attempt_id, claim.claim_id),
    ):
        with pytest.raises((DeliveryRuntimeConflictError, PortfolioApplicationError, KeyError, ValueError)):
            application.release_stuck_worker("change-a", outcome_id, attempt_id, claim_id)
        assert runtime.frontier_bytes() == frontier_before
        assert runtime.retry_ledger().read() == ledger_before


def test_callers_cannot_submit_engine_worker_dispositions(tmp_path: Path) -> None:
    for disposition in ("host-lost", "released-stuck"):
        with pytest.raises(ValidationError):
            DeliveryPlanningRetrySettlement(
                change_id="change-a",
                outcome_id="OUT-001",
                claim_id="claim",
                attempt_id="attempt",
                disposition=disposition,
            )
        with pytest.raises(ValidationError):
            DeliveryBuilderInvocationSettlement(
                change_id="change-a",
                outcome_id="OUT-001",
                claim_id="claim",
                attempt_id="attempt",
                task_id="TASK-001",
                expected_last_reviewed_commit="a" * 40,
                disposition=disposition,
            )
    for failure_code in ("worker-host-lost", "worker-released-stuck"):
        with pytest.raises(ValidationError):
            DeliveryPlanningRetrySettlement(
                change_id="change-a",
                outcome_id="OUT-001",
                claim_id="claim",
                attempt_id="attempt",
                disposition="normal-return",
                request=RetryDelivery(
                    action="retry", outcome_id="OUT-001", claim_id="claim", failure_code=failure_code
                ),
            )

    now = [_iso(_real_now() + timedelta(minutes=10))]
    application, runtimes, _coordinator, _state_root, _probe = _stall_portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING}, now
    )
    claim = _acquire_planning_claim(application)
    runtime = runtimes["change-a"]
    frontier_before = runtime.frontier_bytes()
    forged = DeliveryEnginePlanningSettlement(
        change_id="change-a",
        outcome_id="OUT-001",
        claim_id=claim.claim_id,
        attempt_id=claim.attempt_id,
        disposition="host-lost",
    )
    with pytest.raises(PortfolioApplicationError):
        application.settle_worker_invocation(forged, host_id=claim.owner_id, session_id=claim.process_id)
    assert runtime.frontier_bytes() == frontier_before
    assert DeliveryEngineBuilderSettlement.model_fields["disposition"].annotation is not None


def test_engine_and_caller_worker_endings_share_one_exhausting_builder_episode(tmp_path: Path) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, runtime, _coordinator, state_root, probe, launch, _head = _builder_with_workspace_changes(
        tmp_path, now
    )
    workspace = _workspace_content_snapshot(launch.worktree_path)
    attempt_ids = [launch.claim.attempt_id]

    probe.states[_HOST] = "gone"
    now[0] = _iso(start + timedelta(minutes=10))
    application.acquire_frontier_work()
    assert runtime.show_binding(launch.outcome_id).active_claim is None
    probe.states[_HOST] = "alive"

    now[0] = _iso(start + timedelta(hours=2))
    second = application.acquire_change_action(_continuation_request(application, "change-a")).launch
    assert second is not None
    attempt_ids.append(second.claim.attempt_id)
    application.release_stuck_worker("change-a", second.outcome_id, second.claim.attempt_id, second.claim.claim_id)

    now[0] = _iso(start + timedelta(hours=4))
    third = application.acquire_change_action(_continuation_request(application, "change-a")).launch
    assert third is not None
    attempt_ids.append(third.claim.attempt_id)
    application.settle_worker_invocation(
        DeliveryBuilderInvocationSettlement(
            change_id=third.change_id,
            outcome_id=third.outcome_id,
            claim_id=third.claim.claim_id,
            attempt_id=third.claim.attempt_id,
            task_id=third.task_id,
            expected_last_reviewed_commit=third.last_reviewed_commit,
            disposition="normal-return",
            request=RetryDelivery(
                action="retry",
                outcome_id=third.outcome_id,
                claim_id=third.claim.claim_id,
                attempt_id=third.claim.attempt_id,
                abandoned_commit=_git(third.worktree_path, "rev-parse", "HEAD"),
                failure_code="builder-failed",
            ),
        ),
        host_id=third.claim.owner_id,
        session_id=third.claim.process_id,
    )

    assert _workspace_content_snapshot(launch.worktree_path) == workspace
    binding = runtime.show_binding(launch.outcome_id)
    assert binding.block is not None
    assert "three-attempt limit" in binding.block.reason
    episodes = runtime.retry_ledger().read().episodes
    assert len(episodes) == 1
    assert episodes[0].total_attempts == 3
    assert episodes[0].attempt_ids == tuple(attempt_ids)
    assert [_owner_failure_code(state_root, "change-a", attempt) for attempt in attempt_ids] == [
        "worker-host-lost",
        "worker-released-stuck",
        "builder-failed",
    ]
    now[0] = _iso(start + timedelta(hours=8))
    assert application.acquire_change_action(_continuation_request(application, "change-a")).launch is None
    view = application.show_work_item_view("change-a", "outcome:OUT-001")
    assert view.readiness is not None
    assert view.readiness.reason_code == "retry-exhausted"


@pytest.mark.parametrize("mode", ["host-lost", "released-stuck"])
def test_ended_finalizer_settles_as_reported_attention_and_retries_under_one_budget(tmp_path: Path, mode: str) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, _runtimes, coordinator, state_root, probe = _stall_portfolio(
        tmp_path, {"change-a": DeliveryStage.COMPLETED}, now
    )
    first = application.acquire_change_action(_continuation_request(application))
    assert first.finalization is not None
    attempt = first.finalization.attempt
    issuer = json.loads(_issuer_path(state_root, "change-a", attempt.writer.attempt_id).read_bytes())
    assert (issuer["role"], issuer["outcome_id"], issuer["claim_id"]) == ("finalizer", None, attempt.writer.claim_id)
    forged_report = ReportFinalizationFailure(
        change_id="change-a",
        expected_contract_digest=attempt.contract_digest,
        expected_frontier_digest=attempt.frontier_digest,
        expected_change_head=attempt.exact_head,
        expected_reviewed_head=coordinator.show("change-a").last_reviewed_commit,
        expected_diagnostic_sequence=0,
        attempt_key=attempt.writer.attempt_id,
        category="worker-ended",
        code=FinalizationFailureCode.FINALIZER_ENDED_WITHOUT_REPORT,
        checks_state="unknown",
    )
    with pytest.raises(FinalizationReportError):
        application.report_finalization_failure(forged_report)
    with pytest.raises(ValidationError):
        ReportFinalizationFailure.model_validate_json(
            json.dumps({**forged_report.model_dump(mode="json"), "checks_state": "failed"})
        )
    now[0] = _iso(start + timedelta(minutes=10))

    if mode == "host-lost":
        probe.states[_HOST] = "gone"
        application.acquire_frontier_work()
        probe.states[_HOST] = "alive"
    else:
        released = application.release_stuck_worker(
            "change-a", None, attempt.writer.attempt_id, attempt.writer.claim_id
        )
        assert isinstance(released, FinalizerSettlementReceipt)
        assert (
            application.release_stuck_worker("change-a", None, attempt.writer.attempt_id, attempt.writer.claim_id)
            == released
        )

    receipt = application._read_finalizer_settlement_receipt("change-a", attempt.writer.attempt_id)
    assert receipt is not None
    assert isinstance(receipt.settlement, FinalizerEngineSettlement)
    assert receipt.settlement.disposition == mode
    assert receipt.settlement.outcome == "ended-without-report"
    request = receipt.report.request
    assert (request.category, request.code, request.checks_state) == (
        "worker-ended",
        FinalizationFailureCode.FINALIZER_ENDED_WITHOUT_REPORT,
        "unknown",
    )
    attention = coordinator.show("change-a").finalization_attention
    assert attention is not None
    assert attention.outcome == "ended-without-report"
    assert _owner_failure_code(state_root, "change-a", attempt.writer.attempt_id) == "finalizer-ended-without-report"
    with pytest.raises(DeliveryActionBusyError):
        application.finalize_change(
            "change-a",
            _finalization_request("change-a", attempt.exact_head, attempt.writer.attempt_id),
        )
    with pytest.raises(DeliveryActionSelectionConflictError):
        application.settle_finalizer_invocation(receipt.settlement)

    now[0] = _iso(start + timedelta(hours=2))
    retry = application.acquire_change_action(
        _continuation_request(application, host_id="retry-host", session_id="retry-session")
    )
    assert retry.kind == "acquired", retry
    assert retry.finalization is not None
    second = retry.finalization.attempt
    assert second.writer.attempt_id != attempt.writer.attempt_id
    assert second.exact_head == attempt.exact_head
    episodes = RetryLedger(state_root, "change-a").read().episodes
    assert len(episodes) == 1
    assert episodes[0].total_attempts == 2
    assert {attempt.writer.attempt_id, second.writer.attempt_id} <= set(episodes[0].attempt_ids)
