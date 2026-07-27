"""Assembled public cutover, setup, and native launch proof."""

from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import subprocess
import time
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

import pytest

from owlbear_kanban import LegacyDisposition, verify_legacy_snapshot

_REPO_ROOT = Path(__file__).parent.parent
_SEED_COMMAND = _REPO_ROOT / "serve/cockpit/web/e2e/support/seed-native-proof-stack.py"


@pytest.fixture(scope="module")
def cutover_workspace(tmp_path_factory: pytest.TempPathFactory) -> Path:
    workspace = tmp_path_factory.mktemp("native-cutover")
    subprocess.run(
        [
            "uv",
            "run",
            "python",
            str(_SEED_COMMAND),
            "--project-root",
            str(_REPO_ROOT),
            "--workspace",
            str(workspace),
        ],
        cwd=_REPO_ROOT,
        check=True,
    )
    return workspace


def _proof(workspace: Path) -> dict[str, Any]:
    return json.loads((workspace / ".owlbear/proof-009.json").read_text(encoding="utf-8"))


def test_public_cutover_and_setup_preserve_history_and_create_clean_native_stores(
    cutover_workspace: Path,
) -> None:
    proof = _proof(cutover_workspace)
    snapshot = verify_legacy_snapshot(cutover_workspace / ".owlbear/legacy/kanban-final")
    receipt = json.loads(
        (cutover_workspace / ".owlbear/legacy/bootstrap-finalization.json").read_text(encoding="utf-8")
    )

    assert proof["finalize_command"][-4:] == [
        "--workspace",
        str(cutover_workspace),
        "--request",
        str(cutover_workspace / "finalization-request.json"),
    ]
    assert proof["setup_command"][-1] == str(_REPO_ROOT / "setup/init.py")
    assert proof["snapshot_file_count"] == snapshot.manifest.file_count == 3
    assert proof["source_digest"] == snapshot.manifest.source_digest == receipt["source_digest"]
    assert proof["snapshot_manifest_sha256"] == receipt["snapshot_manifest_sha256"]
    assert proof["expected_delivery_digest"] == receipt["delivery_digest"]
    assert proof["expected_code_revision"] == receipt["code_revision"]
    assert proof["finalization_receipt"] == receipt
    assert proof["tracked_paths"] == [
        ".owlbear/kanban",
        ".vscode/mcp.json",
        ".owlbear/legacy/kanban-final",
        ".owlbear/legacy/bootstrap-finalization.json",
    ]
    assert proof["fixture_legacy_source"] == str(cutover_workspace / ".owlbear/kanban")
    assert proof["live_self_hosting_board"] == str(_REPO_ROOT / ".owlbear/kanban")
    assert proof["live_self_hosting_board_input"] is False
    assert Path(proof["fixture_legacy_source"]).is_relative_to(cutover_workspace)
    assert not Path(proof["fixture_legacy_source"]).is_relative_to(_REPO_ROOT / ".owlbear/kanban")
    assert proof["dn_015_handoff"] == {
        "expected_delivery_digest": proof["expected_delivery_digest"],
        "expected_code_revision": proof["expected_code_revision"],
        "source_digest": proof["source_digest"],
        "snapshot_manifest_sha256": proof["snapshot_manifest_sha256"],
        "finalization_receipt": receipt,
        "returned_commit_paths": proof["tracked_paths"],
    }
    assert {item.disposition for item in snapshot.manifest.active_items} == {LegacyDisposition.COMPLETED_HISTORY}

    native_root = cutover_workspace / ".owlbear/kanban"
    assert all(
        (native_root / path).is_dir()
        for path in ("jobs", "archive", "requests/pending", "requests/resolved", "attempts", "findings")
    )
    assert proof["absent_legacy_runtime_surfaces"] == [
        ".owlbear/kanban/tasks",
        ".owlbear/kanban/decisions",
        "openspec",
    ]
    assert all(not (cutover_workspace / path).exists() for path in proof["absent_legacy_runtime_surfaces"])
    assert not (cutover_workspace / "finalization-request.json").exists()
    assert "ob-kanban" in json.loads((cutover_workspace / ".vscode/mcp.json").read_text(encoding="utf-8"))["servers"]


def test_setup_consumer_launches_public_native_cockpit(cutover_workspace: Path) -> None:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    environment = {
        **os.environ,
        "OWLBEAR_WORK_ROOT": str(cutover_workspace / ".owlbear/kanban"),
        "MEMORY_DIR": str(cutover_workspace / ".owlbear/memory"),
        "COCKPIT_PORT": str(port),
        "COCKPIT_NO_OPEN": "1",
    }
    process = subprocess.Popen(  # noqa: S603 - command and environment are controlled by this test.
        ["uv", "run", "--project", str(_REPO_ROOT), "--package", "owlbear-cockpit", "cockpit"],
        cwd=cutover_workspace,
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    response: dict[str, Any] | None = None
    deadline = time.monotonic() + 15
    try:
        while time.monotonic() < deadline and process.poll() is None:
            try:
                health_url = f"http://127.0.0.1:{port}/api/changes/replace-delivery-pipeline/health/work"
                with urlopen(health_url, timeout=1) as health:  # noqa: S310
                    response = json.load(health)
                    break
            except ConnectionError, TimeoutError, URLError:
                time.sleep(0.05)
    finally:
        process.terminate()
        process.wait(timeout=10)

    assert response is not None
    assert response["checked_paths"]
    assert response["next_cursor"] is None
