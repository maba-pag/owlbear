---
id: 529
title: Extract _entity_from_row and _edge_from_row helpers in graph.py
status: archived
priority: nice-to-have
created: 2026-03-04T07:38:35.4144425+01:00
updated: 2026-03-15T10:27:20.4080047+01:00
started: 2026-03-07T00:16:21.6929909+01:00
completed: 2026-03-15T10:26:57.8740971+01:00
tags:
    - audit
    - dry
    - knowledge
class: standard
---

F-09: Entity and Edge row-to-model deserialization via tuple indexing repeated in 5 methods. Extract _entity_from_row(row) and _edge_from_row(row) helpers. AC: single deserialization point, all methods use it. See docs/code-quality-audit.md.

## Research (checklist items 1-3): N/A - trivial DRY extraction

### Findings

**Entity deserialization** (3 sites, identical 8-field tuple unpacking):
- get_entity (L92)
- list_entities (L136)
- list_entities_for_document (L173)

All use: Entity(id=row[0], name=row[1], entity_type=row[2], description=row[3], metadata=_load_meta(row[4]), scope=row[5], document_id=row[6], chunk_id=row[7])

**Edge deserialization** (2 sites, identical 7-field tuple unpacking):
- get_edge (L238)
- list_edges (L281)

All use: Edge(id=row[0], source_id=row[1], target_id=row[2], relation=row[3], weight=row[4], metadata=_load_meta(row[5]), scope=row[6])

**SELECT column order is consistent** across all sites for each model, so the helpers can be simple staticmethods next to _load_meta.

### Approach
1. Add _entity_from_row(row) staticmethod returning Entity
2. Add _edge_from_row(row) staticmethod returning Edge
3. Replace all 5 sites with calls to the new helpers
4. Run existing tests (no behavior change)

[[2026-03-15]] Sun 08:05
## Acceptance Criteria (Refined)

- [ ] _entity_from_row(row) staticmethod on GraphStore: 9-element tuple, _load_meta for metadata, importance defaults to 0.5 when None
- [ ] _edge_from_row(row) staticmethod on GraphStore: 7-element tuple, _load_meta for metadata
- [ ] get_entity, list_entities, list_entities_for_document all call _entity_from_row
- [ ] get_edge, list_edges all call _edge_from_row
- [ ] Zero inline Entity/Edge construction from row tuples remains in graph.py
- [ ] All existing graph tests pass
- [ ] Ruff clean on src/owlbear/memory/knowledge/graph.py

[[2026-03-15]] Sun 08:05
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
- Original AC 'single deserialization point, all methods use it' was too vague. Replaced with 7 precise verifiable AC lines.

### Architecture Notes
- Pure DRY refactoring within memory/knowledge/graph.py. No behavior change, no new interfaces, no layer violations.
- Helpers follow existing @staticmethod pattern (_load_meta, _dump_meta, _now).
- Stale description fixed: original body said 8-field Entity, actual code has 9 fields (importance added later). AC now specifies 9-element tuple.
- No separate test task needed: existing coverage on all 5 methods provides full regression safety for a refactoring.

### Dependencies
- None. Standalone DRY cleanup.

[[2026-03-15]] Sun 08:29
## Test-Writer Notes
- Test file: tests/test_graph_row_helpers.py
- Classes: TestFromAC_EntityFromRow, TestFromAC_EdgeFromRow, TestFromAC_EntityMethodsDelegation, TestFromAC_EdgeMethodsDelegation, TestFromAC_NoInlineConstruction
- Tests per category: happy 9, edge 3, error 0, boundary 2, delegation 5
- Total: 19 tests, all FAIL
- ruff: clean
- AC coverage:

| AC Line | Test(s) | Category |
|---------|---------|----------|
| _entity_from_row staticmethod, 9-tuple, importance default | test_entity_from_row_exists_as_staticmethod, test_returns_entity_model, test_maps_all_nine_fields, test_importance_defaults_to_half_when_none, test_metadata_deserialized_via_load_meta, test_none_metadata_gives_empty_dict, test_empty_string_metadata_gives_empty_dict | happy, edge, boundary |
| _edge_from_row staticmethod, 7-tuple | test_edge_from_row_exists_as_staticmethod, test_returns_edge_model, test_maps_all_seven_fields, test_metadata_deserialized_via_load_meta, test_none_metadata_gives_empty_dict | happy, edge |
| get_entity/list_entities/list_entities_for_document call _entity_from_row | test_get_entity_calls, test_list_entities_calls, test_list_entities_for_document_calls | delegation |
| get_edge/list_edges call _edge_from_row | test_get_edge_calls, test_list_edges_calls | delegation |
| Zero inline Entity/Edge construction | test_no_inline_entity_from_row_in_source, test_no_inline_edge_from_row_in_source | boundary |

[[2026-03-15]] Sun 09:28
## Review Evidence

### Test Results
- pytest: 19 passed, 0 failed (test_graph_row_helpers.py)
- Existing graph tests: 52 passed, 0 failed (graph_row_helpers + graph_store_neighbors + graph_builder)

### Lint Results
- ruff: All checks passed on graph.py + test_graph_row_helpers.py

### Coverage
- graph.py: 49% (pre-existing; task-added helpers at L58-82 are 100% covered by direct + delegation tests)

