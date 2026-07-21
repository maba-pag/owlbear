from __future__ import annotations

from pathlib import Path

from owlbear_kanban import KanbanEngine


_CONFIG = """\
statuses: [shape, build, verify, collect]
priorities: [low, medium, high]
claim_timeout: 1h
next_id: 1
entry_status: shape
terminal_status: collect
agent_map: {shape: builder, build: builder, verify: verifier, collect: collector}
agent_types: {}
agent_compatibility: {}
non_impl_tags: []
archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
status_predicates: {}
"""


def _board(tmp_path: Path) -> Path:
    board = tmp_path / "board"
    (board / "tasks").mkdir(parents=True)
    (board / "archive").mkdir()
    (board / "config.yml").write_text(_CONFIG, encoding="utf-8")
    return board


def _task(task_id: int, *, depends_on: list[int] | None = None) -> str:
    dependencies = depends_on or []
    return f"""---
id: {task_id}
title: Task {task_id}
status: shape
priority: medium
created: '2026-07-17T00:00:00+00:00'
updated: '2026-07-17T00:00:00+00:00'
parent: null
depends_on: {dependencies}
blocked: false
archival_reason: null
archival_refs: []
---

body
"""


def test_task_health_reports_complete_duplicate_set_and_cycle_context(tmp_path: Path) -> None:
    board = _board(tmp_path)
    duplicate = _task(1)
    (board / "tasks" / "1-one.md").write_text(duplicate, encoding="utf-8")
    reordered = duplicate.replace("id: 1\ntitle: Task 1", "title: Task 1\nid: 1")
    (board / "tasks" / "1-two.md").write_text(reordered, encoding="utf-8")
    (board / "tasks" / "2-two.md").write_text(_task(2, depends_on=[3]), encoding="utf-8")
    (board / "tasks" / "3-three.md").write_text(_task(3, depends_on=[2]), encoding="utf-8")

    result = KanbanEngine(board, activity_log=False).task_health()

    duplicate_finding = next(finding for finding in result.findings if finding.code == "DUPLICATE_TASK_ID")
    assert duplicate_finding.task_id == 1
    assert duplicate_finding.repairable is True
    assert "1-one.md" in duplicate_finding.path
    assert "1-two.md" in duplicate_finding.path
    cycle_findings = [finding for finding in result.findings if finding.code == "DEPENDENCY_CYCLE"]
    assert {finding.task_id for finding in cycle_findings} == {2, 3}
    assert all(finding.field == "depends_on" and finding.path for finding in cycle_findings)
    assert all("2 -> 3 -> 2" in finding.detail for finding in cycle_findings)


def test_task_health_classifies_duplicate_sets_without_mutation(tmp_path: Path) -> None:
    board = _board(tmp_path)
    active_one = board / "tasks" / "4-one.md"
    active_two = board / "tasks" / "4-two.md"
    active_three = board / "tasks" / "4-three.md"
    archived = board / "archive" / "5-archived.md"
    archived_copy = board / "tasks" / "5-archived-copy.md"
    active_one.write_text(_task(4), encoding="utf-8")
    active_two.write_text(_task(4).replace("body", "different body"), encoding="utf-8")
    active_three.write_text(_task(4).replace("body", "third body"), encoding="utf-8")
    archived_content = _task(5).replace("status: shape", "status: archived")
    archived.write_text(archived_content, encoding="utf-8")
    archived_copy.write_text(archived_content, encoding="utf-8")
    before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in board.rglob("*.md")}

    result = KanbanEngine(board, activity_log=False).task_health()

    findings = {finding.task_id: finding for finding in result.findings if finding.code == "DUPLICATE_TASK_ID"}
    assert findings[4].repairable is False
    assert findings[5].repairable is True
    after = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in board.rglob("*.md")}
    assert after == before


def test_task_health_reports_readable_and_unreadable_persisted_defects(tmp_path: Path) -> None:
    board = _board(tmp_path)
    defective = _task(6).replace(
        "parent: null\ndepends_on: []\nblocked: false\narchival_reason: null\narchival_refs: []",
        "parent: 60\ndepends_on: [61, 6]\nblocked: false\narchival_reason: null\narchival_refs: [62]",
    )
    defective_path = board / "tasks" / "6-defective.md"
    unreadable_path = board / "tasks" / "7-unreadable.md"
    defective_path.write_text(defective, encoding="utf-8")
    unreadable_path.write_text("not frontmatter", encoding="utf-8")
    before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in board.rglob("*.md")}

    result = KanbanEngine(board, activity_log=False).task_health()

    findings = {finding.code: finding for finding in result.findings}
    assert findings["ERR_CORRUPT_DELIMITERS"].path == str(unreadable_path)
    assert findings["MISSING_PARENT"].task_id == 6
    assert findings["MISSING_PARENT"].field == "parent"
    assert findings["MISSING_DEPENDENCY"].task_id == 6
    assert findings["MISSING_DEPENDENCY"].field == "depends_on"
    assert findings["DEPENDENCY_SELF_REFERENCE"].task_id == 6
    assert findings["MISSING_ARCHIVAL_REFERENCE"].task_id == 6
    assert findings["MISSING_ARCHIVAL_REFERENCE"].field == "archival_refs"
    after = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in board.rglob("*.md")}
    assert after == before


def test_task_health_reports_reference_and_archived_location_drift(tmp_path: Path) -> None:
    board = _board(tmp_path)
    active_path = board / "tasks" / "8-archived.md"
    active_path.write_text(_task(8).replace("status: shape", "status: archived"), encoding="utf-8")
    (board / "tasks" / "9-references.md").write_text(
        _task(9).replace(
            "parent: null\ndepends_on: []\nblocked: false\narchival_reason: null\narchival_refs: []",
            "parent: 90\ndepends_on: [91]\nblocked: false\narchival_reason: null\narchival_refs: [92]",
        ),
        encoding="utf-8",
    )

    result = KanbanEngine(board, activity_log=False).task_health()

    findings = {finding.code: finding for finding in result.findings}
    assert findings["ARCHIVED_TASK_IN_ACTIVE_STORAGE"].task_id == 8
    assert findings["ARCHIVED_TASK_IN_ACTIVE_STORAGE"].path == str(active_path)
    assert str(active_path) in findings["ARCHIVED_TASK_IN_ACTIVE_STORAGE"].detail
    assert str(board / "archive") in findings["ARCHIVED_TASK_IN_ACTIVE_STORAGE"].detail
    assert findings["MISSING_PARENT"].task_id == 9
    assert findings["MISSING_DEPENDENCY"].task_id == 9
    assert findings["MISSING_ARCHIVAL_REFERENCE"].task_id == 9
