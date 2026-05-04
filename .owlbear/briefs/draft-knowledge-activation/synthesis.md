# Synthesis — Knowledge Engine Activation

## Summary

Four panelists evaluated the converged approach across architecture, data integrity, end-user experience, and security. All endorse the core design: separated ingest/enrich/search pipeline, pull-based enrichment workers, agent-driven LLM access, and browser detection with user validation. The principal agreement is that this is **significant new construction disguised as wiring activation** — the enrichment worker system, schema additions, source identity fix, and content guard wiring are collectively a substantial development effort.

Six material tensions exist, primarily at the boundaries between panels: scope tool inclusion, edge deduplication strategy, search result provenance contract, `get_stats` output depth, content guard timing, and the `consolidated` column collision. Three items surface as convergent blockers that all panels either raise or implicitly depend on.

Confidence scores cluster tightly: architect 0.78, data 0.82, enduser 0.78, security 0.80.

---

## Convergences

### C1. Overall Architecture Is Sound

All four panelists validate the converged approach's core shape:
- Ingest/enrich/search separation with LLM boundary at the VS Code agent (architect §Position, data §Position, enduser §Scope Frame, security §Position)
- Pull-based worker pattern with `get_next_batch`/`store_enrichment` coordination (architect §2, data §3, enduser R1-R2)
- Two-agent model: ingestor (interactive) and enricher (batch) (architect §Agent Model, enduser R1-R2, security §7 consumer matrix)
- Dual-purpose `store_enrichment` with phase discriminator (architect §6, data §4)

### C2. This Is New Construction, Not Wiring

Every panel independently flags scope underestimation:
- Architect (Warning 5): "~3 new schema tables + 3 new MCP tools + upsert graph store methods"
- Data (§1-§3): Three critical schema gaps, none of which have existing implementation
- Enduser (B1-B3): Three activation blockers in output contracts and error handling
- Security (§2, §7): Content guard wiring + tool surface cut required before activation

### C3. Source Identity Is a Critical Integration Gap

Three panelists independently identify source identity as blocking:
- Architect (§1): "highest-priority integration fix" — `ingest_document` must register/resolve source records; refresh, enrichment, consolidation all depend on it
- Data (§1): Consolidation SQL references `entities.source_id` which doesn't exist; must JOIN through `documents`
- Enduser (B2): Source management not viable at 548-source scale without per-source health/state

Security does not address source identity directly but depends on it for provenance-aware content guard decisions.

### C4. Enrichment Writes Must Be Idempotent

Three panelists converge on upsert semantics:
- Architect (§3): `INSERT OR REPLACE` for entities, `INSERT OR IGNORE` for edges; WAL mode required for concurrent workers
- Data (§4): Batch-level transaction wrapping; UPSERT or INSERT-OR-IGNORE for retries
- Security (§8): Graph amplification risk makes write correctness a security concern, not just data quality

### C5. Qdrant Filesystem Persistence Is Non-Negotiable

Architect (§4, Warning 1) identifies in-memory Qdrant as "single highest operational risk" — every MCP server restart loses all vectors, requiring full re-embedding of 5,480+ chunks. Enduser (Warning 4) independently flags the 548-source rebuild as "an untested operational cliff." The current `QdrantVectorStore` constructor already supports a `path` parameter; this is a configuration fix.

### C6. Worker Queue Needs Atomic Claims + Lease Expiry

- Data (§3, CRITICAL): SELECT + UPDATE must use IMMEDIATE transaction; `claimed_at` column + stale-check reaper needed for crash recovery
- Architect (Trade-offs): Acknowledges timeout tuning risk — "too short = duplicates, too long = blocked progress; 10 min default"
- Data adds re-ingest race condition (Warning 3): workers with stale chunk IDs after `delete_document_data()` will write orphaned entities

### C7. copilot_auth Removal Scope

- Architect (Warning 4): Test suite exists (`test_copilot_server_wiring_888.py`) — removal is a contract change, not just code deletion
- Security (§4): Cached token at `~/.owlbear/copilot_token.json` must be deleted; migration/cleanup step required

---

## Disagreements

### T1. Scope Tool Inclusion — architect vs. security

**Architect** (§MCP Tool Surface Assessment): Keep `import_scope` and `export_scope` active — they are fully implemented in `scope_transfer.py` and useful for manual DB snapshots. Exclude only `sync_from_global`, `sync_to_global`, and bookmark tools. Total excluded: 6.

**Security** (§7, Least-Privilege §3): Disable scope transfer tools via `KNOWLEDGE_TOOLS_EXCLUDE` until needed. Narrower active surface reduces exposure.

**Context.md D12** defers scope implementation, which aligns with security's position. But architect's point that import/export are fully implemented and useful for backup/restore is a legitimate operational need.

**User must decide:** Include `import_scope`/`export_scope` in the active 8, or defer all scope tools per D12?

### T2. Edge Deduplication Strategy — architect vs. data

**Architect** (§6, Trade-offs): One `store_enrichment` tool with phase discriminator. Does not specify edge uniqueness constraint beyond mentioning UPSERT.

**Data** (§4): Provenance-aware deduplication required. A naive `UNIQUE(source_id, target_id, relation)` collapses distinct evidence chains. Proposes `UNIQUE(source_id, target_id, relation, document_id)` or similar. Explicitly requests architect input.

