# End User Stance — Cockpit Decisions Tab

## User Experience Stance

The list-plus-modal pattern (D7) is workable for V1, but the design must actively mitigate three concrete UX regressions: modal state loss on close, loss of concurrent task context during resolution, and sparse-page feel with only 1–5 items. These are not hypothetical — they are measurable downgrades from the current sidecar experience. The tab should deliver a genuine improvement in decision handling, not merely prove the tab shell works.

## Usability Reasoning

### 1. List density: generous items, not dense rows

With 1–5 pending DRs, a compact single-column list will look empty and underserved. Each list item should use generous vertical space: metadata line (agent, type, age, task ID), the full 200-char backend preview, and clear visual separation. The page should feel like a focused decision inbox, not a sparse table. The full DR body belongs in the modal (locked pattern) — the list's job is triage and prioritization.

### 2. Modal is acceptable but has a real cost — flag state loss

The ResolveModal supports read-and-leave behavior (cancel/escape close without mutation, submit requires explicit response selection). The pattern works for V1.

**Critical risk:** closing the modal discards in-progress response and notes — local state is lost on unmount. A user who reads a DR, starts drafting a response, then closes the modal to check something loses their work. This is the primary UX cost of the modal pattern and should be flagged as a known limitation for V1 with a clear path to fix (persist draft state, or evolve to inline detail).

**Secondary trade-off:** the current sidecar shows DR list alongside task Detail and Activity tabs. Moving resolution to a separate tab behind a modal removes concurrent access to the blocked task's context. This is a genuine regression from the sidecar workflow. The modal focuses the resolution act but narrows the information available during it.

### 3. Badge: count > 0 only, hidden at zero

The nav-rail badge should render only when pending count > 0 with attention styling. Hide it at zero — a "0" badge on a navigation tab is noise in standard UI convention. The status-bar DRStatusIndicator is a different surface serving a different purpose (persistent system-health signal) and can continue rendering at all states. Acknowledged tension: the current DRStatusIndicator is also count-bearing and interactive, so the distinction is a design choice, not a self-evident one.

### 4. Relative timestamps — standardize the granularity

Use relative timestamps throughout the decisions list. The current surfaces already disagree on granularity (DecisionViewport uses minutes/hours/days; DRStatusIndicator collapses to hours). The decisions tab is an opportunity to standardize: pick one granularity model and apply it consistently. Recommend the DecisionViewport model (minutes for <1h, hours for <24h, days beyond) as it gives the most useful precision for the typical DR lifecycle.

### 5. Never hide the tab — design the empty state

Show a clear "No pending decisions" empty state. Do not hide the tab when count = 0. Persistent tab presence signals the capability exists. Hiding creates a discoverability problem: the user first encounters the tab under decision pressure, which is the worst time to learn new UI. The empty state also serves as orientation for first-time exploration.

### 6. Sidecar should retain a minimal DR presence on the kanban view

Task cards already surface "Decision pending" indicators. The user's current flow is: see blocked task → sidecar shows DR details → resolve. Removing all DR presence from the kanban-view sidecar breaks this flow. The sidecar should retain at minimum a compact DR summary or a navigation affordance pointing to the decisions tab.

However, the sidecar is already collapsible and the status-bar indicator provides an alternative path, so this is a degradation rather than a dead end. The strength of the recommendation depends on how many users rely on the sidecar-as-primary-path versus the status-bar indicator.

On the decisions tab itself, the sidecar can be repurposed or hidden — the tab IS the decisions workspace.

### 7. Tabs are task-oriented workspaces with shared concerns

Kanban = "manage work." Decisions = "unblock work." These are separate workspaces linked by blocked tasks. The nav-rail should use clear labels and workspace-level icons. Even though the kanban-side cross-nav sender is out of V1 scope, the design should not foreclose it — keep the sidecar DR affordances that a future sender would leverage.

### 8. V1 must genuinely improve decision handling

This tab is the pathfinder for multi-tab infrastructure, but that's an engineering concern. From the user's perspective, V1 must deliver a real improvement over the current sidecar-embedded experience: decisions elevated to first-class status with a dedicated workspace, better scanability, and focused resolution. If V1 merely replicates the sidecar content on a full page behind a route, the user gains nothing and loses the in-context convenience. The bar is: "I prefer resolving DRs from the tab over the sidecar."

## Key Trade-offs

| Trade-off | Current (sidecar) | Proposed (tab + modal) | Net |
|-----------|-------------------|----------------------|-----|
| Focus | DRs compete with task detail in sidecar | Dedicated workspace, full attention | Gain |
| Context during resolution | Task detail visible alongside DR | Modal overlays everything; task context lost | Loss |
| Draft persistence | Same modal, same state loss | Same modal, same state loss | Neutral |
| Scanability | Compact list in narrow sidecar column | Full-page list, generous item rendering | Gain |
| Navigation cost | Zero (already visible in sidecar) | Tab switch required from kanban | Loss |
| Discoverability | Embedded in sidecar, easy to miss | Own tab, persistent in nav-rail | Gain |

## Warnings

1. **Modal state loss is the biggest V1 risk.** Users who close the modal to check something will lose in-progress responses. This will cause frustration proportional to DR complexity. Track and fix early.
2. **Live queue mutation during interaction.** SSE events can change the DR list while the user has the modal open or is scanning the list. The design must handle DR disappearance gracefully (resolved by another agent or process) — don't show stale items, don't crash the modal if its DR vanishes.
3. **Mobile viewport is unaddressed.** The current shell has explicit mobile logic (sheet-based sidecar, stacked layout). The list-plus-modal pattern and tab-switching behavior need mobile-specific consideration — a full-page list on a phone is fine, but the nav-rail behavior and modal sizing need attention.
4. **Removing sidecar DRs without a cross-nav sender leaves a gap.** Task cards will say "Decision pending" but the nearby action surface (sidecar) won't show DRs. The status-bar indicator partially covers this, but it's a weaker affordance than the sidecar's direct list.

## Confidence

0.72 — The list-plus-modal pattern is sound for V1 given the low item count and existing component reuse. Key risks (state loss, context regression, sidecar gap) are real but bounded and addressable. The design works if the warnings are tracked as known limitations with clear follow-up paths.
