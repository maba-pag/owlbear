---
id: 1467
title: 'E2a-B2: Merge cockpit_decisions_api task tests into durable'
status: backlog
priority: important
created: 2026-05-09T07:21:35.670259+00:00
updated: 2026-05-09T07:24:15.251344+00:00
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

Merge 6 task-scoped files (72 tests) into existing `test_cockpit_decisions_api.py` (10 tests), then delete sources.

### Source files

| File | Tests |
|------|:-----:|
| test_cockpit_decisions_api_1189.py | 8 |
| test_cockpit_decisions_api_1190.py | 26 |
| test_cockpit_decisions_api_1194.py | 3 |
| test_cockpit_decisions_api_1345.py | 5 |
| test_cockpit_decisions_api_1384.py | 23 |
| test_cockpit_decisions_api_1385.py | 7 |

**Target:** `test_cockpit_decisions_api.py` (existing durable, 10 tests pre-merge)

## AC (td:0)

- [ ] All unique `def test_*` from 6 source files present in `test_cockpit_decisions_api.py`
- [ ] Duplicate test-name collisions resolved by renaming incoming to `test_{name}_1467`
- [ ] Fixture collisions: keep target's if identical, rename source's if different
- [ ] All 6 source files deleted after merge
- [ ] Per-target checkpoint: `uv run pytest tests/test_cockpit_decisions_api.py --collect-only -q` collects ≥ 82 tests (10 existing + 72 merged)
- [ ] `uv run pytest tests/test_cockpit_decisions_api.py -x` passes
- [ ] Full suite: `uv run pytest tests/ --collect-only -q` count does not decrease vs pre-task baseline
- [ ] `uv run pytest tests/ -x` passes with no new failures
- [ ] `test_kanban_topology_1439.py` untouched

## Out of scope

- Other merge targets (mutation_api, mcp_kanban, read_api, pipeline_diagram)
- Renames — handled in #1466


## AC Correction (architect)
**Replace** all `pytest -x` AC lines with delta-based verification:
- Post-cleanup failure count ≤ pre-task baseline failure count (capture baseline before any changes)
- Collected test count ≥ pre-task collect-only baseline

**Replace** collision rename suffix `_1467` with the source file's original task ID (e.g., `test_{name}_1189` for tests from `_1189.py`) for traceability.