"""Focused contracts for the stdlib-only offline Delivery diagnostic."""

from __future__ import annotations

import errno
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import owlbear_tools.delivery_diagnostics as diagnostics
from owlbear_tools.delivery_diagnostics import (
    MAX_ENTRIES,
    MAX_RECORD_BYTES,
    inspect_delivery,
    main,
)


def _root(tmp_path: Path) -> Path:
    delivery = tmp_path / ".owlbear/delivery"
    (delivery / "runtime/changes").mkdir(parents=True)
    (delivery / "runtime/coordination/changes").mkdir(parents=True)
    (delivery / "runtime/host.json").write_text(
        '{"schema_version":1,"execution_capacity":3,"claim_timeout_seconds":3600}\n', encoding="utf-8"
    )
    (delivery / "config.json").write_text(
        '{"schema_version":2,"remote":"origin","target_branch":"dev","github_repository":"safe/project"}\n',
        encoding="utf-8",
    )
    return tmp_path


def _complete_root(tmp_path: Path) -> Path:
    root = _root(tmp_path)
    change = root / ".owlbear/delivery/runtime/changes/example"
    change.mkdir()
    (change / "frontier.json").write_bytes(b'{"schema_version":18,"bindings":[]}\n')
    (root / ".owlbear/delivery/runtime/coordination/changes/example.json").write_bytes(
        b'{"schema_version":1,"change_id":"example"}\n'
    )
    snapshot = root / ".owlbear/delivery/state/example"
    snapshot.mkdir(parents=True)
    (snapshot / "snapshot.json").write_bytes(b'{"schema_version":2,"frontier":{}}\n')
    return root


