"""``delivery-migrate`` console contract on a disposable D03-format portfolio (N02-B)."""

from __future__ import annotations

import json
import subprocess
import sys
from typing import TYPE_CHECKING

from serve.delivery.tests.test_portfolio_application import (
    _seed_loader_composed_completed_change,
    _startup_config,
)

from owlbear_delivery.state_formats import FORMAT_MARKER, record_tree_digest
from owlbear_delivery.storage_io import acquire_controller_lock
from owlbear_tools import delivery_migration

if TYPE_CHECKING:
    from pathlib import Path


def _workspace(tmp_path: Path) -> Path:
    repository, _runtime_root = _seed_loader_composed_completed_change(tmp_path, marked=False)
    (repository / ".owlbear/delivery/config.json").write_text(_startup_config().model_dump_json(), encoding="utf-8")
    return repository


def _cli(repository: Path, *arguments: str) -> tuple[int, dict[str, object]]:
    completed = subprocess.run(  # noqa: S603 - fixed interpreter and argument vector.
        (sys.executable, "-m", "owlbear_tools.delivery_migration", "--project-root", str(repository), *arguments),
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode, json.loads(completed.stdout)


def test_cli_proposes_applies_and_verifies_from_fresh_processes(tmp_path: Path) -> None:
    repository = _workspace(tmp_path)
    before = record_tree_digest(repository)

    code, proposed = _cli(repository, "propose")

    assert code == 0
    assert record_tree_digest(repository) == before
    assert [entry["locator"] for entry in proposed["entries"]] == [FORMAT_MARKER]  # type: ignore[index]
    assert proposed["steps"] == ["format-0-to-1", "format-1-to-2"]
    migration_id = str(proposed["migration_id"])
    assert proposed["staging"] == f".owlbear/delivery-migrations/{migration_id}/stage"
    assert _cli(repository, "apply", migration_id) == (0, _cli(repository, "resume", migration_id)[1])
    code, verified = _cli(repository, "verify", migration_id)
    assert (code, verified["status"]) == (0, "verified")
    code, refused = _cli(repository, "abort", migration_id)
    assert (code, refused["code"]) == (1, "marker-committed")


def test_cli_reports_a_typed_refusal_while_a_controller_holds_the_lock(tmp_path: Path) -> None:
    repository = _workspace(tmp_path)
    migration_id = str(delivery_migration.run(["--project-root", str(repository), "propose"])[1]["migration_id"])
    holder = acquire_controller_lock(repository / ".owlbear/delivery/runtime")
    digests = record_tree_digest(repository)
    try:
        code, payload = delivery_migration.run(["--project-root", str(repository), "apply", migration_id])
    finally:
        holder.release()

    assert code == 1
    assert payload == {
        "status": "refused",
        "code": "controller-running",
        "detail": "a Delivery controller holds the workspace lock",
        "locator": None,
    }
    assert record_tree_digest(repository) == digests


def test_cli_abort_refuses_an_unverifiable_backup_without_writing(tmp_path: Path) -> None:
    repository = _workspace(tmp_path)
    root = ["--project-root", str(repository)]
    migration_id = str(delivery_migration.run([*root, "propose"])[1]["migration_id"])
    namespace = repository / ".owlbear/delivery/runtime/migrations" / migration_id
    namespace.mkdir(parents=True)
    journal = {
        "schema_version": 1,
        "migration_id": migration_id,
        "state": "backed-up",
        "source_format": 0,
        "target_format": 1,
        "backup_manifest_sha256": "0" * 64,
        "batches": [],
    }
    (namespace / "journal.json").write_text(json.dumps(journal), encoding="utf-8")

    code, refused = delivery_migration.run([*root, "abort", migration_id])

    assert (code, refused["code"]) == (1, "backup-invalid")
    assert (namespace / "journal.json").is_file()
