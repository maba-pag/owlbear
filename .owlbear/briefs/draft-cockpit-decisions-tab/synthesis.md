# Synthesis — Cockpit Decisions Tab

## Summary

Four panelists assessed the cockpit decisions tab design across architecture, data quality, end-user experience, and security. Confidence ranges 0.72–0.87. The design is structurally sound: the list-plus-modal pattern, P1/P2 phasing, pending-only V1 scope, and single-ResolveModal ownership are unanimously accepted. Three action-requiring gaps emerged with cross-panel agreement: modal state loss on SSE refetch, missing Pydantic response model on the pending list endpoint, and the need for route-conditional sidecar rendering. Inherited security gaps (DNS rebinding, bodyless CSRF) are real but pre-existing — the panel agrees they are not blockers for this feature.

## Convergences

### C1 — List-plus-modal is the correct V1 pattern

All four stances accept D7 (full-page list + ResolveModal overlay). architect: simplest path, reuses existing modal. data: response shape covers list + detail rendering. enduser: workable for V1 given low item count. security: modal rendering pipeline is XSS-mitigated.

### C2 — One global ResolveModal at Shell level

architect explicitly mandates single Shell-level instance via `selectedDRId` contract. data confirms the derivation path. enduser acknowledges the pattern. security confirms sanitization covers this rendering path. No dissent.

### C3 — Modal state loss is critical and must be fixed pre-ship

data (G1): SSE refetch nullifies `selectedDR`, closing modal mid-edit. enduser (warning #1): closing modal to check something loses in-progress response. Both identify the same failure mode from different angles. data recommends snapshot-to-local-state on modal open. enduser accepts modal pattern but flags state loss as the primary UX cost.

### C4 — Pending-only for V1; resolved DRs deferred

All panelists work within this boundary. data (G3) documents the structural cost of the fast-follow (event pipeline extension). architect's CockpitProvider analysis assumes pending-only. enduser accepts the scope cut. No one argues for including resolved DRs.

### C5 — Route-conditional sidecar rendering required for P1

architect provides detailed implementation (grid template changes at 3 breakpoints, DOM removal, mobile sheet suppression). enduser accepts the decisions tab doesn't need a sidecar. No contradictions.

### C6 — CockpitProvider unchanged for P1/P2

architect: boundary convention — future tabs use local hooks, not CockpitProvider additions. data: existing hooks sufficient. No panelist requires CockpitProvider changes.

### C7 — Pydantic response model needed on pending list endpoint

data (G2): raw `meta.get()` forwards untyped YAML values to the frontend. Type coercion at the API boundary catches malformed DR files. security: input validation is "adequate" but notes the unbounded response. Architect and enduser don't contradict.

### C8 — Tab always visible; empty state required

enduser: never hide the tab, design the empty state for discoverability. architect's nav-rail design implies persistent entries. No dissent.

### C9 — Badge hidden at zero

enduser: count > 0 only, with attention styling. data: count derived from list length, no separate endpoint. Compatible positions.

### C10 — Decisions tab's own security additions are sound

security: path traversal mitigated (regex allowlist), XSS mitigated (rehype-sanitize + CSP), input validation adequate. No panelist raises a security concern specific to the new tab's code.

## Disagreements

### T1 — Sidecar DR presence on kanban view after tab ships

**enduser:** Retain minimal DR presence in the kanban sidecar — removing it breaks the "see blocked task → resolve DR" flow. The status-bar indicator is a weaker affordance.

**architect:** Does not explicitly address whether DecisionViewport stays in the kanban sidecar. Addresses DRStatusIndicator fate only: "keep it, not a P1/P2 decision." The Shell decomposition plan doesn't remove the sidecar content for the kanban route, but doesn't commit to keeping DecisionViewport either.

**Tension level:** Medium. The current scope boundary says "kanban-side cross-nav sender is out of V1" — but whether existing sidecar DRs are retained or stripped is unspecified.

### T2 — Draft persistence scope (snapshot vs. full persistence)

**data:** Recommends snapshot DR data into modal-local state on open. Scope: prevents SSE-triggered data loss. Does not address deliberate close-and-reopen.

**enduser:** Flags both SSE-triggered loss AND deliberate close-to-check-something as the same pain. Wants a "clear path to fix" — implies the snapshot approach is partial.

**Tension level:** Low. Both agree the problem is real; disagreement is only on whether V1's fix (snapshot) fully resolves the UX concern or leaves a known gap.

### T3 — Inherited security gaps: bundle or separate?

**security:** Host header validation is "single highest-value mitigation" — cheap, app-wide, closes DNS rebinding. Framed as a recommendation, not a blocker.

**architect/data/enduser:** Do not address security mitigations. The feature scope (context.md) does not include security hardening.

**Tension level:** Low. No disagreement — just a priority question. Security recommends it but accepts it's pre-existing.

### T4 — Mobile layout for decisions tab

**enduser (warning #3):** Mobile viewport is unaddressed. Nav-rail behavior and modal sizing need attention.

**architect:** Describes sidecar mobile handling (sheet suppression on non-sidecar routes) but does not specify the decisions list mobile layout or modal sizing.

**Tension level:** Low. An unaddressed gap rather than a disagreement.

## Recommendation

Ship the design as specified in context.md with three mandatory pre-ship additions:

1. **Modal snapshot** (C3) — snapshot DR data to modal-local state on open, preventing SSE-triggered state loss
2. **Pydantic response model** (C7) — typed response model on `GET /api/decisions/pending` with coercion for `task_id` and `created`
3. **Notes length cap** — `max_length=10_000` on `ResolveRequest.notes` (security recommendation, trivial cost)

And one P1 implementation requirement confirmed by the panel:

4. **Route-conditional sidecar** (C5) — suppress sidecar DOM on non-kanban routes at all breakpoints, not just desktop grid

The architecture (incremental Shell decomposition, CockpitProvider unchanged, single ResolveModal, lazy loading, route config array) has clear panel support. The end-user concerns about genuine improvement over sidecar (enduser §8) are addressed by the combination of generous list density, focused workspace, and the existing modal pattern.

**Confidence: 0.79**

## Open Questions

1. **Sidecar DR retention (T1):** Should `DecisionViewport` remain in the kanban sidecar after the decisions tab ships, be reduced to a summary/link, or be removed? This affects the "blocked task → resolve" flow.

2. **Draft persistence beyond snapshot (T2):** Is the snapshot-on-open fix sufficient for V1, or should deliberate close-and-reopen also preserve draft state (e.g., localStorage persistence)?

3. **Host header validation timing (T3):** Should this be bundled as P1 infrastructure (low effort, high value, app-wide) or tracked as a separate security-hardening task?

4. **Mobile decisions layout (T4):** What is the decisions tab's mobile rendering? Full-page list is likely fine, but nav-rail collapse behavior and modal sizing on small viewports need a decision.

5. **Timestamp granularity:** enduser recommends standardizing on the DecisionViewport model (minutes/hours/days). Is this a P2 implementation detail or does it need explicit alignment?
