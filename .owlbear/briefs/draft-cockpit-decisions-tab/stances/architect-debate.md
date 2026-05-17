# Architect Debate Log — Cockpit Decisions Tab

## Critic Cycle 1

### Draft Position Summary

Route-based switching is structurally sound. Three risks: (1) route config array required, (2) CockpitProvider must not become god context, (3) sidecar must be route-configurable. CockpitProvider characterized as "data-only." Sidecar collapse described as reusing `[data-sidecar-collapsed]`. Shell decomposition not explicitly scoped.

### Challenges Received (8 challenges, 4 blind spots)

**C1 (critical) — CockpitProvider is not data-only.** Provider holds selectedDRId, selectedTaskId, selectedTask with fetch orchestration — UI workflow state, not just data. "Data-only" characterization factually wrong.

**C2 (critical) — Route config array oversimplified.** Shell constructs complex kanbanProps (~15 props with callbacks, mutation handlers). A config array handles path/label/icon/component but doesn't address view-specific prop wiring. "Each new tab becomes a single array entry" is unsupported.

**C3 (critical) — Sidecar collapse isn't route-ready.** `[data-sidecar-collapsed]` only zeroes the desktop grid column. Mobile sheet triggers on selectedTaskId regardless of route. Tablet has 48px collapsed mode. Three breakpoints, not one.

**C4 (moderate) — Lazy loading doesn't isolate shell-level decision code.** Shell imports DecisionViewport, ResolveModal, DRStatusIndicator at module level. Lazy decisions page doesn't remove those shell-level imports.

**C5 (moderate) — Provider domain description inaccurate.** Task selection is on-demand (not always-polling). Scan polling domain omitted entirely. Provider has 4 domains, not 3.

**C6 (moderate) — DR polling fetches full items, not just count.** Status-bar badge argument was imprecise — DRStatusIndicator uses title/agent/task_id/age, not body/body_preview. But ResolveModal uses full body at Shell level.

**C7 (moderate) — SSE not evidence for provider centralization.** SSE layer is independent of CockpitProvider. Wrong to cite SSE as justification for provider scope.

**C8 (minor) — "1-5 pending DRs" is an operational observation, not a code constraint.** Code doesn't cap DR count.

**Blind spots:** Scan/repair domain omitted from provider analysis. Deep-link semantics for selectedTaskId/selectedDRId not addressed. Two-tier navigation (nav-rail + sidecar tabs) not explicitly modeled. Mobile auto-select is route-sensitive.

### Response

All three critical challenges accepted. Revised stance:

- **C1:** Dropped "data-only" characterization. Acknowledged 4 provider domains including UI workflow state.
- **C2:** Acknowledged Shell is a monolith. Config array solves nav-rail/route dispatch but not view-specific orchestration. Introduced Shell decomposition as prerequisite.
- **C3:** Expanded sidecar treatment to all 3 breakpoints. `[data-sidecar-collapsed]` is insufficient. Need route-aware grid + DOM suppression.
- **C4:** Accepted. Shell-level decision imports remain eager by design (serve Shell surfaces). Lazy boundary is at route-page components.
- **C5:** Accepted. Corrected to 4 domains. Task selection is on-demand, not polling.
- **C6:** Partially accepted. DRStatusIndicator uses subset of fields, but ResolveModal at Shell level uses full body. Full payload is justified.
- **C7:** Accepted. Dropped SSE as justification. Used actual Shell surface consumers as the argument.
- **C8:** Accepted as imprecise. Reframed as "typical volumes" rather than hard limit.

All blind spots incorporated.

---

## Critic Cycle 2

### Revised Position Summary

Route-based switching correct. Shell is a monolith that must be decomposed. CockpitProvider has 4 domains with mixed concerns but stays for P1/P2 with explicit boundary. Sidecar needs route-awareness at all 3 breakpoints. Shell decomposition, F10 dedup, and 3-breakpoint sidecar all pulled into P1 scope.