def _run_cli(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    script = Path(__file__).parents[1] / "src/owlbear_tools/delivery_diagnostics.py"
    isolated_runner = (
        "import importlib.abc,runpy,sys\n"
        "class Blocker(importlib.abc.MetaPathFinder):\n"
        " def find_spec(self,fullname,path=None,target=None):\n"
        "  if fullname.split('.')[0] in {'owlbear','fastapi','pydantic','uvicorn'}:\n"
        "   raise ImportError('blocked unavailable package')\n"
        "sys.meta_path.insert(0,Blocker())\n"
        "target=sys.argv[1]\n"
        "sys.argv = [target, *sys.argv[2:]]\n"
        "runpy.run_path(target,run_name='__main__')\n"
    )
    return subprocess.run(  # noqa: S603 - executable and arguments are fixed by this test
        [sys.executable, "-I", "-B", "-c", isolated_runner, os.fspath(script), *arguments],
        cwd=root if root.is_dir() else root.parent,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )


def test_valid_structure_is_bounded_and_healthy(tmp_path: Path) -> None:
    root = _root(tmp_path)
    change = root / ".owlbear/delivery/runtime/changes/example"
    change.mkdir()
    (change / "frontier.json").write_text('{"schema_version":18,"bindings":[]}\n', encoding="utf-8")
    coordination = root / ".owlbear/delivery/runtime/coordination/changes/example.json"
    coordination.write_text('{"schema_version":1,"change_id":"example"}\n', encoding="utf-8")
    snapshot = root / ".owlbear/delivery/state/example"
    snapshot.mkdir(parents=True)
    (snapshot / "snapshot.json").write_text('{"schema_version":2,"frontier":{}}\n', encoding="utf-8")

    result = inspect_delivery(root)

    assert result["status"] == "healthy-structure"
    assert result["writes_performed"] is False
    assert all(
        result["versions"][key] == value
        for key, value in {"config": 2, "coordination": 1, "frontier": 18, "host": 1, "snapshot": 2}.items()
    )
    assert result["versions"]["python"]["major"] >= 3
    assert result["counts"]["frontier"] == 1
    assert result["maintenance_prompt"]
    assert result["truncated"] is False
    config = next(record for record in result["records"] if record["kind"] == "config")
    assert config["status"] == "supported"
    assert config["schema_version"] == 2


@pytest.mark.parametrize("missing", ["coordination", "changes", "row"])
def test_valid_runtime_frontier_without_coordination_is_unknown_and_read_only(
    tmp_path: Path,
    missing: str,
) -> None:
    root = _root(tmp_path)
    change = root / ".owlbear/delivery/runtime/changes/example"
    change.mkdir()
    (change / "frontier.json").write_bytes(b'{"schema_version":18,"bindings":[]}\n')
    coordination = root / ".owlbear/delivery/runtime/coordination/changes/example.json"
    if missing == "coordination":
        shutil.rmtree(coordination.parent.parent)
    elif missing == "changes":
        shutil.rmtree(coordination.parent)
    else:
        coordination.write_bytes(b'{"schema_version":1,"change_id":"example"}\n')
        coordination.unlink()

    def snapshot() -> tuple[tuple[str, bytes | None], ...]:
        return tuple(
            sorted(
                (
                    path.relative_to(root).as_posix(),
                    path.read_bytes() if path.is_file() else None,
                )
                for path in root.rglob("*")
            )
        )

    before = snapshot()
    results = (inspect_delivery(root), inspect_delivery(root, change_id="example"))
    for result in results:
        assert result["status"] == "degraded"
        assert result["inspection_complete"] is False
        assert {"COORDINATION_MISSING", "PENDING_EFFECTS_UNKNOWN"} <= set(result["diagnostic_codes"])
        assert result["pending_effects"] == "unknown"
        assert result["truncated"] is False
        assert result["writes_performed"] is False
        assert result["counts"]["frontier"] == 1
        assert result["counts"]["coordination"] == 0
        assert "CHANGE_NOT_FOUND" not in result["diagnostic_codes"]

    completed = _run_cli(root, "inspect", "--project-root", os.fspath(root), "--format", "json")
    assert completed.returncode == 1
    cli_result = json.loads(completed.stdout)
    assert cli_result["status"] == "degraded"
    assert cli_result["inspection_complete"] is False
    assert {"COORDINATION_MISSING", "PENDING_EFFECTS_UNKNOWN"} <= set(cli_result["diagnostic_codes"])
    assert cli_result["pending_effects"] == "unknown"
    assert cli_result["truncated"] is False
    assert cli_result["writes_performed"] is False
    assert "example" not in completed.stdout + completed.stderr
    assert snapshot() == before


def test_empty_runtime_without_coordination_is_not_missing_a_change(tmp_path: Path) -> None:
    root = _root(tmp_path)
    shutil.rmtree(root / ".owlbear/delivery/runtime/coordination")

    result = inspect_delivery(root)

    assert result["status"] == "healthy-structure"
    assert result["inspection_complete"] is True
    assert "COORDINATION_MISSING" not in result["diagnostic_codes"]
    assert result["pending_effects"] is False
    assert result["truncated"] is False
    assert result["writes_performed"] is False


def test_coordination_identity_mismatch_is_unknown_not_missing_and_read_only(tmp_path: Path) -> None:
    root = _root(tmp_path)
    change = root / ".owlbear/delivery/runtime/changes/example"
    change.mkdir()
    (change / "frontier.json").write_bytes(b'{"schema_version":18,"bindings":[]}\n')
    coordination = root / ".owlbear/delivery/runtime/coordination/changes/example.json"
    coordination.write_bytes(b'{"schema_version":1,"change_id":"other"}\n')
    before = tuple(
        sorted(
            (path.relative_to(root).as_posix(), path.read_bytes() if path.is_file() else None)
            for path in root.rglob("*")
        )
    )

    result = inspect_delivery(root)

    after = tuple(
        sorted(
            (path.relative_to(root).as_posix(), path.read_bytes() if path.is_file() else None)
            for path in root.rglob("*")
        )
    )
    assert result["status"] == "degraded"
    assert result["inspection_complete"] is False
    assert {"COORDINATION_MALFORMED", "PENDING_EFFECTS_UNKNOWN"} <= set(result["diagnostic_codes"])
    assert "COORDINATION_MISSING" not in result["diagnostic_codes"]
    assert result["pending_effects"] == "unknown"
    assert result["writes_performed"] is False
    assert after == before


def test_listed_coordination_disappearing_at_stat_is_unknown_and_read_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _root(tmp_path)
    change = root / ".owlbear/delivery/runtime/changes/example"
    change.mkdir()
    (change / "frontier.json").write_bytes(b'{"schema_version":18,"bindings":[]}\n')
    coordination = root / ".owlbear/delivery/runtime/coordination/changes/example.json"
    coordination.write_bytes(b'{"schema_version":1,"change_id":"example"}\n')
    before = tuple(
        sorted(
            (path.relative_to(root).as_posix(), path.read_bytes() if path.is_file() else None)
            for path in root.rglob("*")
        )
    )
    real_stat = os.stat

    def disappear_listed_row(path, *args, **kwargs):
        if path == "example.json" and kwargs.get("dir_fd") is not None:
            raise FileNotFoundError(errno.ENOENT, "disappeared", os.fspath(path))
        return real_stat(path, *args, **kwargs)

    monkeypatch.setattr(diagnostics.os, "stat", disappear_listed_row)

    result = inspect_delivery(root)

    after = tuple(
        sorted(
            (path.relative_to(root).as_posix(), path.read_bytes() if path.is_file() else None)
            for path in root.rglob("*")
        )
    )
    assert result["status"] == "degraded"
    assert result["inspection_complete"] is False
    assert "COORDINATION_MISSING" in result["diagnostic_codes"]
    assert "PENDING_EFFECTS_UNKNOWN" in result["diagnostic_codes"]
    assert result["pending_effects"] == "unknown"
    assert result["counts"]["coordination"] == 0
    assert not any(record["kind"] == "coordination" and record["status"] == "missing" for record in result["records"])
    assert result["writes_performed"] is False
    assert after == before


@pytest.mark.parametrize("symlink", ["coordination", "changes"])
def test_symlinked_coordination_is_unknown_not_missing(tmp_path: Path, symlink: str) -> None:
    root = _root(tmp_path)
    change = root / ".owlbear/delivery/runtime/changes/example"
    change.mkdir()
    (change / "frontier.json").write_bytes(b'{"schema_version":18,"bindings":[]}\n')
    coordination = root / ".owlbear/delivery/runtime/coordination/changes/example.json"
    target = root / "target"
    target.mkdir()
    link = coordination.parent.parent if symlink == "coordination" else coordination.parent
    shutil.rmtree(link)
    link.symlink_to(target, target_is_directory=True)

    result = inspect_delivery(root)

    assert result["status"] == "degraded"
    assert result["inspection_complete"] is False
    assert "SYMLINK_REJECTED" in result["diagnostic_codes"]
    assert "COORDINATION_MISSING" not in result["diagnostic_codes"]
    assert result["pending_effects"] == "unknown"
    assert result["truncated"] is True
    assert result["writes_performed"] is False


@pytest.mark.parametrize(
    ("relative", "content", "code"),
    [
        (".owlbear/delivery/config.json", "{", "CONFIG_MALFORMED"),
        (".owlbear/delivery/config.json", '{"schema_version":99}', "CONFIG_UNSUPPORTED"),
        (".owlbear/delivery/runtime/changes/example/frontier.json", '{"schema_version":18}', "FRONTIER_MALFORMED"),
        (
            ".owlbear/delivery/runtime/changes/example/frontier.json",
            '{"schema_version":99,"bindings":[]}',
            "FRONTIER_UNSUPPORTED",
        ),
    ],
)
def test_malformed_and_unsupported_records_are_bounded(tmp_path: Path, relative: str, content: str, code: str) -> None:
    root = _root(tmp_path)
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

    result = inspect_delivery(root)

    assert result["status"] in {"degraded", "unsupported"}
    assert code in result["diagnostic_codes"]
    assert "safe/project" not in json.dumps(result)


def test_missing_root_and_invalid_change_id_have_exit_two(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result = inspect_delivery(tmp_path / "missing")
    assert result["status"] == "unavailable"
    assert {"ROOT_UNAVAILABLE", "PENDING_EFFECTS_UNKNOWN"} <= set(result["diagnostic_codes"])
    assert result["pending_effects"] == "unknown"
    monkeypatch.setattr("sys.argv", ["delivery-diagnose", "inspect", "--change-id", "../secret"])
    with pytest.raises(SystemExit, match="2"):
        main()


def test_project_marker_with_missing_delivery_state_is_degraded(tmp_path: Path) -> None:
    (tmp_path / ".owlbear").mkdir()

    result = inspect_delivery(tmp_path)

    assert result["status"] == "degraded"
    assert result["diagnostic_codes"] == ["DELIVERY_STATE_MISSING"]


def test_valid_project_with_missing_delivery_records_is_not_unavailable(tmp_path: Path) -> None:
    (tmp_path / ".owlbear/delivery").mkdir(parents=True)

    result = inspect_delivery(tmp_path)

    assert result["status"] == "degraded"
    assert "ROOT_UNAVAILABLE" not in result["diagnostic_codes"]
    assert "CONFIG_MISSING" in result["diagnostic_codes"]
    assert "RUNTIME_UNREADABLE" in result["diagnostic_codes"]


def test_missing_delivery_tree_is_distinct_from_unsafe_delivery_tree(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    (missing / ".owlbear").mkdir(parents=True)

    missing_result = inspect_delivery(missing)

    assert missing_result["diagnostic_codes"] == ["DELIVERY_STATE_MISSING"]
    assert missing_result["pending_effects"] is False

    unsafe = tmp_path / "unsafe"
    (unsafe / ".owlbear").mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (unsafe / ".owlbear/delivery").symlink_to(outside, target_is_directory=True)

    unsafe_result = inspect_delivery(unsafe)

    assert "SYMLINK_REJECTED" in unsafe_result["diagnostic_codes"]
    assert unsafe_result["pending_effects"] == "unknown"
    assert unsafe_result["inspection_complete"] is False


def test_invalid_cli_input_uses_bounded_error_without_echo(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit, match="2"):
        main(["inspect", "--not-a-real-option", "private-input"])
    output = capsys.readouterr().out
    assert output == "ERR_INVALID_INVOCATION\n"
    assert "private-input" not in output


def test_standalone_cli_valid_text_and_json_are_isolated_and_bounded(tmp_path: Path) -> None:
    root = _complete_root(tmp_path)
    before_membership = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
    before_bytes = {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}
    readonly_files = [
        root / ".owlbear/delivery/config.json",
        root / ".owlbear/delivery/runtime/host.json",
        root / ".owlbear/delivery/runtime/changes/example/frontier.json",
        root / ".owlbear/delivery/runtime/coordination/changes/example.json",
        root / ".owlbear/delivery/state/example/snapshot.json",
    ]
    readonly_dirs = [root / ".owlbear/delivery/state/example"]
    for path in readonly_files:
        path.chmod(0o444)
    for path in readonly_dirs:
        path.chmod(0o555)

    try:
        text = _run_cli(root, "inspect", "--project-root", os.fspath(root))
        payload = _run_cli(
            root,
            "inspect",
            "--project-root",
            os.fspath(root),
            "--format",
            "json",
        )
    finally:
        for path in readonly_files:
            path.chmod(0o644)
        for path in readonly_dirs:
            path.chmod(0o755)

    after_membership = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
    after_bytes = {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}
    assert text.returncode == 0
    assert text.stdout.startswith("status: healthy-structure\n")
    assert "writes_performed: false" in text.stdout
    assert payload.returncode == 0
    result = json.loads(payload.stdout)
    assert result["status"] == "healthy-structure"
    assert result["writes_performed"] is False
    assert "blocked unavailable package" not in payload.stderr
    assert after_membership == before_membership
    assert after_bytes == before_bytes


@pytest.mark.parametrize(
    ("relative", "content", "expected_status"),
    [
        (".owlbear/delivery/config.json", b"{", "degraded"),
        (".owlbear/delivery/config.json", b'{"schema_version":99}', "unsupported"),
    ],
)
def test_standalone_cli_degraded_and_unsupported_exit_one(
    tmp_path: Path, relative: str, content: bytes, expected_status: str
) -> None:
    root = _root(tmp_path)
    path = root / relative
    path.write_bytes(content)

    completed = _run_cli(root, "inspect", "--project-root", os.fspath(root), "--format", "json")

    assert completed.returncode == 1
    assert json.loads(completed.stdout)["status"] == expected_status


def test_standalone_cli_missing_root_and_error_redaction(tmp_path: Path) -> None:
    missing = tmp_path / "missing-root"
    unavailable = _run_cli(missing, "inspect", "--project-root", os.fspath(missing), "--format", "json")
    assert unavailable.returncode == 2
    assert json.loads(unavailable.stdout)["status"] == "unavailable"

    marked = tmp_path / "marked-project"
    (marked / ".owlbear").mkdir(parents=True)
    missing_state = _run_cli(marked, "inspect", "--project-root", os.fspath(marked), "--format", "json")
    assert missing_state.returncode == 1
    assert json.loads(missing_state.stdout)["status"] == "degraded"

    invalid = _run_cli(
        tmp_path,
        "inspect",
        "--project-root",
        os.fspath(tmp_path),
        "--change-id",
        "../private-secret-identifier",
    )
    assert invalid.returncode == 2
    assert invalid.stdout == "ERR_INVALID_INVOCATION\n"
    assert "private-secret-identifier" not in invalid.stdout


def test_nested_cwd_discovers_nearest_fixed_project_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _root(tmp_path)
    nested = root / "work" / "nested"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)

    result = inspect_delivery()

    assert result["status"] == "healthy-structure"
    assert result["change_scope"] == "all"


def test_pending_yaml_is_opaque_and_private_payload_is_not_echoed(tmp_path: Path) -> None:
    root = _root(tmp_path)
    transaction = root / ".owlbear/delivery/runtime/transactions"
    transaction.mkdir()
    (transaction / "private-secret.yaml").write_text("password: TOP-SECRET\n", encoding="utf-8")

    result = inspect_delivery(root)
    encoded = json.dumps(result)

    assert result["pending_effects"] is True
    assert result["counts"]["pending_transactions"] == 1
    assert "TOP-SECRET" not in encoded
    assert "private-secret" not in encoded


def test_known_nested_transaction_families_are_inspected(tmp_path: Path) -> None:
    root = _root(tmp_path)
    nested = root / ".owlbear/delivery/runtime/finalization-reports/report-1/transactions"
    nested.mkdir(parents=True)
    (nested / "pending.yaml").write_text("secret: hidden\n", encoding="utf-8")
    package = root / ".owlbear/delivery/packages/example/transactions"
    package.mkdir(parents=True)
    (package / "package.yaml").write_text("secret: hidden\n", encoding="utf-8")
    legacy = root / ".owlbear/delivery/runtime/changes/example/transactions"
    legacy.mkdir(parents=True)
    (legacy / "legacy.yaml").write_text("secret: hidden\n", encoding="utf-8")
    reports_tx = root / ".owlbear/delivery/runtime/finalization-reports/report-1/transactions"
    (reports_tx / "report.yaml").write_text("secret: hidden\n", encoding="utf-8")

    result = inspect_delivery(root)

    assert result["counts"]["pending_transactions"] == 4
    assert result["pending_effects"] is True
    assert "hidden" not in json.dumps(result)
    locators = {record["locator"] for record in result["records"] if record["kind"].startswith("transaction")}
    assert ".owlbear/delivery/runtime/changes/<redacted>/transactions/<opaque>.yaml" in locators
    assert ".owlbear/delivery/packages/<redacted>/transactions/<opaque>.yaml" in locators
    assert ".owlbear/delivery/runtime/finalization-reports/<redacted>/transactions/<opaque>.yaml" in locators


def test_package_root_transactions_are_inspected_with_root_locator(tmp_path: Path) -> None:
    root = _root(tmp_path)
    transactions = root / ".owlbear/delivery/packages/transactions"
    transactions.mkdir(parents=True)
    (transactions / "active.yaml").write_text("secret: hidden\n", encoding="utf-8")

    result = inspect_delivery(root)

    assert result["counts"]["pending_transactions"] == 1
    assert result["pending_effects"] is True
    assert ".owlbear/delivery/packages/transactions/<opaque>.yaml" in {
        record["locator"] for record in result["records"]
    }
    assert "hidden" not in json.dumps(result)


def test_regular_package_storage_lock_does_not_degrade_inspection(tmp_path: Path) -> None:
    root = _root(tmp_path)
    packages = root / ".owlbear/delivery/packages"
    packages.mkdir()
    (packages / ".storage.lock").write_bytes(b"")

    result = inspect_delivery(root)

    assert result["status"] == "healthy-structure"
    assert result["inspection_complete"] is True
    assert result["pending_effects"] is False


@pytest.mark.parametrize("entry_type", ["symlink", "fifo"])
def test_non_regular_package_storage_lock_keeps_pending_effects_contained(
    tmp_path: Path,
    entry_type: str,
) -> None:
    root = _root(tmp_path)
    packages = root / ".owlbear/delivery/packages"
    packages.mkdir()
    lock = packages / ".storage.lock"
    if entry_type == "symlink":
        target = tmp_path / "outside"
        target.write_bytes(b"not inspected")
        lock.symlink_to(target)
        diagnostic = "SYMLINK_REJECTED"
    else:
        os.mkfifo(lock)
        diagnostic = "SPECIAL_FILE_REJECTED"

    result = inspect_delivery(root)

    assert result["status"] == "degraded"
    assert result["inspection_complete"] is False
    assert result["pending_effects"] == "unknown"
    assert diagnostic in result["diagnostic_codes"]


def test_optional_host_local_and_selected_package_scope_are_bounded(tmp_path: Path) -> None:
    root = _complete_root(tmp_path)
    runtime = root / ".owlbear/delivery/runtime"
    (runtime / "host.local.json").write_bytes(b'{"schema_version":99}\n')
    other = root / ".owlbear/delivery/packages/other"
    other.mkdir(parents=True)
    selected = root / ".owlbear/delivery/packages/example"
    selected.mkdir(parents=True)

    result = inspect_delivery(root, change_id="example")

    assert "HOST_LOCAL_UNSUPPORTED" in result["diagnostic_codes"]
    assert result["counts"]["packages"] == 1


def test_host_local_optional_null_overrides_are_structurally_valid(tmp_path: Path) -> None:
    root = _root(tmp_path)
    (root / ".owlbear/delivery/runtime/host.local.json").write_bytes(
        b'{"execution_capacity":null,"claim_timeout_seconds":null}\n'
    )
    result = inspect_delivery(root)
    host_local = next(record for record in result["records"] if record["kind"] == "host_local")

    assert "HOST_LOCAL_MALFORMED" not in result["diagnostic_codes"]
    assert host_local["status"] == "supported"


def test_missing_frontier_is_incomplete_without_unknown_pending_effects(tmp_path: Path) -> None:
    root = _root(tmp_path)
    (root / ".owlbear/delivery/runtime/changes/example").mkdir()

    result = inspect_delivery(root)

    assert "FRONTIER_MISSING" in result["diagnostic_codes"]
    assert result["inspection_complete"] is False
    assert result["pending_effects"] is False


@pytest.mark.parametrize(
    ("runtime_changes", "expected_code", "expected_pending_effects"),
    [
        ("missing-record", "CHANGE_NOT_FOUND", "verified-absent"),
        ("unreadable", "SYMLINK_REJECTED", "unknown"),
        ("entry-limit", "ENTRY_LIMIT_EXCEEDED", "unknown"),
    ],
)
def test_selected_change_presence_requires_runtime_record(
    tmp_path: Path,
    runtime_changes: str,
    expected_code: str,
    expected_pending_effects: str,
) -> None:
    root = _complete_root(tmp_path)
    changes = root / ".owlbear/delivery/runtime/changes"
    if runtime_changes == "missing-record":
        shutil.rmtree(changes / "example")
    elif runtime_changes == "unreadable":
        shutil.rmtree(changes)
        outside = tmp_path / "outside"
        outside.mkdir()
        changes.symlink_to(outside, target_is_directory=True)
    else:
        shutil.rmtree(changes / "example")
        for index in range(MAX_ENTRIES + 1):
            (changes / f"other-{index}").mkdir()
    before_membership = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
    before_bytes = {
        path.relative_to(root): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink()
    }

    completed = _run_cli(
        root,
        "inspect",
        "--project-root",
        str(root),
        "--change-id",
        "example",
        "--format",
        "json",
    )
    result = json.loads(completed.stdout)

    assert completed.returncode == 1
    assert result["status"] == "degraded"
    assert result["inspection_complete"] is False
    assert expected_code in result["diagnostic_codes"]
    assert result["pending_effects"] == (False if expected_pending_effects == "verified-absent" else "unknown")
    if expected_pending_effects == "unknown":
        assert "CHANGE_NOT_FOUND" not in result["diagnostic_codes"]
    assert result["writes_performed"] is False
    assert before_membership == sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
    assert before_bytes == {
        path.relative_to(root): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink()
    }


def test_failed_present_pending_families_make_pending_effects_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _root(tmp_path)
    family = root / ".owlbear/delivery/runtime/finalization-reports"
    family.mkdir()
    packages = root / ".owlbear/delivery/packages"
    packages.mkdir()
    real_open_directory = diagnostics._open_directory  # noqa: SLF001

    def deny_pending_family(
        parent_fd: int,
        name: str,
        inspection: object,
        code_prefix: str,
        *,
        required: bool = False,
    ) -> object:
        if name in {"finalization-reports", "packages"}:
            return None
        return real_open_directory(parent_fd, name, inspection, code_prefix, required=required)

    monkeypatch.setattr(diagnostics, "_open_directory", deny_pending_family)

    result = inspect_delivery(root)

    assert result["pending_effects"] == "unknown"
    assert "PENDING_EFFECTS_UNKNOWN" in result["diagnostic_codes"]


def test_unavailable_runtime_makes_pending_effects_unknown(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _root(tmp_path)
    real_open_directory = diagnostics._open_directory  # noqa: SLF001

    def deny_runtime(
        parent_fd: int,
        name: str,
        inspection: object,
        code_prefix: str,
        *,
        required: bool = False,
    ) -> object:
        if name == "runtime":
            return None
        return real_open_directory(parent_fd, name, inspection, code_prefix, required=required)

    monkeypatch.setattr(diagnostics, "_open_directory", deny_runtime)

    result = inspect_delivery(root)

    assert result["pending_effects"] == "unknown"
    assert "PENDING_EFFECTS_UNKNOWN" in result["diagnostic_codes"]


def test_replaced_scanner_ancestor_makes_pending_effects_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _root(tmp_path)
    child = root / "child"
    child.mkdir()
    parent_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    child_fd = os.open("child", os.O_RDONLY | os.O_DIRECTORY, dir_fd=parent_fd)
    opened = os.fstat(child_fd)
    real_stat = diagnostics.os.stat

    def replaced(path: object, *args: object, **kwargs: object) -> os.stat_result:
        current = real_stat(path, *args, **kwargs)
        if path == "child" and kwargs.get("dir_fd") == parent_fd:
            values = list(current)
            values[1] += 1
            return os.stat_result(values)
        return current

    monkeypatch.setattr(diagnostics.os, "stat", replaced)
    inspection = diagnostics._Inspection(root, None)  # noqa: SLF001
    try:
        diagnostics._close_directory(parent_fd, "child", child_fd, opened, inspection)  # noqa: SLF001
    finally:
        os.close(parent_fd)

    assert inspection.transaction_scan_unknown is True


def test_symlink_fifo_and_read_only_membership(tmp_path: Path) -> None:
    root = _root(tmp_path)
    change = root / ".owlbear/delivery/runtime/changes/example"
    change.mkdir()
    (root / ".owlbear/delivery/runtime/changes/unsafe name").mkdir()
    packages = root / ".owlbear/delivery/packages"
    packages.mkdir()
    (packages / "unsafe").symlink_to(root)
    (change / "frontier.json").symlink_to(root / "secret.json")
    os.mkfifo(root / ".owlbear/delivery/runtime/coordination/changes/example.json")
    before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))

    result = inspect_delivery(root)
    after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))

    assert before == after
    assert "SYMLINK_REJECTED" in result["diagnostic_codes"]
    assert "SPECIAL_FILE_REJECTED" in result["diagnostic_codes"]
    assert result["pending_effects"] == "unknown"
    assert result["writes_performed"] is False


