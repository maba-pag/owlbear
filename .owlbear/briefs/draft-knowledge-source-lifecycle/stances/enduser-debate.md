# End-User Debate Log — Knowledge Source Lifecycle

## Critic Round 1

### Challenges Received

1. **Computed status field is weaker than it looks (critical).** Sources have mixed refresh cadences — one staleness threshold doesn't work. The four-state summary (healthy/stale/error/disabled) would collapse distinctions the system already knows about (refreshed, partial, skipped, failed).
   - **Response:** Accepted. Dropped the computed status field entirely. Raw fields are correct for an MCP-tool API consumed by agents — the agent interprets timestamps relative to expected cadence. This was GUI thinking projected onto an API surface.

2. **O2 three-way model incomplete (critical).** Missed `skipped` (unchanged content). Never answered: does a no-change check count as "refreshed"? Also, "no URLs configured" is a config error in the codebase, not a benign no-op.
   - **Response:** Accepted. Expanded to four-way model and took a clear semantic position: `last_refreshed_at` means "last verified," including skipped/unchanged checks. No-URLs-configured reclassified as config error.

3. **O3 not merely cosmetic (moderate).** Agents read `source_type` as semantic contract. `AUTHENTICATED_WEB` on a plain HTTP source steers agent reasoning toward browser/auth assumptions.
   - **Response:** Accepted. Upgraded O3 from cosmetic to moderate priority as a contract-trust issue for agent consumers.

4. **`enrich` dilutes health focus (moderate).** It's processing config, not health data. Adding it weakens the "at a glance" argument. Also, `SourceInfo` shape is contract-tested — expanding it isn't free.
   - **Response:** Accepted. Dropped `enrich` from recommendation.

5. **Dry-run isn't foolproof in agent workflows (critical).** In agent-driven MCP, a preview can be summarized imperfectly or acted on incorrectly. `destructiveHint` is metadata, not enforcement.
   - **Response:** Partially accepted. Repositioned dry-run as defense-in-depth rather than primary safety mechanism. `destructiveHint` is the primary signal; dry-run is secondary. At 10-50 sources with low mutation frequency, the residual risk is acceptable.

6. **Dry-run preview omits Qdrant vectors (moderate).** Stance argued honesty requires vector cleanup but didn't include vectors in the preview.
   - **Response:** Accepted. Added vector/chunk count to dry-run preview specification.

7. **No `get_source` detail tool exists (moderate).** Error presentation assumes a per-source detail surface that doesn't exist. The workflow collapses to "refresh again to see detail."
   - **Response:** Accepted. Recognized that `list_sources` is simultaneously list and detail view. Changed error-presentation recommendation: sanitized full text in `last_error` field, since there's no other passive inspection surface.

8. **Per-URL health is scope creep (moderate).** Brief explicitly narrowed scope (D2). Page-level lifecycle model already exists separately.
   - **Response:** Accepted. Dropped from the main position. Noted as future consideration only.

### Blind Spots Surfaced

- Inline non-refreshable provenance rows from direct ingest — these disabled rows interact with any health or remove semantics. Addressed by noting `enabled=false` needs no special treatment beyond displaying the flag.
- Ambiguity between "last verified" and "last changed" — took explicit position: `last_refreshed_at` = "last verified."
- Preview/delete drift in agent workflows — acknowledged as acceptable risk at current scale.

---

## Critic Round 2

### Challenges Received

1. **`last_error` secret leakage risk (critical).** Raw exception strings can contain auth tokens in URLs, internal paths. Codebase has existing regression test for sanitized browser errors.
   - **Response:** Accepted. Added explicit requirement: `last_error` must be sanitized. Human-readable error descriptions, not raw exception strings. This is critical for an API surface consumed by agents that may relay information.

2. **O3 type change affects runtime dispatch (critical).** Refresh dispatches on `source_type` before `fetch_method`. Changing type from `AUTHENTICATED_WEB` changes which handler runs, not just the label.
   - **Response:** Accepted. Added implementation-coupling warning. The stance still recommends fixing the label for contract-trust reasons, but explicitly flags that this is a behavior change requiring careful implementation — possibly adjusting the dispatch to route on `fetch_method` as primary key.

3. **O2 under-specifies mixed results (moderate).** `refreshed + failed` and `skipped + failed` combinations not handled. "Last verified" claim is stronger than evidence when some URLs failed in the same run.
   - **Response:** Partially accepted. Simplified update rule: bump `last_refreshed_at` whenever ANY URL was successfully verified (`refreshed + partial + skipped > 0`); set `last_error` whenever ANY URL failed (`failed > 0`). Both fields update independently. A mixed-result source shows as "recently verified but has problems."

4. **`enabled=false` has multiple meanings (moderate).** Collapse of "disabled provenance" and "operator-disabled manifest source" into one interpretation.
   - **Response:** Accepted. Broadened: `enabled` is useful as a display field without prescribing why it's false. The operator sees the flag and knows the source won't refresh.

5. **O4 cascade path split between stores (moderate).** `delete_cascade` handles SQLite only; vector cleanup in `DocumentStore`. Dry-run truthfulness depends on unifying both.
   - **Response:** Accepted. Added requirement: `remove_source` must unify both deletion paths. Dry-run must accurately reflect combined scope.

### Blind Spots Surfaced

- `last_error` mixes errors and warnings into one field — acknowledged as a separate concern beyond the 4-outcome scope.
- Dropping `enrich` removes visibility into a flag that affects downstream behavior (enrichment claiming). Held position: health view should stay focused; enrichment config is a separate query concern.
- Agent-facing source contract is already inconsistent (inline provenance not in documented SourceType list). Acknowledged but not actionable within this scope.
- Expanding `list_sources` SourceInfo shape is a bigger contract move than casual "add fields" suggests. Acknowledged in warnings.

### Position Stability

After two rounds, the core position is stable. Major adjustments from Round 1 (dropped computed status, upgraded O3, repositioned dry-run). Round 2 added important safety requirements (error sanitization, implementation-coupling warning for O3) without changing the fundamental recommendations. Confidence settled at 0.80.
