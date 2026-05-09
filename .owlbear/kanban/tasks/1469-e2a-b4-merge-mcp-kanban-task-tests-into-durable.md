---
id: 1469
title: 'E2a-B4: Merge mcp_kanban task tests into durable'
status: backlog
priority: important
created: 2026-05-09T07:21:35.691519+00:00
updated: 2026-05-09T07:24:15.303806+00:00
tags:
- pipeline
- ws-cleanup
- scope:tests
- quality
parent: 1415
depends_on:
- 1466
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Research: `.owlbear/research/1463-python-root-test-cleanup.md` §5b
Supersedes: #1463 (partial)

## Scope

Merge 7 task-scoped files (53 tests) into existing `test_mcp_kanban.py` (67 tests), then delete sources.

### Source files

| File | Tests |
|------|:-----:|
| test_mcp_kanban_1091.py | 3 |
| test_mcp_kanban_1092.py | 7 |
| test_mcp_kanban_1126.py | 1 |
| test_mcp_kanban_1196.py | 12 |
| test_mcp_kanban_1197.py | 5 |
| test_mcp_kanban_1360.py | 8 |
| test_mcp_kanban_1450.py | 17 |

**Target:** `test_mcp_kanban.py` (existing durable, 67 tests pre-merge)

## AC (td:0)

- [ ] All unique `def test_*` from 7 source files present in `test_mcp_kanban.py`
- [ ] Duplicate test-name collisions resolved by renaming incoming to `test_{name}_1469`
- [ ] Fixture collisions: keep target's if identical, rename source's if different
- [ ] All 7 source files deleted after merge
- [ ] Per-target checkpoint: `uv run pytest tests/test_mcp_kanban.py --collect-only -q` collects ≥ 120 tests (67 existing + 53 merged)
- [ ] `uv run pytest tests/test_mcp_kanban.py -x` passes
- [ ] Full suite: `uv run pytest tests/ --collect-only -q` count does not decrease vs pre-task baseline
- [ ] `uv run pytest tests/ -x` passes with no new failures
- [ ] `test_kanban_topology_1439.py` untouched

## Out of scope

- Other merge targets (decisions_api, mutation_api, read_api, pipeline_diagram)
- Renames — handled in #1466


## AC Correction (architect)
**Replace** all `pytest -x` AC lines with delta-based verification:
- Post-cleanup failure count ≤ pre-task baseline failure count (capture baseline before any changes)
- Collected test count ≥ pre-task collect-only baseline

**Replace** collision rename suffix with the source file's original task ID for traceability.