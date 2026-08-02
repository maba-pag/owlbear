---
id: 1557
title: Repair manual enrichment graph persistence contract
status: archived
priority: medium
created: 2026-05-14T15:47:32.454745+00:00
updated: 2026-05-15T16:12:08.570040+00:00
tags:
  - scope:knowledge
  - type:build
  - bug
  - mcp
parent:
depends_on:
  - 1556
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Context:
OwlBear knowledge module audit found that manual VS Code-agent enrichment can report progress while persisting orphan graph rows. `get_next_batch` gives the agent chunk text and source display data, but not enough durable provenance for ordinary extracted entity dictionaries. `store_enrichment(chunk_id=...)` can then insert entities with NULL `document_id` and NULL `chunk_id` while marking the chunk enriched. Phase 2 has a parallel identity gap: `get_consolidation_candidates` does not expose entity row IDs, while `store_enrichment(candidate_id=..., edges=[...])` expects endpoint IDs and can insert edges with NULL endpoints.

Related task:
- Depends on #1556 because this task assumes chunks belong to source-linked documents with trustworthy document/source/scope identity.

Proof bundle: critical

Scope:
- In scope: manual enrichment API persistence contract for `get_next_batch`, `get_consolidation_candidates`, and `store_enrichment`; provenance stamping for Phase 1 entities and edges; Phase 2 candidate identity and review/edge persistence; rejection behavior for missing required persistence fields; idempotent retry behavior.
- Out of scope: MCP-side automatic LLM extraction, automatic enrichment workers, replacing the intentional VS Code-agent manual enrichment flow, and broad graph/search redesign beyond the persistence contract.

Complexity waiver:
This exceeds the usual planner budget because Phase 1 and Phase 2 share one failure mode: enrichment APIs accept caller-supplied graph payloads without durable persistence identity. Splitting the two phases would allow one path to keep creating orphan graph rows while the other is repaired.

Functional acceptance note:
Acceptance is based on API outputs and persisted row state. Passing or failing tests alone is not functional proof for this task.

Acceptance Criteria:
AC-1: Given `get_next_batch(ctx, limit=1)` selects a chunk from an enrich-enabled source-linked document, the returned batch item includes `chunk_id`, text, title/section display fields, and either `document_id`, `source_id`, and `scope` or a persistence token that lets `store_enrichment(ctx, chunk_id=...)` derive those three fields without caller-supplied entity provenance.
AC-2: Given `store_enrichment(ctx, chunk_id={chunk_id}, entities=[{"name":"ProbeEntity","type":"concept"}], edges=[{"relationship":"mentions","target_name":"ProbeTarget"}])` for a chunk whose document has `document_id="doc-a"` and `scope="team-a"`, persisted entity and edge rows from that call carry `document_id="doc-a"`, `chunk_id={chunk_id}`, and `scope="team-a"`; no row from that call has NULL in `document_id`, `chunk_id`, or `scope`.
AC-3: Given `store_enrichment(ctx, chunk_id={chunk_id}, entities=[{"name":"BrokenEntity"}])` cannot resolve the required document, chunk, source scope, or graph endpoint fields, the call returns an error result or raises a persistence error, inserts no graph row with NULL required provenance or endpoint fields, and leaves the chunk enrichment state as pending or failed rather than enriched.
AC-4: Given `get_consolidation_candidates(ctx, limit=1)` finds two mergeable entity rows named `ProbeEntity`, the returned candidate includes the two durable entity row identifiers needed by `store_enrichment(ctx, candidate_id=..., edges=[...])` or includes a reviewed-without-edge action that `store_enrichment` accepts and that makes that candidate absent from the next candidate batch.
AC-5: Given `store_enrichment(ctx, candidate_id={candidate_id}, edges=[{"relationship":"same_as"}])` receives a candidate returned by `get_consolidation_candidates`, the call either persists an edge whose `source_id` and `target_id` are non-NULL and match the candidate entity row identifiers, or rejects the payload without inserting a NULL-endpoint edge; repeating the same accepted or reviewed-without-edge payload does not create duplicate edges and does not make the reviewed candidate appear in the next candidate batch.
2026-05-15T01:12:28+00:00


Audit refinement — orphan chunks must not be enrichable:
`get_next_batch` currently uses a `LEFT JOIN` to `knowledge_sources` and `COALESCE(ks.enrich, 1) = 1`, which makes chunks from documents with missing/NULL source records eligible for enrichment. Because `store_enrichment` must derive durable `document_id`, `source_id`, and `scope`, orphan chunks should not be claimed for manual enrichment.

Required follow-up before review:
- `get_next_batch` must only return chunks whose document resolves to an existing enrich-enabled source, or must return a persistence token that proves equivalent source identity.
- Missing source rows/NULL source IDs should be excluded or surfaced as a repairable data-integrity issue; they must not be silently claimed and marked enriched.
- Add proof that an orphan chunk is not returned by `get_next_batch`, while an enrich-enabled source-linked chunk is returned.
2026-05-15T03:08:08+00:00


Audit refinement — enrichment edge payload schema must be explicit:
`store_enrichment(...)` currently reads `edge.get("relation")`, while audit/task examples and adjacent API language often use `relationship`, and the handbook does not define the exact accepted edge payload shape. This can let a semantically reasonable agent payload insert an edge with a NULL/missing relation or otherwise behave inconsistently.

Required follow-up before review:
- Define the accepted edge payload schema for Phase 1 and Phase 2 enrichment, including relation/relationship naming, endpoint fields, document/source/scope fields, and any name-to-ID resolution fields.
- `store_enrichment` must either normalize documented aliases or reject malformed edge payloads before inserting rows.
- Persisted edges from enrichment must not have NULL/empty `relation`, `source_id`, or `target_id` unless the chosen schema explicitly supports a reviewed-without-edge action that inserts no edge.
- Update the knowledge ops handbook and/or knowledge-enricher guidance so manual agents know the exact payload shape to send.
- Add proof that an unsupported edge payload is rejected without inserting a malformed edge, and that a documented payload stores the expected relation and endpoints.
2026-05-15T04:00:10+00:00


Audit refinement — enrichment claim ownership must be explicit:
`get_next_batch` marks chunks as `claimed`, but `store_enrichment(chunk_id=...)` currently accepts a chunk ID without proving the caller owns the current claim or that the chunk has not already been enriched by a newer pass. In the intended manual workflow this may be acceptable as a one-worker assumption, but the contract should say so.

Required follow-up before review:
- Explicitly document whether manual enrichment assumes a single active worker.
- At minimum, `store_enrichment` should reject missing chunks and define behavior for already-enriched chunks.
- If multiple enrichment agents are allowed, add a small claim token/lease ownership contract so stale claims cannot write after another worker has reclaimed the chunk.
- Proof should cover stale/already-enriched behavior according to the chosen contract, without overbuilding distributed-worker semantics unless they are actually desired.
2026-05-15T11:18:17+00:00
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One contract: enrichment API persistence identity. Complexity waiver justified — Phase 1 and Phase 2 share one failure mode (caller-supplied identity without validation). |
| Interface clarity | PASS (after refinement) | AC-2 edge chunk_id clarified (metadata, not column). AC-6 added for orphan chunk exclusion. Audit refinements provide builder guidance for payload schema normalization. |
| Dependency correctness | PASS | Depends on #1556 (archived/completed). Source identity contract proven across 36 tests. #1557 assumes trustworthy document/source/scope from ingestion — correct. |
| Module layering | PASS | All changes within serve/mcp-knowledge/ (server.py) and serve/knowledge/ (graph_store, schema). No upward imports. MCP server → knowledge package → stores. |
| TDD compliance | PASS | Proof bundle `critical` — test-writer will create full integration tests. |
| KISS/YAGNI | PASS | Minimal scope: fix persistence identity derivation, add validation/rejection, expose entity IDs for Phase 2. No new abstractions. |
| Premise challenge | PASS | Confirmed bugs: (1) get_next_batch returns no document_id/source_id/scope; (2) store_enrichment Phase 1 accepts caller-supplied provenance without validation, inserts NULLs silently; (3) no rejection for unresolvable fields; (4) get_consolidation_candidates exposes no entity row IDs; (5) store_enrichment Phase 2 cannot resolve endpoint IDs from candidate_id; (6) orphan chunks eligible via LEFT JOIN with COALESCE. |
| Pattern consistency | PASS | Follows existing knowledge module patterns: SQLite transactions, MCP tool wrappers, provenance stamping. Mirrors #1556 source identity fix. |
| Security surface | PASS | No new system boundaries. Input validation IS the fix — server-side provenance derivation prevents caller-supplied NULLs. |
| Single domain | PASS | All knowledge domain. |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| get_next_batch → LEFT JOIN ks | Orphan chunk returned (NULL source_id) | None (silent) | NO | NULL-provenance entities/edges from enrichment |
| store_enrichment Phase 1 → entity insert | NULL document_id/chunk_id/scope from caller | None (silent) | NO | Orphan entities in graph |
| store_enrichment Phase 1 → edge insert | NULL source_id/target_id/relation from caller | None (silent) | NO | Broken edge relationships |
| store_enrichment Phase 2 → edge insert | NULL endpoint IDs (candidate_id lacks entity row IDs) | None (silent) | NO | NULL-endpoint edges in graph |
| store_enrichment → chunk not found | Missing chunk_id accepted | None (marks nonexistent chunk enriched) | NO | Ghost enrichment state |

AC-1 through AC-6 prescribe fixes for all identified failure modes.

### AC Refinements

**AC-2 — Edge chunk_id precision:**
The `edges` table schema at `schema.py:64-75` has `document_id` and `scope` columns but NO `chunk_id` column. The `entities` table has `chunk_id` as a column. The #1556 precedent (`tests/test_knowledge_ingest_source_identity_1556.py:1065-1080`) stores edge chunk provenance in metadata, not as a row column.

Refined AC-2: Given `store_enrichment(ctx, chunk_id={chunk_id}, entities=[{"name":"ProbeEntity","type":"concept"}], edges=[{"relationship":"mentions","target_name":"ProbeTarget"}])` for a chunk whose document has `document_id="doc-a"` and `scope="team-a"`, persisted entity rows carry `document_id="doc-a"`, `chunk_id={chunk_id}`, and `scope="team-a"` as column values; persisted edge rows carry `document_id="doc-a"` and `scope="team-a"` as column values, with `chunk_id` in edge metadata; no entity row from that call has NULL in `document_id`, `chunk_id`, or `scope`; no edge row from that call has NULL in `document_id`, `scope`, `source_id`, `target_id`, or `relation`.

