---
id: 1468
title: 'E2a-B3: Merge cockpit_mutation_api task tests into durable'
status: backlog
priority: important
created: 2026-05-09T07:21:35.681226+00:00
updated: 2026-05-09T07:24:15.308956+00:00
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

Merge 7 task-scoped files (105 tests) into existing `test_cockpit_mutation_api.py` (53 tests), then delete sources.

### Source files

| File | Tests |
|------|:-----:|
| test_cockpit_mutation_api_1132.py | 28 |
| test_cockpit_mutation_api_1134.py | 9 |
| test_cockpit_mutation_api_1135.py | 14 |
| test_cockpit_mutation_api_1239.py | 12 |
| test_cockpit_mutation_api_1243.py | 19 |
| test_cockpit_mutation_api_1344.py | 5 |
| test_cockpit_mutation_api_1448.py | 18 |

**Target:** `test_cockpit_mutation_api.py` (existing durable, 53 tests pre-merge)

## AC (td:0)

- [ ] All unique `def test_*` from 7 source files present in `test_cockpit_mutation_api.py`
- [ ] Duplicate test-name collisions resolved by renaming incoming to `test_{name}_1468`
- [ ] Fixture collisions: keep target's if identical, rename source's if different
- [ ] All 7 source files deleted after merge
- [ ] Per-target checkpoint: `uv run pytest tests/test_cockpit_mutation_api.py --collect-only -q` collects ≥ 158 tests (53 existing + 105 merged)
- [ ] `uv run pytest tests/test_cockpit_mutation_api.py -x` passes
- [ ] Full suite: `uv run pytest tests/ --collect-only -q` count does not decrease vs pre-task baseline
- [ ] `uv run pytest tests/ -x` passes with no new failures
- [ ] `test_kanban_topology_1439.py` untouched

## Out of scope

- Other merge targets (decisions_api, mcp_kanban, read_api, pipeline_diagram)
- Renames — handled in #1466


## AC Correction (architect)
**Replace** all `pytest -x` AC lines with delta-based verification:
- Post-cleanup failure count ≤ pre-task baseline failure count (capture baseline before any changes)
- Collected test count ≥ pre-task collect-only baseline

**Replace** collision rename suffix with the source file's original task ID for traceability.