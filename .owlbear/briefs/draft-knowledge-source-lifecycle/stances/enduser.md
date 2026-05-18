# End-User Stance — Knowledge Source Lifecycle (4-Outcome Fix Plan)

## User Experience Stance

The 4-outcome plan addresses real operator pain. The priority order from a usability standpoint is **O2 > O1 > O4 > O3** — trust in data accuracy first, then visibility, then cleanup capability, then label correctness.

### O1 — Expose health in `list_sources`

The four proposed fields (`last_refreshed_at`, `last_error`, `enabled`, `fetch_method`) are the right set. Adding more dilutes the health-at-a-glance purpose.

**Drop the computed status field.** Sources have mixed refresh cadences — some are stable references, some change weekly. A single staleness threshold would mislead more than it helps. Since the primary consumers are AI agents (not a dashboard), the agent can interpret timestamps relative to each source's expected cadence.

**Drop `enrich` from this change.** It's processing configuration, not health data. Including it weakens the "health at a glance" framing. If operators need to know which sources get enrichment, that's a separate query concern.

**`last_error` must be sanitized.** Since there is no `get_source` detail tool, the `list_sources` response is the only passive way to see error information. Full raw exception strings are not acceptable — the codebase already has regressions around secret leakage into error paths (auth tokens in URLs, internal paths). The error text should be human-readable and sanitized, not truncated to a status code but not raw stack traces either.

**`enabled=false` needs no special treatment.** The field correctly distinguishes sources that won't refresh (whether disabled provenance rows from direct ingest, or operator-toggled manifest sources). The operator sees the flag and knows not to expect freshness. No need to overinterpret why a source is disabled.

### O2 — Fix refresh honesty

**Highest-value fix.** A lying timestamp destroys trust in the entire knowledge base. The operator cannot confidently answer "is my knowledge current?" when a source that failed every URL still shows as recently refreshed.

**Semantic decision: `last_refreshed_at` means "last verified," not "last changed."** A successful no-change check (skipped) counts as verification — the system confirmed the content is current. This matches the operator's real question.

**Update rule (covers all counter combinations):**

- Bump `last_refreshed_at` whenever `refreshed + partial + skipped > 0` (any URL was successfully verified)
- Set `last_error` whenever `failed > 0` (regardless of whether other URLs succeeded)
- When `refreshed + partial + skipped == 0` and `failed == 0` (nothing to do / no URLs configured), treat as config error — set `last_error`, don't bump timestamp

This handles mixed results cleanly: a source with 8 URLs where 6 succeeded and 2 failed gets its timestamp bumped AND its error field set. The operator sees "recently verified but has problems."

### O3 — Direct-ingest type label

**Moderate priority, not cosmetic.** Upgraded from the initial assessment because agents read `source_type` as a semantic contract. An agent seeing `AUTHENTICATED_WEB` for a plain HTTP URL may reason toward browser-fetch or auth requirements that don't apply.

**Warning: this is not a simple label swap.** Refresh dispatch branches on `source_type` before `fetch_method`. Changing the type from `AUTHENTICATED_WEB` to something else changes the runtime refresh path, not just the display label. The fix must ensure the refresh handler still works after re-typing — or the dispatch logic must be updated to route on `fetch_method` as the primary key. The stance recommends fixing the label, but flags that this has implementation coupling beyond what "clean up semantics" suggests.

### O4 — Add `remove_source`

**Essential.** A system that can create artifacts but not remove them forces the operator into direct DB access for cleanup — that's a broken workflow at any scale.

**Safeguards:**

1. `destructiveHint=True` annotation — signals the agent framework to confirm with the user before executing
2. **Dry-run mode** — report what would be deleted: source name, page count, document count, entity count, and vector/chunk count (must include Qdrant vectors, not just SQLite rows)
3. **No undo mechanism** — at 10-50 sources, re-ingest is the recovery path; an undo system is over-engineering

**Critical implementation concern:** The current `delete_cascade` in `KnowledgeSourceStore` handles SQLite rows only. Vector cleanup lives in a separate `DocumentStore` path. The `remove_source` tool must unify both — otherwise "removed" is dishonest in the same way O2's "refreshed" is dishonest. The dry-run preview must also accurately reflect what both paths would delete.

**Agent workflow caveat:** In an agent-driven workflow, dry-run is defense-in-depth, not a guarantee. The agent might summarize the preview imperfectly, or state could drift between preview and delete. At this scale (10-50 sources, low mutation frequency) that risk is acceptable. The `destructiveHint` annotation is the primary safety mechanism; dry-run is the secondary one.

## Key Trade-offs

| Trade-off | Position |
|-----------|----------|
| Computed status vs. raw fields | Raw fields — mixed cadences make a single status misleading; agents can interpret |
| Full error text vs. summary | Sanitized full text — `list_sources` is the only passive error-inspection surface |
| O3 priority | Moderate, not cosmetic — agent contract-trust matters, but implementation coupling is higher than it looks |
| Dry-run as safety | Defense-in-depth, not guarantee — destructiveHint is the primary mechanism |
| `enrich` in health view | Exclude — processing config, not health; separate concern |

## Warnings

1. **No detail endpoint exists.** The operator has no way to inspect a single source in depth. `list_sources` is simultaneously the list view and the detail view. This is workable for O1's four health fields but will become a problem if source management grows. A `get_source` detail tool is a natural follow-up but out of scope here.
2. **O3 has hidden implementation coupling.** Changing `source_type` changes the refresh dispatch path. The brief frames this as a semantics cleanup, but it's a behavior change that needs careful implementation.
3. **`last_error` mixes errors and warnings.** The current implementation joins errors and warnings into a single `last_error` field. This means the operator can't distinguish "all URLs failed" from "some URLs had non-fatal warnings." Separating them would be clearer but is an implementation concern beyond the 4-outcome scope.
4. **Qdrant vector cleanup is not wired in `delete_cascade`.** This must be resolved before shipping O4 — otherwise cascade delete creates orphaned vectors, and the operator who thinks they cleaned up a source actually hasn't.

## Confidence

**0.80** — Two Critic rounds hardened the position. The core recommendations are sound. Residual uncertainty is around O3 implementation coupling (the type-label fix is riskier than it appears) and whether `list_sources` can sustainably serve as both list and detail view.
