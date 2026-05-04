# End-User Stance — Knowledge Engine Activation

## User Experience Position

The converged approach has sound technical design and the right separation of concerns (ingest/enrich/search, pull-based workers, browser detection). The UX problems are not in the architecture — they're in the interaction seams: where the system meets the operator's understanding, expectations, and trust.

I evaluate against **two users**: the human operator (curates sources, triggers enrichment, validates results) and pipeline agents (consume `search_knowledge` programmatically). The operator is the primary UX concern; agents need structured, machine-readable output contracts.

### Scope Frame

This is an activation/refactor, not a product build. I distinguish:

- **Activation blockers** — gaps that make the system unusable or untrustworthy at first use
- **Activation risks** — gaps that will cause friction or confusion, solvable with design decisions in the Brief
- **Post-activation polish** — real improvements that can follow without blocking delivery

---

## Activation Blockers

### B1. Search provenance is a contract contradiction

The activation outcome promises "cross-source relationships surfaced via graph traversal" (Outcome 4). The MCP tool surface defines `search_knowledge` as "semantic search + graph-augmented results" (D11). But the current implementation returns only `title`, `score`, `snippet`, and `entity_type` — no graph edges, no cross-source links, no retrieval-path indicator.

This is not a presentation detail. The entire value proposition (D4: "vector search alone doesn't work") depends on the user seeing and trusting cross-source relationships. If results look identical with or without graph enrichment, the user cannot verify the system works, and agents cannot leverage relationship data.

**Requirement:** Each search result must include a machine-readable `retrieval_path` field and, when graph-augmented, the entity links and cross-source relationships that contributed to the result. For human-facing output, the agent presenting results should be able to say "Found via requirement REQ-123 linked to ticket PROJ-456" — not just "score: 0.87."

**Caveat:** D13 leaves entity types as a Phase 2 research question. The provenance contract should be type-agnostic (entity name + relationship type + source) so it doesn't depend on a finalised taxonomy.

### B2. Source management is not viable at 548-source scale

`list_sources` returns name, source_type, and scope. `get_stats` returns document/entity/edge counts. The design treats richer source management as post-activation polish — but the starting state already contains ~548 source references in `sources.yaml`. The operator's first experience is not "add one source and explore"; it's "rebuild 548 sources and understand what I have."

At that scale, thin tool output is a trustworthiness failure. The operator needs to answer: Which sources are enriched? Which are stale? Which failed? What's the enrichment coverage? Without this, the knowledge base is a black box the operator populated but cannot inspect.

**Requirement:** `get_stats` must include enrichment coverage (chunks processed / total), consolidation progress (pairs reviewed / total candidates), and source-level health (per-source chunk count + enrichment status). `list_sources` should support filtering (by enrichment state, staleness, source type).

### B3. Error feedback on ingest failure is unspecified

The ingest flow describes the happy path (fetch → preview → confirm → store) and the "user spots login page" path (→ browser fallback). Missing: what happens on HTTP 404, timeout, DNS failure, connection refused, or malformed/empty content? Also missing: what happens when browser fallback fails (Playwright not installed, Edge not running, SSO expired)?

Without explicit error messages and recovery guidance, the operator hits a wall on their first failed fetch. For an activation project where every source is being ingested for the first time, error paths ARE the common path.

**Requirement:** Every fetch failure mode must produce a clear error message with a suggested next step. The ingest prompt agent should handle these gracefully, not pass through raw exceptions.

---

## Activation Risks

### R1. Worker count needs a default, not a bare choice

The enrichment prompt asks "How many workers? [1-6]" without context. The operator has no basis for this decision — no throughput data, no cost signal, no understanding of what "workers" means operationally.

**Recommendation:** Default to a sensible number (the Brief should pick one based on testing). Show a one-line explanation: "N workers will process chunks in parallel. Fewer = slower, more = higher Copilot session usage." Let the user accept the default or override. Don't present a bare numeric choice as the primary interaction.

Note: I accept D3/D7's position that session coupling and visible costs are intentional. The fix is adding context to the choice, not hiding it.

### R2. Phase transitions need system-suggested handoff

D7 (entity extraction) and D14 (cross-source consolidation) are genuinely different operations with different pull queues and completion semantics — they should not be collapsed into one action. But the operator needs to be told WHEN Phase 2 is relevant.

**Recommendation:** (a) Name the phases in user-meaningful terms: "extract entities" and "connect across sources" rather than "Phase 1" and "Phase 2." (b) When `get_stats` shows entity extraction is complete, its output should include the consolidation candidate count and suggest the next step: "Entity extraction complete for all sources. 47 cross-source candidates found — run /kb-enrich to connect them." This requires `get_stats` to expose candidate count, which is not in the current contract.

