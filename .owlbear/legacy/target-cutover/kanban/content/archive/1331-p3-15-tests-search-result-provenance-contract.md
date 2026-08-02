---
id: 1331
title: 'P3-15: Tests — Search result provenance contract'
status: archived
priority: medium
created: 2026-05-04T05:48:50.155044+00:00
updated: 2026-05-05T05:32:34.241538+00:00
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
[[2026-05-05]]
## Review Evidence
### Test Results
- Quality-runner task-scoped rerun: 21 collected, 21 passed for [tests/test_search_provenance_1331.py](tests/test_search_provenance_1331.py#L112-L464).
- Adjacent durable regression: 24 passed for [serve/mcp-knowledge/tests/test_search_v2.py](serve/mcp-knowledge/tests/test_search_v2.py#L64-L319).

### Lint
- Clean for [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L162-L219) and [tests/test_search_provenance_1331.py](tests/test_search_provenance_1331.py#L35-L464).

### Coverage
- Scoped coverage reported 36% for [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L654-L668).
- Informational only: the task-owned serialization slice at [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L654-L668) is directly exercised by the 21 task tests plus the 24 adjacent regression tests; low module-level percentage reflects the breadth of server.py, not an uncovered task-owned branch.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| retrieval_path field with enum values vector / graph / vector+graph | [tests/test_search_provenance_1331.py](tests/test_search_provenance_1331.py#L112-L156) | Yes. Key omission or wrong serialized value fails exact assertions against [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L654-L662). | COVERED |
| entities array of {name, type} objects | [tests/test_search_provenance_1331.py](tests/test_search_provenance_1331.py#L163-L200) | Yes. Missing key, wrong container type, or missing item keys fails against serialization in [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L162-L176). | COVERED |
| related_sources array of {name, relationship, entity} objects | [tests/test_search_provenance_1331.py](tests/test_search_provenance_1331.py#L207-L249) | Yes. Missing key, wrong container type, or missing item keys fails against serialization in [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L180-L203). | COVERED |
| unenriched entities=[], related_sources=[], retrieval_path=vector, source populated | [tests/test_search_provenance_1331.py](tests/test_search_provenance_1331.py#L265-L323) | Yes for the approved MCP-layer contract: unenriched empty arrays, vector retrieval_path, and populated source all fail if serialization diverges from the mock-carried provenance specified by [task 1331](.owlbear/kanban/tasks/1331-p3-15-tests-search-result-provenance-contract.md#L30) and the scoped mock strategy at [task 1331](.owlbear/kanban/tasks/1331-p3-15-tests-search-result-provenance-contract.md#L78-L81). | COVERED |
| all provenance keys always present; arrays empty not absent | [tests/test_search_provenance_1331.py](tests/test_search_provenance_1331.py#L341-L388) | Yes. Missing keys or absent arrays fail direct presence and empty-list assertions against [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L656-L668). | COVERED |
| source field is object with name and url string keys | [tests/test_search_provenance_1331.py](tests/test_search_provenance_1331.py#L395-L464) | Yes. Wrong container type, missing keys, wrong value types, or wrong serialized values fail direct assertions against [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L206-L219) and [task 1331](.owlbear/kanban/tasks/1331-p3-15-tests-search-result-provenance-contract.md#L32). | COVERED |

#### Security Review
- No issues found in the scoped change. The reviewed logic is normalization and response-dict construction in [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L162-L219) and [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L654-L668); no injection, path handling, unsafe deserialization, or secret exposure was introduced.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_SearchProvenanceFields / UnenrichedState / Determinism in [tests/test_search_provenance_1331.py](tests/test_search_provenance_1331.py#L104-L464) | No weakening or removal observed in the live task test file. Builder notes scope only [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L654-L668) via [task 1331](.owlbear/kanban/tasks/1331-p3-15-tests-search-result-provenance-contract.md#L131-L145), and commit 6803ae985f2ad967676e5f5402c3c3e6ceefbf61 exists in [.git/logs/HEAD](.git/logs/HEAD#L1919) and [.git/logs/refs/heads/dev](.git/logs/refs/heads/dev#L1764). Direct git show/status was unavailable in this tool surface. | PRESERVED with small confidence deduction |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact equality and key-presence assertions at [tests/test_search_provenance_1331.py](tests/test_search_provenance_1331.py#L124-L156), [tests/test_search_provenance_1331.py](tests/test_search_provenance_1331.py#L265-L323), [tests/test_search_provenance_1331.py](tests/test_search_provenance_1331.py#L341-L388), and [tests/test_search_provenance_1331.py](tests/test_search_provenance_1331.py#L395-L464). |
| Negative and state coverage | ADEQUATE | Both enriched and unenriched states are exercised. Query-service assembly coverage is explicitly out of scope per [task 1331](.owlbear/kanban/tasks/1331-p3-15-tests-search-result-provenance-contract.md#L37) and [task 1331](.owlbear/kanban/tasks/1331-p3-15-tests-search-result-provenance-contract.md#L78-L81). |
| Manual mutation reasoning | ADEQUATE | Removing or renaming any provenance key in [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L656-L668) would fail the task suite. The omitted-attribute fallback branches at [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L654-L668) are implementation detail for current runtime compatibility, not an AC-blocking proof requirement for 1331's MCP-layer contract. |
| Test independence | STRONG | Fresh mocks and per-test AsyncMock setup in [tests/test_search_provenance_1331.py](tests/test_search_provenance_1331.py#L35-L95). |
| Descriptive names | STRONG | Test names at [tests/test_search_provenance_1331.py](tests/test_search_provenance_1331.py#L112-L464) map directly to the AC lines. |

#### Data Safety
- No issues found. The scoped code only transforms in-memory query results into output dicts in [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L654-L668).

#### Implementation-Aware Gaps
- No AC-blocking gaps found.
- Code-reader raised omitted-attribute fallback coverage concerns around [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L654-L668), but those branches are outside this task's approved review scope because [task 1331](.owlbear/kanban/tasks/1331-p3-15-tests-search-result-provenance-contract.md#L37) excludes query-service-layer assembly tests and [task 1331](.owlbear/kanban/tasks/1331-p3-15-tests-search-result-provenance-contract.md#L78-L81) explicitly defines this as MCP-layer serialization of mock-carried provenance attributes.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 at [task 1331](.owlbear/kanban/tasks/1331-p3-15-tests-search-result-provenance-contract.md#L131-L145) |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- Commit presence was independently verified from [.git/logs/HEAD](.git/logs/HEAD#L1919) and [.git/logs/refs/heads/dev](.git/logs/refs/heads/dev#L1764), but direct git show and git status were unavailable in this tool surface. I could not independently re-run changed-file ownership or dirty-tree contamination checks; confidence reduced slightly.
- The first mixed-suite quality-runner batch underreported per-file counts. A second task-only scoped run resolved this to 21 collected and 21 passed, so I used the rerun as the authoritative test-count evidence.
- Current runtime query results in [serve/knowledge/src/owlbear_knowledge/query_service.py](serve/knowledge/src/owlbear_knowledge/query_service.py#L17-L124) still do not emit provenance fields directly; that assembly work remains outside this task's approved scope and belongs to later implementation work.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| retrieval_path enum values | Serialization at [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L654-L662) | [tests/test_search_provenance_1331.py](tests/test_search_provenance_1331.py#L112-L156) | PASS |
| entities array shape | Entity normalization at [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L162-L176) | [tests/test_search_provenance_1331.py](tests/test_search_provenance_1331.py#L163-L200) | PASS |
| related_sources array shape | Related-source normalization at [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L180-L203) | [tests/test_search_provenance_1331.py](tests/test_search_provenance_1331.py#L207-L249) | PASS |
| unenriched provenance defaults/presence | Unenriched serialization path at [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L654-L668) and scoped task contract at [task 1331](.owlbear/kanban/tasks/1331-p3-15-tests-search-result-provenance-contract.md#L30) | [tests/test_search_provenance_1331.py](tests/test_search_provenance_1331.py#L265-L323) | PASS |
| all provenance keys always present | Unconditional key construction at [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L656-L668) | [tests/test_search_provenance_1331.py](tests/test_search_provenance_1331.py#L341-L388) | PASS |
| source object shape | Source normalization at [serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py](serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py#L206-L219) and task AC at [task 1331](.owlbear/kanban/tasks/1331-p3-15-tests-search-result-provenance-contract.md#L32) | [tests/test_search_provenance_1331.py](tests/test_search_provenance_1331.py#L395-L464) | PASS |

### Confidence: .94
### Verdict: PASS
[[2026-05-05]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | `serve/mcp-knowledge/README.md` lists `search_knowledge` as "Semantic search over the knowledge base" — no response schema documented; description remains accurate after provenance fields added |
| 2 | Module docstrings | Yes | Verified | `_serialize_search_entities`, `_serialize_related_sources`, `_serialize_source` all have accurate docstrings; `search_knowledge` docstring "Search the knowledge base for relevant context" remains correct |
| 3 | External attribution | No | N/A | Research drew only from internal codebase and brief; no external repos or articles used |
| 4 | Research doc | Yes | Verified | `.owlbear/research/1331-search-provenance-contract.md` exists and is linked in task body |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/mcp-topology.excalidraw` describes `serve/mcp-*/src/**` — matches changed `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`; footer updated from `(ba422c28)` to `(80586384)` |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No files deleted in this task |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` | IN (docstrings) | Verified — docstrings accurate |
| `tests/test_search_provenance_1331.py` | OUT (test file) | No action |
| `share/diagrams/mcp-topology.excalidraw` | IN (diagram) | Footer updated |

### Files Updated
- `share/diagrams/mcp-topology.excalidraw` — footer updated to `Last verified: 2026-05-05 (80586384)` (commit `6a8561b4`)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `1331-*` scratch files found)
[[2026-05-05]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| retrieval_path field with enum values vector/graph/vector+graph | Serialization at server.py:L650-662, tests at test_search_provenance_1331.py:L112-156 | PASS |
| entities array of {name, type} objects | _serialize_search_entities at server.py:L162-176, tests at L163-200 | PASS |
| related_sources array of {name, relationship, entity} objects | _serialize_related_sources at server.py:L180-203, tests at L207-249 | PASS |
| unenriched: entities=[], related_sources=[], retrieval_path=vector, source populated | Defaults via getattr at server.py:L651-668, tests at L265-323 | PASS |
| all provenance keys always present; arrays empty not absent | Unconditional key construction at server.py:L653-668, tests at L341-388 | PASS |
| source field is object with name (str) and url (str) | _serialize_source at server.py:L206-219, tests at L395-464 | PASS |

### Test Results
- pytest: 4439 passed, 262 failed (all outside task scope — kanban engine, mcp-memory, cockpit events), 4 skipped
- ruff: 12 violations (all outside task scope — copilot_auth.py, test_root.py)
- vitest: 950 passed, 13 failed (shell tests, outside scope)
- eslint: 4 problems (outside scope)

### Architect Quality: 5/5
AC lines were specific (enum values, object shapes, unenriched defaults), complete (6 lines covering all provenance fields), and left no ambiguity for test-writer or builder.

### Deduction Breakdown
- No AC lines without evidence: 0
- No lint violations in task scope: 0
- AC quality ≤3: N/A (5/5)
- Reviewer evidence: present, thorough, PASS: 0
- No full-suite failures in task scope: 0

### Confidence: 1.00
### Action: archive

### Commit Verification
- Test-writer: ba422c28 (test: add failing tests for search result provenance contract)
- Builder: 6803ae98 (feat: add search provenance serialization)
- Working tree clean for task-scoped files (no uncommitted changes)