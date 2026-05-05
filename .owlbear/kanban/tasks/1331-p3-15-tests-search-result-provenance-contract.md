---
id: 1331
title: 'P3-15: Tests — Search result provenance contract'
status: review
priority: important
created: 2026-05-04T05:48:50.155044+00:00
updated: 2026-05-05T03:07:16.162216+00:00
tags:
- phase-3
- scope:mcp-knowledge
- knowledge
- test
parent: 1316
depends_on:
- 1324
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1316 → `.owlbear/briefs/draft-knowledge-activation/brief.md` (§4.8)

## Acceptance Criteria

- [ ] Tests verify search results include retrieval_path field with valid enum values: "vector", "graph", "vector+graph" (td:2)
- [ ] Tests verify search results include entities array of {name, type} objects (td:1)
- [ ] Tests verify search results include related_sources array of {name, relationship, entity} objects (td:1)
- [ ] Tests verify entities=[] and related_sources=[] when enrichment has not been run; retrieval_path defaults to "vector"; source is always populated (td:2)
- [ ] Tests verify all provenance keys are present in every result dict regardless of enrichment state — no missing keys, arrays are empty not absent (td:2)
- [ ] Tests verify source field is an object with name (str) and url (str) keys (td:1)

## Scope

- **In scope:** search_knowledge response contract tests for provenance fields (retrieval_path, entities, related_sources, source). Tests assert these fields on the MCP tool response dicts.
- **Out of scope:** Graph query optimization, ranking algorithm changes, full response envelope migration (list→wrapped object, snippet→chunk_text rename — those are #1332 implementation decisions), query-service-layer assembly tests (belong in #1332 or a dedicated integration task).
- **Test layer:** MCP tool level — mock `query_service.query()` following `test_search_v2.py` patterns. Use `MagicMock`/`AsyncMock` for provenance attributes on mock results.
- **Test file:** `tests/test_search_provenance_1331.py`
- **Existing test awareness:** `test_search_v2.py`, `test_outputschema_541.py`, and `test_ingest_graph_wiring.py` pin the current response shape. New tests assert provenance additions without conflicting — #1332 will reconcile old shape tests when implementing.

## Research

Analyzed Brief §4.8 provenance contract against current search_knowledge implementation.

**Key findings:**
- Current response: {title, score, snippet, entity_type} — missing 4 provenance fields
- Required additions: retrieval_path (enum), entities (array), related_sources (array), source (name+url object)
- Infrastructure exists: KnowledgeSource model (name, config.url), graph_store.list_entities_for_document(), get_neighbors() for cross-source edges
- Empty-state behavior: entities=[], related_sources=[] when unenriched; retrieval_path="vector" when unenriched; source always populated (set at ingest)

**Testing approach:** Two test classes (MCP tool shape + determinism), mock query_service at MCP layer following test_search_v2.py patterns.

**Doc:** .owlbear/research/1331-search-provenance-contract.md
**Confidence:** 0.90
**Tier:** T1 (autonomous) — no decisions needed, brief specifies contract fully.
**No new follow-up tasks** — TDD pair #1331/#1332 already exists.
[[2026-05-05]]
## Architecture Review

### Verdict: APPROVED → todo

AC refined for precision; architecture sound for RED-phase test task.

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| retrieval_path field (vector/graph/vector+graph) | Original lacked type/enum spec | Refined: explicit enum values, td:2 |
| entities array | Lacked object shape spec | Refined: {name, type} objects, td:1 |
| related_sources array | Lacked object shape spec | Refined: {name, relationship, entity} objects, td:1 |
| provenance fields empty when unenriched | **Imprecise** — said "empty arrays" but retrieval_path is string, source is always populated | Refined: entities=[], related_sources=[], retrieval_path="vector", source always populated, td:2 |
| response shape deterministic | **Vague** — didn't specify what "deterministic" means | Refined: all keys present in every dict, arrays empty not absent, td:2 |
| source field name+URL | Clear but lacked type spec | Refined: object with name (str) and url (str), td:1 |

### Architecture Notes

- **Test layer**: MCP tool level (mock query_service.query()) — correct for contract tests. Assembly correctness is #1332's scope.
- **Mock strategy**: MagicMock/AsyncMock following test_search_v2.py patterns. Mock objects can carry arbitrary provenance attributes; tests assert search_knowledge serializes them into response dicts.
- **Existing tests**: test_search_v2.py, test_outputschema_541.py, test_ingest_graph_wiring.py pin current shape. New tests are additive (provenance fields), not conflicting. #1332 reconciles old shape tests.
- **Scope boundary**: Task tests provenance field presence/shape only. Full response envelope migration (list→wrapped, snippet→chunk_text) is out of scope — implementation decision for #1332.

### Dependency Analysis

- **#1324** (enrichment schema): archived/done. Provides enrichment_state, claims, edge uniqueness. Logical prerequisite for provenance (provenance uses entities from enrichment). Dependency is soft for mock-based tests but ordering is correct.
- **#1332** (implementation): depends on #1331. TDD pair intact.

### Challenger Results

Challenger returned **reconsider** (confidence 0.42). Four challenges assessed:

1. **Contract contradiction** (brief envelope vs current shape): Downgraded — task scoped to provenance fields, not full migration. Added explicit scope note.
2. **False-green test strategy**: Accepted as noted — MCP-layer mocking is correct for contract tests. Assembly tests belong in #1332.
3. **Dependency overclaim** (#1324 doesn't provide provenance interfaces): Acknowledged — dependency is logical ordering, not interface dependency. Tests mock everything.
4. **Interface gap** (StructuredSearchResult lacks provenance fields): Expected in TDD RED phase — tests are written before interface exists.

All concerns addressed through AC refinement and scope clarification. Override justified: challenger evaluated as if this were a full-stack implementation task, not a RED-phase test task where mocking the target interface is the correct approach.
[[2026-05-05]]
## Test-Writer Notes

- **Test file:** `tests/test_search_provenance_1331.py`
- **Test classes:** `TestFromAC_SearchProvenanceFields`, `TestFromAC_SearchProvenanceUnenrichedState`, `TestFromAC_SearchProvenanceDeterminism`
- **Total tests:** 21 — all FAIL (RED phase confirmed)
- **Lint:** ruff clean

### Tests per category
| Category | Count | Tests |
|----------|-------|-------|
| Happy / field presence | 4 | retrieval_path key + 3 enum values |
| Structured shape | 4 | entities items {name,type}, related_sources items {name,relationship,entity} |
| Unenriched defaults | 4 | entities=[], related_sources=[], retrieval_path="vector", source present |
| Determinism / all-keys | 4 | all provenance keys enriched, all keys unenriched, empty-not-absent ×2 |
| Source field contract | 5 | is dict, has name key, has url key, name is str, url is str, name/url match mock |

### AC Coverage
| AC Line | Tests |
|---------|-------|
| retrieval_path field with enum values "vector"/"graph"/"vector+graph" (td:2) | test_retrieval_path_key_present, test_retrieval_path_value_is_vector, test_retrieval_path_value_is_graph, test_retrieval_path_value_is_vector_plus_graph |
| entities array of {name, type} objects (td:1) | test_entities_key_present_and_is_list, test_entities_items_have_name_and_type_keys |
| related_sources array of {name, relationship, entity} objects (td:1) | test_related_sources_key_present_and_is_list, test_related_sources_items_have_required_keys |
| unenriched: entities=[], related_sources=[], retrieval_path="vector", source populated (td:2) | test_unenriched_entities_is_empty_list, test_unenriched_related_sources_is_empty_list, test_unenriched_retrieval_path_defaults_to_vector, test_source_always_present_in_unenriched_result |
| all provenance keys present regardless of enrichment state (td:2) | test_all_provenance_keys_present_in_enriched_result, test_all_provenance_keys_present_in_unenriched_result, test_entities_empty_not_absent, test_related_sources_empty_not_absent |
| source field with name (str) and url (str) (td:1) | test_source_field_is_dict_with_name_and_url, test_source_name_value_is_str, test_source_url_value_is_str, test_source_name_matches_mock_value, test_source_url_matches_mock_value |

### Failure root cause
`search_knowledge` serializes only `{title, score, snippet, entity_type}` — the 4 provenance fields are absent from the current dict comprehension. All assertions on `retrieval_path`, `entities`, `related_sources`, `source` raise `AssertionError` or `KeyError`. No import errors.

### Mock strategy
Used `MagicMock` objects (not `StructuredSearchResult` instances) so provenance attributes can be set freely before the fields exist on the model. `_make_enriched_result()` sets all provenance attrs; `_make_unenriched_result()` sets empty defaults. Follows `test_search_v2.py` ctx-mocking pattern.
[[2026-05-05]]
## Builder Notes
- Implementation: added provenance-aware search result serialization in serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py.
- Files changed: serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py
- Tests: 21/21 TestFromAC tests passed in tests/test_search_provenance_1331.py (quality-runner scoped).
- Durable regression check: 18/18 passed in serve/mcp-knowledge/tests/test_search_v2.py.
- Coverage: 36% for module owlbear_mcp_knowledge.server in scoped run.
- Ruff: clean for changed source file and task test file.
- Approach: extended SearchResult contract with retrieval_path, entities, related_sources, and source; added normalizers that ensure keys are always present with unenriched-safe defaults (retrieval_path defaults to "vector", list fields default to [], source defaults to {name:"", url:""}).
- Fixes applied: resolved ANN401 lint findings by tightening helper input types from Any to object.

### Evidence Summary
- RED verification before implementation: 21/21 failed in tests/test_search_provenance_1331.py.
- GREEN verification after implementation: 21/21 passed, failed=[].
- Lint verification after fix: clean=true, violations=[].
- Commit: 6803ae98 with only serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py staged.

### Post-task Reflection
- The smallest successful intervention was confined to response serialization; no query/graph pipeline behavior needed changes.
- Using dedicated normalizers made it easy to satisfy both enriched and unenriched key-presence guarantees without touching models.
- Existing package-level search tests remained green, which lowers regression risk for legacy response fields.
- Module coverage remains low because server.py is broad; scoped proof is strongest at the task test level for this change.