### R3. Source saving determines rebuild survivability

The ingest flow ends with "Offer to save source to sources.yaml manifest." The Brief defines `sources.yaml` as the source of truth for rebuilds (Outcome 5, D10). An ingested source NOT saved to manifest is invisible to `/kb-rebuild` — it will vanish on the next machine setup.

**Recommendation:** Default to saving. The ingest prompt should save to manifest unless the user explicitly says "this is exploratory, don't persist." Opt-out, not opt-in.

### R4. No delete-source capability

The tool surface includes `refresh_source` for re-ingesting stale content but no `delete_source` for removing wrongly ingested, duplicate, or accidentally persisted sources. Refresh re-fetches — it doesn't remove.

For an activation project where ingestion errors are expected during setup, the operator needs an escape hatch for bad data. The current path is: edit `sources.yaml` manually + rebuild the DB. That's viable but fragile and undocumented.

**Recommendation:** Either add `delete_source` to the active tool surface, or document the manual removal path explicitly in the ingest prompt's error handling.

---

## Post-Activation Polish

### P1. Preview validation enrichment

The "title + ~200 chars" preview is thin for corporate SSO detection, but `fetch_method` persistence means this is one-time validation per source. Recommendation for later: add structural indicators (heading count, word count, detected content type) alongside the text excerpt. Not a blocker because: (a) the user CAN spot most login pages from title + excerpt, (b) bad ingests are recoverable via refresh, (c) the method is persisted so future re-ingests skip validation.

### P2. Cockpit integration for source browsing

Post-activation, a cockpit view showing source health, enrichment coverage, and relationship density would replace the chat-based `list_sources`/`get_stats` interaction. Not needed for activation — the tools are sufficient when their output contracts are rich enough (see B2).

---

## Agent-as-User Requirements

Pipeline agents calling `search_knowledge` are the highest-volume consumer. Their needs:

1. **Structured provenance:** Graph-augmented results must include machine-readable fields (source_id, entity_name, relationship_type, linked_source_id) — not just human-readable explanations
2. **Deterministic result shape:** The response schema should be identical whether graph enrichment has been run or not (empty relationship fields, not missing fields)
3. **Scope filtering:** Agents operating in project scope need to filter results by scope without knowing the scope machinery internals

---

## Key Trade-offs

| Trade-off | Position | Reasoning |
|-----------|----------|-----------|
| Worker count visibility vs. simplicity | Guided default, not hidden | D3/D7 intentionally couple sessions; the fix is context, not concealment |
| Two-phase vs. single enrichment action | Keep phases, add system-guided transitions | Operations are genuinely different; collapsing loses observability |
| Rich preview vs. simple preview | Simple is fine for activation | One-time validation + persistence mitigates thin preview risk |
| Source management depth | Richer stats are a blocker, browse UI is polish | 548-source scale demands inspection capability; visual browsing can follow |
| Delete source | Risk, not blocker | Manual path exists; explicit tool or documentation needed |

---

## Warnings

1. **Search provenance is the make-or-break UX.** If the user cannot see WHY a result was returned (vector match vs. graph relationship), the graph enrichment investment is invisible and unverifiable. This is the single most important UX contract to get right.

2. **The first user experience is server startup.** The auth loop blocker (copilot_auth device-flow) means none of my concerns apply until Outcome 1 is delivered. If startup fails, everything else is irrelevant.

3. **Entity schema uncertainty propagates to UX trust.** D13 leaves entity types open. If the schema doesn't include TICKET, COMPLIANCE_CONTROL, etc., the cross-source mapping use case (D4) will produce incomplete relationship graphs. The user will see gaps they can't explain. The provenance contract should be schema-agnostic to survive taxonomy changes.

4. **548-source rebuild is an untested operational cliff.** Research notes estimate ~5,480 chunks. A full rebuild's duration, resource usage, and failure modes are unknown. The operator's first `/kb-rebuild` experience could be a multi-hour surprise.

---

## Confidence

**0.78**

The activation blockers (B1-B3) are grounded in contract contradictions and explicit design decisions. The risks (R1-R4) are well-supported by the design's own choices and user constraints. Main uncertainty: B1's provenance requirement may be partially addressed by existing query.py graph expansion logic that I cannot verify from context alone; and the 548-source scale argument (B2) assumes all sources are active at activation, which may not be true if rebuild is incremental.
