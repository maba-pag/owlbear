from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import yaml
from pydantic import ValidationError as PydanticValidationError

import owlbear_kanban
from owlbear_kanban import ChangeDiagnosticCode, load_change

if TYPE_CHECKING:
    from collections.abc import Callable


def _documents(change_id: str) -> tuple[dict[str, object], dict[str, object]]:
    decisions: dict[str, object] = {
        "schema_version": 1,
        "change_id": change_id,
        "decisions": [
            {
                "id": "DEC-002",
                "title": "Second decision",
                "status": "accepted",
                "decided_at": "2026-07-22",
                "authority": "user",
                "selected": "second",
                "rationale": "Second rationale",
                "options": [
                    {
                        "id": "second",
                        "label": "Second option",
                        "confidence": 0.9,
                        "recommended": True,
                        "pros": ["Focused"],
                        "cons": ["New"],
                        "risks": ["Small"],
                    }
                ],
            },
            {
                "id": "DEC-001",
                "title": "First decision",
                "status": "accepted",
                "decided_at": "2026-07-21",
                "authority": "user",
                "selected": "first",
                "rationale": "First rationale",
                "options": [
                    {
                        "id": "first",
                        "label": "First option",
                        "confidence": 0.8,
                        "recommended": True,
                        "pros": ["Simple"],
                        "cons": ["Limited"],
                        "risks": ["Known"],
                    }
                ],
            },
        ],
    }
    graph: dict[str, object] = {
        "schema_version": 1,
        "change_id": change_id,
        "state": "draft",
        "authority": {
            "intent": "intent.md",
            "design": "design.md",
            "decisions": "decisions.yaml",
            "research": [],
        },
        "requirements": [
            {"id": "REQ-001", "title": "First", "statement": "First requirement", "workflows": ["WF-001"]},
            {"id": "REQ-002", "title": "Second", "statement": "Second requirement", "workflows": ["WF-001"]},
        ],
        "negative_requirements": [{"id": "NEG-001", "statement": "No partial authority"}],
        "preserved_behaviors": [{"id": "KEEP-001", "statement": "Preserve identity"}],
        "workflows": [
            {
                "id": "WF-001",
                "title": "Load authority",
                "entry": "A caller names a change",
                "result": "One revision is returned",
                "proof": "PROOF-001",
            }
        ],
        "modules": [
            {
                "id": "MOD-001",
                "paths": ["serve/kanban/src/owlbear_kanban/"],
                "current_responsibility": "Kanban core",
                "planned_change": "Load native changes",
            }
        ],
        "interfaces": [
            {
                "id": "IF-001",
                "name": "Change loader",
                "producer": "DN-001",
                "consumers": ["DN-001"],
                "contract": "Return one semantic revision",
                "authority": "MOD-001",
                "failure_semantics": "Return diagnostics without partial authority",
                "migration": "MIG-001",
                "proof": "PROOF-001",
            }
        ],
        "migrations": [
            {
                "id": "MIG-001",
                "title": "Replace authority",
                "owner": "DN-001",
                "from": "Generated artifacts",
                "to": "Native authority",
                "ordered_steps": ["Load native files"],
                "consumer_inventory": ["Kanban"],
                "compatibility": "None",
                "deletion_owner": "DN-001",
                "absence_proof": "PROOF-001",
            }
        ],
        "risks": [
            {
                "id": "RISK-001",
                "class": "security",
                "title": "Path escape",
                "scenarios": ["A change path traverses outside its root"],
                "disposition": "Reject unsafe paths",
                "owner": "DN-001",
                "proof": "PROOF-001",
            }
        ],
        "proofs": [
            {
                "id": "PROOF-001",
                "title": "Loader proof",
                "boundary": "Public change loader",
                "owner": "DN-001",
                "method": ["Load a temporary package"],
                "allowed_replacements": ["Temporary filesystem"],
                "durable_outputs": ["Contract tests"],
            }
        ],
        "nodes": [
            {
                "id": "DN-001",
                "title": "Load authority",
                "outcome": "One native revision",
                "owns": ["REQ-001", "REQ-002", "NEG-001"],
                "supports": ["KEEP-001"],
                "modules": ["MOD-001"],
                "produces": ["IF-001"],
                "consumes": [],
                "dependencies": [],
                "risks": ["RISK-001"],
                "proof": "PROOF-001",
            }
        ],
        "execution": {"node_plans": {}},
    }
    return decisions, graph


