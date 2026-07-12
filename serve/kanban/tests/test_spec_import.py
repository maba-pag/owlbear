"""Tests for deterministic Spec Kit to OwlBear Kanban import."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from owlbear_kanban import KanbanEngine
from owlbear_kanban.spec_import import (
    SpecImportError,
    apply_import,
    build_import_preview,
    load_import_document,
)


def _make_board(tmp_path: Path) -> Path:
    kanban_dir = tmp_path / ".owlbear" / "kanban"
    (kanban_dir / "tasks").mkdir(parents=True)
    (kanban_dir / "archive").mkdir()
    return kanban_dir


def _manifest(*, second_depends_on: list[str] | None = None) -> dict[str, object]:
    return {
        "schema_version": 1,
        "feature": "alert-repair",
        "spec": "spec.md",
        "plan": "plan.md",
        "aggregate": {
            "title": "Prepare trustworthy alert evidence",
            "priority": "high",
            "tags": ["feature:alert-repair"],
            "acceptance": ["Normal CLI path returns trustworthy evidence"],
        },
        "tasks": [
            {
                "key": "T001",
                "title": "Expose and call the generated alert operation",
                "requirement_ids": ["REQ-001"],
                "invariant_ids": ["INV-001"],
                "depends_on": [],
                "priority": "high",
                "tags": ["scope:collection"],
                "proof_bundle": "behavioral",
                "boundary": "assembled security analyst context",
                "allowed_replacement": "remote HTTP transport",
                "acceptance": ["Given the assembled context, AlertsList is visible and callable"],
            },
            {
                "key": "T002",
                "title": "Project typed alert evidence",
                "requirement_ids": ["REQ-002"],
                "invariant_ids": ["INV-002"],
                "depends_on": second_depends_on if second_depends_on is not None else ["T001"],
                "priority": "medium",
                "tags": ["scope:projection"],
                "proof_bundle": "critical",
                "boundary": "normal CLI application",
                "allowed_replacement": "remote HTTP transport",
                "acceptance": ["Given production-shaped alerts, the CLI emits typed evidence"],
            },
        ],
    }


def _write_feature(tmp_path: Path, manifest: dict[str, object]) -> Path:
    feature_dir = tmp_path / "specs" / "001-alert-repair"
    feature_dir.mkdir(parents=True)
    requirements = sorted({requirement_id for task in manifest["tasks"] for requirement_id in task["requirement_ids"]})
    spec_text = "# Spec\n\n" + "\n".join(f"- **{requirement_id}**: Requirement" for requirement_id in requirements)
    (feature_dir / "spec.md").write_text(f"{spec_text}\n", encoding="utf-8")
    (feature_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
    frontmatter = yaml.safe_dump({"owlbear": manifest}, sort_keys=False)
    tasks_file = feature_dir / "tasks.md"
    tasks_file.write_text(f"---\n{frontmatter}---\n# Tasks\n", encoding="utf-8")
    return tasks_file


def test_load_and_preview_preserve_dependency_order(tmp_path: Path) -> None:
    document = load_import_document(_write_feature(tmp_path, _manifest()))

    preview = build_import_preview(document)

    assert [task["key"] for task in preview["tasks"]] == ["T001", "T002"]
    assert preview["tasks"][1]["depends_on"] == ["T001"]
    assert preview["aggregate"]["depends_on"] == ["T001", "T002"]
    assert preview["import_tag"] == "spec-kit:alert-repair"


def test_apply_creates_build_leaves_and_collect_parent(tmp_path: Path) -> None:
    kanban_dir = _make_board(tmp_path)
    document = load_import_document(_write_feature(tmp_path, _manifest()))

    result = apply_import(document, kanban_dir)

    engine = KanbanEngine(kanban_dir)
    first = engine.show_task(str(result["task_ids"]["T001"]))
    second = engine.show_task(str(result["task_ids"]["T002"]))
    aggregate = engine.show_task(str(result["aggregate_id"]))
    assert first.status == "build"
    assert second.depends_on == [first.id]
    assert first.parent == aggregate.id
    assert second.parent == aggregate.id
    assert aggregate.status == "collect"
    assert aggregate.depends_on == [first.id, second.id]
    assert "spec-kit:alert-repair" in aggregate.tags
    assert first.ac == ["Given the assembled context, AlertsList is visible and callable"]
    assert "Boundary: assembled security analyst context" in str(first.body)


def test_apply_rejects_duplicate_feature_import(tmp_path: Path) -> None:
    kanban_dir = _make_board(tmp_path)
    document = load_import_document(_write_feature(tmp_path, _manifest()))
    apply_import(document, kanban_dir)

    with pytest.raises(SpecImportError, match="already imported"):
        apply_import(document, kanban_dir)


def test_manifest_rejects_dependency_cycle(tmp_path: Path) -> None:
    manifest = _manifest(second_depends_on=["T001"])
    manifest["tasks"][0]["depends_on"] = ["T002"]

    with pytest.raises(ValidationError, match="dependency cycle"):
        load_import_document(_write_feature(tmp_path, manifest))


def test_manifest_rejects_unknown_dependency(tmp_path: Path) -> None:
    manifest = _manifest(second_depends_on=["T999"])

    with pytest.raises(ValidationError, match="unknown dependencies"):
        load_import_document(_write_feature(tmp_path, manifest))


def test_manifest_rejects_duplicate_invariant_owner(tmp_path: Path) -> None:
    manifest = _manifest()
    manifest["tasks"][1]["invariant_ids"] = ["INV-001"]

    with pytest.raises(ValidationError, match="multiple owners"):
        load_import_document(_write_feature(tmp_path, manifest))


def test_manifest_rejects_unresolved_placeholder(tmp_path: Path) -> None:
    manifest = _manifest()
    manifest["tasks"][0]["boundary"] = "[Normal boundary]"

    with pytest.raises(ValidationError, match="unresolved template placeholder"):
        load_import_document(_write_feature(tmp_path, manifest))
