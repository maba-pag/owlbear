"""``delivery-controller``: immutable releases, pin enforcement, preflight custody and upgrade fences (N02-D)."""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import shutil
import stat
import subprocess
import sys
import textwrap
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from serve.delivery.tests.test_state_formats import _portfolio

from owlbear_delivery import close_delivery_application, load_delivery_application, release_integrity
from owlbear_delivery.delivery_application_loader import DeliveryStateVersionError
from owlbear_delivery.state_formats import SUPPORTED_FORMAT, record_tree_digest
from owlbear_delivery.storage_io import acquire_controller_lock
from owlbear_tools import delivery_controller
from owlbear_tools.delivery_controller import ControllerError, Layout, ProcessRow

_REPO = Path(__file__).resolve().parents[3]
_PACKAGES = ("delivery", "delivery-mcp", "delivery-github", "cockpit", "tools")
_SOURCES = tuple(f"serve/{package}/src" for package in _PACKAGES)
_NOW = datetime(2026, 10, 4, tzinfo=UTC)


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(  # noqa: S603 - fixed Git argument vector.
        ("git", "-C", str(repository), *arguments),  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture(scope="module")
def source(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, list[str]]:
    """A clone-shaped repository holding the real controller packages, with three release commits."""
    repository = tmp_path_factory.mktemp("source") / "owlbear"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "Controller Test")
    _git(repository, "config", "user.email", "controller@example.invalid")
    for relative in _SOURCES:
        shutil.copytree(_REPO / relative, repository / relative, ignore=shutil.ignore_patterns("__pycache__"))
    (repository / "serve/cockpit/web").mkdir(parents=True)
    shutil.copyfile(_REPO / "serve/cockpit/web/.nvmrc", repository / "serve/cockpit/web/.nvmrc")
    commits = []
    for index in range(3):
        (repository / "release.txt").write_text(f"release {index}\n", encoding="utf-8")
        _git(repository, "add", "-A")
        _git(repository, "commit", "-q", "-m", f"release {index}")
        commits.append(_git(repository, "rev-parse", "HEAD"))
    return repository, commits


class ShimToolchain:
    """A release interpreter that imports only the release tree's packages (below the release owner)."""

    def sync(self, tree: Path) -> None:
        python = tree / ".venv/bin/python"
        python.parent.mkdir(parents=True)
        paths = [str(tree / relative) for relative in _SOURCES]
        python.write_text(
            f"#!{sys.executable}\n"
            + textwrap.dedent(
                f"""
                import runpy, sys
                sys.path[:0] = {paths!r}
                arguments = [argument for argument in sys.argv[1:] if argument not in {{"-I", "-B", "-S"}}]
                if arguments[0] == "-m":
                    sys.argv = [arguments[1], *arguments[2:]]
                    runpy.run_module(arguments[1], run_name="__main__", alter_sys=True)
                else:
                    sys.argv = ["-c", *arguments[2:]]
                    exec(compile(arguments[1], "<string>", "exec"), {{"__name__": "__main__"}})
                """
            ),
            encoding="utf-8",
        )
        python.chmod(0o755)

    def build_bundle(self, tree: Path) -> None:
        dist = tree / "serve/cockpit/dist"
        dist.mkdir(parents=True)
        (dist / "index.html").write_text("<!doctype html><title>Cockpit</title>\n", encoding="utf-8")


def _stopped() -> list[ProcessRow]:
    return []


def _install(layout: Layout, source: Path, commit: str) -> dict[str, Any]:
    return delivery_controller.install(layout, commit, source=source, toolchain=ShimToolchain(), now=lambda: _NOW)


def _pin(layout: Layout, commit: str, *, first: bool) -> dict[str, Any]:
    return delivery_controller.pin(layout, commit, first=first, processes=_stopped, now=lambda: _NOW)


def _workspace(tmp_path: Path) -> tuple[Layout, Any]:
    repository, config = _portfolio(tmp_path)
    return Layout(repository), config


def _mark(layout: Layout, format_value: int = SUPPORTED_FORMAT) -> None:
    marker = layout.runtime / "format.json"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps({"format": format_value}), encoding="utf-8")


def _controller_state(layout: Layout) -> dict[str, bytes]:
    return {
        path.relative_to(layout.root).as_posix(): path.read_bytes()
        for path in sorted(layout.root.rglob("*"))
        if path.is_file() and "releases" not in path.parts and path.name != ".maintenance.lock"
    }