def _reverse_mappings(value: object) -> object:
    if isinstance(value, dict):
        return {key: _reverse_mappings(item) for key, item in reversed(tuple(value.items()))}
    if isinstance(value, list):
        return [_reverse_mappings(item) for item in value]
    return value


def _write_package(
    changes_dir: Path,
    change_id: str,
    *,
    authority: tuple[dict[str, object], dict[str, object]] | None = None,
    markdown: tuple[str, str] = ("Product intent\n", "Implementation design\n"),
    formatting: tuple[str, int] = ("\n", 1),
) -> Path:
    default_decisions, default_graph = _documents(change_id)
    decision_data, graph_data = authority or (default_decisions, default_graph)
    intent, design = markdown
    line_ending, trailing_lines = formatting
    change_dir = changes_dir / change_id
    change_dir.mkdir(parents=True)

    def encoded(text: str) -> bytes:
        normalized = text.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n")
        return (normalized + "\n" * trailing_lines).replace("\n", line_ending).encode()

    (change_dir / "intent.md").write_bytes(encoded(intent))
    (change_dir / "design.md").write_bytes(encoded(design))
    decision_yaml = yaml.safe_dump(decision_data, sort_keys=False, allow_unicode=True)
    graph_yaml = yaml.safe_dump(graph_data, sort_keys=False, allow_unicode=True)
    (change_dir / "decisions.yaml").write_bytes(encoded(decision_yaml))
    (change_dir / "graph.yaml").write_bytes(encoded(graph_yaml))
    return change_dir


def _revision_digest(changes_dir: Path, change_id: str) -> str:
    result = load_change(changes_dir, change_id)
    assert result.diagnostics == ()
    assert result.revision is not None
    return result.revision.delivery_digest


def test_package_exports_native_change_boundary() -> None:
    expected = {
        "ChangeDiagnostic",
        "ChangeDiagnosticCode",
        "ChangeLoadResult",
        "ChangeRevision",
        "DecisionsDocument",
        "DeliveryGraph",
        "compute_delivery_digest",
        "load_change",
    }

    assert expected <= set(owlbear_kanban.__all__)
    assert all(hasattr(owlbear_kanban, name) for name in expected)


def test_load_change_returns_one_immutable_indexed_revision(tmp_path: Path) -> None:
    changes_dir = tmp_path / ".owlbear" / "changes"
    decisions, graph = _documents("sample-change")
    graph["execution"] = {"node_plans": {"DN-001": {"packets": ["DN-001-PK-001"]}}}
    _write_package(changes_dir, "sample-change", authority=(decisions, graph))

    result = load_change(changes_dir, "sample-change")

    assert result.diagnostics == ()
    assert result.revision is not None
    assert result.revision.change_id == "sample-change"
    assert [item.id for item in result.revision.accepted_decisions] == ["DEC-001", "DEC-002"]
    assert result.revision.resolve("REQ-002").id == "REQ-002"
    assert result.revision.resolve("DN-001").id == "DN-001"
    with pytest.raises(PydanticValidationError):
        result.revision.change_id = "other-change"
    with pytest.raises(PydanticValidationError):
        result.revision.graph.nodes[0].title = "Changed"
    with pytest.raises(TypeError):
        result.revision.graph.execution.node_plans["DN-002"] = {}
    node_plan = result.revision.graph.execution.node_plans["DN-001"]
    assert isinstance(node_plan, Mapping)
    with pytest.raises(TypeError):
        node_plan["packets"] = []
    payload = result.revision.model_dump(mode="json")
    assert payload["graph"]["execution"] == {"node_plans": {"DN-001": {"packets": ["DN-001-PK-001"]}}}


