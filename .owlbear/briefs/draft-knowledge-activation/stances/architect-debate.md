# Architect — Critic Debate Log

## Cycle 1

### Draft Position Summary

The converged approach is structurally sound. Separation of ingest from agent-driven enrichment correctly places the LLM boundary at the agent. Three corrections needed: (1) content fetching is correctly outside the engine but `refresh_source` creates asymmetry, (2) consolidation SQL assumes `entities.source_id` but the real schema chains through `documents`, (3) scope tools should be excluded via `KNOWLEDGE_TOOLS_EXCLUDE`. Additional judgments: dual-schema `store_enrichment` with phase discriminator, claim-timeout worker coordination, two agent files, `StructuredExtractor` becomes dormant, startup fix deletes copilot_auth, exact string equality for entity matching.

Confidence: 0.82

### Critic Challenges (7 critical, 4 moderate)

**C1 (Critical — accepted): Source identity gap in `ingest_document`.**
The agent's "fetch → ingest_document(text=...)" flow doesn't preserve source identity. `ingest_text` builds a `Document` without `source_id`, but `Document.source_id` exists in the model. Refresh, source-scoped cleanup, and consolidation all depend on source identity. My draft ignored this entirely.

**Revision:** `ingest_document` MCP tool must accept `source_id` (or source metadata that generates one). Source registration must happen as part of ingest, not only in the `loader.py` path. This is a primary integration seam, not a minor detail.

**C2 (Critical — accepted): Worker infrastructure doesn't exist.**
`get_next_batch`, `store_enrichment`, `claimed_at`, `claimed_by`, `reviewed_pairs` — none of these exist in the current codebase. The existing `consolidate_knowledge` tool does chunk-batch summarization via LLM, which is a fundamentally different model from entity-pair-based review. My draft framed the worker model as "corrections" when it's actually new construction replacing an existing consolidation model.

**Revision:** Frame the enrichment/consolidation worker infrastructure as new development. The current `consolidation.py` module is being replaced, not extended. The scope of new code is larger than my draft implied.

**C3 (Critical — accepted): Idempotency problem with claim timeouts.**
Entity and edge inserts are direct `INSERT` without conflict handling. A timed-out claim re-processed by another worker produces duplicate graph data. The 5-minute timeout compounds this: BGE-M3 first-load (2.2 GB) alone can exceed 5 minutes.

**Revision:** `store_enrichment` must use upsert semantics (`INSERT OR REPLACE` or `INSERT ... ON CONFLICT`). Claim timeout should be 10 minutes minimum, or configurable. First-use embedding download must be excluded from timeout accounting.

**C4 (Critical — accepted): Refresh is half-wired, not just asymmetric.**
`RefreshOrchestrator` is instantiated without `content_fetcher`, `graph_store`, or `inter_doc_builder`. This isn't "browser refresh doesn't work" — refresh is structurally incomplete regardless of fetch method.

**Revision:** Upgrade this from "document the asymmetry" to "refresh needs structural completion." The orchestrator wiring in the MCP server is incomplete. This is activation work, not a documentation item.

**C5 (Critical — rejected as overstated, partially accepted): Timeout-only reliability with current persistence.**
Valid that WAL mode isn't enabled and writes aren't idempotent. However, the fix is straightforward: enable WAL, add upsert semantics. The claim-timeout model itself is still correct — the implementation details need attention, not the architecture.

**Retained position:** Claim-timeout coordination is architecturally correct. **Added requirement:** Enable WAL mode, implement upsert semantics for enrichment writes.

**C6 (Moderate — accepted): EntityExtractor already handles None.**
`EntityExtractor.__init__` accepts optional extractor; the no-extractor path is already a no-op. My warning #2 was based on the `IngestPipeline` constructor signature showing it as mandatory, but the inner `EntityExtractor` handles the None case. Removed from warnings.

**C7 (Moderate — accepted): Exact string equality is a regression from inter_doc_graph_builder.**
The existing `inter_doc_graph_builder.py` already does canonical-name blocking + vector similarity filtering for cross-source matching. The proposed exact-string-only approach is a capability regression. However, the inter_doc_graph_builder requires LLM (it uses the structured extractor for comparison). In a no-LLM environment, the regression is justified by the constraint.

**Revision:** Frame correctly as a justified regression due to the no-API-key constraint, not a "future enhancement." Note that canonical-name normalization (lowercase, strip underscores) could be added without LLM to narrow the gap.

**C8 (Moderate — partially accepted): Scope tool exclusion collapses implemented and degraded.**
`import_scope` and `export_scope` are fully implemented in `scope_transfer.py`. Only `sync_from_global` and `sync_to_global` are degraded (throw NotImplementedError). My blanket "exclude all 4" was too coarse.

**Revision:** Exclude `sync_from_global`, `sync_to_global` (degraded), and the bookmark tools (premature). Keep `import_scope` and `export_scope` available — they're implemented and may be useful for manual DB snapshots.

**C9 (Moderate — rejected): Two-agent split not grounded in current interface.**
The current interface is a single mixed surface because it was designed before agent-driven enrichment. The two-agent split is forward-looking design — the enricher worker loop is a distinct behavioral mode (batch, headless, cheap model) from the ingestor (interactive, user-facing). The current code not having this boundary is expected; we're designing activation, not documenting status quo.

**Retained position:** Two agent files. The behavioral modes are distinct enough to warrant separate agents.

**C10 (Moderate — accepted): In-memory Qdrant = vector loss on restart.**
The server defaults to in-memory Qdrant (`location=None`). Every restart loses all vectors, requiring re-embedding. This is a far bigger operational risk than just the BGE-M3 download warning.

**Revision:** Qdrant must use filesystem persistence (e.g., `store/knowledge/qdrant/`). This is a critical configuration fix, not optional. Upgraded to primary warning.

**C11 (Blind spot — noted): Copilot auth deletion has blast radius.**
Test suite `test_copilot_server_wiring_888.py` exists and tests the auth path. Deleting copilot_auth requires updating or removing these tests.

**Noted:** Include test cleanup in the copilot_auth removal scope.

### Revised Confidence: 0.78

The Critic surfaced genuine structural gaps (source identity, idempotency, Qdrant persistence, refresh wiring) that my draft missed by not reading the actual implementation carefully enough. The core architecture remains sound but the scope of new construction and the number of integration fixes needed is larger than initially assessed.