# ---------------------------------------------------------------------------
# Release integrity
# ---------------------------------------------------------------------------


def test_install_builds_a_read_only_release_whose_digest_detects_any_modification(
    tmp_path: Path, source: tuple[Path, list[str]]
) -> None:
    repository, commits = source
    layout, _config = _workspace(tmp_path)

    installed = _install(layout, repository, commits[0])

    release = installed["release"]
    assert (release["commit"], release["supported_format"]) == (commits[0], SUPPORTED_FORMAT)
    assert release["bundle"]["origin"] == "built"
    assert delivery_controller.verify(layout, commits[0])["failures"] == []
    assert _install(layout, repository, commits[0])["reused"] is True
    tree = layout.release(commits[0])
    with pytest.raises(PermissionError):
        (tree / "release.txt").write_text("tampered\n", encoding="utf-8")
    module = tree / "serve/delivery/src/owlbear_delivery/state_formats.py"
    module.chmod(0o644)
    module.write_bytes(module.read_bytes() + b"\n# tampered\n")
    failures = delivery_controller.verify(layout, commits[0])["failures"]
    assert any("modified after install" in failure for failure in failures)
    assert any("writable entries" in failure for failure in failures)
    with pytest.raises(ControllerError) as refused:
        _install(layout, repository, commits[0])
    assert refused.value.code == "release-invalid"


def test_an_interrupted_install_is_rebuilt_and_an_unknown_revision_is_refused(
    tmp_path: Path, source: tuple[Path, list[str]]
) -> None:
    repository, commits = source
    layout, _config = _workspace(tmp_path)
    partial = layout.release(commits[1])
    partial.mkdir(parents=True)
    (partial / "half-extracted").write_text("", encoding="utf-8")

    installed = _install(layout, repository, commits[1])

    assert installed["reused"] is False
    assert not (partial / "half-extracted").exists()
    with pytest.raises(ControllerError) as refused:
        _install(layout, repository, "no-such-revision")
    assert refused.value.code == "commit-unknown"