**New AC-6 — Orphan chunk exclusion:**
AC-6: Given the database contains a chunk from a document with NULL `source_id` and a chunk from a document linked to an enrich-enabled source, `get_next_batch(ctx, limit=10)` returns only the source-linked chunk and omits the orphan chunk.

### Challenge Results
- Challenger: `block` (confidence 0.33)
- Architect response: **PARTIALLY ACCEPTED** — Two corrections incorporated, remainder rebutted:
  1. "AC-2 edge chunk_id schema mismatch" — ACCEPTED. Edges table has no chunk_id column. AC-2 refined: entity chunk_id as column, edge chunk_id as metadata. Edge NULL constraints now explicit (document_id, scope, source_id, target_id, relation).
  2. "Orphan chunk coverage gap" — ACCEPTED. Added AC-6 for orphan chunk exclusion from get_next_batch.
  3. "Payload contract ambiguity" — ACKNOWLEDGED, not blocking. AC-2's example shows caller INPUT format; the audit refinement (already in body) requires the builder to define normalization. The AC's ASSERTION side correctly names persisted field names. Test-writer tests persisted state.
  4. "AC-3 scope split" — REJECTED. AC-3 bundles related failure modes sharing one recovery path (rejection + no partial data). Test-writer writes separate tests per mode under one AC. "Or" disjunctions provide design flexibility, not ambiguity.
  5. "AC-1/AC-4 design independence" — REJECTED. Disjunctions provide architecture flexibility. Test-writer tests whichever design the builder implements. AC constrains the contract (provenance must be derivable), not the mechanism.
  6. "Phase 1 retry coverage" — ACKNOWLEDGED. Phase 1 retry is an implicit consequence of server-side identity derivation (deterministic entity/edge IDs from chunk+name combination). Not carrying as separate AC.
  7. "AC-5 Phase 2 edge scope/document_id" — ACKNOWLEDGED. Cross-source consolidation edges reasonably have NULL document_id (graph-level, not document-level). AC-5's endpoint non-NULL requirement is sufficient.
  8. "Complexity waiver incomplete" — REJECTED. Waiver is about keeping Phase 1+2 together, which remains justified. Broader scope (orphan gating, schema normalization) follows from the persistence contract fix.

### Proof-Bundle Validation
- Planner assignment: `critical`
- Final bundle: `critical`
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: REFINE → APPROVE
### Action Taken: AC-2 refined (edge chunk_id as metadata, not column; edge NULL-field constraints explicit). AC-6 added (orphan chunk exclusion). Advancing to `todo`.
2026-05-15T11:18:25+00:00
Architecture review complete. Two AC refinements: (1) AC-2 corrected — edges table has no chunk_id column; refined to specify entity chunk_id as column, edge chunk_id in metadata, plus explicit edge NULL constraints (document_id, scope, source_id, target_id, relation); (2) AC-6 added — orphan chunk exclusion from get_next_batch (documents with NULL source_id must not be returned). Challenger partially accepted (block @ 0.33): edge schema mismatch and orphan coverage gap incorporated; payload alias ambiguity, AC-3 scope split, design-independence disjunctions, and complexity waiver all rebutted with evidence. Six confirmed bugs map to six AC lines. Proof bundle: critical. Advanced to todo.
2026-05-15T11:32:26+00:00
## Test-Writer Notes

**Test file:** `tests/test_enrichment_persistence_1557.py`
**Commit:** `6c6aa33a`

### Test classes

| Class | AC | Tests | Category breakdown |
|---|---|---|---|
| `TestFromAC_GetNextBatchProvenance` | AC-1 | 3 | happy/contract (missing fields) |
| `TestFromAC_StoreEnrichmentPhase1Provenance` | AC-2 | 9 | contract (server-side provenance derivation) |
| `TestFromAC_StoreEnrichmentRejection` | AC-3 | 4 | error + boundary (ghost chunk, orphan chunk, null endpoints) |
| `TestFromAC_ConsolidationCandidateIdentifiers` | AC-4 | 3 | contract (entity row IDs in candidate) |
| `TestFromAC_StoreEnrichmentPhase2Edges` | AC-5 | 5 | contract + boundary (endpoint derivation, idempotency, batch exclusion) |
| `TestFromAC_OrphanChunkExclusion` | AC-6 | 3 | happy + edge (orphan exclusion from get_next_batch) |

**Total: 27 tests — all FAIL (verified via quality-runner)**
**Lint: clean (ruff exit 0)**

### AC coverage

| AC | Tests | Failure reason |
|---|---|---|
| AC-1 | 3 | `document_id`, `source_id`, `scope` absent from `get_next_batch` return dict |
| AC-2 | 9 | `store_enrichment` uses `entity.get("document_id")` etc. (caller-supplied, not server-derived); `edge.get("relation")` ignores `"relationship"` alias; no chunk_id in edge metadata |
| AC-3 | 4 | No rejection for ghost/orphan chunks; NULL-endpoint edges inserted silently |
| AC-4 | 3 | `ConsolidationCandidate` lacks `entity_id_a`/`entity_id_b` fields |
| AC-5 | 5 | Phase 2 uses caller-supplied `source_id`/`target_id` (NULL); `INSERT OR IGNORE` fails idempotency with NULLs; NULL-endpoint edges not excluded from next batch |
| AC-6 | 3 | `LEFT JOIN + COALESCE(ks.enrich, 1) = 1` makes orphan chunks (NULL source_id) eligible |
2026-05-15T11:47:52+00:00
builder crashed once; releasing claim before retry: network error (ERR_NETWORK_CHANGED)
2026-05-15T12:05:36+00:00
## Builder Notes

### Files Changed
- serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py
- share/skills/h-knowledge-ops/SKILL.md

### Fixes Applied
- Enforced source-linked chunk eligibility in `get_next_batch` by requiring an existing `knowledge_sources` join (`ks.enrich = 1`) so orphan chunks are excluded.
- Expanded `get_next_batch` return contract to include durable provenance fields: `document_id`, `source_id`, and `scope`.
- Extended consolidation candidate payloads to include durable endpoint identifiers: `entity_id_a` and `entity_id_b`.
- Added phase-1 server-side provenance stamping in `store_enrichment(chunk_id=...)`:
  - entity rows now stamp `document_id`, `chunk_id`, `scope` from chunk/document provenance.
  - edge rows now stamp `document_id`, `scope` from provenance and include `chunk_id` in edge metadata.
- Added explicit edge payload normalization/validation:
  - accept `relation` or `relationship` alias.
  - reject unresolved endpoints before inserting malformed rows.
- Added phase-1 rejection handling for invalid/unresolvable chunks:
  - missing/orphan chunk rejects with `ToolError`.
  - already enriched chunk rejects.
  - no ghost/orphan chunk persistence side effects.
- Added phase-2 endpoint derivation/idempotency improvements:
  - candidate endpoint IDs resolved from persisted candidate identity.
  - deterministic fallback edge IDs for candidate-derived edges to support idempotent retries.
  - reviewed pair marking persists for accepted phase-2 outcomes to keep processed candidates out of subsequent batches.

### Test Results
- Scoped RED verification (before implementation):
  - `tests/test_enrichment_persistence_1557.py` -> 0 passed / 20 failed (expected RED); lint clean.
- Scoped GREEN verification (post-fix):
  - `tests/test_enrichment_persistence_1557.py`
  - `tests/test_mcp_knowledge_phase2_tools.py`
  - `serve/mcp-knowledge/tests/test_server.py`
  - Result: **85 passed, 0 failed, 0 skipped**.
- Lint (scoped):
  - `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`
  - `tests/test_enrichment_persistence_1557.py`
  - `tests/test_mcp_knowledge_phase2_tools.py`
  - `serve/mcp-knowledge/tests/test_server.py`
  - Result: **clean (ruff exit 0)**.
- Coverage evidence:
  - `coverage_modules=["owlbear_mcp_knowledge.server"]` in scoped run reported module coverage around **60%**.

### Additional Evidence / Regression Context
- Broader mcp-knowledge proof attempt (`serve/mcp-knowledge/tests` + task/durable files) surfaced pre-existing unrelated failures in list-sources/get-stats suites; reran scoped changed-surface proof to isolate task impact and confirmed green on impacted contract paths.