def test_entry_and_size_limits_are_reported_without_reading_unbounded_data(tmp_path: Path) -> None:
    root = _root(tmp_path)
    changes = root / ".owlbear/delivery/runtime/changes"
    for index in range(MAX_ENTRIES + 1):
        (changes / f"change-{index}").mkdir()
    huge = root / ".owlbear/delivery/config.json"
    huge.write_bytes(b"{" + b"x" * MAX_RECORD_BYTES)

    result = inspect_delivery(root)

    assert "ENTRY_LIMIT_EXCEEDED" in result["diagnostic_codes"]
    assert "OVERSIZED_RECORD" in result["diagnostic_codes"]
    assert result["inspection_complete"] is False
    assert result["counts"]["frontier"] <= MAX_ENTRIES
    assert result["counts"]["config"] == 0
    assert result["counts"]["pending_transactions"] == 0


def test_entry_limit_is_global_across_fixed_directories(tmp_path: Path) -> None:
    root = _root(tmp_path)
    changes = root / ".owlbear/delivery/runtime/changes"
    coordination = root / ".owlbear/delivery/runtime/coordination/changes"
    for index in range(MAX_ENTRIES // 2 + 2):
        (changes / f"change-{index}").mkdir()
        (coordination / f"change-{index}.json").write_text("{}", encoding="utf-8")

    result = inspect_delivery(root)

    assert "ENTRY_LIMIT_EXCEEDED" in result["diagnostic_codes"]
    assert result["inspection_complete"] is False


def test_total_byte_limit_is_independent_of_record_and_entry_limits(tmp_path: Path) -> None:
    root = _root(tmp_path)
    changes = root / ".owlbear/delivery/runtime/changes"
    record = b"{" + b"x" * (MAX_RECORD_BYTES - 2) + b"}"
    for index in range(9):
        change = changes / f"change-{index}"
        change.mkdir()
        (change / "frontier.json").write_bytes(record)

    result = inspect_delivery(root)

    assert "TOTAL_LIMIT_EXCEEDED" in result["diagnostic_codes"]
    assert "ENTRY_LIMIT_EXCEEDED" not in result["diagnostic_codes"]
    assert result["inspection_complete"] is False


def test_total_byte_budget_stays_bounded_when_file_grows_during_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _root(tmp_path)
    baseline = int(inspect_delivery(root)["bytes_inspected"])
    monkeypatch.setattr(diagnostics, "MAX_TOTAL_BYTES", baseline + 16)
    frontier = root / ".owlbear/delivery/runtime/changes/example/frontier.json"
    frontier.parent.mkdir()
    frontier.write_bytes(b"{}")
    real_open = diagnostics.os.open
    real_read = diagnostics.os.read
    frontier_fd: int | None = None
    grown = False

    def capture_frontier_fd(path: object, flags: int, mode: int = 0o777, *, dir_fd: int | None = None) -> int:
        nonlocal frontier_fd
        descriptor = real_open(path, flags, mode, dir_fd=dir_fd)
        if path == "frontier.json" and dir_fd is not None:
            frontier_fd = descriptor
        return descriptor

    def grow_after_read(fd: int, size: int) -> bytes:
        nonlocal grown
        data = real_read(fd, size)
        if fd == frontier_fd and data and not grown:
            frontier.write_bytes(b'{"schema_version":18,"bindings":[]}\n')
            grown = True
        return data

    monkeypatch.setattr(diagnostics.os, "open", capture_frontier_fd)
    monkeypatch.setattr(diagnostics.os, "read", grow_after_read)

    result = inspect_delivery(root)

    assert grown is True
    assert {"CHANGED_DURING_READ", "REPLACED_DURING_READ"} & set(result["diagnostic_codes"])
    assert result["bytes_inspected"] <= diagnostics.MAX_TOTAL_BYTES
    assert result["inspection_complete"] is False


def test_unreadable_record_is_reported_without_treating_it_as_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _root(tmp_path)
    real_stat = diagnostics.os.stat

    def deny_config(path: object, *args: object, **kwargs: object) -> os.stat_result:
        if path == "config.json" and kwargs.get("dir_fd") is not None:
            raise PermissionError from None
        return real_stat(path, *args, **kwargs)

    monkeypatch.setattr(diagnostics.os, "stat", deny_config)

    result = inspect_delivery(root)

    assert "CONFIG_UNREADABLE" in result["diagnostic_codes"]
    assert "CONFIG_MISSING" not in result["diagnostic_codes"]


def test_helper_substitution_probe_is_deterministic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _root(tmp_path)
    real_state = diagnostics._same_file_state  # noqa: SLF001 - deterministic race probe
    calls = 0

    def substitute_once(left: os.stat_result, right: os.stat_result) -> bool:
        nonlocal calls
        calls += 1
        return False if calls == 1 else real_state(left, right)

    monkeypatch.setattr(diagnostics, "_same_file_state", substitute_once)

    result = inspect_delivery(root)

    assert "REPLACED_DURING_READ" in result["diagnostic_codes"]


def test_real_file_substitution_during_open_is_detected_without_blocking(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _root(tmp_path)
    config = root / ".owlbear/delivery/config.json"
    replacement = (
        b'{"schema_version":2,"remote":"replacement","target_branch":"dev","github_repository":"safe/project"}\n'
    )
    original = config.read_bytes()
    real_open = diagnostics.os.open
    swapped = False

    def swap_before_open(path: object, flags: int, mode: int = 0o777, *, dir_fd: int | None = None) -> int:
        nonlocal swapped
        if path == "config.json" and dir_fd is not None and not swapped:
            config.replace(config.with_name("config.original"))
            config.write_bytes(replacement)
            swapped = True
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(diagnostics.os, "open", swap_before_open)
    result = inspect_delivery(root)

    assert swapped is True
    assert "REPLACED_DURING_READ" in result["diagnostic_codes"]
    assert (root / ".owlbear/delivery/config.original").read_bytes() == original


def test_log_path_substitution_after_read_is_detected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _root(tmp_path)
    logs = root / ".owlbear/delivery/runtime/logs"
    logs.mkdir()
    log = logs / "entry.log"
    original = b"original log\n"
    log.write_bytes(original)
    real_open = diagnostics.os.open
    real_read = diagnostics.os.read
    log_fd: int | None = None
    swapped = False

    def capture_log_fd(path: object, flags: int, mode: int = 0o777, *, dir_fd: int | None = None) -> int:
        nonlocal log_fd
        descriptor = real_open(path, flags, mode, dir_fd=dir_fd)
        if path == "entry.log" and dir_fd is not None:
            log_fd = descriptor
        return descriptor

    def swap_log_path(fd: int, size: int) -> bytes:
        nonlocal swapped
        if fd == log_fd and not swapped:
            log.replace(log.with_name("entry.original"))
            log.write_bytes(b"replacement log\n")
            swapped = True
        return real_read(fd, size)

    monkeypatch.setattr(diagnostics.os, "open", capture_log_fd)
    monkeypatch.setattr(diagnostics.os, "read", swap_log_path)
    result = inspect_delivery(root)

    assert swapped is True
    assert "REPLACED_DURING_READ" in result["diagnostic_codes"]
    assert (logs / "entry.original").read_bytes() == original


def test_opaque_transaction_replacement_is_detected_without_yaml_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _root(tmp_path)
    transactions = root / ".owlbear/delivery/runtime/transactions"
    transactions.mkdir()
    pending = transactions / "pending.yaml"
    pending.write_text("secret: opaque\n", encoding="utf-8")
    real_stat = diagnostics.os.stat
    stat_calls = 0

    def swap_on_poststat(path: object, *args: object, **kwargs: object) -> os.stat_result:
        nonlocal stat_calls
        if path == "pending.yaml" and kwargs.get("dir_fd") is not None:
            stat_calls += 1
            if stat_calls == 2:
                pending.replace(transactions / "pending.original")
                pending.write_text("secret: replacement\n", encoding="utf-8")
        return real_stat(path, *args, **kwargs)

    monkeypatch.setattr(diagnostics.os, "stat", swap_on_poststat)
    result = inspect_delivery(root)

    assert stat_calls >= 2
    assert "REPLACED_DURING_READ" in result["diagnostic_codes"]
    assert result["pending_effects"] == "unknown"
    assert "replacement" not in json.dumps(result)


def test_root_ancestor_replacement_is_revalidated_before_return(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _complete_root(tmp_path)
    real_scan_runtime = diagnostics._scan_runtime  # noqa: SLF001

    def replace_after_scan(delivery_fd: int, inspection: object, *, selected: str | None) -> None:
        real_scan_runtime(delivery_fd, inspection, selected=selected)
        root.rename(root.with_name("replaced-root"))
        root.mkdir()

    monkeypatch.setattr(diagnostics, "_scan_runtime", replace_after_scan)
    result = inspect_delivery(root)

    assert "REPLACED_DURING_INSPECTION" in result["diagnostic_codes"]
    assert result["inspection_complete"] is False
    assert result["pending_effects"] == "unknown"
    assert result["status"] == "degraded"


@pytest.mark.parametrize("part", [".owlbear", ".owlbear/delivery", ".owlbear/delivery/runtime"])
def test_cli_unsafe_ancestry_is_unknown_without_reading_target(tmp_path: Path, part: str) -> None:
    root = _complete_root(tmp_path / "project")
    rejected = root / part
    retained = tmp_path / "retained"
    rejected.rename(retained)
    rejected.symlink_to(retained, target_is_directory=True)
    before = {path: path.read_bytes() for path in retained.rglob("*") if path.is_file()}

    completed = _run_cli(root, "inspect", "--project-root", str(root), "--format", "json")
    result = json.loads(completed.stdout)

    assert completed.returncode == (2 if part == ".owlbear" else 1)
    assert result["inspection_complete"] is False
    assert result["pending_effects"] == "unknown"
    assert "PENDING_EFFECTS_UNKNOWN" in result["diagnostic_codes"]
    assert before == {path: path.read_bytes() for path in retained.rglob("*") if path.is_file()}


@pytest.mark.parametrize("kind", ["symlink", "fifo", "unsafe-name"])
def test_cli_rejected_records_are_incomplete(tmp_path: Path, kind: str) -> None:
    root = _complete_root(tmp_path)
    frontier = root / ".owlbear/delivery/runtime/changes/example/frontier.json"
    if kind == "unsafe-name":
        record = root / ".owlbear/delivery/runtime/coordination/changes/unsafe name.json"
        record.write_bytes(b"private-placeholder")
    else:
        frontier.unlink()
        if kind == "fifo":
            os.mkfifo(frontier)
        else:
            target = tmp_path / "not-inspected"
            target.write_bytes(b"private-placeholder")
            frontier.symlink_to(target)
    before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))

    completed = _run_cli(root, "inspect", "--project-root", str(root), "--format", "json")
    result = json.loads(completed.stdout)

    assert completed.returncode == 1
    assert result["status"] == "degraded"
    assert result["inspection_complete"] is False
    assert "private-placeholder" not in completed.stdout
    assert before == sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))


