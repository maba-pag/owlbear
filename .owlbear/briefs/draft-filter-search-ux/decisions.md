# Decisions — Filter/Search UX (Task 1232)

_Append-only. Chosen and rejected options with rationale._

## D1 — 2026-05-01 — Project Type

**Decision:** `existing-feature/refactor` — pure frontend. All data already
client-side in `useBoard`. No new endpoints, no model changes.

Note: `/api/tasks` already supports `?status=`, `?priority=`, `?tag=`, `?blocked=`
server-side filter params — but client-side filtering is correct for the board view
(instant, no round-trip, polling keeps data fresh).

---

## D2 — 2026-05-01 — Investment Tier

**Decision:** Tool tier. Standard M2, selective panel, full Brief.

---

## D3 — 2026-05-01 — M1/M2 Decisions

| Dimension | Decision | Rationale |
|-----------|----------|-----------|
| Filter combinator | AND across all dimensions | All active filters must match simultaneously |
| Tag filter | Multi-select, AND (task must have all selected tags) | Multi-valued field; AND is consistent |
| Priority filter | Single-select dropdown | Task has one priority; multi-select = implicit OR = inconsistent |
| Blocked filter | Toggle (show only blocked) | Boolean field |
| Text search | Substring match on title (case-insensitive) | Standard |
| Empty columns | Keep visible with "0 tasks" indicator | Preserves board structure |
| Persistence | None — resets on page load | Simplest; no localStorage complexity |
| UI shape | Expandable filter panel with toggle button | Saves space; filter not always needed |
| Active filter display | Chips row + task count update | Both communicates state clearly |
| Filter panel location | Inside `KanbanBoard` (above columns) | Self-contained; no upward state needed |

---

## D4 — 2026-05-01 — M4 Decisions (Mediator)

| Dimension | Decision | Rationale |
|-----------|----------|-----------|
| Result count | Adopt "142 / 1,247 tasks" adjacent to toggle | Eliminates filtered-view blindness (top UX risk); trivial cost |
| Tag selector | PDS multi-select with type-to-filter | Handles 30+ tags natively; PDS 3.34 has p-multi-select |
| Column CSS | Flexbox layout (panel + columns in flex-column, columns get flex:1 + overflow) | No magic numbers, adapts to panel presence |
| Accessibility | aria-live on result count, aria-expanded on toggle, focus management, explicit labels | Uncontested additive requirement from end-user panel |
| Horizontal panel layout | Controls in 1–2 rows | Columns stay visible when panel expanded |
| Cancel interactions on filter | Filter change cancels active drag, dismisses context menu | Prevents stale state from removed cards |
| Filter logic extraction | Pure `filterTasks()` in `lib/filterTasks.ts` | Unit-testable without React |
| Component structure | Controlled `FilterPanel` component, no custom hook | YAGNI — inline state sufficient |
| Tags source | Derived from full (unfiltered) task set | Prevents AND-filter dead-ends |

**Rejected:**
- Custom `useFilterState` hook — YAGNI, file-splitting without encapsulation benefit
- Badge-only communication — fails "forgot I filtered 3 hours ago" scenario
- Vertical panel layout — obscures column tops
- Tags from filtered set — creates dead-end where selected tags vanish

---

## D5 — 2026-05-01 — Artifact Reconciliation

**D3 inconsistency:** D3 listed "Chips row + task count" for active filter display, but context.md (later, confirmed artifact) locks "badge only." Reconciled: **badge + result count** (adopting panel recommendation). No chips row.

---

---

## D6 — 2026-05-01 — Critic Validation (O15)

| Finding | Classification | Resolution |
|---------|---------------|------------|
| Drag cancellation overclaim | minor | Board-side "cancel" (clear dragSourceStatus) is sufficient; browser gesture irrelevant |
| Vertical layout not converged | minor | M4 locked flexbox; Column's hardcoded height is what gets replaced |
| Panel state ownership | **material** → resolved | **Board owns panelOpen.** Enables aria-expanded, focus management. |
| Polling + tag disappearance | **material** → resolved | **Keep selected tag active.** Filter persists; user sees 0 results and clears manually. |
| PDS availability | nonsense | Verified available. Locked in M4. |
| React Compiler perf | minor | Pre-existing render behavior, not worsened by filters |
| aria-live scope | clarified | **User-initiated filter changes only.** Polling-driven count drift is silent. |

_All decisions locked. Proceeding to Brief._