### Commit
- `16bfa775` — `fix: enforce enrichment persistence provenance contract (#1557, builder)`
2026-05-15T12:27:33+00:00
## Review Evidence
- Verdict: FAIL
- Routing signal: FAIL #1557 -> in-progress | Phase 2 still permits wrong endpoint identity, candidate review identity remains lossy, and the claimed-chunk failure path does not satisfy AC-3.
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-5 | `store_enrichment(candidate_id=...)` still trusts caller-supplied `source_id` / `target_id` when present instead of validating them against the reviewed candidate. That can persist an unrelated edge and still consume the candidate as reviewed. | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:524,534-535,565`; task proof only covers omitted-endpoint payloads at `tests/test_enrichment_persistence_1557.py:611,633,657,660`; adjacent proof still asserts caller-supplied endpoints verbatim at `tests/test_mcp_knowledge_phase2_tools.py:557-558,1077-1085`. | in-progress |
| 2 | AC-4 / AC-5 | Phase 2 identity is still lossy. Candidate rows are produced at row-pair granularity (`entity_id_a` / `entity_id_b`), but `candidate_id` omits those IDs, `store_enrichment` re-resolves the first matching pair, and `reviewed_pairs` also collapses identity to `entity_name + source_a + source_b`. Duplicate same-name pairs for one source pair can therefore be persisted or dismissed against the wrong pair. | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:171,286,307,309-310,322,350,565`; `serve/knowledge/src/owlbear_knowledge/schema.py:173-177`. | in-progress |
| 3 | AC-3 | A claimed chunk that fails Phase 1 validation is never moved back to `pending` or `failed`. `get_next_batch` marks chunks `claimed`, but Phase 1 only clears the claim on the success path; failures just roll back, leaving an already-claimed chunk claimed. | Claim path: `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:782-783`; success-only state transition: `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:649`; failure rollback: `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:842-852`; rejection branches: `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:467,486,489`. | in-progress |
| 4 | AC-3 / AC-5 proof | The green proof packet would still false-green the defects above. There is no regression proving rejection of mismatched explicit Phase 2 endpoints, and no task-local proof for the already-enriched rejection branch or claimed-chunk post-failure state. | Task-local Phase 2 tests only use `edges=[{"relationship": "same_as"}]` at `tests/test_enrichment_persistence_1557.py:611,633,657,681,684,707`; AC-3 rejection block is `tests/test_enrichment_persistence_1557.py:431-515` and does not cover `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:489` or claimed-state recovery after failure. | in-progress |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Validate or overwrite Phase 2 edge endpoints so persisted `source_id` / `target_id` must match the reviewed candidate entity IDs; reject mismatched explicit endpoints before insert. | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`, `tests/test_enrichment_persistence_1557.py`, `tests/test_mcp_knowledge_phase2_tools.py` | AC-5; `server.py:524,534-535,565`; proof gap in `tests/test_enrichment_persistence_1557.py:611,633,657,660` |
| 2 | builder | Make candidate review identity durable at row-pair granularity so `candidate_id`, persistence, and `reviewed_pairs` all identify the same entity pair. | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`, `serve/knowledge/src/owlbear_knowledge/schema.py`, `tests/test_enrichment_persistence_1557.py`, `tests/test_mcp_knowledge_phase2_tools.py` | AC-4 / AC-5; `server.py:171,286,307,309-310,322,350,565`; `schema.py:173-177` |
| 3 | builder | On rejected Phase 1 writes from claimed chunks, move the chunk back to `pending` or `failed` instead of leaving it `claimed`, and add regression proof for that state transition plus the already-enriched rejection branch. | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`, `tests/test_enrichment_persistence_1557.py` | AC-3; `server.py:467,486,489,649,782-783,842-852`; current rejection coverage is only `tests/test_enrichment_persistence_1557.py:431-515` |
| 4 | builder | Rebuild the proof packet after the code fix with regression cases for mismatched explicit Phase 2 endpoints and the corrected claimed-chunk failure state; include a complete critical-bundle evidence summary in builder notes. | `tests/test_enrichment_persistence_1557.py`, `tests/test_mcp_knowledge_phase2_tools.py`, task body evidence | Independent quality-runner rerun was scoped only: 85 passed, 0 failed, 0 skipped; lint clean; coverage for `owlbear_mcp_knowledge.server` 60% |

## Observations
- AC-1, AC-2, and AC-6 appear implemented on the changed surface: `get_next_batch` now returns `document_id`, `source_id`, and `scope` while excluding orphan chunks via an inner join on sources in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:735-807`; Phase 1 stamping and the documented edge payload schema are present in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:473-649` and `share/skills/h-knowledge-ops/SKILL.md:66-125`.
- Independent verification on the supplied proof surface was green but scoped: quality-runner reported 85 passed, 0 failed, 0 skipped; lint clean; coverage for `owlbear_mcp_knowledge.server` at 60%. That is useful regression evidence, but it does not erase the contract defects above.
2026-05-15T12:38:58+00:00
## Builder Notes
- Implementation:
  - `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`
  - `serve/knowledge/src/owlbear_knowledge/schema.py`
- Fixes applied:
  - Phase-2 candidate IDs now carry durable pair identity (`entity_id_a`/`entity_id_b`) while remaining backward-compatible for legacy 3-part IDs.
  - `store_enrichment(candidate_id=...)` now resolves candidate identity durably and validates edge endpoints against the reviewed candidate pair; mismatched explicit endpoints are rejected.
  - `reviewed_pairs` filtering now supports row-pair identity (`entity_id_a`/`entity_id_b`) with legacy fallback rows (`entity_id_* = ''`) still honored.
  - Phase-2 review persistence now stores reviewed rows with pair identity columns.
  - Phase-1 failure recovery now clears stale claims (`claimed -> failed`, `claimed_at=NULL`) so rejected writes do not leave chunks stuck claimed.
  - Schema init now guarantees `reviewed_pairs.entity_id_a/entity_id_b` columns and rebuilds `reviewed_pairs` PK shape to include pair IDs on upgraded databases without changing schema version contract.
- RED verification:
  - `tests/test_enrichment_persistence_1557.py` currently returns all pass (no failing `TestFromAC_*` baseline remained at retry entry).
- Verification (quality-runner, scoped):
  - Tests: `tests/test_enrichment_persistence_1557.py`, `serve/mcp-knowledge/tests/test_server.py`, `tests/test_enrichment_schema.py`
  - Result: 65 passed, 0 failed, 0 skipped
  - Lint: clean
  - Coverage (scoped modules): `owlbear_mcp_knowledge.server` 56%, `owlbear_knowledge.schema` 64%
- Additional evidence:
  - A broader exploratory run including `tests/test_mcp_knowledge_phase2_tools.py` surfaced one legacy expectation conflict (`test_phase2_multiple_edges_writes_all_edges`) that assumes Phase-2 may persist edges outside the selected candidate pair; this now correctly rejects under the hardened contract.
- Commit:
  - `b962d372` — `fix: harden enrichment phase2 identity and claim recovery (#1557, builder)`
2026-05-15T12:59:12+00:00
## Review Evidence
- Verdict: FAIL
- Routing signal: FAIL #1557 -> in-progress | critical-bundle proof remains contradictory and AC-3 rejection-path proof is incomplete.
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | Critical bundle / AC-5 / AC-6 proof | Builder advanced with scoped proof only, while adjacent durable suites still fail against the hardened contract. Independent quality-runner rerun on `tests/test_mcp_knowledge_enrichment_tools.py`, `tests/test_mcp_knowledge_phase2_tools.py`, and `tests/test_enrichment_persistence_1557.py` produced `101 passed, 2 failed`: `test_source_name_is_none_for_document_without_knowledge_source` still expects sourceless chunks to be returned, conflicting with AC-6 and the orphan-excluding source join at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:887-891`; `test_phase2_multiple_edges_writes_all_edges` still expects one candidate review to persist edges outside the reviewed pair, conflicting with endpoint validation at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:444-476`. The task record also shows only scoped builder verification plus an admitted broader conflict at `.owlbear/kanban/tasks/1557-repair-manual-enrichment-graph-persistence-contract.md:254-264`. | quality-runner scoped adjacent rerun; `tests/test_mcp_knowledge_enrichment_tools.py:365`; `tests/test_mcp_knowledge_phase2_tools.py:1500-1546`; `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:444-476,887-891`; `.owlbear/kanban/tasks/1557-repair-manual-enrichment-graph-persistence-contract.md:254-264` | in-progress |
| 2 | AC-3 proof | The retry did not rebuild AC-3 proof for the new rejection branches. Task-local tests at `tests/test_enrichment_persistence_1557.py:431-515` only prove ghost/orphan non-success and no NULL endpoints; they do not assert the `chunk is already enriched` guard at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:599-607`, the claimed->failed recovery / `claimed_at=NULL` path at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:624-635,970-986`, or a truly unresolvable Phase 1 endpoint error path because `target_name="NonExistentTarget"` resolves via placeholder-entity creation at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:507-585` instead of hitting the reject branch. | `tests/test_enrichment_persistence_1557.py:431-515`; `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:507-607,624-635,970-986` | in-progress |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Reconcile the critical-bundle proof surface with the hardened contract: update or replace adjacent durable tests that still assert orphan-chunk inclusion or cross-pair Phase 2 edge writes, then rerun the broader knowledge proof surface and report that evidence in builder notes. | `tests/test_mcp_knowledge_enrichment_tools.py`, `tests/test_mcp_knowledge_phase2_tools.py`, `.owlbear/kanban/tasks/1557-repair-manual-enrichment-graph-persistence-contract.md` | quality-runner rerun: `101 passed, 2 failed`; stale expectations at `tests/test_mcp_knowledge_enrichment_tools.py:365` and `tests/test_mcp_knowledge_phase2_tools.py:1500-1546` |
| 2 | builder | Add regression proof for the AC-3 branches introduced by the retry: already-enriched chunk rejection, claimed->failed recovery with `claimed_at` cleared, and a truly unresolvable Phase 1 edge payload that reaches the reject path instead of placeholder-entity creation. | `tests/test_enrichment_persistence_1557.py`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` | missing proof against `server.py:599-607,624-635,970-986`; false-green path in `tests/test_enrichment_persistence_1557.py:494-515` vs `server.py:507-585` |
| 3 | builder | Rebuild the builder evidence packet for the `critical` bundle with the broadened test surface, scoped lint, and current coverage numbers after the durable-suite alignment above. | `.owlbear/kanban/tasks/1557-repair-manual-enrichment-graph-persistence-contract.md`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`, `serve/knowledge/src/owlbear_knowledge/schema.py` | builder note currently lists only scoped verification at `.owlbear/kanban/tasks/1557-repair-manual-enrichment-graph-persistence-contract.md:254-264` |

## Observations
- Current code looks materially aligned with the prior reviewer follow-ups. Direct code inspection and code-reader analysis found no remaining blocking implementation defect on the main AC-1/AC-2/AC-4/AC-5/AC-6 surfaces: batch provenance fields are returned, Phase 2 candidate IDs carry durable pair identity, explicit Phase 2 endpoints are validated against the reviewed pair, reviewed_pairs stores pair IDs, and failed Phase 1 writes clear stale claims.
- Independent quality-runner full-repo verification was noisy with unrelated legacy failures, so the gating evidence here uses the narrower adjacent-suite rerun rather than repo-wide counts.
- Lint remained clean on the reviewed surface.
2026-05-15T13:02:46+00:00
## Builder Notes
- Implementation changes: none in this retry.
- Decision: reject to test-writer because current failing durable tests assert interfaces that contradict approved AC behavior.
- Proof run (quality-runner, scoped):
  - test_paths:
    - `tests/test_enrichment_persistence_1557.py`
    - `tests/test_mcp_knowledge_enrichment_tools.py`
    - `tests/test_mcp_knowledge_phase2_tools.py`
  - result: 101 passed, 2 failed, 0 skipped
  - lint: clean
  - coverage (scoped): `owlbear_mcp_knowledge.server` 54%, `owlbear_knowledge.schema` 51%

### Interface Mismatch Summary
1. `tests/test_mcp_knowledge_enrichment_tools.py::TestFromAC_GetNextBatch::test_source_name_is_none_for_document_without_knowledge_source` expects sourceless documents to remain eligible via LEFT JOIN behavior. This conflicts with AC-6 (orphan chunk exclusion from `get_next_batch`).
2. `tests/test_mcp_knowledge_phase2_tools.py::TestFromAC_StoreEnrichmentPhase2_1330::test_phase2_multiple_edges_writes_all_edges` expects Phase-2 to persist edges whose endpoints are outside the reviewed candidate pair. This conflicts with AC-5 hardening that endpoints must match candidate entity row identifiers.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Update durable enrichment-tool test expectations to align with AC-6 orphan exclusion contract (sourceless chunks must not be returned by `get_next_batch`). | `tests/test_mcp_knowledge_enrichment_tools.py` | quality-runner failure: `TestFromAC_GetNextBatch::test_source_name_is_none_for_document_without_knowledge_source` |
| 2 | test-writer | Update Phase-2 durable test expectations so one candidate review cannot persist edges for unrelated endpoint pairs; explicit or implicit endpoints must resolve to reviewed candidate IDs. | `tests/test_mcp_knowledge_phase2_tools.py` | quality-runner failure: `TestFromAC_StoreEnrichmentPhase2_1330::test_phase2_multiple_edges_writes_all_edges`; error `edge endpoints must match candidate entity row identifiers` |
| 3 | test-writer | Add explicit AC-3 proof cases for (a) already-enriched chunk rejection, and (b) claimed-chunk failure recovery (`state` becomes `failed` and `claimed_at` clears) on rejected Phase-1 writes. | `tests/test_enrichment_persistence_1557.py` | reviewer-required missing branches from prior cycle; task-local AC-3 block currently does not assert these guards |

2026-05-15T13:24:32+00:00
## Test-Writer Notes

**Retry cycle — direct-to-review advance (Step 1b.1).**

**Commit:** `bf0000e2`

### Changes made

| File | Change | Reason |
|------|--------|--------|
| `tests/test_mcp_knowledge_enrichment_tools.py` | Rewrote `test_source_name_is_none_for_document_without_knowledge_source` | Stale LEFT JOIN expectation conflicts with AC-6; updated to assert orphan chunk is NOT returned |
| `tests/test_mcp_knowledge_phase2_tools.py` | Rewrote `test_phase2_multiple_edges_writes_all_edges` | Cross-pair endpoints now rejected by AC-5 hardening; updated to use 2 valid same-pair edges and assert 2 rows written |
| `tests/test_enrichment_persistence_1557.py` | Added `test_already_enriched_chunk_raises_tool_error` | AC-3 proof: already-enriched chunk must raise, no entity rows inserted, state remains 'enriched' |
| `tests/test_enrichment_persistence_1557.py` | Added `test_claimed_chunk_state_becomes_failed_on_rejected_phase1_write` | AC-3 proof: claimed chunk whose provenance fails must become 'failed' with claimed_at=NULL |

### Verification

- All 105 tests in the scoped surface PASS (105 passed, 0 failed, 0 skipped)
- Lint: clean (ruff exit 0)
- All new tests PASS against current implementation → builder has no code changes to make

### AC-3 coverage table (updated)

| AC-3 branch | Test |
|-------------|------|
| Ghost chunk (nonexistent) | existing: `test_ghost_chunk_does_not_succeed_silently` |
| Ghost chunk no entity insert | existing: `test_ghost_chunk_inserts_no_entity` |
| Orphan chunk not marked enriched | existing: `test_orphan_chunk_not_marked_enriched` |
| NULL-endpoint edge not inserted | existing: `test_unresolvable_edge_not_inserted_with_null_endpoints` |
| Already-enriched chunk rejected | **NEW**: `test_already_enriched_chunk_raises_tool_error` |
| Claimed chunk → failed + claimed_at cleared | **NEW**: `test_claimed_chunk_state_becomes_failed_on_rejected_phase1_write` |
2026-05-15T13:37:25+00:00
## Review Evidence
- Verdict: FAIL
- Routing signal: FAIL #1557 -> backlog | repeated review cycle and critical-bundle proof is still insufficient for AC-3 and AC-5 reject/dismissal branches.
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-3 | The task-local "unresolvable edge" proof still does not exercise the reject branch for unresolved Phase 1 endpoints. The payload in `test_unresolvable_edge_not_inserted_with_null_endpoints` is actually resolvable because the first extracted entity becomes the default source endpoint and `target_name` creates a placeholder entity, so the test proves a successful write with non-NULL endpoints, not rejection on unresolvable endpoints. | `tests/test_enrichment_persistence_1557.py:494`; `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:507`; `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:575`; `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:585`; `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:711`; `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:752` | backlog |
| 2 | AC-5 | The green packet still does not prove the actual Phase 2 reject branch for mismatched explicit endpoints. The implementation rejects valid `candidate_id` payloads whose explicit `source_id` / `target_id` do not match the reviewed candidate pair, but current negatives only cover malformed `candidate_id` and current positives cover only valid same-pair endpoints. | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:444`; `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:462`; `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:468`; `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:473`; `tests/test_mcp_knowledge_phase2_tools.py:1471`; `tests/test_mcp_knowledge_phase2_tools.py:1483`; `tests/test_mcp_knowledge_phase2_tools.py:1494`; `tests/test_mcp_knowledge_phase2_tools.py:1529`; `tests/test_enrichment_persistence_1557.py:694`; `tests/test_enrichment_persistence_1557.py:716`; `tests/test_enrichment_persistence_1557.py:740`; `tests/test_enrichment_persistence_1557.py:764`; `tests/test_enrichment_persistence_1557.py:790` | backlog |
| 3 | AC-5 | The reviewed-without-edge path is still under-proved for the new row-pair identity contract. There is no end-to-end proof that `store_enrichment(candidate_id=..., edges=[])` both persists the durable pair identity now stored in `reviewed_pairs` and makes that reviewed candidate disappear from the next batch. Existing dismissal tests stop at row counts or only read `entity_name/source_a/source_b`, while exclusion tests use manually inserted `reviewed_pairs` rows instead of rows written by `store_enrichment`. | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:291`; `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:299`; `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:306`; `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:310`; `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:692`; `serve/knowledge/src/owlbear_knowledge/schema.py:173`; `tests/test_mcp_knowledge_phase2_tools.py:342`; `tests/test_mcp_knowledge_phase2_tools.py:573`; `tests/test_mcp_knowledge_phase2_tools.py:1102`; `tests/test_mcp_knowledge_phase2_tools.py:1157`; `tests/test_mcp_knowledge_phase2_tools.py:1268`; `tests/test_mcp_knowledge_phase2_tools.py:1277`; `tests/test_mcp_knowledge_phase2_tools.py:1543` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine AC-3 proof obligations so the retry explicitly requires a truly unresolved Phase 1 endpoint payload that reaches the reject branch and proves no side effects beyond the allowed chunk-state recovery. | `tests/test_enrichment_persistence_1557.py`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` | Finding 1; `tests/test_enrichment_persistence_1557.py:494`; `server.py:585` |
| 2 | architect | Refine AC-5 proof obligations so the retry explicitly requires a valid-candidate negative test for mismatched explicit Phase 2 endpoints and a direct proof that `edges=[]` written by `store_enrichment` removes the reviewed candidate from the next batch. | `tests/test_enrichment_persistence_1557.py`, `tests/test_mcp_knowledge_phase2_tools.py`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` | Findings 2-3; `server.py:444`; `tests/test_mcp_knowledge_phase2_tools.py:573`; `tests/test_mcp_knowledge_phase2_tools.py:1543` |
| 3 | architect | Tighten the Phase 2 durability contract so the proof packet must read back `reviewed_pairs.entity_id_a` and `entity_id_b` written by `store_enrichment(edges=[])`, not only the legacy three-field prefix of `candidate_id`. | `tests/test_mcp_knowledge_phase2_tools.py`, `serve/knowledge/src/owlbear_knowledge/schema.py`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` | Finding 3; `tests/test_mcp_knowledge_phase2_tools.py:1268`; `tests/test_mcp_knowledge_phase2_tools.py:1277`; `schema.py:173`; `server.py:692` |

## Observations
- Direct code inspection plus the adversarial pass found no new blocking implementation defect on the main AC-1 / AC-2 / AC-4 / AC-6 paths. The blocker is evidence quality: this is a critical-bundle task and the remaining gaps are still in the exact reject/dismissal branches that distinguish a hardened persistence contract from a false green.
- The newly added AC-3 tests for already-enriched rejection and claimed->failed recovery are useful and appear aligned with the implementation at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:604-635`, but they do not close the unresolved-endpoint proof gap above.
- Because this is now a repeated review cycle on the same task, the routing target is `backlog` as the loop-breaker rather than another direct test-only retry.
2026-05-15T13:47:05+00:00
## Architecture Review (Refinement Cycle)

### Context
Reviewer routed to backlog after third review cycle. Implementation is materially correct on AC-1, AC-2, AC-4, AC-6. Three proof-obligation gaps remain in AC-3 and AC-5 reject/dismissal branches. No AC text changes needed — the existing AC lines are correct; the test suite does not cover the specified branches.

### Proof Obligation Refinements

**PO-1 (AC-3) — Truly unresolvable Phase 1 edge endpoints:**
Current `test_unresolvable_edge_not_inserted_with_null_endpoints` is a false-negative test: the payload `entities=[{"name": "SomeEntity"}], edges=[{"relationship": "mentions", "target_name": "NonExistentTarget"}]` resolves successfully via `_resolve_or_create_chunk_entity` (placeholder creation for target_name) and `default_source_id` (first extracted entity). It proves successful resolution, not rejection.

Test-writer must add or replace with: `store_enrichment(chunk_id=..., entities=[], edges=[{"relationship": "mentions"}])` — no entities means `default_source_id=None`, no `source_name`/`target_name`/`source_id`/`target_id` in the edge — both resolution sides fail → `ToolError("unable to resolve edge endpoints from provided payload")` at `server.py:_resolve_phase1_edge_endpoints`. Assert: ToolError raised, zero edges inserted, chunk state not marked enriched.

**PO-2 (AC-5) — Mismatched explicit Phase 2 endpoints (all three reject branches):**
`_resolve_phase2_edge_endpoints` has three reject paths: (a) both explicit and mismatched `{source_id, target_id} != {entity_id_a, entity_id_b}`, (b) one-sided mismatch with target explicit/invalid and source omitted, (c) one-sided mismatch with source explicit/invalid and target omitted. None are exercised by current tests.

Test-writer must cover all three reject branches using a valid candidate returned by `get_consolidation_candidates`:
- Two-sided: `edges=[{"relationship": "same_as", "source_id": "wrong", "target_id": "also-wrong"}]` → ToolError, zero edges.
- One-sided (target invalid): `edges=[{"relationship": "same_as", "target_id": "wrong"}]` → ToolError, zero edges.
- One-sided (source invalid): `edges=[{"relationship": "same_as", "source_id": "wrong"}]` → ToolError, zero edges.

**PO-3 (AC-5) — Reviewed-without-edge end-to-end durability:**
Existing `test_accepted_candidate_absent_from_next_batch` covers `edges=[{"relationship": "same_as"}]` (with an edge), but no test covers `edges=[]` (reviewed-without-edge action).

Test-writer must add: `store_enrichment(candidate_id=..., edges=[])` followed by:
(a) `get_consolidation_candidates()` no longer returns that candidate (candidate absent from next batch).
(b) `reviewed_pairs` row has non-empty `entity_id_a` and `entity_id_b` matching the candidate pair's entity row IDs (read back via SQL query on `reviewed_pairs` table).

### Challenge Results
- Challenger: `reconsider` (confidence 0.61)
- Architect response: **PARTIALLY ACCEPTED.**
  1. "One-sided Phase 2 reject branches" — ACCEPTED. Expanded PO-2 to require all three reject paths (two-sided + both one-sided directions).
  2. "AC wording quality on shortened summaries" — REJECTED. The challenger prompt used shortened AC summaries for brevity; the authoritative AC text is in the task body and is independently verifiable per h-ac-quality. No AC text changes needed.
  3. "Schema migration proof for reviewed_pairs columns" — ACKNOWLEDGED, not blocking. Schema migration is outside this task's AC scope (persistence contract, not schema versioning). The builder's schema rebuild logic is already in code; proving it is a separate concern.
  4. "Stale three-part candidate_id in durable tests" — ACKNOWLEDGED, not blocking. Builder notes confirm backward compatibility with legacy 3-part IDs. Existing durable tests that pass with the new code already prove backward compat implicitly.

### Proof-Bundle Validation
- Finalized bundle: `critical` (unchanged)
- Test-writer: PROCEED with PO-1, PO-2, PO-3 additions

### Verdict: REFINE → APPROVE
Three proof obligations added for AC-3 and AC-5 reject/dismissal branches. No AC text changes. Implementation is sound. Advancing to todo.
2026-05-15T13:47:11+00:00
Architecture review refinement cycle complete. Three proof obligations added for AC-3 and AC-5 reject/dismissal branches: PO-1 (truly unresolvable Phase 1 edge endpoints), PO-2 (all three Phase 2 mismatched-endpoint reject branches), PO-3 (reviewed-without-edge end-to-end durability with reviewed_pairs pair identity readback). No AC text changes. Challenger partially accepted (expanded PO-2 to cover one-sided rejects). Proof bundle: critical. Advanced to todo.
2026-05-15T13:52:41+00:00
## Test-Writer Notes

**Retry cycle — direct-to-review advance (Step 1b.1).**

**Commit:** `98bcdf21`

### Changes made

| File | Change | Reason |
|------|--------|--------|
| `tests/test_enrichment_persistence_1557.py` | Added `from mcp.server.fastmcp.exceptions import ToolError` import | Needed for `pytest.raises(ToolError)` in new tests |
| `tests/test_enrichment_persistence_1557.py` | Added `test_truly_unresolvable_edge_raises_tool_error` in `TestFromAC_StoreEnrichmentRejection` | PO-1 (AC-3): `entities=[], edges=[{"relationship":"mentions"}]` → no default_source_id, no source/target fields → `_resolve_phase1_edge_endpoints` raises ToolError; asserts zero edges inserted and chunk not marked 'enriched' |
| `tests/test_enrichment_persistence_1557.py` | Added `test_phase2_two_sided_mismatched_endpoints_rejected` in `TestFromAC_StoreEnrichmentPhase2Edges` | PO-2 (AC-5): both `source_id="wrong-id"` and `target_id="also-wrong-id"` explicit → ToolError, zero edges |
| `tests/test_enrichment_persistence_1557.py` | Added `test_phase2_one_sided_invalid_target_rejected` in `TestFromAC_StoreEnrichmentPhase2Edges` | PO-2 (AC-5): only `target_id="wrong-id"` explicit → ToolError, zero edges |
| `tests/test_enrichment_persistence_1557.py` | Added `test_phase2_one_sided_invalid_source_rejected` in `TestFromAC_StoreEnrichmentPhase2Edges` | PO-2 (AC-5): only `source_id="wrong-id"` explicit → ToolError, zero edges |
| `tests/test_enrichment_persistence_1557.py` | Added `test_reviewed_without_edge_excludes_candidate_and_persists_pair_identity` in `TestFromAC_StoreEnrichmentPhase2Edges` | PO-3 (AC-5): `store_enrichment(candidate_id=..., edges=[])` → candidate absent from next batch; `reviewed_pairs` row has non-empty `entity_id_a`/`entity_id_b` matching candidate entity PKs |

### Verification

- All 34 tests in the scoped surface PASS (34 passed, 0 failed, 0 skipped)
- All 5 new tests PASS against current implementation → builder has no code changes to make
- Lint: clean (ruff exit 0)

### AC-3 proof obligation coverage (updated)

| PO-1 branch | Test |
|-------------|------|
| Truly unresolvable Phase 1 edge (no entities, no source/target fields) | NEW: `test_truly_unresolvable_edge_raises_tool_error` |

### AC-5 proof obligation coverage (updated)

| PO branch | Test |
|-----------|------|
| PO-2: Two-sided mismatched explicit endpoints | NEW: `test_phase2_two_sided_mismatched_endpoints_rejected` |
| PO-2: One-sided invalid target_id | NEW: `test_phase2_one_sided_invalid_target_rejected` |
| PO-2: One-sided invalid source_id | NEW: `test_phase2_one_sided_invalid_source_rejected` |
| PO-3: reviewed-without-edge → batch exclusion + reviewed_pairs pair identity | NEW: `test_reviewed_without_edge_excludes_candidate_and_persists_pair_identity` |
2026-05-15T14:11:44+00:00
## Review Evidence
- Verdict: FAIL
- Routing signal: FAIL #1557 -> backlog | repeated review cycle: the critical-bundle packet is green but still leaves a Phase 1 direct-ID contract gap and an unproved reviewed_pairs upgrade path.
- Independent verification: quality-runner rerun on `tests/test_enrichment_persistence_1557.py`, `tests/test_mcp_knowledge_enrichment_tools.py`, `tests/test_mcp_knowledge_phase2_tools.py`, `serve/mcp-knowledge/tests/test_server.py`, and `tests/test_enrichment_schema.py` reported **148 passed, 0 failed, 0 skipped**; lint clean; coverage: `owlbear_mcp_knowledge.server` 62%, `owlbear_knowledge.schema` 64%.
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-3 | Phase 1 endpoint handling is still not reviewable as safe under the written contract. `_resolve_phase1_edge_endpoints` treats any provided `source_id` / `target_id` string as already resolved and only errors when an endpoint remains `None`; `_persist_phase1_enrichment` then inserts those endpoint values and marks the chunk enriched. Because `init_db()` keeps SQLite foreign-key enforcement off, arbitrary explicit IDs are not DB-rejected on this path. The handbook also says unresolved endpoints must raise and insert no malformed edge row, while the current green packet proves only omitted-endpoint rejection and valid direct-ID happy paths. That leaves an unresolved contract/proof gap on whether explicit Phase 1 IDs must resolve to persisted entity rows or are accepted verbatim. | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:559-585,777`; `serve/knowledge/src/owlbear_knowledge/schema.py:364`; `share/skills/h-knowledge-ops/SKILL.md:118-121`; `tests/test_enrichment_persistence_1557.py:605,842,871,899,927`; `tests/test_mcp_knowledge_enrichment_tools.py:716,741` | backlog |
| 2 | Critical bundle / AC-4 / AC-5 proof | The schema upgrade path added for durable reviewed-pair identity is still unproved. `init_db()` now adds `entity_id_a` / `entity_id_b` and rebuilds `reviewed_pairs` when the primary-key shape is legacy, but the durable schema suite only proves table existence, a legacy three-column insert, and v10->v11 table creation. There is no proof that an existing `reviewed_pairs` table is rebuilt to the five-column PK with legacy rows preserved. | `serve/knowledge/src/owlbear_knowledge/schema.py:381-415`; `tests/test_enrichment_schema.py:192,211,525` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Clarify the Phase 1 edge contract for explicit `source_id` / `target_id`: either require them to resolve to persisted entity rows and add a negative proof case for bogus explicit IDs, or explicitly document that verbatim IDs are accepted and remove the unresolved-endpoint ambiguity from the task/handbook. | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`, `share/skills/h-knowledge-ops/SKILL.md`, `tests/test_enrichment_persistence_1557.py`, `tests/test_mcp_knowledge_enrichment_tools.py` | Finding 1; `server.py:559-585,777`; `SKILL.md:118-121` |
| 2 | architect | Add an explicit upgrade-path proof obligation for `reviewed_pairs`: verify that the repair path adds `entity_id_a` / `entity_id_b`, rebuilds the PK shape, and preserves existing rows on upgraded databases. | `serve/knowledge/src/owlbear_knowledge/schema.py`, `tests/test_enrichment_schema.py` | Finding 2; `schema.py:381-415`; `tests/test_enrichment_schema.py:192,211,525` |

## Observations
- Direct inspection plus code-reader analysis did not uncover a fresh blocking defect on the main AC-1 / AC-2 / AC-4 / AC-5 / AC-6 happy paths. The late-cycle task-local negatives for truly missing Phase 1 endpoints and Phase 2 mismatched endpoints are materially better than the prior packets.
- Challenger confidence on the original implementation-defect framing was low (0.47): the risk is real, but the stronger current conclusion is contract/proof ambiguity rather than a clean builder-owned regression. That is why the loop-breaker route here is `backlog`, not another direct builder retry.
- Because this is a repeated review cycle on the same task, the pipeline loop-breaker applies even though the scoped verification rerun was green.
2026-05-15T14:22:02+00:00
## Architecture Review (Refinement Cycle 2)

### Context
Reviewer routed to backlog after fourth review cycle. Implementation materially correct on all 6 AC lines (148 passed, 0 failed across knowledge suite). Two recorded concerns remain: (1) Phase 1 explicit source_id/target_id accepted verbatim without DB validation, FK enforcement OFF; (2) reviewed_pairs schema upgrade path unproved.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Unchanged from prior review. |
| Interface clarity | REFINE | AC-3 "resolve" wording ambiguous for explicit IDs; AC-2 has conflicting versions. |
| Dependency correctness | PASS | #1556 archived/completed. |
| Module layering | PASS | No upward imports. |
| TDD compliance | PASS | Critical bundle. |
| KISS/YAGNI | PASS | PO-4 is small (one SELECT check + one test). PO-5 is one test. |
| Pattern consistency | PASS | Phase 2 already validates explicit endpoints; Phase 1 should match. |
| Security surface | REFINE | Explicit Phase 1 IDs bypass validation with FK OFF → dangling edge references. |

### AC Refinements

**AC-2 — Authoritative version (supersedes original AC-2 text):**
Given `store_enrichment(ctx, chunk_id={chunk_id}, entities=[{"name":"ProbeEntity","type":"concept"}], edges=[{"relationship":"mentions","target_name":"ProbeTarget"}])` for a chunk whose document has `document_id="doc-a"` and `scope="team-a"`, persisted entity rows carry `document_id="doc-a"`, `chunk_id={chunk_id}`, and `scope="team-a"` as column values; persisted edge rows carry `document_id="doc-a"` and `scope="team-a"` as column values, with `chunk_id` in edge metadata; no entity row from that call has NULL in `document_id`, `chunk_id`, or `scope`; no edge row from that call has NULL in `document_id`, `scope`, `source_id`, `target_id`, or `relation`.

**AC-3 — "Resolve" clarification:**
AC-3 "cannot resolve the required... graph endpoint fields" means: (a) for name-based endpoints (`source_name`/`target_name`): the lookup-or-create path fails; (b) for explicit ID endpoints (`source_id`/`target_id`): the provided ID does not match a persisted entity row. An explicit ID that does not correspond to an existing entity in the database is "unresolvable" and must trigger the rejection path. This applies regardless of FK enforcement state.

### New Proof Obligations

**PO-4 (AC-3) — Phase 1 bogus explicit endpoint ID rejection:**
`_resolve_phase1_edge_endpoints` currently accepts any non-NULL string as resolved without DB lookup (`server.py:559-561`). With FK enforcement OFF (`schema.py:364`), bogus IDs persist as dangling edge references. Downstream `inter_doc_graph_builder` assumes edge endpoints map to real entities.

Test-writer must add: `store_enrichment(chunk_id=..., entities=[{"name":"RealEntity","type":"concept"}], edges=[{"relationship":"mentions","source_id":"nonexistent-entity-id","target_name":"RealEntity"}])` where `"nonexistent-entity-id"` does not match any persisted entity. Assert: ToolError raised, zero edges inserted from that call, chunk state not marked enriched. Builder must add a SELECT check in `_resolve_phase1_edge_endpoints` for explicit IDs.

**PO-5 (AC-4/AC-5) — reviewed_pairs schema upgrade path:**
`init_db()` adds `entity_id_a`/`entity_id_b` columns and rebuilds PK shape from 3-col to 5-col (`schema.py:381-427`). This mutates existing tables on startup and is part of the shipped change. No existing test covers the upgrade from a legacy 3-column table with data.

Test-writer must add in `tests/test_enrichment_schema.py`: Starting from a database with the old 3-column PK `reviewed_pairs` table containing rows `(entity_name="E", source_a="S1", source_b="S2")`, calling `init_db(conn)` produces a table with the 5-column PK `(entity_name, source_a, source_b, entity_id_a, entity_id_b)` and the legacy row is preserved with `entity_id_a=""` and `entity_id_b=""`.

### Challenge Results
- Challenger: `block` (confidence 0.38)
- Architect response: **PARTIALLY ACCEPTED** — Two proof obligations added, AC clarifications made:
  1. "AC-3 contract ambiguity on explicit IDs" — ACCEPTED. AC-3 "resolve" now explicitly includes DB existence check for explicit IDs. PO-4 added.
  2. "Upgrade-path proof" — ACCEPTED. init_db mutates existing tables; one upgrade test is warranted. PO-5 added.
  3. "AC-2 conflicting versions" — ACCEPTED. Authoritative AC-2 version declared (edge chunk_id in metadata, not column).
  4. "AC-4/AC-5 or-branches" — ACKNOWLEDGED, not blocking. Design flexibility disjunctions have been successfully consumed by test-writer through 4 cycles. The or-branches are working as intended.
  5. "AC-1 either/or branch" — ACKNOWLEDGED, not blocking. Same rationale as AC-4/AC-5.

### Proof-Bundle Validation
- Finalized bundle: `critical` (unchanged)
- Test-writer: PROCEED with PO-4 and PO-5

### Verdict: REFINE → APPROVE
AC-3 clarified (explicit IDs must resolve to persisted entities). AC-2 authoritative version declared. PO-4 (bogus Phase 1 explicit ID rejection) and PO-5 (reviewed_pairs upgrade proof) added. Advancing to todo.
2026-05-15T14:22:09+00:00
Architecture review refinement cycle 2 complete. AC-3 clarified: "resolve" for explicit Phase 1 IDs means DB existence check, not just non-NULL string. AC-2 authoritative version declared (edge chunk_id in metadata). Two new proof obligations: PO-4 (bogus Phase 1 explicit endpoint ID → ToolError, zero edges) and PO-5 (reviewed_pairs 3-col→5-col PK upgrade with data preserved). Challenger partially accepted (block @ 0.38): explicit-ID gap and upgrade-path gap incorporated; AC or-branch concerns acknowledged but not blocking. Proof bundle: critical. Advanced to todo.
2026-05-15T14:28:37+00:00
## Test-Writer Notes

**Retry cycle — advancing to in-progress (PO-4 requires builder fix).**

**Commit:** `814e0b7f`

### Changes made

| File | Change | Reason |
|------|--------|--------|
| `tests/test_enrichment_persistence_1557.py` | Added `test_bogus_explicit_phase1_source_id_raises_tool_error` in `TestFromAC_StoreEnrichmentRejection` | PO-4 (AC-3): explicit `source_id="nonexistent-entity-id"` provided in edge payload → expected ToolError; current `_resolve_phase1_edge_endpoints` accepts any non-None string verbatim without DB lookup → test FAILS |
| `tests/test_enrichment_schema.py` | Added `TestFromAC_ReviewedPairsUpgradePath` class with 4 tests | PO-5 (AC-4/AC-5): proves that `init_db()` on a DB with legacy 3-col PK `reviewed_pairs` table rebuilds to 5-col PK and preserves legacy rows with `entity_id_a=""` and `entity_id_b=""` |

### Verification (quality-runner, scoped)

- test_paths: `tests/test_enrichment_persistence_1557.py`, `tests/test_enrichment_schema.py`
- Result: **66 passed, 1 failed, 0 skipped**
- Failing: `TestFromAC_StoreEnrichmentRejection::test_bogus_explicit_phase1_source_id_raises_tool_error` — DID NOT RAISE ToolError (builder fix required)
- PO-5 (4 × `TestFromAC_ReviewedPairsUpgradePath`): all PASS — proves existing upgrade-path behavior
- Lint: clean (ruff exit 0)

### AC proof obligation coverage (this retry)

| PO | Branch | Test | Status |
|----|--------|------|--------|
| PO-4 (AC-3) | Bogus explicit Phase 1 source_id → ToolError, zero edges, chunk not enriched | NEW: `test_bogus_explicit_phase1_source_id_raises_tool_error` | FAIL ✓ (builder fix needed) |
| PO-5 (AC-4/5) | `init_db` upgrades legacy 3-col reviewed_pairs to 5-col PK | NEW: `TestFromAC_ReviewedPairsUpgradePath` (4 tests) | PASS (proof of existing behavior) |

### Builder Required Follow-up

PO-4 requires: add SELECT check in `_resolve_phase1_edge_endpoints` at `server.py:559` to validate explicit `source_id`/`target_id` strings against persisted entity rows; reject with ToolError when ID not found.
2026-05-15T14:33:41+00:00
## Builder Notes

### Files Changed
- serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py

### Fixes Applied
- Added explicit Phase-1 endpoint ID validation in `_resolve_phase1_edge_endpoints`.
- For caller-supplied `source_id`/`target_id`, the function now performs a DB existence check against `entities.id`.
- If an explicit endpoint ID does not resolve to a persisted entity row, `store_enrichment` now raises `ToolError("unable to resolve edge endpoints from provided payload")` before edge insert.
- Existing name-based resolution and default-source fallback behavior remain unchanged.

### RED Verification (pre-fix)
- quality-runner scoped run:
  - tests/test_enrichment_persistence_1557.py
  - tests/test_enrichment_schema.py
- Result: 66 passed, 1 failed, 0 skipped
- Failing test: `tests/test_enrichment_persistence_1557.py::TestFromAC_StoreEnrichmentRejection::test_bogus_explicit_phase1_source_id_raises_tool_error`
- Lint: clean

### GREEN Verification (post-fix)
- quality-runner scoped critical-surface run:
  - tests/test_enrichment_persistence_1557.py
  - tests/test_mcp_knowledge_enrichment_tools.py
  - tests/test_mcp_knowledge_phase2_tools.py
  - serve/mcp-knowledge/tests/test_server.py
  - tests/test_enrichment_schema.py
- Result: 153 passed, 0 failed, 0 skipped
- Lint: clean
- Coverage:
  - owlbear_mcp_knowledge.server: 62%
  - owlbear_knowledge.schema: 67%

### Commit
- 5d76847d — fix: validate phase1 explicit edge endpoint IDs (#1557, builder)

### Evidence Summary
- PO-4 blocker is resolved by enforcing explicit endpoint resolvability to persisted entity rows.
- Critical bundle adjacent suites are green on this retry with no regressions on Phase-2 or schema-upgrade surfaces.
2026-05-15T15:02:53+00:00
## Review Evidence
- Verdict: FAIL
- Routing signal: FAIL #1557 -> backlog | repeated review cycle: Phase 1 explicit-ID validation remains scope-blind, so the current green packet still permits cross-scope edge injection and false-greens it.
- Independent verification: quality-runner rerun on `tests/test_enrichment_persistence_1557.py`, `tests/test_mcp_knowledge_enrichment_tools.py`, `tests/test_mcp_knowledge_phase2_tools.py`, `serve/mcp-knowledge/tests/test_server.py`, and `tests/test_enrichment_schema.py` reported **153 passed, 0 failed, 0 skipped**; lint clean; coverage: `owlbear_mcp_knowledge.server` **62%**, `owlbear_knowledge.schema` **67%**.
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-1 / AC-2 / AC-3 / Safety | `_resolve_phase1_edge_endpoints` accepts any caller-supplied `source_id` / `target_id` that exists anywhere in `entities`; it does not bind explicit endpoints to the claimed chunk's provenance boundary. `_persist_phase1_enrichment` then stamps the edge with the current chunk's `document_id` and `scope`. Because graph consumers scope-filter edges but fetch peer entities by raw ID, a scoped Phase 1 write can create a `team-a` edge pointing at a foreign-scope entity and surface that foreign entity through scoped traversal/query paths. This leaves the root provenance-hardening problem partially open. | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:550-597,712-789`; `serve/knowledge/src/owlbear_knowledge/graph_store.py:107-114,233-257,311-353`; `serve/knowledge/src/owlbear_knowledge/query_service.py:121-133` | backlog |
| 2 | AC-3 proof | The green packet would still false-green the defect above. The only Phase 1 explicit-ID negative covers a nonexistent `source_id`; there is no proof that an existing but foreign-scope / foreign-document endpoint is rejected with zero edge writes and no enrichment success. | `tests/test_enrichment_persistence_1557.py:644-691`; independent quality-runner rerun: `153 passed, 0 failed, 0 skipped` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine the Phase 1 explicit-endpoint contract so caller-supplied `source_id` / `target_id` must resolve within the claimed chunk's allowed provenance boundary (at minimum the chunk scope, and document/source if that is the intended contract), not merely to any existing entity row. | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`, `serve/knowledge/src/owlbear_knowledge/graph_store.py`, `serve/knowledge/src/owlbear_knowledge/query_service.py`, `share/skills/h-knowledge-ops/SKILL.md` | Finding 1; `server.py:550-597,712-789`; `graph_store.py:107-114,233-257,311-353`; `query_service.py:121-133` |
| 2 | architect | Add an explicit proof obligation for an existing-but-foreign Phase 1 endpoint ID and require rejection with zero inserted edges and no enrichment success. | `tests/test_enrichment_persistence_1557.py`, `tests/test_mcp_knowledge_enrichment_tools.py` | Finding 2; `tests/test_enrichment_persistence_1557.py:644-691` |

## Observations
- Prior blockers around orphan-chunk exclusion, Phase 2 candidate identity, reviewed-without-edge durability, and reviewed_pairs upgrade proof appear closed in the current workspace: `get_next_batch` now returns provenance fields and excludes orphan chunks (`serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:875-943` with proof at `tests/test_enrichment_persistence_1557.py:1044-1094` and `tests/test_mcp_knowledge_enrichment_tools.py:365-382`); Phase 2 candidate identity and reject/dismissal paths are validated in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:172-206,392-476,652-709`, `tests/test_enrichment_persistence_1557.py:899-1018`, and `tests/test_mcp_knowledge_phase2_tools.py:573,1102,1246,1500,1543`; schema upgrade proof is present in `serve/knowledge/src/owlbear_knowledge/schema.py:381-427` and `tests/test_enrichment_schema.py:615-657`.
- The remaining blocker is narrower than the earlier stale FAIL packets: it is a live scope-integrity gap in Phase 1 explicit-ID acceptance, not the previously closed Phase 2 or migration issues.
2026-05-15T15:14:47+00:00
## Architecture Review (Refinement Cycle 3)

### Context
Reviewer routed to backlog after fifth review cycle. All 6 AC lines materially implemented (153 passed, 0 failed across knowledge suite). One remaining gap: Phase 1 explicit `source_id`/`target_id` accepted without scope binding — existence check is global (`WHERE id = ?`), not scope-bound.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Unchanged. |
| Interface clarity | REFINE | AC-3 "resolve" boundary for explicit IDs must be explicitly scope-bound. |
| Dependency correctness | PASS | #1556 archived. |
| Module layering | PASS | No upward imports. |
| TDD compliance | PASS | Critical bundle, PO-6 adds one failing + one positive test. |
| KISS/YAGNI | PASS | One SQL condition change + two tests. Proportionate. |
| Pattern consistency | PASS | Name-based resolution is already scope-bound (line ~518-522). Phase 2 is pair-bound. Phase 1 explicit IDs should be scope-bound for consistency. |
| Security surface | REFINE | Cross-scope explicit IDs bypass scope trust boundary; downstream traversal surfaces foreign-scope entities through scoped edges. |

### AC Refinement

**AC-3 — Scope-binding contract for explicit Phase 1 endpoint IDs:**
AC-3 "cannot resolve the required... graph endpoint fields" now explicitly includes: for explicit `source_id`/`target_id` in Phase 1 edge payloads, "resolve" means the ID must correspond to an existing entity row within the claimed chunk's scope (`entities.scope = provenance.scope`). Cross-document and cross-chunk references within the same scope are allowed — this is how inter-document graph building works. Cross-scope explicit IDs are unresolvable and must trigger the rejection path.

**Rationale for scope as the boundary (not document-local or chunk-local):**
- `scope` is the trust/visibility boundary throughout the knowledge module: `list_edges`, `list_entities`, `get_neighbors`, and `query_service` all scope-filter.
- Cross-document within-scope references are the purpose of explicit IDs — agents reference entities from prior enrichment of other chunks/documents in the same scope to build the inter-document graph.
- Cross-scope is the prohibited case: a `team-a` edge pointing at a `team-b` entity would leak through scoped traversal because `get_neighbors` scope-filters edges but fetches peer entities by raw ID.
- Name-based resolution (`_resolve_or_create_chunk_entity`) is chunk-local because it creates/finds entities; explicit ID resolution references existing entities and should use the broader scope boundary.

### New Proof Obligation

**PO-6 (AC-3) — Foreign-scope explicit Phase 1 endpoint ID rejection:**
`_entity_id_exists` at `server.py:564-566` checks `WHERE id = ?` globally. With FK enforcement OFF and scope as the trust boundary, a caller-supplied explicit ID from a foreign scope passes validation and creates a cross-scope edge.

Builder must: change `_entity_id_exists` (or equivalent check) to `WHERE id = ? AND scope = ?` using `provenance.scope`.

Test-writer must add two tests:
1. **Negative (foreign-scope):** Create entity E1 in scope `team-b`. Call `store_enrichment(chunk_id=..., entities=[{"name":"LocalEntity","type":"concept"}], edges=[{"relationship":"mentions","source_id":"{E1.id}","target_name":"LocalEntity"}])` where the chunk belongs to scope `team-a`. Assert: ToolError raised, zero edges inserted, chunk not marked enriched.
2. **Positive (same-scope cross-document):** Create entity E2 in scope `team-a` from a different document. Call `store_enrichment(chunk_id=..., entities=[{"name":"LocalEntity","type":"concept"}], edges=[{"relationship":"mentions","source_id":"{E2.id}","target_name":"LocalEntity"}])` where the chunk also belongs to scope `team-a`. Assert: edge persisted with non-NULL endpoints, source_id matches E2.id.

### Challenge Results
- Challenger: `block` (confidence 0.36)
- Architect response: **PARTIALLY ACCEPTED.**
  1. "Contract-scope mismatch" — ACCEPTED. Explicit scope-as-boundary contract now defined with evidence from codebase scope-filtering patterns. Cross-document within scope explicitly allowed; cross-scope explicitly prohibited.
  2. "False-green proof" — PARTIALLY ACCEPTED. PO-6 requires both a foreign-scope negative AND a same-scope cross-document positive to prove the boundary is correctly scoped, not over-restricted.
  3. "Downstream-safety gap" — REJECTED. Write-time scope-binding makes traversal safe: if all entities reachable through scope-filtered edges are within scope, `get_entity` by raw ID cannot leak foreign-scope data. Fixing traversal scope-checks is a separate graph-store concern outside this task.
  4. "AC-quality on AC-1/AC-3" — PARTIALLY ACCEPTED for AC-3 (boundary now explicit). REJECTED for AC-1: "display fields" and "persistence token" are design-flexible disjunctions successfully consumed by test-writer through 5 cycles.

### Proof-Bundle Validation
- Finalized bundle: `critical` (unchanged)
- Test-writer: PROCEED with PO-6

### Verdict: REFINE → APPROVE
AC-3 scope-binding contract explicitly defined (scope as trust boundary). PO-6 added (foreign-scope rejection + same-scope cross-document acceptance). Advancing to todo.
2026-05-15T15:14:54+00:00
Architecture review refinement cycle 3 complete. AC-3 scope-binding contract explicitly defined: explicit Phase 1 source_id/target_id must resolve to an existing entity within the claimed chunk's scope (WHERE id = ? AND scope = ?). Cross-document within-scope references allowed (inter-document graph building). Cross-scope rejected. PO-6 added with two tests: foreign-scope rejection negative and same-scope cross-document positive. Challenger partially accepted (block @ 0.36): contract boundary now explicit with codebase evidence; downstream traversal safety rejected as out-of-scope (write-time enforcement suffices). Proof bundle: critical. Advanced to todo.
2026-05-15T15:25:57+00:00
## Test-Writer Notes

**Retry cycle — advancing to in-progress (PO-6 negative requires builder fix).**

**Commit:** `a7cd4b49`

### Changes made

| File | Change | Reason |
|------|--------|--------|
| `tests/test_enrichment_persistence_1557.py` | Added `test_foreign_scope_explicit_source_id_raises_tool_error` in `TestFromAC_StoreEnrichmentRejection` | PO-6 negative (AC-3): entity `foreign-ent-1` in scope `team-b` used as `source_id` for a `team-a` chunk → expected ToolError but `_entity_id_exists` checks `WHERE id = ?` (no scope-binding) → test FAILS |
| `tests/test_enrichment_persistence_1557.py` | Added `test_same_scope_cross_document_explicit_source_id_accepted` in `TestFromAC_StoreEnrichmentRejection` | PO-6 positive (AC-3): entity `cross-doc-ent-1` in scope `team-a` from different doc-a1, used as `source_id` for chunk in doc-a2 (same scope) → edge persisted with non-NULL endpoints and source_id matches; proves fix does not over-restrict cross-document within-scope references |

### Verification (quality-runner, scoped)

- test_paths: `tests/test_enrichment_persistence_1557.py`
- Result: **36 passed, 1 failed, 0 skipped**
- Failing: `TestFromAC_StoreEnrichmentRejection::test_foreign_scope_explicit_source_id_raises_tool_error` — DID NOT RAISE ToolError (builder fix required)
- PO-6 positive: PASS — confirms same-scope cross-document entity IDs are accepted by current code
- Lint: clean (ruff exit 0)

### Builder Required Follow-up

PO-6 requires: change `_entity_id_exists` at `server.py:562` from `WHERE id = ? LIMIT 1` to `WHERE id = ? AND scope = ? LIMIT 1`, passing `provenance.scope` as the second binding; this scopes explicit Phase 1 endpoint validation to the claimed chunk's scope, rejecting foreign-scope entity IDs while preserving cross-document same-scope references.

### PO-6 proof obligation coverage

| PO branch | Test | Status |
|-----------|------|--------|
| PO-6 negative: foreign-scope entity ID rejected | NEW: `test_foreign_scope_explicit_source_id_raises_tool_error` | FAIL ✓ (builder fix needed) |
| PO-6 positive: same-scope cross-document entity ID accepted | NEW: `test_same_scope_cross_document_explicit_source_id_accepted` | PASS (regression guard for fix) |
2026-05-15T15:38:23+00:00
## Builder Notes
- Implementation: serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py
- Fix applied: scope-bound explicit Phase-1 endpoint validation in `_resolve_phase1_edge_endpoints` by changing explicit-ID existence check from global lookup to scope lookup (`id` + `provenance.scope`).
- Expected behavior: explicit `source_id`/`target_id` now resolve only within the claimed chunk scope; foreign-scope explicit IDs reject with `ToolError` before insert, while same-scope cross-document explicit IDs remain allowed.
- RED verification (pre-fix): quality-runner scoped on `tests/test_enrichment_persistence_1557.py` -> 36 passed, 1 failed (`TestFromAC_StoreEnrichmentRejection::test_foreign_scope_explicit_source_id_raises_tool_error`), lint clean.
- GREEN verification (post-fix, critical surface):
  - Tests: `tests/test_enrichment_persistence_1557.py`, `tests/test_mcp_knowledge_enrichment_tools.py`, `tests/test_mcp_knowledge_phase2_tools.py`, `serve/mcp-knowledge/tests/test_server.py`, `tests/test_enrichment_schema.py`
  - Result: 155 passed, 0 failed, 0 skipped
  - Lint: clean
  - Coverage (scoped modules): `owlbear_mcp_knowledge.server` 62%, `owlbear_knowledge.schema` 67%
- Commit: e8e0fe61 — fix: scope-bind phase1 explicit endpoint validation (#1557, builder)
- Evidence summary: PO-6 negative now enforced without regressing PO-6 positive and adjacent critical enrichment/schema surfaces.
2026-05-15T15:54:14+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation (one line): PASS #1557 -> docs | AC mapped to code and evidence sufficient.
- Independent verification: quality-runner reran `tests/test_enrichment_persistence_1557.py`, `tests/test_mcp_knowledge_enrichment_tools.py`, `tests/test_mcp_knowledge_phase2_tools.py`, `serve/mcp-knowledge/tests/test_server.py`, and `tests/test_enrichment_schema.py` with `155 passed, 0 failed, 0 skipped`; scoped lint was clean; coverage reported `owlbear_mcp_knowledge.server` at 62% and `owlbear_knowledge.schema` at 67%.
- AC evidence map:

| AC | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 | `get_next_batch` now claims only source-linked enrich-enabled chunks and returns `document_id`, `source_id`, and `scope` in the batch payload (`serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:905-946`). | Proven by durable batch-shape tests plus task-local provenance-field tests (`tests/test_mcp_knowledge_enrichment_tools.py:295-403`; `tests/test_enrichment_persistence_1557.py:153-185`). | PASS |
| AC-2 | Phase 1 persistence stamps server-derived provenance onto entity rows and edge rows, with `chunk_id` added to edge metadata and no caller-supplied provenance required (`serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:741-792`). | Exact DB-column assertions cover entity provenance, edge provenance, relation alias normalization, and edge metadata chunk stamping (`tests/test_enrichment_persistence_1557.py:210-401`). | PASS |
| AC-3 | Phase 1 now rejects unresolved or out-of-bound endpoint/provenance states, validates explicit Phase 1 IDs within the claimed chunk scope, and clears failed chunk claims instead of leaving chunks stuck claimed (`serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:559-603`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:639-650`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:981-994`). | Rejection and recovery proofs cover ghost/orphan chunks, already-enriched chunks, truly unresolvable endpoints, bogus explicit IDs, foreign-scope explicit IDs, and same-scope cross-document explicit IDs (`tests/test_enrichment_persistence_1557.py:431-813`). | PASS |
| AC-4 | Consolidation candidates expose durable pair identity through `entity_id_a`/`entity_id_b` and durable candidate IDs (`serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:339-342`). | Candidate identity is asserted in task-local tests (`tests/test_enrichment_persistence_1557.py:839-871`). | PASS |
| AC-5 | Phase 2 endpoint resolution is bound to the reviewed candidate pair, reviewed-without-edge persistence stores durable pair identity, and repeated accepted/reviewed payloads do not duplicate or re-surface the candidate (`serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:447-475`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:707-711`). | Task-local and durable suites prove candidate-pair validation, mismatched-endpoint rejection, idempotence, reviewed-without-edge exclusion, and reviewed_pairs identity persistence (`tests/test_enrichment_persistence_1557.py:899-1100`; `tests/test_mcp_knowledge_phase2_tools.py:1102-1543`). | PASS |
| AC-6 | Orphan chunks are excluded by the source join and enrich flag filter in `get_next_batch` (`serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:905-927`). | Proven by durable orphan/exclude tests and task-local orphan exclusion coverage (`tests/test_mcp_knowledge_enrichment_tools.py:365-382`, `tests/test_mcp_knowledge_enrichment_tools.py:588-604`, `tests/test_enrichment_persistence_1557.py:1160-1199`). | PASS |
- Adversarial review summary: `code-reader` found no blocking implementation mismatch on the current surface. A tentative FAIL based on missing mirrored Phase 1 `target_id` scope-binding tests was challenged successfully: `source_id` and `target_id` share the same scope-bound resolver path in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:559-603`, the architect-approved PO-6 refinement used representative `source_id` proofs, and adjacent Phase 1 direct-`target_id` happy-path tests remain green (`tests/test_mcp_knowledge_enrichment_tools.py:719-760`). That concern is recorded below as optional hardening, not a blocking false-green.

## Observations
- Non-blocking: `share/skills/h-knowledge-ops/SKILL.md:111-121` documents direct Phase 1 `source_id`/`target_id` usage but does not yet mention the newly enforced same-scope requirement for explicit IDs. That should be aligned in the docs stage so manual agents have the exact current contract.
- Non-blocking: if the team wants extra redundancy later, add mirrored Phase 1 `target_id` negative/positive tests equivalent to the new `source_id` scope-binding tests. The current packet is still sufficient because both operands flow through the same resolver and the shared critical surface is independently green.
2026-05-15T15:56:31+00:00
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | README verification | Yes | Updated | `serve/mcp-knowledge/README.md` — tool table accurate, no enrichment contract detail belongs here; `serve/knowledge/README.md` — schema migration is internal, no public API change; `share/skills/h-knowledge-ops/SKILL.md` — updated Phase 1 edge endpoint contract with scope-binding constraint (flagged by reviewer as the required docs-gate change) |
| 2 | External attribution | No | N/A | No external sources influenced implementation |
| 3 | Research doc | No | N/A | No research artifact exists for #1557 |
| 4 | Deletion detection | No | N/A | No source files deleted; no orphaned references |

### Verification Layers
- Layer 1 — grep confirmed `within the claimed chunk's scope` present at `share/skills/h-knowledge-ops/SKILL.md:119`; old vague "optional when provided directly" text absent
- Layer 2 — LLM editorial read: updated section is coherent; scope-binding constraint clearly stated; cross-document within-scope case explicitly allowed; no contradictions with Phase 2 endpoint derivation or behavior section

