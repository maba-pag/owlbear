---
id: 1873
title: 'Knowledge: GraphStore — entities & edges'
status: archived
priority: needed
created: 2026-05-25T19:03:25.225852+02:00
updated: 2026-05-26T00:53:21.874105+02:00
tags:
  - knowledge
  - layer-1
  - greenfield
parent:
depends_on: []
ac:
  - 'upsert_entity(EntityInput) → EntityRecord: applies canonicalize_name(name) +
    entity_type as identity key; creates new or updates existing; returns EntityRecord
    with deterministic stable ID; raises ValueError if name is empty after canonicalization'
  - 'upsert_entity idempotency: same (canonical_name, entity_type) always yields same
    entity ID; on update, metadata is shallow-merged per CP25 ({**existing, **new})'
  - 'upsert_edge(EdgeInput) → EdgeRecord: creates or updates edge; identity = (source_entity_id,
    target_entity_id, relation_type); on update with same identity: weight and metadata
    are replaced from the new EdgeInput and updated_at advances beyond created_at;
    raises ValueError if source or target entity does not exist; raises ValueError
    if relation_type is SAME_AS'
  - 'get_entity(entity_id) → EntityRecord | None: returns entity with current alias_names
    (empty tuple when no aliases exist) or None if not found'
  - 'find_entities(EntityQuery) → tuple[EntityRecord, ...]: filters by canonical name
    match and/or entity_type; when graph_aliases table exists includes alias matches,
    otherwise queries canonical_name only; respects query.limit; returns empty tuple
    on no match'
  - 'get_adjacent(AdjacencyQuery) → tuple[EdgeRecord, ...]: returns edges adjacent
    to entity_id; respects direction (outgoing/incoming/both) and relation_types filter;
    returns empty tuple for unknown entity_id'
  - 'Table DDL graph_entities: columns (id, name, canonical_name, entity_type, description,
    metadata_json, created_at, updated_at); UNIQUE constraint covers exactly (canonical_name,
    entity_type); ensure_tables() is idempotent'
  - 'Table DDL graph_edges: columns (id, source_entity_id, target_entity_id, relation_type,
    weight, metadata_json, created_at, updated_at); UNIQUE constraint covers exactly
    (source_entity_id, target_entity_id, relation_type); FK source_entity_id → graph_entities.id;
    FK target_entity_id → graph_entities.id; ensure_tables() is idempotent'
  - SqliteGraphStore is synchronous; constructor accepts sqlite3.Connection; 
    upsert methods use explicit BEGIN IMMEDIATE transactions for SELECT+INSERT 
    atomicity
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Objective

Implement entity and edge management with canonical identity (CP1), upsert semantics, adjacency queries, and direction filtering. Owns `graph_entities`, `graph_edges` tables.

## Context

- Protocol: `serve/knowledge/src/owlbear_knowledge/protocols/graph.py`
- Design decisions: CP1 (canonical identity), CP25 (metadata merge), D53 (graph is global, no scope in identity)
- Target file: `serve/knowledge/src/owlbear_knowledge/stores/graph.py`

## Implementation Notes

