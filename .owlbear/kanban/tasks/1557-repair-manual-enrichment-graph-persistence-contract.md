---
id: 1557
title: Repair manual enrichment graph persistence contract
status: backlog
priority: critical
created: 2026-05-14T15:47:32.454745+00:00
updated: 2026-05-15T04:00:10.884058+00:00
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
archival_reason:
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