### Challenges Received (6 challenges, 3 blind spots)

**C1 (critical) — P1 scope overloaded.** Brief locks P1 to tab-shell + skeleton decisions page. Shell decomposition, 3-breakpoint sidecar cleanup, and F10 dedup collapse P1 back into mixed infrastructure + refactor work. Violates D5 decomposition intent.

**C2 (critical) — ResolveModal ownership contradictory.** Stance says Shell owns cross-cutting ResolveModal AND decisions page renders its own modal. One global selectedDRId chain, but two implied modal instances. Ownership ambiguous.

**C3 (critical) — Task selection doesn't serve Shell surfaces.** Only serves kanban sidecar. On non-kanban routes, it's hidden route-specific state doing work behind the scenes. "All four domains serve Shell-level surfaces" is wrong.

**C4 (moderate) — Shell decomposition understated.** selectedTaskSubtab, tab-change wiring, validation/banner state, sidecar collapse state all omitted from decomposition scope.

**C5 (moderate) — Sidecar is not just a grid problem.** Aside DOM, focusable controls, collapse button, test contracts all need addressing. Not just CSS grid template changes.

**C6 (moderate) — Full DR payload at Shell level overstated.** DRStatusIndicator uses only title/agent/task_id/age. Full body only needed for ResolveModal.

**Blind spots:** Existing test contracts assert sidecar as persistent Shell region. "URL is source of truth" only covers route, not within-view state (selectedDRId, selectedTaskId, selectedTaskSubtab). DRStatusIndicator fate unresolved per research Q3.

### Response

**C1:** Accepted — most impactful challenge. Revised to scope Shell changes incrementally: P1 gets minimal route-conditional rendering (not full decomposition). P2 evaluates KanbanView extraction if needed. Post-P2 justifies full extraction when third route arrives. F10 dedup scoped to sidecar conditioning work (needed to avoid maintaining route-conditional logic in two places), not a separate cleanup initiative.

**C2:** Accepted and resolved. Single global ResolveModal at Shell level. Both DRStatusIndicator and decisions page set selectedDRId via CockpitProvider → same modal instance. No second modal. Explicit in final stance.

**C3:** Accepted. Task selection is the exception — serves only kanban sidecar, not Shell-level surfaces. Acknowledged that on non-kanban routes it's inert (no fetches triggered) but architecturally misplaced. Left in CockpitProvider for P1 pragmatism, flagged for eventual extraction.

**C4:** Partially accepted. Full inventory of Shell-owned kanban state acknowledged. But the stance now explicitly defers full extraction, so the incomplete inventory is bounded by the incremental decomposition approach.

**C5:** Accepted. Expanded sidecar treatment to include aside DOM removal (not just visual hiding), focusable control suppression, and test contract updates.

**C6:** Partially accepted. DRStatusIndicator uses a subset, but ResolveModal (Shell-level) uses full body. Net: full payload is justified for ResolveModal, not DRStatusIndicator. Revised to be precise about which component needs what.

**Blind spots:** Test contract updates added to warnings. URL-as-truth clarified as route-level only (correct — within-view state in React state is the right pattern). DRStatusIndicator fate explicitly deferred per research Q3.

### Position Stability

Core positions survived both cycles:
- Route-based switching: unchallenged
- Shell needs decomposition: accepted, scope recalibrated
- CockpitProvider boundary: refined (task selection is the exception)
- Sidecar route-awareness: expanded from CSS-only to full DOM/responsive treatment
- ResolveModal single ownership: resolved from ambiguous to explicit

Major revisions from Critic pressure:
- P1 scope pulled back from full decomposition to incremental conditioning
- ResolveModal ownership made unambiguous (one instance, one state source)
- Task selection acknowledged as kanban-specific, not cross-cutting
- Sidecar treatment expanded beyond grid-template changes

Confidence moved from initial 0.82 → post-C1 0.78 → final 0.80 (recovered after resolving ResolveModal ownership and P1 scope).
