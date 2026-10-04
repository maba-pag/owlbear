"""``delivery-repair`` console contract (N08-A): exits, confirmation, bounded output and the I7 fallback."""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

from serve.delivery.tests.test_portfolio_application import (
    _seed_loader_composed_completed_change,
    _startup_config,
)

from owlbear_delivery.state_formats import record_tree_digest
from owlbear_delivery.storage_io import acquire_controller_lock
from owlbear_tools import delivery_repair

_SENTINEL = "SENTINEL-CLI-VALUE-41c9"
_FINDING = "C01:runtime/host.local.json"
_FAILING_IMPORT = """
import importlib.abc, sys
class Refuse(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name == "owlbear_delivery.portfolio_application":
            raise RuntimeError("{sentinel} eager import failed")
        return None
sys.meta_path.insert(0, Refuse())
from owlbear_tools import delivery_repair
sys.exit(delivery_repair.main(sys.argv[1:]))
""".replace("{sentinel}", _SENTINEL)


def _workspace(tmp_path: Path) -> Path:
    repository, _runtime_root = _seed_loader_composed_completed_change(tmp_path)
    (repository / ".owlbear/delivery/config.json").write_text(_startup_config().model_dump_json(), encoding="utf-8")
    host_local = repository / ".owlbear/delivery/runtime/host.local.json"
    host_local.write_text(f'{{"schema_version":1,"execution_capacity":"{_SENTINEL}"', encoding="utf-8")
    return repository


def _cli(repository: Path, *arguments: str) -> tuple[int, str]:
    completed = subprocess.run(  # noqa: S603 - fixed interpreter and argument vector.
        (sys.executable, "-m", "owlbear_tools.delivery_repair", "--project-root", str(repository), *arguments),
        check=False,
        capture_output=True,
        text=True,
    )
    assert "Traceback" not in completed.stderr, completed.stderr
    return completed.returncode, completed.stdout


def _json(repository: Path, *arguments: str) -> tuple[int, dict[str, object]]:
    code, stdout = _cli(repository, *arguments)
    return code, json.loads(stdout)


def test_cli_classifies_proposes_confirms_applies_and_verifies_from_fresh_processes(tmp_path: Path) -> None:
    repository = _workspace(tmp_path)
    tree = record_tree_digest(repository)

    code, classified = _json(repository, "classify")
    assert code == 1
    assert [item["finding_id"] for item in classified["findings"]] == [_FINDING]  # type: ignore[union-attr]
    code, proposed = _json(repository, "propose", _FINDING)
    assert (code, proposed["policy"]) == (0, "user-confirmed")
    assert proposed["precondition"] == delivery_repair.MAINTENANCE_PRECONDITION
    assert "do not restart any of them until delivery-repair verify or abort has finished" in str(
        proposed["precondition"]
    )
    proposal_id = str(proposed["proposal_id"])
    assert proposed["backup"] == f".owlbear/delivery-migrations/{proposal_id}/backup"
    assert record_tree_digest(repository) == tree
    code, refused = _json(repository, "apply", "--proposal", proposal_id)
    assert (code, refused["code"]) == (1, "repair-confirmation-required")
    assert refused["precondition"] == delivery_repair.MAINTENANCE_PRECONDITION
    assert record_tree_digest(repository) == tree

    assert _json(repository, "apply", "--proposal", proposal_id, "--confirm", proposal_id) == (
        0,
        {
            "status": "applied",
            "proposal_id": proposal_id,
            "kind": "repair",
            "precondition": delivery_repair.MAINTENANCE_PRECONDITION,
        },
    )
    assert _json(repository, "verify", proposal_id)[1]["status"] == "verified"
    assert "precondition" not in _json(repository, "classify")[1]
    code, healthy = _json(repository, "classify")
    assert (code, healthy["status"], healthy["findings"]) == (0, "healthy", [])
    checks = healthy["online_checks"]
    assert [(item["condition"], item["operation"]) for item in checks] == [  # type: ignore[union-attr]
        ("remote-snapshot-quarantined", "repair_quarantined_delivery_state_snapshot"),
        ("local-frontier-mismatch", "repair_delivery_state_snapshot"),
        ("remote-change-head-mismatch", "recover_out_of_band_head"),
        ("target-sync-publication", "repair_target_sync_publication"),
    ]
    code, text = _cli(repository, "classify", "--format", "text")
    lines = text.splitlines()
    assert (code, lines[0], len(lines)) == (0, "healthy: no findings", 5)
    assert all("online -> " in line and "needs online check:" in line for line in lines[1:])


