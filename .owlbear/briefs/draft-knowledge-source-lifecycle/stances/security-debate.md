# Security Debate Log — Knowledge Source Lifecycle Fixes

## Cycle 1

### Draft Position (Security Panelist)

Six positions covering O1-O4 security implications:

1. **`last_error` exposure is a real leak vector (O1):** Raw `str(exc)` stored without sanitization. HTTP errors from authenticated corporate endpoints can contain auth headers, tokens, internal URLs, stack traces. Exposing via `list_sources` extends blast radius from "persisted in DB" to "visible to every MCP consumer." Recommended sanitization or a boolean `has_error` flag.

2. **`config` must NOT be exposed in `list_sources` (O1):** Contains full URLs with potential embedded credentials or internal hostnames. Research notes correctly exclude it from the minimum field set.

3. **`remove_source` enables knowledge-base wipe (O4):** `delete_cascade` deletes entire source graph in a single transaction — no confirmation, no audit, no soft-delete. `destructiveHint=True` is advisory; agents can ignore it. A misbehaving agent could enumerate via `list_sources` then cascade-delete each source.

4. **O2 is a security improvement:** Preserving stale `last_refreshed_at` on failure prevents false-freshness signals. Net positive, no additional concern.

5. **Attack chain: enumerate → exfiltrate → destroy:** Prompt-injected agent could harvest error details, then wipe knowledge base.

6. **Qdrant vector orphaning (O4 gap):** `delete_cascade` doesn't clean Qdrant vectors. Orphaned vectors from deleted sensitive documents persist. Data retention concern, not directly security.

**Confidence: 0.82**

### Critic Challenges

**Challenge 1 (Critical): Pre-O1 baseline misstated.**
`refresh_source` already returns raw `errors` and `warnings` to MCP callers (server.py L1508-1509). O1 widens discoverability but is not the first tool-surface exposure of unsanitized error text. The draft treats O1 as creating new attack surface when it actually extends existing passive discoverability.

**Challenge 2 (Critical): URL leakage already exists outside `list_sources`.**
`search_knowledge` serializes `source.url` from `config` into result metadata (server.py L985-997). The `config` exclusion argument treats `list_sources` as the decisive leak point, but URL exposure already exists on another MCP surface.

**Challenge 3 (Moderate): Agent access is scoped, not universal.**
Agent tool surfaces are explicitly scoped via `.agent.md` files. `knowledge-ingestor` has `list_sources` and `refresh_source`; `knowledge-enricher` does not. The server supports `KNOWLEDGE_TOOLS_EXCLUDE`. "Every agent" wording is unsupported.

**Challenge 4 (Moderate): Destructive mutation already exists.**
`ingest_document` has replace-on-change semantics that delete prior document data. O4 escalates to whole-source removal but isn't a wholly new class of destructive power.

**Challenge 5 (Moderate): O2 state ambiguity.**
Preserving `last_refreshed_at` alone doesn't distinguish never-refreshed from failed-recently from unsupported. "No additional concern" is stronger than the evidence supports.

**Challenge 6 (Moderate): Existing sanitization pattern ignored.**
Browser-fetcher errors are already sanitized (server.py L63-65). The codebase distinguishes controlled from uncontrolled error text. Binary framing (full exposure vs. suppression) misses this.

**Challenge 7 (Moderate): Qdrant persistence is deployment-dependent.**
Default production path uses persisted vectors at `.owlbear/knowledge/vectors`. Orphaned vectors from corporate documents in persisted mode are a data-remanence concern, not just data integrity.

**Critic confidence in draft position: 0.57 (high pressure)**

### Refinements Applied

1. **Recalibrated O1 risk from HIGH to MEDIUM.** Acknowledged that `refresh_source` already exposes raw errors. O1 changes the exposure model from active (must trigger refresh) to passive (stale errors visible on list), which is a meaningful but incremental widening.

2. **Expanded `config` analysis.** Maintained exclusion recommendation but noted that `search_knowledge` already leaks source URLs. Flagged for separate audit rather than claiming O1 creates the leak.

3. **Scoped agent access claims.** Replaced "every agent" with accurate description of `.agent.md` scoping and `KNOWLEDGE_TOOLS_EXCLUDE`. Noted these are advisory, not privilege boundaries.

4. **Contextualized O4 destructive risk.** Acknowledged existing replace-on-change semantics. Reframed O4 as escalation (whole-source vs. per-document) rather than new class.

5. **Added O2 caveat.** Noted state ambiguity between never-refreshed, failed-recently, and unsupported. Recommended `last_error` differentiation rather than claiming "no concern."

6. **Incorporated existing sanitization pattern.** Referenced browser-fetcher pattern as the model to extend, rather than proposing new sanitization from scratch.

7. **Upgraded Qdrant concern to hard gate.** Recognized data-remanence risk in persisted mode. Made vector cleanup a pre-condition for O4.

8. **Grounded deployment model.** Anchored `destructiveHint` analysis in actual VS Code stdio deployment rather than theoretical "all hosts" reasoning.

**Post-refinement confidence: 0.82**

## Cycle Assessment

One cycle was sufficient. The Critic's challenges were well-evidenced and required material corrections to the baseline analysis, agent access claims, and existing exposure surfaces. The refined position addresses all critical and moderate challenges without abandoning the core security recommendations.