def test_delivery_digest_normalizes_markdown_mapping_and_decision_order(tmp_path: Path) -> None:
    changes_dir = tmp_path / ".owlbear" / "changes"
    decisions, graph = _documents("canonical-a")
    _write_package(changes_dir, "canonical-a", authority=(decisions, graph))

    reordered_decisions, reordered_graph = _documents("canonical-b")
    decision_rows = reordered_decisions["decisions"]
    assert isinstance(decision_rows, list)
    reordered_decisions["decisions"] = list(reversed(decision_rows))
    _write_package(
        changes_dir,
        "canonical-b",
        authority=(_reverse_mappings(reordered_decisions), _reverse_mappings(reordered_graph)),
        formatting=("\r\n", 3),
    )

    canonical_digest = _revision_digest(changes_dir, "canonical-a")
    assert canonical_digest == "08c3810d58cfae26e15fc507c0f34436e16b67233c67ab78a7fdeedd54fa0b17"
    assert canonical_digest == _revision_digest(changes_dir, "canonical-b")


def test_delivery_digest_changes_with_semantic_authority(tmp_path: Path) -> None:
    changes_dir = tmp_path / ".owlbear" / "changes"
    _write_package(changes_dir, "base-change")
    base_digest = _revision_digest(changes_dir, "base-change")

    semantic_digests: list[str] = []
    _write_package(
        changes_dir,
        "intent-change",
        markdown=("Different product intent\n", "Implementation design\n"),
    )
    semantic_digests.append(_revision_digest(changes_dir, "intent-change"))

    decisions, graph = _documents("decision-change")
    decision_rows = decisions["decisions"]
    assert isinstance(decision_rows, list)
    assert isinstance(decision_rows[0], dict)
    decision_rows[0]["rationale"] = "Changed rationale"
    _write_package(changes_dir, "decision-change", authority=(decisions, graph))
    semantic_digests.append(_revision_digest(changes_dir, "decision-change"))

    decisions, graph = _documents("mapping-change")
    requirement_rows = graph["requirements"]
    assert isinstance(requirement_rows, list)
    assert isinstance(requirement_rows[0], dict)
    requirement_rows[0]["statement"] = "Changed requirement"
    _write_package(changes_dir, "mapping-change", authority=(decisions, graph))
    semantic_digests.append(_revision_digest(changes_dir, "mapping-change"))

    decisions, graph = _documents("sequence-change")
    requirement_rows = graph["requirements"]
    assert isinstance(requirement_rows, list)
    graph["requirements"] = list(reversed(requirement_rows))
    _write_package(changes_dir, "sequence-change", authority=(decisions, graph))
    semantic_digests.append(_revision_digest(changes_dir, "sequence-change"))

    assert all(digest != base_digest for digest in semantic_digests)


@pytest.mark.parametrize("change_id", ["/absolute", "../escape", "nested/change", "bad\\change", "bad\x00id"])
def test_load_change_rejects_unsafe_change_ids(tmp_path: Path, change_id: str) -> None:
    result = load_change(tmp_path / "changes", change_id)

    assert result.revision is None
    assert [item.code for item in result.diagnostics] == [ChangeDiagnosticCode.PATH_UNSAFE]


def _missing_file(change_dir: Path, _decisions: dict[str, object], _graph: dict[str, object]) -> None:
    (change_dir / "design.md").unlink()


def _bom_markdown(change_dir: Path, _decisions: dict[str, object], _graph: dict[str, object]) -> None:
    intent = change_dir / "intent.md"
    intent.write_bytes(b"\xef\xbb\xbf" + intent.read_bytes())


