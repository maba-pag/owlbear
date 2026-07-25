"""Public Cockpit contract tests for native change and graph resources."""

from __future__ import annotations

import shutil
from pathlib import Path
from unittest import mock

import pytest
from fastapi.testclient import TestClient
from owlbear_kanban import KanbanEngine

from owlbear_cockpit.deps import NativeContextCache, get_engine, get_native_context_cache
from owlbear_cockpit.main import app

_CHANGE_ID = "replace-delivery-pipeline"


@pytest.fixture
def native_client(tmp_path: Path, project_root: Path) -> tuple[TestClient, Path, NativeContextCache]:
    ops_root = tmp_path / ".owlbear"
    work_root = ops_root / "kanban"
    work_root.mkdir(parents=True)
    (work_root / "config.yml").write_text("next_id: 1\n", encoding="utf-8")
    (work_root / "tasks").mkdir()
    (work_root / "archive").mkdir()
    source = project_root / ".owlbear" / "changes" / _CHANGE_ID
    change_dir = ops_root / "changes" / _CHANGE_ID
    shutil.copytree(source, change_dir)
    malformed = ops_root / "changes" / "broken-change"
    malformed.mkdir()
    (malformed / "intent.md").write_text("broken\n", encoding="utf-8")

    engine = KanbanEngine(work_root)
    cache = NativeContextCache()
    app.dependency_overrides[get_engine] = lambda: engine
    app.dependency_overrides[get_native_context_cache] = lambda: cache
    try:
        yield TestClient(app), change_dir, cache
    finally:
        app.dependency_overrides.clear()


def test_list_changes_orders_loaded_and_malformed_entries(
    native_client: tuple[TestClient, Path, NativeContextCache],
) -> None:
    client, _, _ = native_client
    response = client.get("/api/changes")

    assert response.status_code == 200
    assert [item["change_id"] for item in response.json()["changes"]] == ["broken-change", _CHANGE_ID]
    assert response.json()["changes"][0]["state"] == "invalid"
    assert response.json()["changes"][1]["delivery_digest"]
    assert "path" not in response.text


def test_show_change_and_graph_return_joined_authority(
    native_client: tuple[TestClient, Path, NativeContextCache],
) -> None:
    client, _, _ = native_client

    detail = client.get(f"/api/changes/{_CHANGE_ID}")
    graph = client.get(f"/api/changes/{_CHANGE_ID}/graph")

    assert detail.status_code == 200
    assert detail.json()["change_id"] == _CHANGE_ID
    assert detail.json()["graph"]["nodes"]
    assert graph.status_code == 200
    assert graph.json()["delivery_digest"] == detail.json()["delivery_digest"]
    assert set(graph.json()["plans"]) == {"DN-001"}
    assert graph.json()["plans"]["DN-001"]["packets"][0]["id"] == "DN-001-PK-001"


def test_missing_and_invalid_changes_have_stable_envelopes(
    native_client: tuple[TestClient, Path, NativeContextCache],
) -> None:
    client, _, _ = native_client

    missing = client.get("/api/changes/not-present")
    invalid = client.get("/api/changes/broken-change")

    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "ERR_CHANGE_NOT_FOUND"
    assert invalid.status_code == 422
    assert invalid.json()["detail"]["code"] == "ERR_CHANGE_INVALID"
    assert str(Path.cwd()) not in invalid.text


def test_context_cache_reuses_revision_then_replaces_changed_digest(
    native_client: tuple[TestClient, Path, NativeContextCache],
) -> None:
    client, change_dir, cache = native_client
    first = client.get(f"/api/changes/{_CHANGE_ID}")
    first_context = next(iter(cache._contexts.values()))  # noqa: SLF001

    second = client.get(f"/api/changes/{_CHANGE_ID}")
    assert next(iter(cache._contexts.values())) is first_context  # noqa: SLF001
    assert second.json()["delivery_digest"] == first.json()["delivery_digest"]

    design = change_dir / "design.md"
    design.write_text(design.read_text(encoding="utf-8") + "\nRevision marker.\n", encoding="utf-8")
    changed = client.get(f"/api/changes/{_CHANGE_ID}")

    assert changed.status_code == 200
    assert changed.json()["delivery_digest"] != first.json()["delivery_digest"]
    assert next(iter(cache._contexts.values())) is not first_context  # noqa: SLF001


def test_missing_changes_directory_returns_empty_list(
    native_client: tuple[TestClient, Path, NativeContextCache],
) -> None:
    client, change_dir, _ = native_client
    shutil.rmtree(change_dir.parent)

    response = client.get("/api/changes")

    assert response.status_code == 200
    assert response.json() == {"changes": []}


def test_failed_reassembly_preserves_cached_context_and_work_store(
    native_client: tuple[TestClient, Path, NativeContextCache],
) -> None:
    client, change_dir, cache = native_client
    first = client.get(f"/api/changes/{_CHANGE_ID}")
    assert first.status_code == 200
    first_context = next(iter(cache._contexts.values()))  # noqa: SLF001
    work_root = change_dir.parent.parent / "kanban"
    proof_root = change_dir.parent.parent / "scratch" / "proof"
    files_before = {path.relative_to(work_root) for path in work_root.rglob("*")}
    proof_files_before = {path.relative_to(proof_root) for path in proof_root.rglob("*")}

    design = change_dir / "design.md"
    design.write_text(design.read_text(encoding="utf-8") + "\nFailed revision marker.\n", encoding="utf-8")
    with mock.patch("owlbear_cockpit.deps.DispatchRuntime", side_effect=RuntimeError("injected")):
        failed = client.get(f"/api/changes/{_CHANGE_ID}")

    assert failed.status_code == 503
    assert failed.json()["detail"] == {
        "code": "ERR_NATIVE_CONTEXT_UNAVAILABLE",
        "message": "native context assembly failed",
    }
    assert next(iter(cache._contexts.values())) is first_context  # noqa: SLF001
    assert {path.relative_to(work_root) for path in work_root.rglob("*")} == files_before
    assert {path.relative_to(proof_root) for path in proof_root.rglob("*")} == proof_files_before