@pytest.mark.parametrize(
    ("content", "status"),
    [
        ('{"execution_capacity":3}', "healthy-structure"),
        ('{"schema_version":99,"execution_capacity":3}', "unsupported"),
        ('{"execution_capacity":true}', "degraded"),
        ('{"execution_capacity":0}', "degraded"),
        ('{"execution_capacity":"3"}', "degraded"),
        ('{"unexpected":3}', "degraded"),
    ],
)
def test_cli_local_override_structural_compatibility(tmp_path: Path, content: str, status: str) -> None:
    root = _complete_root(tmp_path)
    override = root / ".owlbear/delivery/runtime/host.local.json"
    override.write_text(content, encoding="utf-8")

    completed = _run_cli(root, "inspect", "--project-root", str(root), "--format", "json")
    result = json.loads(completed.stdout)

    assert completed.returncode == (0 if status == "healthy-structure" else 1)
    assert result["status"] == status
    assert override.read_text(encoding="utf-8") == content
    if status == "healthy-structure":
        record = next(record for record in result["records"] if record["kind"] == "host_local")
        assert record["schema_version"] == 1


def test_initial_fstat_failure_is_bounded_and_closes_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _complete_root(tmp_path)
    real_open = diagnostics.os.open
    real_fstat = diagnostics.os.fstat
    real_close = diagnostics.os.close
    failed_fd = None
    closed = False
    failed = False

    def capture_open(path: object, flags: int, mode: int = 0o777, *, dir_fd: int | None = None) -> int:
        nonlocal failed_fd
        fd = real_open(path, flags, mode, dir_fd=dir_fd)
        if path == "config.json":
            failed_fd = fd
        return fd

    def fail_first_record_stat(fd: int) -> os.stat_result:
        nonlocal failed
        if fd == failed_fd and not failed:
            failed = True
            message = "private failure text"
            raise OSError(message)
        return real_fstat(fd)

    def capture_close(fd: int) -> None:
        nonlocal closed
        if fd == failed_fd and failed:
            closed = True
        real_close(fd)

    monkeypatch.setattr(diagnostics.os, "open", capture_open)
    monkeypatch.setattr(diagnostics.os, "fstat", fail_first_record_stat)
    monkeypatch.setattr(diagnostics.os, "close", capture_close)
    result_code = main(["inspect", "--project-root", str(root), "--format", "json"])
    output = capsys.readouterr().out
    result = json.loads(output)

    assert failed
    assert closed
    assert result_code == 1
    assert "CONFIG_UNREADABLE" in result["diagnostic_codes"]
    assert result["inspection_complete"] is False
    assert "private failure text" not in output
    expected_bytes = sum(
        path.stat().st_size for path in (root / ".owlbear/delivery").rglob("*.json") if path.name != "config.json"
    )
    assert result["bytes_inspected"] == expected_bytes