Both agree edges need deduplication. The tension is **coarse-grained vs. fine-grained uniqueness** — collapsing duplicates for simplicity vs. preserving provenance for auditability.

### T3. `consolidated` Column Semantics — data raises, architect silent

**Data** (§2, CRITICAL): `chunks.consolidated` (INTEGER 0/1) already means "batched into a consolidation insight" in current `consolidation.py`. Using it for enrichment state (entity extraction lifecycle) corrupts existing semantics. Requires new `enrichment_state TEXT DEFAULT 'pending'` column + `claimed_at` for lease expiry.

**Architect** does not address this collision. The enrichment worker infrastructure (§2) is framed as new construction but doesn't specify how enrichment state is tracked at schema level.

**Impact:** If unresolved, the schema migration will either break existing consolidation semantics or produce ambiguous state tracking.

### T4. Search Result Provenance Depth — enduser raises, others silent

**Enduser** (B1, Warning 1): Activation blocker. Search results must include machine-readable `retrieval_path`, entity links, and cross-source relationships. "If the user cannot see WHY a result was returned, the graph enrichment investment is invisible." For agents: structured provenance fields (source_id, entity_name, relationship_type, linked_source_id). Deterministic response shape regardless of enrichment state.

**Architect**, **data**, and **security** do not address search result output format. The MCP tool surface (D11) says "semantic search + graph-augmented results" without specifying the response schema.

**Impact:** Without provenance, Outcome 4 ("cross-source relationships surfaced via graph traversal") is unverifiable by both humans and agents.

### T5. `get_stats` Output Richness — enduser raises, others silent

**Enduser** (B2): Activation blocker at 548-source scale. `get_stats` must include enrichment coverage (chunks processed / total), consolidation progress (pairs reviewed / total candidates), source-level health (per-source chunk count + enrichment state). `list_sources` needs filtering by enrichment state, staleness, source type.

**Enduser** (R2): `get_stats` should expose consolidation candidate count to enable system-guided phase transitions.

No other panelist specifies `get_stats` output depth.

### T6. Content Guard Timing — security raises, others silent

**Security** (§2, §8): Content guard must scan at ingest AND before enrichment. A poisoned chunk that passes ingest (e.g., because the guard wasn't wired at that time) could manipulate the extraction model during enrichment to produce fabricated entities/edges.

**Architect** does not mention the content guard. **Data** does not mention it. **Enduser** (B3) addresses error handling for fetch failures but not injection scanning.

**Impact:** If the guard runs only at ingest, chunks ingested before the guard was wired (or via a path that bypasses it) enter enrichment unscanned.

---

## Recommendation

Wire the following into the Brief as hard requirements, grounded in convergence across 3+ panelists:

1. **Source identity fix** in `ingest_document` (C3) — highest priority, blocks everything downstream
2. **Qdrant filesystem persistence** (C5) — one-line config fix, highest operational risk
3. **Content guard wiring** to ingest pipeline (T6, security §2) — one-line fix, blocking security finding
4. **New `enrichment_state` column** (T3, data §2) — avoids semantic collision with `consolidated`
5. **Atomic worker claims + lease expiry** (C6) — required for parallel worker safety
6. **Upsert semantics on all enrichment writes** (C4) — required for retry/timeout safety
7. **Search result provenance contract** (T4) — without this, Outcome 4 is unverifiable

Defer to user decision: scope tool inclusion (T1), edge deduplication granularity (T2), `get_stats` output depth (T5), content guard at enrichment time (T6).

**Confidence: 0.82**

The convergences are strong — four independent analyses arrived at overlapping conclusions from different evaluation angles. The tensions are real but localized (schema details, output contracts, tool surface boundaries). The primary risk is scope: the Brief must honestly frame this as significant new development, not activation of existing code.

---

## Open Questions

1. **Scope tools active or deferred?** (T1) `import_scope`/`export_scope` are implemented and useful for backup — but D12 says defer all scope work. Which takes precedence?

2. **Edge uniqueness constraint?** (T2) Coarse `UNIQUE(source, target, relation)` or provenance-aware `UNIQUE(source, target, relation, document_id)`? Data requests architect input; the right answer depends on how provenance is queried downstream.

3. **`get_stats` output contract?** (T5) Enduser calls enrichment coverage and source-level health an activation blocker. Is this in scope for the Brief, or post-activation polish?

4. **Content guard at enrichment time?** (T6) Security recommends scanning before enrichment (not just ingest). Adds processing overhead per enrichment batch. Is the risk (chunks ingested pre-guard reaching enrichment) worth the mitigation cost?

5. **Entity type schema timing?** (D13) Left as Phase 2 research. Enduser (Warning 3) and data (§6) note that without domain-specific types (TICKET, COMPLIANCE_CONTROL), cross-source mapping produces incomplete graphs. When does this research happen relative to the Brief?

6. **Delete source capability?** (Enduser R4) No `delete_source` tool exists. Manual path (edit sources.yaml + rebuild) works but is fragile. Include in the active tool surface or document the manual path?

7. **Rebuild duration/failure modes?** (Enduser Warning 4, Architect Warning 3) 548 sources × BGE-M3 embedding (2.2 GB model) = untested operational cliff. Should the Brief include a rebuild benchmark or at least document expected duration?