def test_install_refuses_a_bundle_without_the_pinned_node(
    tmp_path: Path, source: tuple[Path, list[str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, commits = source
    layout, _config = _workspace(tmp_path)
    monkeypatch.setattr(delivery_controller.shutil, "which", lambda _name: None)
    toolchain = delivery_controller.UvNodeToolchain()

    with pytest.raises(ControllerError) as refused:
        delivery_controller.install(layout, commits[0], source=repository, toolchain=toolchain)

    assert refused.value.code == "bundle-unavailable"
    assert delivery_controller.read_release(layout, commits[0]) is None


# ---------------------------------------------------------------------------
# Pin, launchers and code origin (I6)
# ---------------------------------------------------------------------------


async def _mcp_health(launcher: Path, workspace: Path) -> dict[str, Any]:
    parameters = StdioServerParameters(command=str(launcher), args=[], cwd=str(workspace), env=dict(os.environ))
    async with stdio_client(parameters) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        result = await session.call_tool("delivery_health", {})
    return json.loads(result.content[0].text)  # type: ignore[union-attr]


def test_pin_writes_launchers_that_run_release_code_and_refuse_checkout_code(
    tmp_path: Path, source: tuple[Path, list[str]]
) -> None:
    repository, commits = source
    layout, config = _workspace(tmp_path)
    _install(layout, repository, commits[0])

    pinned = _pin(layout, commits[0], first=True)

    assert pinned == {"status": "pinned", "commit": commits[0], "previous": None}
    assert delivery_controller.verify(layout)["verified"] is True
    health = asyncio.run(asyncio.wait_for(_mcp_health(layout.bin / "delivery-mcp", layout.workspace), 60))
    assert health["status"] == "healthy"
    assert delivery_controller.verify(layout)["verified"] is True
    digests = record_tree_digest(layout.workspace)
    with pytest.raises(DeliveryStateVersionError) as refused:
        load_delivery_application(config, workspace_root=layout.workspace)
    assert refused.value.code == "controller-not-pinned"
    assert record_tree_digest(layout.workspace) == digests


def test_a_hand_edited_launcher_fails_verification(tmp_path: Path, source: tuple[Path, list[str]]) -> None:
    repository, commits = source
    layout, _config = _workspace(tmp_path)
    _install(layout, repository, commits[0])
    _pin(layout, commits[0], first=True)
    launcher = layout.bin / "delivery-mcp"
    launcher.chmod(0o755)
    launcher.write_text("#!/bin/sh\nexec uv run python -m owlbear_delivery_mcp\n", encoding="utf-8")

    result = delivery_controller.verify(layout)

    assert result["verified"] is False
    assert result["failures"] == ["launcher bin/delivery-mcp does not exec the pinned release"]


def _tamper(layout: Layout, commit: str, marker: Path) -> None:
    """Modify one release module so that importing it would leave ``marker`` behind."""
    module = layout.release(commit) / "serve/delivery/src/owlbear_delivery/__init__.py"
    module.chmod(0o644)
    module.write_bytes(module.read_bytes() + f"\nopen({str(marker)!r}, 'w').close()\n".encode())


@pytest.mark.parametrize("launcher", delivery_controller.LAUNCHERS)
def test_a_launcher_refuses_a_modified_release_before_importing_any_of_its_code(
    tmp_path: Path, source: tuple[Path, list[str]], launcher: str
) -> None:
    repository, commits = source
    layout, _config = _workspace(tmp_path)
    _install(layout, repository, commits[0])
    _pin(layout, commits[0], first=True)
    marker = tmp_path / "imported"
    _tamper(layout, commits[0], marker)
    digests = record_tree_digest(layout.workspace)

    completed = subprocess.run(  # noqa: S603 - the generated launcher of this test's workspace.
        (str(layout.bin / launcher),),
        cwd=layout.workspace,
        env={**os.environ, "COCKPIT_NO_OPEN": "1"},
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert completed.returncode == 78
    assert completed.stderr.startswith(f"controller-release-invalid: controller release {layout.release(commits[0])}")
    assert "modified after install" in completed.stderr
    assert not marker.exists()
    assert record_tree_digest(layout.workspace) == digests
    assert delivery_controller.verify(layout)["verified"] is False


_ENTRY_PROBE = """
import asyncio, json
from pathlib import Path
from owlbear_cockpit.target_context import load_target_context
from owlbear_delivery import load_delivery_application
from owlbear_delivery.delivery_application_loader import DeliveryApplicationLoadError, DeliveryStartupConfig
from owlbear_delivery_mcp.server import app_lifespan, mcp
root = Path.cwd()
refusals = {}
config = DeliveryStartupConfig.model_validate_json((root / ".owlbear/delivery/config.json").read_bytes())
try:
    load_delivery_application(config, workspace_root=root)
except DeliveryApplicationLoadError as exc:
    refusals["loader"] = exc.detail
try:
    load_target_context(root)
except RuntimeError as exc:
    refusals["cockpit"] = str(exc)
async def start():
    async with app_lifespan(mcp):
        pass
try:
    asyncio.run(start())
except Exception as exc:
    refusals["mcp"] = getattr(exc, "detail", str(exc))
print(json.dumps(refusals))
"""


def test_every_entry_that_bypasses_a_launcher_refuses_a_modified_release_before_reading_state(
    tmp_path: Path, source: tuple[Path, list[str]]
) -> None:
    repository, commits = source
    layout, _config = _workspace(tmp_path)
    _install(layout, repository, commits[0])
    _pin(layout, commits[0], first=True)
    module = layout.release(commits[0]) / "serve/cockpit/src/owlbear_cockpit/target_context.py"
    module.chmod(0o644)
    module.write_bytes(module.read_bytes() + b"\n# modified after install\n")
    digests = record_tree_digest(layout.workspace)

    completed = subprocess.run(  # noqa: S603 - the release interpreter runs a fixed probe.
        (str(layout.release(commits[0]) / ".venv/bin/python"), "-I", "-B", "-c", _ENTRY_PROBE),
        cwd=layout.workspace,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

    refusals = json.loads(completed.stdout)
    assert sorted(refusals) == ["cockpit", "loader", "mcp"], completed.stderr
    for detail in refusals.values():
        assert "controller-release-invalid: controller release" in detail
        assert "modified after install" in detail
    assert record_tree_digest(layout.workspace) == digests


def test_switch_records_previous_rolls_back_and_prune_keeps_current_and_previous(
    tmp_path: Path, source: tuple[Path, list[str]]
) -> None:
    repository, commits = source
    layout, _config = _workspace(tmp_path)
    _mark(layout)
    for commit in commits:
        _install(layout, repository, commit)
    _pin(layout, commits[0], first=True)

    assert _pin(layout, commits[1], first=False)["previous"] == commits[0]
    rolled_back = _pin(layout, commits[0], first=False)
    pruned = delivery_controller.prune(layout, processes=_stopped)

    assert rolled_back["previous"] == commits[1]
    assert pruned["kept"] == sorted(commits[:2])
    assert pruned["removed"] == [commits[2]]
    assert sorted(path.name for path in layout.releases.iterdir()) == sorted(commits[:2])
    listing = delivery_controller.list_releases(layout)
    assert {row["commit"]: row["role"] for row in listing["releases"]} == {
        commits[0]: "current",
        commits[1]: "previous",
    }
    assert delivery_controller.verify(layout)["verified"] is True


def _unexpected_digest(_tree: Path) -> str:
    msg = "an unchanged pinned release is not re-hashed at start"
    raise AssertionError(msg)


def test_an_unchanged_release_starts_without_rehashing_and_an_edit_with_restored_times_is_refused(
    tmp_path: Path, source: tuple[Path, list[str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, commits = source
    layout, _config = _workspace(tmp_path)
    _install(layout, repository, commits[0])
    _pin(layout, commits[0], first=True)
    pinned = delivery_controller.current_pin(layout)
    assert pinned is not None
    release = layout.release(commits[0])
    anchors = (pinned.release_sha256, pinned.release_stat_sha256)
    with monkeypatch.context() as patched:
        patched.setattr(release_integrity, "tree_digest", _unexpected_digest)
        assert release_integrity.release_failures(release, *anchors) == []
    assert delivery_controller.verify(layout)["fast_start"] is True
    module = release / "serve/delivery/src/owlbear_delivery/state_formats.py"
    times = module.stat()
    module.chmod(0o644)
    module.write_bytes(module.read_bytes().replace(b"Registry", b"registry", 1))
    module.chmod(times.st_mode)
    os.utime(module, ns=(times.st_atime_ns, times.st_mtime_ns))

    failures = release_integrity.release_failures(release, *anchors)

    assert failures == ["the release tree was modified after install (tree digest differs)"]
    assert delivery_controller.verify(layout)["fast_start"] is False
    assert delivery_controller.verify(layout)["verified"] is False


def test_verify_detects_a_changed_interpreter_and_a_release_record_the_pin_does_not_name(
    tmp_path: Path, source: tuple[Path, list[str]]
) -> None:
    repository, commits = source
    layout, _config = _workspace(tmp_path)
    installed = _install(layout, repository, commits[0])
    _pin(layout, commits[0], first=True)
    interpreter = installed["release"]["interpreter"]
    assert interpreter == release_integrity.interpreter_identity()
    record = layout.release(commits[0]) / release_integrity.RELEASE_FILE
    payload = json.loads(record.read_text(encoding="utf-8"))
    payload["interpreter"]["sha256"] = "0" * 64
    record.chmod(0o644)
    record.write_text(json.dumps(payload), encoding="utf-8")

    failures = delivery_controller.verify(layout)["failures"]

    assert f"the interpreter {interpreter['path']} of release {commits[0]} changed after install" in failures
    assert f"pin.json does not name the RELEASE.json of release {commits[0]}" in failures


def test_prune_belongs_to_the_stopped_interval_after_switch_and_verify(
    tmp_path: Path, source: tuple[Path, list[str]]
) -> None:
    repository, commits = source
    layout, _config = _workspace(tmp_path)
    _mark(layout)
    for commit in commits:
        _install(layout, repository, commit)
    _pin(layout, commits[0], first=True)
    _pin(layout, commits[1], first=False)
    assert delivery_controller.verify(layout)["verified"] is True

    pruned = delivery_controller.prune(layout, processes=_stopped)
    restarted = acquire_controller_lock(layout.runtime)
    try:
        with pytest.raises(ControllerError) as refused:
            delivery_controller.prune(layout, processes=_stopped)
    finally:
        restarted.release()

    assert (pruned["kept"], pruned["removed"]) == (sorted(commits[:2]), [commits[2]])
    assert refused.value.code == "controller-running"
    assert sorted(path.name for path in layout.releases.iterdir()) == sorted(commits[:2])
    assert delivery_controller.verify(layout)["verified"] is True
    assert delivery_controller.verify(layout, commits[0])["verified"] is True


def test_pin_and_switch_refuse_without_changing_the_pin(tmp_path: Path, source: tuple[Path, list[str]]) -> None:
    repository, commits = source
    layout, _config = _workspace(tmp_path)
    _install(layout, repository, commits[0])
    _install(layout, repository, commits[1])
    with pytest.raises(ControllerError) as unpinned:
        _pin(layout, commits[0], first=False)
    _pin(layout, commits[0], first=True)
    pinned = _controller_state(layout)
    _mark(layout, SUPPORTED_FORMAT + 1)

    refusals = []
    for commit, first in ((commits[1], False), (commits[1], True), (commits[0], False), (commits[2], False)):
        with pytest.raises(ControllerError) as refused:
            _pin(layout, commit, first=first)
        refusals.append(refused.value.code)

    assert unpinned.value.code == "not-pinned"
    assert refusals == ["release-refuses-state", "already-pinned", "already-current", "release-invalid"]
    assert _controller_state(layout) == pinned


def test_a_release_without_a_capability_gate_cannot_be_pinned(tmp_path: Path, source: tuple[Path, list[str]]) -> None:
    repository, commits = source
    ungated = tmp_path / "ungated"
    _git(repository, "worktree", "add", "-q", "--detach", str(ungated), commits[0])
    (ungated / "serve/delivery/src/owlbear_delivery/state_formats.py").unlink()
    for package in (
        "delivery/src/owlbear_delivery",
        "delivery-mcp/src/owlbear_delivery_mcp",
        "cockpit/src/owlbear_cockpit",
        "tools/src/owlbear_tools",
    ):
        (ungated / "serve" / package / "__init__.py").write_text("", encoding="utf-8")
    _git(ungated, "commit", "-q", "-am", "synthetic pre-N02-A release without a capability gate")
    commit = _git(ungated, "rev-parse", "HEAD")
    layout, _config = _workspace(tmp_path)
    _install(layout, repository, commit)

    with pytest.raises(ControllerError) as refused:
        _pin(layout, commit, first=True)

    assert refused.value.code == "release-ungated"
    assert not layout.pin.exists()


# ---------------------------------------------------------------------------
# Fences: running controllers, the N02 controller lock and concurrent upgrades
# ---------------------------------------------------------------------------


def _fenced_commands(layout: Layout, commit: str, backup: Path, processes: Any) -> dict[str, Any]:
    return {
        "switch": lambda: delivery_controller.pin(layout, commit, first=False, processes=processes),
        "prune": lambda: delivery_controller.prune(layout, processes=processes),
        "preflight": lambda: delivery_controller.preflight(layout, processes=processes),
        "backup": lambda: delivery_controller.backup(layout, backup, processes=processes),
    }


def test_upgrade_steps_refuse_while_a_gated_controller_holds_the_shared_lock(
    tmp_path: Path, source: tuple[Path, list[str]]
) -> None:
    repository, commits = source
    layout, _config = _workspace(tmp_path)
    _install(layout, repository, commits[0])
    _install(layout, repository, commits[1])
    _pin(layout, commits[0], first=True)
    pinned = _controller_state(layout)
    holder = acquire_controller_lock(layout.runtime)
    try:
        codes = {}
        for name, command in _fenced_commands(layout, commits[1], tmp_path / "backup", _stopped).items():
            with pytest.raises(ControllerError) as refused:
                command()
            codes[name] = refused.value.code
    finally:
        holder.release()

    assert set(codes.values()) == {"controller-running"}
    assert _controller_state(layout) == pinned
    assert not (tmp_path / "backup").exists()
    assert delivery_controller.pin(layout, commits[1], first=False, processes=_stopped)["previous"] == commits[0]


@pytest.mark.parametrize(
    ("row", "code"),
    [
        (ProcessRow(41, "python3.14", ("python", "-m", "owlbear_delivery_mcp"), "{workspace}"), "controller-running"),
        (ProcessRow(42, "uv", ("uv", "run", "cockpit"), "{workspace}/serve"), "controller-running"),
        (
            ProcessRow(43, "sh", ("/bin/sh", "{workspace}/.owlbear/controller/bin/cockpit"), "{workspace}"),
            "controller-running",
        ),
        (ProcessRow(44, "python3.14", ("python", "-m", "owlbear_cockpit"), None), "controller-unknown"),
        (ProcessRow(45, "python3.14", None, None), "controller-unknown"),
    ],
    ids=["d03-mcp", "uv-cockpit", "launcher", "unreadable-cwd", "unreadable-cmdline"],
)
def test_an_ungated_or_uninspectable_controller_process_blocks_every_fenced_step(
    tmp_path: Path, row: ProcessRow, code: str
) -> None:
    layout, _config = _workspace(tmp_path)
    workspace = str(layout.workspace)
    shaped = ProcessRow(
        row.pid,
        row.name,
        None if row.cmdline is None else tuple(part.format(workspace=workspace) for part in row.cmdline),
        None if row.cwd is None else row.cwd.format(workspace=workspace),
    )
    elsewhere = ProcessRow(50, "python3.14", ("python", "-m", "owlbear_delivery_mcp"), f"{workspace}-lane-b")
    digests = record_tree_digest(layout.workspace)

    for command in _fenced_commands(layout, "a" * 40, tmp_path / "backup", lambda: [elsewhere, shaped]).values():
        with pytest.raises(ControllerError) as refused:
            command()
        assert refused.value.code == code

    assert delivery_controller.running_controllers(layout.workspace, lambda: [elsewhere]) == []
    assert record_tree_digest(layout.workspace) == digests


def test_a_held_migration_fence_refuses_preflight_and_a_concurrent_upgrade_refuses(tmp_path: Path) -> None:
    layout, _config = _workspace(tmp_path)
    migration = acquire_controller_lock(layout.runtime, exclusive=True)
    try:
        with pytest.raises(ControllerError) as fenced:
            delivery_controller.preflight(layout, processes=_stopped)
    finally:
        migration.release()
    holder = subprocess.Popen(  # noqa: S603 - fixed interpreter and argument vector.
        (sys.executable, "-c", _MAINTENANCE_HOLDER, str(layout.workspace)),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert holder.stdout is not None
        assert holder.stdout.readline() == "held\n"
        code, payload = delivery_controller.run(["--project-root", str(layout.workspace), "preflight"])
    finally:
        assert holder.stdin is not None
        holder.stdin.close()
        holder.wait(timeout=10)

    assert fenced.value.code == "controller-running"
    assert (code, payload["code"]) == (1, "upgrade-in-progress")


_MAINTENANCE_HOLDER = """
import sys
from pathlib import Path
from owlbear_tools.delivery_controller import Layout, maintenance_lock
with maintenance_lock(Layout(Path(sys.argv[1]))):
    print("held", flush=True)
    sys.stdin.read()
"""


def test_a_pinned_controller_is_fenced_by_an_upgrade_and_an_unverified_migration_blocks_preflight(
    tmp_path: Path, source: tuple[Path, list[str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, commits = source
    layout, config = _workspace(tmp_path)
    _install(layout, repository, commits[0])
    _pin(layout, commits[0], first=True)
    module = layout.release(commits[0]) / "serve/delivery/src/owlbear_delivery/delivery_application_loader.py"
    from owlbear_delivery import delivery_application_loader  # noqa: PLC0415

    monkeypatch.setattr(delivery_application_loader, "__file__", str(module))
    upgrade = acquire_controller_lock(layout.runtime, exclusive=True)
    try:
        with pytest.raises(delivery_application_loader.DeliveryApplicationLoadError) as fenced:
            load_delivery_application(config, workspace_root=layout.workspace)
    finally:
        upgrade.release()
    application = load_delivery_application(config, workspace_root=layout.workspace)
    close_delivery_application(application)
    journal = layout.runtime / "migrations" / ("c" * 64) / "journal.json"
    journal.parent.mkdir(parents=True)
    journal.write_text(json.dumps({"schema_version": 1, "migration_id": "c" * 64, "state": "applied"}), "utf-8")

    report = delivery_controller.preflight(layout, processes=_stopped)

    assert fenced.value.code == "controller-fenced"
    assert report["ready"] is False
    assert [row["code"] for row in report["blockers"]] == ["state-migration-incomplete"]


# ---------------------------------------------------------------------------
# Preflight custody classification (D6)
# ---------------------------------------------------------------------------

_CHANGE = "runtime/changes/demo"
_OPERATION = "continue-" + "d" * 64


def _record(layout: Layout, locator: str, payload: object) -> None:
    path = layout.workspace / ".owlbear/delivery" / locator
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _claim(layout: Layout) -> None:
    claim = {"attempt_id": "attempt-1", "claim_id": "claim-1", "worker_role": "builder"}
    _record(layout, f"{_CHANGE}/frontier.json", {"schema_version": 18, "bindings": [{"active_claim": claim}]})
    window = {"pid": 4242, "create_time": 1.0, "name": "Code Helper"}
    _record(layout, f"{_CHANGE}/claim-issuers/attempt-1.json", {"schema_version": 1, "window": window})


def _coordination(layout: Layout, **fields: object) -> None:
    _record(layout, "runtime/coordination/changes/demo.json", {"schema_version": 2, "change_id": "demo", **fields})


def _publication(status: str) -> dict[str, object]:
    return {"schema_version": 1, "status": status, "frontier_digest": "e" * 64}


def _retained(layout: Layout, reason: str) -> None:
    _coordination(layout, continuation_action={"operation_id": _OPERATION, "kind": "sync-target", "finished_at": None})
    _record(layout, f"{_CHANGE}/action-receipts/{_OPERATION}/intent.json", {})
    _record(layout, f"{_CHANGE}/action-receipts/{_OPERATION}/started.json", {})
    _record(layout, f"{_CHANGE}/action-receipts/{_OPERATION}/result.json", {"kind": "blocked", "reason_code": reason})


_CUSTODY = {
    "running-claim": (_claim, "alive", ["claim-running"], []),
    "unknown-window": (_claim, "unknown", ["claim-running"], []),
    "host-lost-claim": (_claim, "gone", [], ["claim-host-lost"]),
    "started-action": (
        lambda layout: _record(layout, f"{_CHANGE}/action-receipts/{_OPERATION}/started.json", {}),
        "gone",
        ["engine-action-started"],
        [],
    ),
    "interrupted-action": (
        lambda layout: _retained(layout, "engine-action-interrupted"),
        "gone",
        ["engine-action-interrupted"],
        ["engine-action-retained"],
    ),
    "failed-action": (
        lambda layout: _retained(layout, "engine-action-failed"),
        "gone",
        [],
        ["engine-action-retained", "engine-action-failed"],
    ),
    "pending-publication": (
        lambda layout: _record(layout, f"{_CHANGE}/state-publication.json", _publication("pending")),
        "gone",
        ["pending-state-publication"],
        [],
    ),
    "acknowledged-publication": (
        lambda layout: _record(layout, f"{_CHANGE}/state-publication.json", _publication("acknowledged")),
        "gone",
        [],
        [],
    ),
    "unreadable-publication": (
        lambda layout: _record(layout, f"{_CHANGE}/state-publication.json", {"schema_version": 1}),
        "gone",
        ["custody-unknown"],
        [],
    ),
    "pending-checkpoint": (
        lambda layout: _record(
            layout,
            f"{_CHANGE}/frontier.json",
            {"schema_version": 18, "bindings": [], "pending_checkpoint": {"head": "x"}},
        ),
        "gone",
        ["pending-checkpoint"],
        [],
    ),
    "publication-lease": (
        lambda layout: _coordination(layout, publication_lease={"owner_id": "o"}),
        "gone",
        ["publication-in-flight"],
        [],
    ),
    "unreceipted-summary": (
        lambda layout: _record(
            layout, "runtime/publications/pull-requests/summary-operations/demo--op.json", {"schema_version": 1}
        ),
        "gone",
        ["publication-unreceipted"],
        [],
    ),
    "pending-transaction": (
        lambda layout: (
            (layout.runtime / "transactions").mkdir(parents=True)
            or (layout.runtime / "transactions/op.yaml").write_text("x: 1\n", encoding="utf-8")
        ),
        "gone",
        ["transaction-pending"],
        [],
    ),
    "passive-custody": (
        lambda layout: _coordination(layout, builder_handoff={"change_id": "demo"}),
        "gone",
        [],
        [],
    ),
}


@pytest.mark.parametrize("case", sorted(_CUSTODY))
def test_preflight_blocks_exactly_the_d6_custody_shapes_and_changes_nothing(tmp_path: Path, case: str) -> None:
    layout, _config = _workspace(tmp_path)
    _mark(layout)
    seed, window, blockers, attention = _CUSTODY[case]
    seed(layout)
    digests = record_tree_digest(layout.workspace)

    report = delivery_controller.preflight(layout, processes=_stopped, window_state=lambda _window: window)

    assert [row["code"] for row in report["blockers"]] == blockers
    assert [row["code"] for row in report["attention"]] == attention
    assert report["ready"] is (not blockers)
    assert record_tree_digest(layout.workspace) == digests


def test_preflight_reports_an_unmigrated_workspace_as_attention_only(tmp_path: Path) -> None:
    layout, _config = _workspace(tmp_path)
    _record(layout, f"{_CHANGE}/frontier.json", {"schema_version": 18, "bindings": []})

    code, report = delivery_controller.run(["--project-root", str(layout.workspace), "preflight"])

    assert (code, report["ready"], report["format"]) == (0, True, 0)
    assert [row["code"] for row in report["attention"]] == ["migration-required"]


def _without_blocking(fifo: Path, command: Any) -> Any:
    """Run ``command`` in a thread; a reader still blocked on ``fifo`` after 10 s is released and fails the test."""
    with ThreadPoolExecutor(1) as pool:
        future = pool.submit(command)
        try:
            return future.result(timeout=10)
        finally:
            with contextlib.suppress(OSError):
                os.close(os.open(fifo, os.O_WRONLY | os.O_NONBLOCK))


@pytest.mark.parametrize(
    "locator",
    [
        f"{_CHANGE}/state-publication.json",
        f"{_CHANGE}/frontier.json",
        f"{_CHANGE}/claim-issuers/attempt-1.json",
        "runtime/coordination/changes/demo.json",
    ],
    ids=["state-publication", "frontier", "claim-issuer", "coordination"],
)
def test_preflight_refuses_a_fifo_record_without_blocking_under_the_controller_lock(
    tmp_path: Path, locator: str
) -> None:
    layout, _config = _workspace(tmp_path)
    _mark(layout)
    if "claim-issuers" in locator:
        _claim(layout)
        (layout.workspace / ".owlbear/delivery" / locator).unlink()
    fifo = layout.workspace / ".owlbear/delivery" / locator
    fifo.parent.mkdir(parents=True, exist_ok=True)
    os.mkfifo(fifo)

    report = _without_blocking(
        fifo, lambda: delivery_controller.preflight(layout, processes=_stopped, window_state=lambda _w: "gone")
    )

    assert report["ready"] is False
    codes = {row["code"] for row in report["blockers"]}
    assert codes & {"custody-unknown", "claim-running"}
    assert stat.S_ISFIFO(fifo.lstat().st_mode)
    assert _exclusive_controller_lock_free(layout)


def test_backup_refuses_a_fifo_record_without_blocking(tmp_path: Path) -> None:
    layout, _config = _workspace(tmp_path)
    _mark(layout)
    fifo = layout.workspace / ".owlbear/delivery" / _CHANGE / "frontier.json"
    fifo.parent.mkdir(parents=True)
    os.mkfifo(fifo)

    with pytest.raises(ControllerError) as refused:
        _without_blocking(fifo, lambda: delivery_controller.backup(layout, tmp_path / "backup", processes=_stopped))

    assert refused.value.code == "backup-invalid"
    assert not (tmp_path / "backup").exists()


def _exclusive_controller_lock_free(layout: Layout) -> bool:
    acquire_controller_lock(layout.runtime, exclusive=True).release()
    return True


# ---------------------------------------------------------------------------
# Backup (procedure step 4)
# ---------------------------------------------------------------------------


def test_backup_copies_state_and_delivery_refs_outside_the_repository(tmp_path: Path) -> None:
    layout, _config = _workspace(tmp_path)
    _mark(layout)
    _record(layout, f"{_CHANGE}/frontier.json", {"schema_version": 18, "bindings": []})
    (layout.workspace / ".owlbear/delivery/worktrees/demo").mkdir(parents=True)
    _git(layout.workspace, "update-ref", "refs/heads/owlbear/change/demo", "HEAD")
    _git(layout.workspace, "update-ref", "refs/remotes/origin/owlbear/delivery-state", "HEAD")
    _git(layout.workspace, "update-ref", "refs/remotes/origin/feature", "HEAD")

    result = delivery_controller.backup(layout, tmp_path / "backup", processes=_stopped)

    backup = tmp_path / "backup"
    assert result["refs"] == 2
    assert not (backup / "delivery/worktrees").exists()
    assert json.loads((backup / "manifest.json").read_text(encoding="utf-8")).keys() >= {
        "config.json",
        f"{_CHANGE}/frontier.json",
    }
    refs = (backup / "refs.txt").read_text(encoding="utf-8")
    assert "refs/heads/owlbear/change/demo" in refs
    assert "refs/remotes/origin/feature" not in refs
    _git(layout.workspace, "bundle", "verify", str(backup / "delivery-refs.bundle"))
    for destination in (backup, layout.workspace / "backup"):
        with pytest.raises(ControllerError) as refused:
            delivery_controller.backup(layout, destination, processes=_stopped)
        assert refused.value.code == "backup-invalid"