def _non_utf8_markdown(change_dir: Path, _decisions: dict[str, object], _graph: dict[str, object]) -> None:
    (change_dir / "intent.md").write_bytes(b"\xff")


def _malformed_yaml(change_dir: Path, _decisions: dict[str, object], _graph: dict[str, object]) -> None:
    (change_dir / "graph.yaml").write_text("[unclosed", encoding="utf-8")


def _duplicate_id(change_dir: Path, _decisions: dict[str, object], graph: dict[str, object]) -> None:
    requirements = graph["requirements"]
    assert isinstance(requirements, list)
    assert isinstance(requirements[1], dict)
    requirements[1]["id"] = "REQ-001"
    (change_dir / "graph.yaml").write_text(yaml.safe_dump(graph, sort_keys=False), encoding="utf-8")


def _missing_reference(change_dir: Path, _decisions: dict[str, object], graph: dict[str, object]) -> None:
    nodes = graph["nodes"]
    assert isinstance(nodes, list)
    assert isinstance(nodes[0], dict)
    nodes[0]["dependencies"] = ["DN-999"]
    (change_dir / "graph.yaml").write_text(yaml.safe_dump(graph, sort_keys=False), encoding="utf-8")


def _redirected_authority(change_dir: Path, _decisions: dict[str, object], graph: dict[str, object]) -> None:
    authority = graph["authority"]
    assert isinstance(authority, dict)
    authority["intent"] = "../../outside.md"
    (change_dir / "graph.yaml").write_text(yaml.safe_dump(graph, sort_keys=False), encoding="utf-8")


def _symlinked_file(change_dir: Path, _decisions: dict[str, object], _graph: dict[str, object]) -> None:
    design = change_dir / "design.md"
    target = change_dir / "design-target.md"
    design.rename(target)
    try:
        design.symlink_to(target.name)
    except OSError:
        pytest.skip("symlinks unavailable")


@pytest.mark.parametrize(
    ("defect", "expected_code"),
    [
        (_missing_file, ChangeDiagnosticCode.FILE_MISSING),
        (_bom_markdown, ChangeDiagnosticCode.ENCODING),
        (_non_utf8_markdown, ChangeDiagnosticCode.ENCODING),
        (_malformed_yaml, ChangeDiagnosticCode.YAML_PARSE),
        (_duplicate_id, ChangeDiagnosticCode.ID_DUPLICATE),
        (_missing_reference, ChangeDiagnosticCode.REFERENCE_MISSING),
        (_redirected_authority, ChangeDiagnosticCode.SCHEMA_INVALID),
        (_symlinked_file, ChangeDiagnosticCode.PATH_UNSAFE),
    ],
)
def test_load_change_rejects_package_defects(
    tmp_path: Path,
    defect: Callable[[Path, dict[str, object], dict[str, object]], None],
    expected_code: ChangeDiagnosticCode,
) -> None:
    changes_dir = tmp_path / "changes"
    decisions, graph = _documents("defective-change")
    change_dir = _write_package(changes_dir, "defective-change", authority=(decisions, graph))
    defect(change_dir, decisions, graph)

    result = load_change(changes_dir, "defective-change")

    assert result.revision is None
    assert [item.code for item in result.diagnostics] == [expected_code]


def test_load_change_rejects_symlinked_change_directory(tmp_path: Path) -> None:
    changes_dir = tmp_path / "changes"
    _write_package(changes_dir, "real-change")
    alias = changes_dir / "alias-change"
    try:
        alias.symlink_to(changes_dir / "real-change", target_is_directory=True)
    except OSError:
        pytest.skip("symlinks unavailable")

    result = load_change(changes_dir, "alias-change")

    assert result.revision is None
    assert [item.code for item in result.diagnostics] == [ChangeDiagnosticCode.PATH_UNSAFE]