- Entity identity: `(canonicalize_name(name), entity_type)` — deterministic, global (not scoped)
- `canonicalize_name` from `protocols/common.py` — lowercase, strip whitespace, normalise unicode
- Upsert: INSERT OR UPDATE on identity key; metadata shallow-merged on update
- Edge identity: `(source_entity_id, target_entity_id, relation_type)` — upsert semantics
- AdjacencyQuery.direction uses TraversalDirection enum (OUTGOING/INCOMING/BOTH)
- find_entities must also search graph_aliases table (task #5 creates that table)

[[2026-05-25T19:42:56+02:00]]
## Research
- Research doc: .owlbear/research/1873-graphstore-entities-edges.md
- Sources: 8 studied, 5 high-relevance
- Recommendation: UUID5 deterministic IDs + Python-side shallow merge + explicit BEGIN IMMEDIATE transactions (confidence: .75)
- Follow-up tasks created: none needed (companion task #1874 already exists for evidence/aliases/traversal)
- Decision requests: none

## Challenge Results
- Challenger: reconsider (revised to proceed after incorporating feedback)
- Confidence in original: .75 (down from .85)
- Key challenges: AC/protocol mismatch on method names, transaction safety under asyncio.to_thread, alias DDL boundary drift
- Researcher response: accepted 3/5 — added explicit transactions, removed graph_aliases DDL from scope, clarified protocol-authoritative interpretation; rebutted 2/5 — greenfield tag means legacy cutover is separate, partial Protocol is intentional decomposition

[[2026-05-25T20:12:34+02:00]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Entity+edge CRUD for graph_* tables only |
| Interface clarity | PASS | After AC rewrite — all methods match protocol signatures with explicit input→output and error conditions |
| Dependency correctness | PASS | No deps; #1874 depends on this (correct ordering) |
| Module layering | PASS | stores/graph.py imports only protocols/common.py and protocols/graph.py types — no upward imports |
| TDD compliance | PASS | Greenfield; test-writer will create tests |
| KISS/YAGNI | PASS | Minimal CRUD subset; NotImplementedError for future methods (traverse, evidence, aliases) |
| Premise challenge | PASS | Protocol exists, legacy graph_store.py needs replacement, new stores/ pattern established |
| Pattern consistency | PASS | Matches ContentStore research pattern (deterministic IDs, connection injection, synchronous) |
| Security surface | PASS | No external input — takes typed Pydantic models at boundary; SQL parameterized |
| Single domain | PASS | Knowledge/Graph domain only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| upsert_entity with empty name | canonicalize_name returns empty | ValueError | Yes — AC requires raise | Caller gets clear error |
| upsert_edge with missing entity | FK target absent | ValueError | Yes — AC requires existence check before INSERT | Caller gets clear error |
| upsert_edge with SAME_AS | Invalid relation type | ValueError | Yes — AC requires raise | Caller directed to add_alias |
| find_entities with no aliases table | Table absent | N/A | Yes — graceful degradation per AC | Returns canonical matches only |

### Design Diverge
- Trigger: skipped — single clear approach from research (UUID5 + shallow merge + explicit transactions)

### Challenge Results
- Challenger: reconsider (confidence 0.38)
- Architect response: Accepted AC-quality and protocol-alignment challenges (rewrote all 8 AC lines). Accepted alias-split concern (reworded as conditional). Partially accepted concurrency (added synchronous contract AC). Rebutted process-threshold (research confidence ≠ architecture gate), partial-protocol (greenfield decomposition is correct), and UUID5 opacity (implementation detail, not AC-visible).

### Proof-Bundle Validation
- Planner assignment: null (not set)
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### AC Refinement Summary
Rewrote all AC lines to be protocol-exact:
- Replaced find_edges → get_adjacent (protocol method name)
- Removed metadata filter (EntityQuery has no metadata field)
- Removed get_edge (not in protocol)
- Added error conditions (ValueError for empty name, missing endpoints, SAME_AS)
- Added alias graceful-degradation wording
- Added synchronous/transaction contract line
- Each AC line now names concrete target with input→output pair

### Verdict: APPROVE
### Action Taken: Refined AC to protocol-exact wording, set proof_bundle=behavioral, advanced to todo

[[2026-05-25T20:33:32+02:00]]
## Test-Writer Notes

**Test file:** `tests/test_graph_store_1873.py`
**Class:** `TestFromAC_GraphStore`
**Total:** 40 tests, all FAIL (ModuleNotFoundError — `owlbear_knowledge.stores.graph` is greenfield)
**Lint:** clean

**AC Coverage:**
| AC | Tests | Categories |
|----|-------|------------|
| AC1 upsert_entity basics | 7 | happy ×3, error ×2, boundary ×1, edge ×1 |
| AC2 idempotency + metadata merge | 4 | happy ×2, edge ×2 |
| AC3 upsert_edge | 5 | happy ×1, error ×3, edge ×1 |
| AC4 get_entity | 3 | happy ×2, edge ×1 |
| AC5 find_entities | 8 | happy ×3, edge ×3, boundary ×1, graceful-degradation ×1 |
| AC6 get_adjacent | 6 | happy ×2, edge ×4 |
| AC7 Table DDL | 4 | happy ×3, boundary ×1 |
| AC8 Synchronous | 3 | happy ×3 |

**Expected failure type:** `ModuleNotFoundError: No module named 'owlbear_knowledge.stores'` — all tests fail at collection.

**Key test notes:**
- AC3 SAME_AS: uses `model_construct` to bypass Pydantic boundary (tests store-level guard)
- AC5 alias graceful degradation: default store fixture has no graph_aliases table (AC7 scope is graph_entities + graph_edges only)
- AC5 alias resolution: manually creates graph_aliases table + row to test inclusion path without depending on task #1874
- AC7 UNIQUE constraint: uses `PRAGMA index_list` — builder must ensure composite UNIQUE on (canonical_name, entity_type)

[[2026-05-25T20:51:59+02:00]]
## Builder Notes
- Implementation: Added synchronous `SqliteGraphStore` in `serve/knowledge/src/owlbear_knowledge/stores/graph.py` with `ensure_tables`, `upsert_entity`, `upsert_edge`, `get_entity`, `find_entities`, and `get_adjacent`; exported via `serve/knowledge/src/owlbear_knowledge/stores/__init__.py`.
- Approach: Implemented canonical identity with deterministic UUID5 IDs, CP25 shallow metadata merge on entity updates, explicit `BEGIN IMMEDIATE` transactions for upsert atomicity, alias-table-aware entity search with graceful degradation when `graph_aliases` is absent, and direction/relation filtering for adjacency queries.
- Out-of-scope protocol methods: Added explicit `NotImplementedError` stubs for traversal/evidence/alias/stats methods to preserve protocol surface without expanding this task scope.
- RED verification: `quality-runner` on `tests/test_graph_store_1873.py` failed at collection with `ModuleNotFoundError` before implementation (expected greenfield state).
- Tests: 40/40 passed (`tests/test_graph_store_1873.py`).
- Coverage: 95% for `owlbear_knowledge.stores.graph`.
- Lint: clean (`ruff` via quality-runner on source + task test paths).
- Module-level durable test check: No `test_graph_store.py` module-level durable test file exists in package-local or root test paths; skipped per workflow guidance.
- Commit: `5709b162` (`feat: implement SqliteGraphStore entities and edges (#1873, builder)`).

[[2026-05-25T21:23:09+02:00]]
## Review Evidence
- Verdict: FAIL
- Route: todo
- Builder evidence reviewed first and found internally consistent: task notes report 40/40 task tests passed, 95% coverage, and lint clean (.owlbear/kanban/tasks/1873-knowledge-graphstore-entities-edges.md:165, .owlbear/kanban/tasks/1873-knowledge-graphstore-entities-edges.md:166, .owlbear/kanban/tasks/1873-knowledge-graphstore-entities-edges.md:167). No independent rerun was needed to establish the blocking issue because the failure is proof sufficiency, not missing evidence.
- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC1 and AC2 (.owlbear/kanban/tasks/1873-knowledge-graphstore-entities-edges.md:15, .owlbear/kanban/tasks/1873-knowledge-graphstore-entities-edges.md:18) | The task suite proves same-type idempotency only; it never exercises the same canonical name under two different entity types, so an implementation that ignored entity_type in the identity key could still pass. | tests/test_graph_store_1873.py:154, tests/test_graph_store_1873.py:162 | todo |
| 2 | AC4 (.owlbear/kanban/tasks/1873-knowledge-graphstore-entities-edges.md:23) | The direct get_entity tests cover only the empty-alias case. The suite proves alias search in find_entities, but it does not prove that get_entity returns current non-empty alias_names when graph_aliases exists. | tests/test_graph_store_1873.py:254, tests/test_graph_store_1873.py:331, serve/knowledge/src/owlbear_knowledge/stores/graph.py:220, serve/knowledge/src/owlbear_knowledge/stores/graph.py:337 | todo |
| 3 | AC7 (.owlbear/kanban/tasks/1873-knowledge-graphstore-entities-edges.md:32) | DDL proof is too weak for the contract named in the AC. The tests check table existence, no-raise idempotence, and that graph_entities has some unique index, but they do not verify graph_edges composite uniqueness or foreign-key declarations. | tests/test_graph_store_1873.py:435, tests/test_graph_store_1873.py:446, tests/test_graph_store_1873.py:457, tests/test_graph_store_1873.py:463, serve/knowledge/src/owlbear_knowledge/stores/graph.py:43, serve/knowledge/src/owlbear_knowledge/stores/graph.py:52, serve/knowledge/src/owlbear_knowledge/stores/graph.py:58, serve/knowledge/src/owlbear_knowledge/stores/graph.py:69 | todo |
| 4 | AC8 (.owlbear/kanban/tasks/1873-knowledge-graphstore-entities-edges.md:37) | The task tests show the methods are synchronous, but they do not discriminate the explicit BEGIN IMMEDIATE contract. A weaker transaction implementation could still pass the current suite. | tests/test_graph_store_1873.py:481, tests/test_graph_store_1873.py:488, serve/knowledge/src/owlbear_knowledge/stores/graph.py:84, serve/knowledge/src/owlbear_knowledge/stores/graph.py:163 | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add a task-scoped test that inserts the same canonical name under two different entity types and proves distinct entity rows or IDs. | tests/test_graph_store_1873.py | AC1 and AC2; tests/test_graph_store_1873.py:154, tests/test_graph_store_1873.py:162 |
| 2 | test-writer | Add a get_entity alias hydration test that creates graph_aliases data and asserts alias_names are returned, not only searchable. | tests/test_graph_store_1873.py | AC4; tests/test_graph_store_1873.py:254, tests/test_graph_store_1873.py:331 |
| 3 | test-writer | Strengthen DDL tests to verify the specific graph_entities and graph_edges constraints named by the AC, including graph_edges composite uniqueness and foreign-key declarations. | tests/test_graph_store_1873.py | AC7; tests/test_graph_store_1873.py:435, tests/test_graph_store_1873.py:446, tests/test_graph_store_1873.py:463 |
| 4 | test-writer | Add a discriminating test for the explicit BEGIN IMMEDIATE contract in both upsert paths, or otherwise assert transaction mode strongly enough that a weaker transaction implementation fails. | tests/test_graph_store_1873.py | AC8; tests/test_graph_store_1873.py:481, tests/test_graph_store_1873.py:488 |

## Observations
- Direct code inspection maps the implementation to the contract: the store includes alias hydration in get_entity, the declared DDL includes the named uniqueness constraints, and both upsert paths use BEGIN IMMEDIATE (serve/knowledge/src/owlbear_knowledge/stores/graph.py:43, serve/knowledge/src/owlbear_knowledge/stores/graph.py:52, serve/knowledge/src/owlbear_knowledge/stores/graph.py:58, serve/knowledge/src/owlbear_knowledge/stores/graph.py:69, serve/knowledge/src/owlbear_knowledge/stores/graph.py:84, serve/knowledge/src/owlbear_knowledge/stores/graph.py:163, serve/knowledge/src/owlbear_knowledge/stores/graph.py:220, serve/knowledge/src/owlbear_knowledge/stores/graph.py:337).
- Non-blocking: AC7 and AC8 each bundle several verifiable requirements into one line, which makes downstream proof harder to judge mechanically under the AC quality rule.

[[2026-05-25T21:38:37+02:00]]
## Test-Writer Notes
- Retry: 6 new tests added for all 4 reviewer gaps. All pass against current impl.
- Builder skip: test-only retry — all 6 new tests green.

**Test file:** `tests/test_graph_store_1873.py`
**Class:** `TestFromAC_GraphStore`
**New tests (gap-fill):**
| Gap | Test | Category |
|-----|------|----------|
| AC1+AC2: entity_type part of identity key | `test_upsert_entity_same_name_different_type_yields_distinct_ids` | boundary |
| AC4: get_entity alias hydration | `test_get_entity_returns_alias_names_when_aliases_exist` | happy |
| AC7: graph_edges composite unique index | `test_graph_edges_has_unique_constraint_on_composite_key` | DDL |
| AC7: graph_edges FK declarations | `test_graph_edges_declares_foreign_keys_to_graph_entities` | DDL |
| AC8: upsert_entity uses BEGIN IMMEDIATE | `test_upsert_entity_executes_begin_immediate_transaction` | contract |
| AC8: upsert_edge uses BEGIN IMMEDIATE | `test_upsert_edge_executes_begin_immediate_transaction` | contract |

**Technique note:** AC8 tests use `sqlite3.Connection.set_trace_callback()` to record executed SQL; monkey-patching `db.execute` is not possible (read-only C attribute).
**Total suite:** 46 tests, 46 passed, lint clean.
**Commit:** `88328318`

[[2026-05-25T21:57:37+02:00]]
## Review Evidence
- Verdict: FAIL
- Route: backlog
- Builder evidence reviewed first and found internally consistent: original builder notes report 40/40 task tests passed, 95% coverage, and lint clean (.owlbear/kanban/tasks/1873-knowledge-graphstore-entities-edges.md:165, .owlbear/kanban/tasks/1873-knowledge-graphstore-entities-edges.md:166, .owlbear/kanban/tasks/1873-knowledge-graphstore-entities-edges.md:167). The retry notes report 6 new tests added and 46/46 passed, lint clean (.owlbear/kanban/tasks/1873-knowledge-graphstore-entities-edges.md:198, .owlbear/kanban/tasks/1873-knowledge-graphstore-entities-edges.md:214). No independent rerun was needed because the remaining blocker is proof sufficiency, not missing execution evidence.
- Behavioral challenger: reconsider. Accepted in part: the retry now sufficiently proves the prior AC1/AC2, AC4, and AC8 gaps, so the remaining blockers are narrowed to AC3 and AC7.
- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC3: `upsert_edge(EdgeInput) -> EdgeRecord` creates or updates edge | The suite proves duplicate identity reuse, but it never observes changed edge state on second upsert. An implementation that returns the same ID while ignoring updated weight, metadata, or updated_at could still pass. | tests/test_graph_store_1873.py:231, tests/test_graph_store_1873.py:240, serve/knowledge/src/owlbear_knowledge/stores/graph.py:201 | backlog |
| 2 | AC7: table DDL contract | The DDL assertions remain non-discriminating. The `graph_entities` and `graph_edges` unique tests assert only that some unique index exists, and the FK test checks only that at least one FK references `graph_entities`. Implementations missing the required composite columns or one of the two FK declarations could still pass. | tests/test_graph_store_1873.py:463, tests/test_graph_store_1873.py:470, tests/test_graph_store_1873.py:552, tests/test_graph_store_1873.py:562, tests/test_graph_store_1873.py:565, tests/test_graph_store_1873.py:575, tests/test_graph_store_1873.py:576, serve/knowledge/src/owlbear_knowledge/stores/graph.py:52, serve/knowledge/src/owlbear_knowledge/stores/graph.py:67, serve/knowledge/src/owlbear_knowledge/stores/graph.py:68, serve/knowledge/src/owlbear_knowledge/stores/graph.py:69 | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine AC3 or the next retry scope so the next test pass must observe the update half of `upsert_edge` on repeated identity, then re-dispatch to test-writer. | .owlbear/kanban/tasks/1873-knowledge-graphstore-entities-edges.md, tests/test_graph_store_1873.py | AC3; tests/test_graph_store_1873.py:231, tests/test_graph_store_1873.py:240, serve/knowledge/src/owlbear_knowledge/stores/graph.py:201 |
| 2 | architect | Split or sharpen AC7 into mechanically provable DDL checks that require exact unique-column assertions and both FK declarations before re-dispatch. | .owlbear/kanban/tasks/1873-knowledge-graphstore-entities-edges.md, tests/test_graph_store_1873.py | AC7; tests/test_graph_store_1873.py:463, tests/test_graph_store_1873.py:470, tests/test_graph_store_1873.py:552, tests/test_graph_store_1873.py:562, tests/test_graph_store_1873.py:565, tests/test_graph_store_1873.py:575, tests/test_graph_store_1873.py:576 |

## Observations
- The retry did close the prior AC1/AC2, AC4, and AC8 gaps with direct tests at tests/test_graph_store_1873.py:501, tests/test_graph_store_1873.py:516, tests/test_graph_store_1873.py:582, and tests/test_graph_store_1873.py:603.
- Direct code inspection still suggests the current implementation itself satisfies alias hydration, DDL declaration, and `BEGIN IMMEDIATE` requirements; the remaining issue is gate-quality proof, not a confirmed source defect.
- This is review cycle 2: a prior reviewer FAIL is already recorded in task history (.owlbear/kanban/tasks/1873-knowledge-graphstore-entities-edges.md:172, .owlbear/kanban/tasks/1873-knowledge-graphstore-entities-edges.md:173), with the subsequent test-only retry recorded at .owlbear/kanban/tasks/1873-knowledge-graphstore-entities-edges.md:197 and .owlbear/kanban/tasks/1873-knowledge-graphstore-entities-edges.md:198. Per pipeline protocol, repeated review failure routes to backlog.

[[2026-05-25T22:20:07+02:00]]
## Architecture Review (Re-review after reviewer rejection)

### Context
Re-review triggered by reviewer FAIL (cycle 2) routing task back to backlog. Two specific gaps identified by reviewer:
1. AC3: tests never observe changed edge state on second upsert
2. AC7: DDL assertions non-discriminating (don't verify exact constraint columns or both FKs)

### AC Refinements Applied
| AC | Change | Rationale |
|----|--------|----------|
| AC3 | Added "on update with same identity: weight and metadata are replaced from the new EdgeInput and updated_at advances beyond created_at" | Makes update half mechanically testable — test-writer must observe state change |
| AC7 | Split into AC7 (graph_entities) and AC8 (graph_edges); added "covers exactly" before column lists; named both FK targets individually; fixed `metadata` → `metadata_json` to match physical DDL | Each constraint is now separately verifiable with exact column assertions |
| AC7+AC8 | Column name corrected: `metadata` → `metadata_json` | Physical schema uses `metadata_json` for JSON serialization |

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Unchanged — entity+edge CRUD only |
| Interface clarity | PASS | AC3 update behavior now explicit; DDL split into discrete verifiable lines |
| Dependency correctness | PASS | No deps; #1874 depends on this |
| Module layering | PASS | stores/graph.py imports only protocols — confirmed in prior review |
| TDD compliance | PASS | 46 tests exist; gaps now addressable via refined AC |
| KISS/YAGNI | PASS | No change to scope |
| Premise challenge | PASS | Confirmed prior review |
| Pattern consistency | PASS | Matches ContentStore pattern |
| Security surface | PASS | Parameterized SQL, typed inputs |
| Single domain | PASS | Knowledge/Graph only |

### Challenge Results
- Challenger: block (confidence 0.27)
- Architect response: Accepted 1/5 (metadata_json column name mismatch — fixed). Rebutted 4/5: (1) deterministic ID is store-internal testability guarantee, not protocol-surface contract — no conflict with opaque-ID protocol rule; (2) AC3 "advances beyond" is mechanically testable via time-aware assertions; (3) DDL already split, execution-model line is cohesive; (4) process cycle count is immaterial to technical decision.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Refined AC3 update semantics, split AC7 into two lines with exact column names, corrected metadata_json, advanced to todo

[[2026-05-25T22:40:41+02:00]]
## Test-Writer Notes

**Test file:** `tests/test_graph_store_1873.py`
**Class:** `TestFromAC_GraphStore`
**Retry:** Round 2 — surgical gap-fill for reviewer FAIL #2
**Total suite:** 51 tests, 51 passed, lint clean
**Commit:** `72a5ba95`

**New tests (5, gap-fill for reviewer round 2):**
| Gap | Test | Category |
|-----|------|----------|
| AC3: upsert_edge update half (weight, metadata, updated_at) | `test_upsert_edge_update_replaces_weight_metadata_and_advances_updated_at` | behavioral |
| AC7: graph_entities exact unique columns | `test_graph_entities_unique_index_covers_exactly_canonical_name_and_entity_type` | DDL |
| AC8: graph_edges exact unique columns | `test_graph_edges_unique_index_covers_exactly_source_target_and_relation_type` | DDL |
| AC8: source_entity_id FK specific | `test_graph_edges_source_entity_id_fk_references_graph_entities` | DDL |
| AC8: target_entity_id FK specific | `test_graph_edges_target_entity_id_fk_references_graph_entities` | DDL |

**Technique notes:**
- AC3: uses `time.sleep(0.001)` to ensure clock advances between INSERT and UPDATE so `updated_at > created_at` is assertable
- AC7/AC8 unique: iterates all unique indexes via `PRAGMA index_list` + `PRAGMA index_info` and checks column set equality — handles implicit PK index (covers only `id`) being distinct from the constraint index
- AC8 FK: uses `PRAGMA foreign_key_list` with column-position indexing (fk[3]=from, fk[2]=referenced table) to assert both `source_entity_id` and `target_entity_id` FKs exist separately

**AC coverage (full suite):**
| AC | Tests |
|----|-------|
| AC1 upsert_entity basics | 7 |
| AC2 idempotency + metadata merge | 4 |
| AC3 upsert_edge + update semantics | 6 (+1 new) |
| AC4 get_entity | 4 |
| AC5 find_entities | 8 |
| AC6 get_adjacent | 6 |
| AC7 graph_entities DDL | 6 (+1 new) |
| AC8 graph_edges DDL | 6 (+2 new, +2 new FK) |
| AC9 synchronous | 3 |

[[2026-05-25T23:06:40+02:00]]
## Builder Notes
- Implementation: No source changes required in this builder cycle; existing implementation in serve/knowledge/src/owlbear_knowledge/stores/graph.py and serve/knowledge/src/owlbear_knowledge/stores/__init__.py satisfies current AC/test surface.
- Tests: 51/51 passed (`tests/test_graph_store_1873.py`).
- Coverage: 95% for `owlbear_knowledge.stores.graph`.
- ruff: clean.
- Approach: Per behavioral proof bundle, verified task-scoped tests + lint + coverage via quality-runner; no failing assertions remained after test-writer round-2 gap-fill.
- Module-level durable test check: No `test_graph_store.py` exists in package-local (`serve/**/tests/`) or root `tests/`; recorded as skip per workflow guidance.
- Evidence summary: quality-runner returned `failed: []`, `clean: true`, coverage module `owlbear_knowledge.stores.graph: 95%`.
- Fixes applied: none (verification-only builder pass).

[[2026-05-25T23:55:50+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1873 to docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first and internally consistent: task notes report 51/51 task tests passed, 95% coverage for owlbear_knowledge.stores.graph, ruff clean, and a quality-runner summary of failed: [] and clean: true (.owlbear/kanban/tasks/1873-knowledge-graphstore-entities-edges.md:325, .owlbear/kanban/tasks/1873-knowledge-graphstore-entities-edges.md:326, .owlbear/kanban/tasks/1873-knowledge-graphstore-entities-edges.md:327, .owlbear/kanban/tasks/1873-knowledge-graphstore-entities-edges.md:330).
- Behavioral challenger: reconsider. Reviewer response: accepted the warning against treating theoretical hardening gaps as blockers when the current AC, current code, and current proof set already align.
- Blocking findings: none.

| AC | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1-AC2 | serve/knowledge/src/owlbear_knowledge/stores/graph.py:77-115, serve/knowledge/src/owlbear_knowledge/stores/graph.py:323 | tests/test_graph_store_1873.py:104, tests/test_graph_store_1873.py:119, tests/test_graph_store_1873.py:130, tests/test_graph_store_1873.py:154, tests/test_graph_store_1873.py:170, tests/test_graph_store_1873.py:179, tests/test_graph_store_1873.py:501 | PASS |
| AC3 | serve/knowledge/src/owlbear_knowledge/stores/graph.py:143-202, serve/knowledge/src/owlbear_knowledge/stores/graph.py:327 | tests/test_graph_store_1873.py:190, tests/test_graph_store_1873.py:202, tests/test_graph_store_1873.py:209, tests/test_graph_store_1873.py:216, tests/test_graph_store_1873.py:231, tests/test_graph_store_1873.py:631 | PASS |
| AC4 | serve/knowledge/src/owlbear_knowledge/stores/graph.py:220, serve/knowledge/src/owlbear_knowledge/stores/graph.py:341 | tests/test_graph_store_1873.py:245, tests/test_graph_store_1873.py:254, tests/test_graph_store_1873.py:263, tests/test_graph_store_1873.py:516 | PASS |
| AC5 | serve/knowledge/src/owlbear_knowledge/stores/graph.py:232-255 | tests/test_graph_store_1873.py:273, tests/test_graph_store_1873.py:288, tests/test_graph_store_1873.py:297, tests/test_graph_store_1873.py:314, tests/test_graph_store_1873.py:321, tests/test_graph_store_1873.py:331 | PASS |
| AC6 | serve/knowledge/src/owlbear_knowledge/stores/graph.py:262-284 | tests/test_graph_store_1873.py:359, tests/test_graph_store_1873.py:370, tests/test_graph_store_1873.py:381, tests/test_graph_store_1873.py:395, tests/test_graph_store_1873.py:410, tests/test_graph_store_1873.py:422 | PASS |
| AC7 | serve/knowledge/src/owlbear_knowledge/stores/graph.py:39-52 | tests/test_graph_store_1873.py:435, tests/test_graph_store_1873.py:457, tests/test_graph_store_1873.py:676, tests/test_graph_store_1873.py:104, tests/test_graph_store_1873.py:154, tests/test_graph_store_1873.py:170 | PASS |
| AC8 | serve/knowledge/src/owlbear_knowledge/stores/graph.py:58-69 | tests/test_graph_store_1873.py:446, tests/test_graph_store_1873.py:704, tests/test_graph_store_1873.py:729, tests/test_graph_store_1873.py:743, tests/test_graph_store_1873.py:190, tests/test_graph_store_1873.py:231, tests/test_graph_store_1873.py:631 | PASS |
| AC9 | serve/knowledge/src/owlbear_knowledge/stores/graph.py:35, serve/knowledge/src/owlbear_knowledge/stores/graph.py:84, serve/knowledge/src/owlbear_knowledge/stores/graph.py:163 | tests/test_graph_store_1873.py:476, tests/test_graph_store_1873.py:481, tests/test_graph_store_1873.py:488, tests/test_graph_store_1873.py:582, tests/test_graph_store_1873.py:603 | PASS |

## Observations
- Non-blocking: AC1's deterministic stable ID wording is stronger than the protocol's explicit opaque-ID guarantee at serve/knowledge/src/owlbear_knowledge/protocols/graph.py:285-295. The current implementation satisfies the stronger wording via UUID5 identity helpers at serve/knowledge/src/owlbear_knowledge/stores/graph.py:323 and serve/knowledge/src/owlbear_knowledge/stores/graph.py:327, but future ACs should avoid coupling externally visible contract to internal ID strategy unless that is intentional.
- Non-blocking: the new graph_edges FK tests assert the declaring table and source/target columns, but do not separately assert the referenced target column id. Current source declares REFERENCES graph_entities(id) exactly at serve/knowledge/src/owlbear_knowledge/stores/graph.py:67-68, so this is hardening only, not a blocker.
- No independent quality-runner rerun was needed because the builder evidence was complete, internally consistent, and matched the reviewed source/test surface.

[[2026-05-26T00:34:39+02:00]]
## Docs Gate

### Item 1: README Verification
- Convention mapping: `serve/knowledge/src/**` → `serve/knowledge/README.md`
- Layer 1 grep: `SqliteGraphStore` absent from README (correct — not in public `__init__.py`); `GraphStore` reference in README maps to legacy `graph_store.py` (intact, unchanged).
- Layer 2 editorial: README accurately describes the public package surface. No contradictions introduced by this task — `SqliteGraphStore` is an internal `stores/` layer only; the public API is unchanged.
- Result: no docs update required.

### Item 2: External Attribution
- `.owlbear/sources/overview.md` contains "GraphStore — Entities & Edges (Task #1873)" section with 3 sources (SQLite UPSERT docs, LightRAG, Claude Cookbook KG guide).
- Result: N/A — attribution already recorded.

### Item 3: Research Doc
- `.owlbear/research/1873-graphstore-entities-edges.md` exists and is linked from task body Research section.
- Result: N/A — linkage present.

### Item 4: Deletion Detection
- Files added: `serve/knowledge/src/owlbear_knowledge/stores/graph.py`, `serve/knowledge/src/owlbear_knowledge/stores/__init__.py` (extended). No files deleted.
- Result: N/A — no orphaned references.

### Scratch Cleanup
- No `.owlbear/scratch/1873-*` files found.

### Verdict
DONE #1873 -> done | docs gate passed

[[2026-05-26T00:53:21+02:00]]
## Audit

### Regression Detection
quality-runner full report: 40 passed, 0 failed in knowledge domain scope. Lint violations (31 total) are all pre-existing in `protocols/` files not touched by this task — no regressions introduced by #1873.

### Intent Verification
Changed files: `stores/graph.py`, `stores/__init__.py`, `tests/test_graph_store_1873.py`. All within Knowledge/Graph domain. Implementation addresses stated purpose (entity+edge CRUD with canonical identity, upsert semantics, adjacency queries). No extraneous scope.

### Architect Quality
Score: 4/5. Final AC (9 lines) is protocol-exact with explicit input→output pairs and error conditions. Required 2 review cycles + re-architecture to reach this quality — initial AC was too vague for discriminating proof, but architect responded well to feedback and produced specific, verifiable criteria.

### Commit Integrity
Builder: `5709b162` (feat). Test-writer: `c97c0714`, `88328318`, `72a5ba95` (test). All committed with proper format and task ID reference. No uncommitted deliverables.

### Deduction Breakdown
- No deductions. Tests green, intent aligned, AC quality 4/5 (deduction threshold is ≤3), reviewer evidence detailed and present, commits clean.

### Confidence: 1.00
### Action: ARCHIVE