def test_cli_output_never_contains_a_record_value_or_an_absolute_path(tmp_path: Path) -> None:
    repository = _workspace(tmp_path)
    outputs = [_cli(repository, "classify")[1], _cli(repository, "classify", "--format", "text")[1]]
    code, stdout = _cli(repository, "propose", _FINDING)
    outputs.append(stdout)
    proposal_id = json.loads(stdout)["proposal_id"]
    outputs.extend(
        _cli(repository, *arguments)[1]
        for arguments in (
            ("apply", "--proposal", proposal_id),
            ("apply", "--proposal", proposal_id, "--confirm", proposal_id),
            ("verify", proposal_id),
            ("abort", proposal_id),
            ("propose", f"C07:{_SENTINEL}"),
        )
    )

    rendered = "\n".join(outputs)
    assert code == 0
    assert _SENTINEL not in rendered
    assert str(tmp_path) not in rendered
    assert str(tmp_path.resolve()) not in rendered


def test_invalid_invocation_exits_2_without_echoing_input(tmp_path: Path) -> None:
    code, stdout = _cli(tmp_path, "apply", "--unknown", _SENTINEL)

    assert code == 2
    assert json.loads(stdout) == {"status": "invalid-invocation"}
    assert _SENTINEL not in stdout


def test_a_controller_holding_the_lock_is_a_typed_refusal_without_a_write(tmp_path: Path) -> None:
    repository = _workspace(tmp_path)
    root = ["--project-root", str(repository)]
    proposal_id = str(delivery_repair.run([*root, "propose", _FINDING])[1]["proposal_id"])
    holder = acquire_controller_lock(repository / ".owlbear/delivery/runtime")
    tree = record_tree_digest(repository)
    try:
        code, payload, _format = delivery_repair.run(
            [*root, "apply", "--proposal", proposal_id, "--confirm", proposal_id]
        )
    finally:
        holder.release()

    assert (code, payload["code"]) == (1, "repair-controller-running")
    assert record_tree_digest(repository) == tree


def test_a_failing_eager_delivery_import_is_a_c09_maintenance_finding_beside_the_inspector(tmp_path: Path) -> None:
    repository = _workspace(tmp_path)
    tree = record_tree_digest(repository)

    completed = subprocess.run(  # noqa: S603 - fixed interpreter and argument vector.
        (sys.executable, "-c", _FAILING_IMPORT, "--project-root", str(repository), "classify"),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert "Traceback" not in completed.stderr
    payload = json.loads(completed.stdout)
    assert [(item["catalogue"], item["route"], item["exception_class"]) for item in payload["findings"]] == [
        ("C09", "maintenance", "RuntimeError")
    ]
    assert "HOST_LOCAL_MALFORMED" in payload["inspector"]["diagnostic_codes"]
    assert _SENTINEL not in completed.stdout
    assert record_tree_digest(repository) == tree


def test_delivery_repair_imports_only_the_standard_library_at_module_load() -> None:
    tree = ast.parse(Path(delivery_repair.__file__).read_text(encoding="utf-8"))
    imported = {
        module.split(".", 1)[0]
        for node in tree.body
        for module in (
            [alias.name for alias in node.names]
            if isinstance(node, ast.Import)
            else [node.module]
            if isinstance(node, ast.ImportFrom) and node.module is not None
            else []
        )
    }

    assert imported <= set(sys.stdlib_module_names) | {"__future__"}


def test_delivery_repair_is_a_registered_console_script() -> None:
    pyproject = (Path(__file__).parents[1] / "pyproject.toml").read_text(encoding="utf-8")

    assert 'delivery-repair = "owlbear_tools.delivery_repair:main"' in pyproject
