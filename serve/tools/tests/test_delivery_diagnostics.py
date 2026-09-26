"""Focused contracts for the stdlib-only offline Delivery diagnostic."""

from __future__ import annotations

import json
import os
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
    (change / "contract.json").write_bytes(b'{"schema_version":2}\n')
    (change / "admission.json").write_bytes(b'{"schema_version":1}\n')
    (change / "frontier.json").write_bytes(b'{"schema_version":18,"bindings":[]}\n')
    (root / ".owlbear/delivery/runtime/coordination/changes/example.json").write_bytes(
        b'{"schema_version":1,"change_id":"example"}\n'
    )
    snapshot = root / ".owlbear/delivery/state/example"
    snapshot.mkdir(parents=True)
    (snapshot / "snapshot.json").write_bytes(b'{"schema_version":2,"frontier":{}}\n')
    return root


def _run_cli(root: Path, *arguments: str, poison_path: Path | None = None) -> subprocess.CompletedProcess[str]:
    script = Path(__file__).parents[1] / "src/owlbear_tools/delivery_diagnostics.py"
    environment = os.environ.copy()
    if poison_path is not None:
        environment["PYTHONPATH"] = os.fspath(poison_path)
    return subprocess.run(  # noqa: S603 - executable and arguments are fixed by this test
        [sys.executable, "-I", "-B", os.fspath(script), *arguments],
        cwd=root if root.is_dir() else root.parent,
        env=environment,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )


def test_valid_structure_is_bounded_and_healthy(tmp_path: Path) -> None:
    root = _root(tmp_path)
    change = root / ".owlbear/delivery/runtime/changes/example"
    change.mkdir()
    (change / "contract.json").write_text('{"schema_version":2}\n', encoding="utf-8")
    (change / "admission.json").write_text('{"schema_version":1}\n', encoding="utf-8")
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


@pytest.mark.parametrize(
    ("relative", "content", "code"),
    [
        (".owlbear/delivery/config.json", "{", "CONFIG_MALFORMED"),
        (".owlbear/delivery/config.json", '{"schema_version":99}', "CONFIG_UNSUPPORTED"),
        (".owlbear/delivery/runtime/changes/example/contract.json", "{", "CONTRACT_MALFORMED"),
        (".owlbear/delivery/runtime/changes/example/admission.json", '{"schema_version":99}', "ADMISSION_UNSUPPORTED"),
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


def test_change_authority_missing_files_are_reported(tmp_path: Path) -> None:
    root = _root(tmp_path)
    change = root / ".owlbear/delivery/runtime/changes/example"
    change.mkdir()
    (change / "frontier.json").write_bytes(b'{"schema_version":18,"bindings":[]}\n')

    result = inspect_delivery(root)

    assert "CONTRACT_MISSING" in result["diagnostic_codes"]
    assert "ADMISSION_MISSING" in result["diagnostic_codes"]
    assert result["status"] == "degraded"


def test_missing_root_and_invalid_change_id_have_exit_two(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result = inspect_delivery(tmp_path / "missing")
    assert result["status"] == "unavailable"
    assert result["diagnostic_codes"] == ["ROOT_UNAVAILABLE"]
    monkeypatch.setattr("sys.argv", ["delivery-diagnose", "inspect", "--change-id", "../secret"])
    with pytest.raises(SystemExit, match="2"):
        main()


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
    poison = tmp_path / "poison"
    poison.mkdir()
    (poison / "owlbear_tools.py").write_text("raise RuntimeError('poison imported')\n", encoding="utf-8")
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
        text = _run_cli(root, "inspect", "--project-root", os.fspath(root), poison_path=poison)
        payload = _run_cli(
            root,
            "inspect",
            "--project-root",
            os.fspath(root),
            "--format",
            "json",
            poison_path=poison,
        )
    finally:
        for path in readonly_files:
            path.chmod(0o644)
        for path in readonly_dirs:
            path.chmod(0o755)

    assert text.returncode == 0
    assert text.stdout.startswith("status: healthy-structure\n")
    assert "writes_performed: false" in text.stdout
    assert payload.returncode == 0
    result = json.loads(payload.stdout)
    assert result["status"] == "healthy-structure"
    assert result["writes_performed"] is False
    assert "poison imported" not in payload.stderr


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


def test_symlink_fifo_and_read_only_membership(tmp_path: Path) -> None:
    root = _root(tmp_path)
    change = root / ".owlbear/delivery/runtime/changes/example"
    change.mkdir()
    (change / "frontier.json").symlink_to(root / "secret.json")
    os.mkfifo(root / ".owlbear/delivery/runtime/coordination/changes/example.json")
    before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))

    result = inspect_delivery(root)
    after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))

    assert before == after
    assert "SYMLINK_REJECTED" in result["diagnostic_codes"]
    assert "SPECIAL_FILE_REJECTED" in result["diagnostic_codes"]
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
