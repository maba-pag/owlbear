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

_Open decisions delegated to mediator — see research-notes.md._
