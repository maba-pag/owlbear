# Data Stance — Critic Debate Log

## Cycle 1

### Draft Position

Five gaps identified:
1. ERR_STALE not surfaced to user (infinite retry loop on dead DRs)
2. NaN propagation in `formatAge()` from empty `created` string
3. `count` vs `items.length` divergence risk
4. `PendingDR` type name bakes in status assumption
5. No schema validation boundary on API response

### Critic Challenges

**Challenge 1 (Gap 2 — NaN propagation): Contradicted by implementation.** `formatAge()` guards with `Number.isFinite(parsedCreatedAt) ? parsedCreatedAt : Date.now()`. The NaN path is already handled. Severity: moderate.

**Challenge 2 (Gap 1 — ERR_STALE): Overstated failure mode.** The modal only marks `retryable: true` for status >= 500. ERR_STALE returns 409, which shows as non-retryable with the backend's descriptive message. No infinite retry loop. The backend message "Decision 'x' is already resolved" is preserved. Severity: moderate.

**Challenge 3 (Gap 3 — count divergence): No evidence of current bug.** Backend derives `count` from `len(items)` and tests lock that invariant. The hook consumes `payload.count`, but there's no evidence the values diverge. Severity: minor.

**Challenge 4 (Gap 4 — PendingDR naming): Wrong extensibility pressure point.** The real constraint is the SSE event pipeline: watch filter only monitors `decisions/pending/*.md`, classifier only emits events for pending paths, tests explicitly reject resolved paths. The TypeScript type name is cosmetic compared to the structural event pipeline assumption. Severity: critical.

**Challenge 5 (Gap 5 — No schema boundary): Under-scoped.** The unsound boundary is not future field-rename drift — it's present-day raw YAML type drift. `meta.get("task_id")` could return any YAML type. No Pydantic response model validates the item shape before serialization. Severity: critical.

**Blind Spot 1: Modal state loss on SSE refetch.** `selectedDR` is derived live from `pendingDRItems.find()`. When SSE triggers refetch and the resolved DR disappears, `selectedDR` nulls out, closing the modal and discarding user input. This is the real race condition — more impactful than the submit-time ERR_STALE handling.

**Blind Spot 2: Two distinct "already resolved" error paths.** Backend splits on `resolved_by`: cockpit-origin duplicates get 404, external resolutions get 409 ERR_STALE. Frontend doesn't distinguish but both are non-retryable, so impact is minor.

### Refinements Applied

- **Gap 2 withdrawn.** `formatAge()` NaN guard confirmed in source. Invalid gap.
- **Gap 1 reframed.** Submit-time ERR_STALE handling is adequate (non-retryable with descriptive message). The critical race is the modal state loss from SSE refetch, not the submit error path. Promoted blind spot 1 to Gap 1 (Critical).
- **Gap 3 downgraded.** Latent defense-in-depth concern, not a current bug. Dropped from pre-ship gaps.
- **Gap 4 reframed.** TypeScript naming is cosmetic. The real extensibility constraint is the SSE event pipeline hardcoded to pending-only. Reframed as structural observation for the fast-follow.
- **Gap 5 upgraded.** Scoped to present-day raw YAML type drift, not future rename drift. Promoted to High.

### Position After Cycle 1

Three genuine gaps: (1) modal state loss on SSE refetch — critical, (2) no Pydantic response model on pending items — high, (3) SSE pipeline structurally pending-only — structural for fast-follow. Position is solid. Critic challenges fully addressed with evidence.