### Pass 1 - CRITICAL
#### Security Review
- No security issues. SQL remains parameterized. No new deps. No deserialization risk.

#### Test Integrity (TestFromAC comparison)
Builder did NOT modify test file (git log shows only test-writer commit a276ca8).
All 19 TestFromAC tests PRESERVED as-is.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | All 9 entity fields + 7 edge fields checked by exact value (L106-118, L172-178) |
| Negative/error paths | ADEQUATE | None/empty-string metadata edge cases covered; importance=None default tested |
| Mutation reasoning | STRONG | Swapping row indices would fail field assertions; removing importance default would fail L124 |
| Test independence | STRONG | Each class uses its own fixture; no shared mutable state |
| Descriptive names | STRONG | e.g. test_importance_defaults_to_half_when_none, test_no_inline_entity_from_row_in_source |

#### Data Safety
- No data safety issues. Pure refactoring of existing deserialization logic.

### Pass 2 - INFORMATIONAL
- No informational findings. Clean, minimal refactoring.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| _entity_from_row staticmethod, 9-tuple, importance default | graph.py L58-70, staticmethod with 9 fields, importance=row[8] if not None else 0.5 | test_entity_from_row_exists_as_staticmethod, test_maps_all_nine_fields, test_importance_defaults_to_half_when_none | PASS |
| _edge_from_row staticmethod, 7-tuple | graph.py L73-82, staticmethod with 7 fields | test_edge_from_row_exists_as_staticmethod, test_maps_all_seven_fields | PASS |
| get_entity/list_entities/list_entities_for_document call _entity_from_row | graph.py L122, L157, L183 all use self._entity_from_row | test_get_entity_calls, test_list_entities_calls, test_list_entities_for_document_calls | PASS |
| get_edge/list_edges call _edge_from_row | graph.py L237, L271 both use self._edge_from_row | test_get_edge_calls, test_list_edges_calls | PASS |
| Zero inline Entity/Edge construction | grep for Entity(id=row and Edge(id=row returns 0 matches | test_no_inline_entity_from_row_in_source, test_no_inline_edge_from_row_in_source | PASS |
| All existing graph tests pass | 52 passed across 3 graph test files | All graph test suites | PASS |
| Ruff clean on graph.py | ruff check: All checks passed! | - | PASS |

### Process Note
Source changes (graph.py) are uncommitted. Test file committed by test-writer (a276ca8).

### Verdict: PASS
### Confidence: .95
### Action: move to docs, release claim

[[2026-03-15]] Sun 09:28
## Review Evidence
See docs/scratch/529-reviewer.md for full evidence.
Verdict: PASS | Confidence: .95

[[2026-03-15]] Sun 09:28
## Review Evidence
Verdict: PASS | Confidence: .95

### Test Results
- pytest test_graph_row_helpers.py: 19 passed, 0 failed
- All graph tests (52 total): 0 failures

### Lint: ruff clean
### Coverage: graph.py helpers 100% covered

### Pass 1 CRITICAL
- Security: No issues (parameterized SQL, no new deps)
- TestFromAC: All 19 tests PRESERVED (builder did not modify test file)
- Test quality: all dimensions STRONG/ADEQUATE
- Data safety: No issues (pure refactoring)

### AC Compliance (all PASS)
- _entity_from_row staticmethod at L58-70
- _edge_from_row staticmethod at L73-82
- 3 entity methods delegate at L122, L157, L183
- 2 edge methods delegate at L237, L271
- Zero inline Entity/Edge(id=row) remaining
- All existing graph tests pass (52/52)
- Ruff clean

[[2026-03-15]] Sun 09:56
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Pure DRY refactoring, no behavior/API change |
| 2 | Docstrings complete | Yes | Pass | _entity_from_row (L59) and _edge_from_row (L74) both have docstrings |
| 3 | sources/overview.md | No | N/A | No external patterns adopted |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | No | N/A | Trivial DRY extraction, no research phase |
| 6 | No impact | -- | -- | Items 1,3-5 N/A; item 2 verified |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/529-* found)

[[2026-03-15]] Sun 10:27
## Audit (2026-03-15)
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| _entity_from_row staticmethod, 9-tuple, importance default | graph.py L58-70: staticmethod, 9 fields, importance=row[8] if not None else 0.5 | PASS |
| _edge_from_row staticmethod, 7-tuple | graph.py L73-82: staticmethod, 7 fields | PASS |
| get_entity/list_entities/list_entities_for_document call _entity_from_row | L122, L157, L183 all use self._entity_from_row | PASS |
| get_edge/list_edges call _edge_from_row | L237, L271 both use self._edge_from_row | PASS |
| Zero inline Entity/Edge from row tuples | grep Entity(id=row and Edge(id=row: 0 matches | PASS |
| All existing graph tests pass | 52 passed (graph_row_helpers+graph_store_neighbors+graph_builder), 122 knowledge tests total | PASS |
| Ruff clean on graph.py | ruff check: All checks passed! | PASS |

### Test Results
- Task-specific: 52 passed, 0 failed
- Broader knowledge: 122 passed, 0 failed
- Ruff: clean on task files

### Process Gap
graph.py uncommitted by builder. Committed by auditor as f41662a.

### Confidence: .97
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| a276ca8 | test | test_graph_row_helpers.py | #529 |
| f41662a | refactor | graph.py | #529 |
