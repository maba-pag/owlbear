# Decisions List Page with Empty State

> **Owning task:** #1645 — P2-01: Decisions list page with empty state
> **Date:** 2026-05-19 **Status:** Complete

## 1. Context and Question

The DecisionsPage skeleton (from P1-01) needs to be replaced with a full-width single-column list of pending decision requests. Data source: `useDRState()` from CockpitProvider. The sidecar's `DecisionViewport.tsx` has existing rendering logic to draw from.

**Question:** What implementation patterns and structures should the builder use?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `serve/cockpit/web/src/components/DecisionViewport.tsx` | Codebase | 0.9 — same data, same fields, `formatAge()` utility |
| 2 | `serve/cockpit/web/src/pages/MemoryTab.tsx` | Codebase | 0.8 — reference for full-page tab component pattern |
| 3 | `serve/cockpit/web/src/hooks/CockpitProvider.tsx` | Codebase | 0.9 — `useDRState()` interface contract |
| 4 | `serve/cockpit/web/src/hooks/usePendingDRs.ts` | Codebase | 0.9 — `PendingDR` type definition |
| 5 | `.owlbear/briefs/draft-cockpit-decisions-tab/brief.md` | Brief | 1.0 — authoritative design spec |

## 3. Analysis

### Data Flow

```
CockpitProvider → usePendingDRs() → useDRState() → DecisionsPage
                                                    ↓
                                              items: PendingDR[]
                                              setSelectedDRId: (id) => void
```

### PendingDR Fields Available vs Required

| Field | In `PendingDR` | Required by AC | Notes |
|-------|----------------|----------------|-------|
| `agent` | ✓ | ✓ | Direct render |
| `request_type` | ✓ | ✓ | Direct render |
| `created` | ✓ | ✓ (as relative age) | Use `formatAge()` from DecisionViewport |
| `task_id` | ✓ | ✓ | Direct render |
| `body_preview` | ✓ | ✓ (truncated 200 chars) | API provides field; enforce 200-char limit in component |
| `id` | ✓ | — | For key prop and `setSelectedDRId` |

### Implementation Pattern: List Item

From `DecisionViewport.tsx`, each item renders: agent, request_type, age, task_id, body_preview. The tab version needs:
- Generous vertical spacing (brief: "not dense rows")
- Full-page width (brief: "full-width single-column")
- Clickable region with `data-testid` (AC3)

### Implementation Pattern: Empty State

DecisionViewport uses `<PText data-testid="decision-empty">No pending decision requests.</PText>`. The tab version needs a dedicated empty-state element with `data-testid` (AC2).

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| `formatAge()` reuse | Extract to shared util or inline in DecisionsPage | DRY — same function in DecisionViewport; shared util preferred |
| Click handler | Calls `setSelectedDRId(item.id)` | Wires to Shell-level ResolveModal (P2-02 will integrate) |
| 200-char truncation | `body_preview.slice(0, 200)` in render | API field may exceed; component enforces AC limit |
| Spacing | CSS `gap` or `margin-bottom` on list items | Modern CSS gap preferred for `<ul>` or flexbox column |
| PDS usage | `PText` for content, semantic `<article>` per item | Matches DecisionViewport pattern |

## 4. Recommendation

**Confidence: 0.90** — Straightforward component task with clear existing patterns.

The builder should:
1. Replace the skeleton with a component that calls `useDRState()` directly
2. Extract `formatAge()` into a shared util (e.g., `src/utils/formatAge.ts`) or copy inline
3. Render items as `<article>` elements within a single-column flex layout
4. Use `data-testid="decision-item-{id}"` per AC3
5. Empty state: a styled element with `data-testid` and "nothing to decide" messaging

**Challenge:** Skipped — T1 Autonomous task, no architecture decisions, confidence > 0.85.

## 5. Follow-up Tasks

No follow-up research tasks needed. The task itself (#1645) is ready for `todo` status — AC is well-specified, implementation approach is clear, all data sources are available and verified.

**Tier: T1 — Autonomous.** Standard frontend component build from existing hook data.