@pytest.mark.parametrize("part", ["root", ".owlbear", ".owlbear/delivery"])
def test_cli_replaced_ancestry_reports_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], part: str
) -> None:
    root = _complete_root(tmp_path / "project")
    original = root if part == "root" else root / part
    retained = tmp_path / "original-tree"
    before = {path.relative_to(original): path.read_bytes() for path in original.rglob("*") if path.is_file()}
    real_scan = diagnostics._scan_runtime  # noqa: SLF001

    def replace_after_scan(fd: int, inspection: diagnostics._Inspection, *, selected: str | None) -> None:
        real_scan(fd, inspection, selected=selected)
        original.rename(retained)
        original.mkdir()

    monkeypatch.setattr(diagnostics, "_scan_runtime", replace_after_scan)
    exit_code = main(["inspect", "--project-root", str(root), "--format", "json"])
    result = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert result["status"] == "degraded"
    assert result["inspection_complete"] is False
    assert result["pending_effects"] == "unknown"
    assert before == {path.relative_to(retained): path.read_bytes() for path in retained.rglob("*") if path.is_file()}


def test_installed_console_creates_no_bytecode_or_project_writes(tmp_path: Path) -> None:
    """Exercise the built wheel's actual launcher, not an import-target imitation."""
    uv = shutil.which("uv")
    assert uv is not None, "the maintained uv build/install tool is required"
    tools = Path(__file__).parents[1]
    wheels = tmp_path / "wheels"
    subprocess.run(  # noqa: S603 - maintained offline build with fixed arguments
        [uv, "build", "--offline", "--wheel", "--out-dir", str(wheels), str(tools)],
        check=True,
        capture_output=True,
        timeout=30,
    )
    root = _complete_root(tmp_path / "project")
    environment = root / ".venv"
    subprocess.run(  # noqa: S603 - disposable virtual environment only
        [uv, "venv", "--offline", "--python", sys.executable, str(environment)],
        check=True,
        capture_output=True,
        timeout=30,
    )
    python = environment / "bin/python"
    wheel = next(wheels.glob("*.whl"))
    subprocess.run(  # noqa: S603 - install only the locally built wheel, without dependencies
        [uv, "pip", "install", "--offline", "--no-deps", "--python", str(python), str(wheel)],
        check=True,
        capture_output=True,
        timeout=30,
    )
    assert not list(root.rglob("__pycache__"))
    before = {
        path.relative_to(root): path.read_bytes() if path.is_file() and not path.is_symlink() else None
        for path in root.rglob("*")
    }
    env = dict(os.environ)
    env.pop("PYTHONDONTWRITEBYTECODE", None)
    env.pop("PYTHONPYCACHEPREFIX", None)
    launcher = environment / "bin/delivery-diagnose"
    completed = subprocess.run(  # noqa: S603 - actual installed command under inspected root
        [str(launcher), "inspect", "--project-root", str(root), "--format", "json"],
        env=env,
        cwd=root,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["status"] == "healthy-structure"
    assert not list(root.rglob("__pycache__"))
    assert not list(root.rglob("*.pyc"))
    assert before == {
        path.relative_to(root): path.read_bytes() if path.is_file() and not path.is_symlink() else None
        for path in root.rglob("*")
    }