### Files Updated
- `share/skills/h-knowledge-ops/SKILL.md` — Phase 1 `source_id`/`target_id` line updated to state explicit IDs must match a persisted entity within the claimed chunk's scope; cross-scope IDs rejected with ToolError; cross-document same-scope references allowed
- Commit: `b6644e2f`

### Scratch Files Cleaned
- None (no 1557-* scratch files found)
2026-05-15T16:12:08+00:00
## Audit\n### Regression Detection\n- quality-runner mode full: 155 passed, 0 failed on knowledge-domain surface (task-scoped + adjacent durable suites). Broad full-suite run shows 233 failures in unrelated domains (cockpit_view, engine_accessor_migration, ideation_diagram, frontend) — all pre-existing with no recent commits to those files.\n- regression verdict: PASS\n\n### Intent Verification\n- scope alignment: PASS (all changed files within knowledge domain: serve/mcp-knowledge/server.py, serve/knowledge/schema.py, share/skills/h-knowledge-ops/SKILL.md, plus 4 test files)\n- purpose match: PASS (task repairs enrichment persistence contract — changes enforce provenance stamping, rejection paths, scope-binding, and candidate identity across Phase 1 and Phase 2)\n- extraneous scope: none\n- boundary check: function-level behavior verification deferred to reviewer\n\n### Architect Quality: 3/5\nInitial AC-1 through AC-5 were specific on happy-path behavior but missed multiple edge cases requiring 3 architect refinement cycles: AC-2 needed chunk_id column/metadata correction, AC-3 needed 3 clarifications (orphan chunks → scope-binding for explicit IDs), AC-6 added for orphan exclusion, and 6 proof obligations (PO-1 through PO-6) were added iteratively. Design direction was sound and complexity waiver justified. The challenger engagement was productive. But the initial AC did not anticipate reject/dismissal branches or scope-binding requirements, causing repeated builder/reviewer/architect cycles.\n\n### Commit Integrity\n- upstream commit presence: PASS\n  - builder: 16bfa775, b962d372, 5d76847d, e8e0fe61 (all tagged #1557)\n  - test-writer: bf0000e2, 98bcdf21, 814e0b7f, a7cd4b49 (all tagged #1557)\n  - doc-writer: b6644e2f (tagged #1557)\n- kanban commit packaging: pending (this archival)\n\n### Deduction Breakdown\n- AC quality score 3: -.03\n- Regression failures: none (0)\n- Intent mismatch: none (0)\n- Evidence integrity: none (0)\n- Lint violations: none (0)\n- Missing reviewer evidence: none (0) — final PASS review includes full AC map with code and test evidence for all 6 AC lines\n\n### Confidence: .97\n### Action: archive