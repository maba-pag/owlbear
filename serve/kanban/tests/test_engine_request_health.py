"""Real-filesystem coverage for the public request-health boundary."""

from __future__ import annotations

import uuid
from pathlib import Path

from owlbear_kanban import KanbanEngine


_CONFIG_YAML = "next_id: 1001\n"

_TASK_TEMPLATE = """\
---
id: {task_id}
title: Task {task_id}
status: {status}
priority: medium
created: "2026-01-01T10:00:00+00:00"
updated: "2026-01-01T10:00:00+00:00"
tags: []
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_at: null
archival_reason: null
archival_refs: []
---

Body text.
"""


def _make_engine(tmp_path: Path, task_ids: tuple[int, ...] = ()) -> tuple[KanbanEngine, Path]:
    kanban_dir = tmp_path / "board"
    (kanban_dir / "tasks").mkdir(parents=True)
    (kanban_dir / "archive").mkdir()
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    for task_id in task_ids:
        (kanban_dir / "tasks" / f"{task_id}-task.md").write_text(
            _TASK_TEMPLATE.format(task_id=task_id, status="build"), encoding="utf-8"
        )
    return KanbanEngine(kanban_dir, activity_log=False), kanban_dir


def _write_request(
    kanban_dir: Path,
    *,
    subdir: str = "pending",
    request_id: str | None = None,
    task_id: int = 42,
    resolved_at: str | None = None,
) -> Path:
    request_id = request_id or str(uuid.uuid4())
    path = kanban_dir / "decisions" / subdir / f"{request_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    resolved_value = f"'{resolved_at}'" if resolved_at else "null"
    path.write_text(
        f"""---
request_id: '{request_id}'
task_id: {task_id}
kind: action
title: Test Request
summary: A test summary.
agent: test-agent
created_at: '2026-05-24T12:00:00+02:00'
options: []
resolution:
  selected_option_id: null
  free_text: null
  resolved_at: {resolved_value}
---
Request body.
""",
        encoding="utf-8",
    )
    return path


def test_request_health_reports_malformed_duplicates_and_does_not_mutate_storage(tmp_path: Path) -> None:
    engine, kanban_dir = _make_engine(tmp_path)
    duplicate_id = str(uuid.uuid4())
    first = _write_request(kanban_dir, request_id=duplicate_id)
    second = _write_request(kanban_dir, subdir="resolved", request_id=duplicate_id, resolved_at="2026-05-24T14:00:00+02:00")
    malformed = kanban_dir / "decisions" / "pending" / "malformed.md"
    malformed.write_text("not frontmatter", encoding="utf-8")
    before = {path: path.read_bytes() for path in (first, second, malformed)}

    result = engine.request_health()

    findings = result.findings
    assert any(finding.code == "REQUEST_SCHEMA_ERROR" and finding.path == str(malformed) for finding in findings)
    duplicate = next(finding for finding in findings if finding.code == "DUPLICATE_REQUEST_ID")
    assert duplicate.request_id == duplicate_id
    assert duplicate.path == f"{first}, {second}"
    assert {path: path.read_bytes() for path in before} == before


def test_request_health_accepts_active_and_archived_owners_and_reports_missing_owner(tmp_path: Path) -> None:
    engine, kanban_dir = _make_engine(tmp_path, (10,))
    (kanban_dir / "archive" / "11-task.md").write_text(
        _TASK_TEMPLATE.format(task_id=11, status="archived"), encoding="utf-8"
    )
    active = _write_request(kanban_dir, task_id=10)
    archived = _write_request(kanban_dir, task_id=11)
    missing = _write_request(kanban_dir, task_id=99)

    result = engine.request_health()

    owner_findings = [finding for finding in result.findings if finding.code == "MISSING_REQUEST_OWNER"]
    assert [(finding.request_id, finding.task_id, finding.path) for finding in owner_findings] == [
        (missing.stem, 99, str(missing))
    ]
    assert active.stem not in {finding.request_id for finding in owner_findings}
    assert archived.stem not in {finding.request_id for finding in owner_findings}


def test_request_health_reports_both_location_mismatch_directions(tmp_path: Path) -> None:
    engine, kanban_dir = _make_engine(tmp_path)
    completed_in_pending = _write_request(
        kanban_dir, request_id=str(uuid.uuid4()), resolved_at="2026-05-24T14:00:00+02:00"
    )
    unresolved_in_resolved = _write_request(kanban_dir, subdir="resolved")

    result = engine.request_health()

    mismatches = {finding.path: finding for finding in result.findings if finding.code == "REQUEST_LOCATION_MISMATCH"}
    assert set(mismatches) == {str(completed_in_pending), str(unresolved_in_resolved)}
    assert "belongs in resolved" in mismatches[str(completed_in_pending)].detail
    assert "belongs in pending" in mismatches[str(unresolved_in_resolved)].detail
