# Remove DecisionViewport from Sidecar

> **Owning task:** #1648 — P2-04: Remove DecisionViewport from sidecar
> **Date:** 2026-05-20 **Status:** Complete

## 1. Context and Question

With the decisions tab (P2-01, task #1645, now archived) providing a dedicated full-page DR list at `/decisions`, the `DecisionViewport` rendered inside the Shell sidecar is redundant. Task asks: what's involved in removing it, and does `DRStatusIndicator` remain functional independently?

## 2. Sources Studied

| Source | Relevance |
|--------|-----------|
| `serve/cockpit/web/src/Shell.tsx` lines 20, 562, 660 | DecisionViewport import + 2 render sites (mobile/desktop sidecar) |
| `serve/cockpit/web/src/components/DRStatusIndicator.tsx` | Independent component; own state, own popover, own `onItemClick` prop |
| `.owlbear/briefs/draft-cockpit-decisions-tab/brief.md` P2-05 | Brief explicitly scopes this removal |
| `serve/cockpit/web/src/pages/DecisionsPage.tsx` | Replacement: full-page list, no shared dependency on DecisionViewport |

## 3. Analysis

### Removal scope (Shell.tsx)

| Item | Location | Action |
|------|----------|--------|
| Import | Line 20 | Remove `import DecisionViewport from './components/DecisionViewport'` |
| Mobile sidecar render | ~Line 562 | Remove `<DecisionViewport ... />` + surrounding `<PDivider />` |
| Desktop sidecar render | ~Line 660 | Remove `<DecisionViewport ... />` + surrounding `<PDivider />` |

### DRStatusIndicator independence

`DRStatusIndicator` (line 357) receives `pendingDRItems` and `setSelectedDRId` directly from Shell state — no dependency on DecisionViewport. Removal has zero effect on it.

### Test impact

| Test file | Impact |
|-----------|--------|
| `Shell.decision-viewport.test.tsx` | **Delete entirely** — tests sidecar rendering of DecisionViewport |
| `Shell.callbacks.test.tsx` | Remove mock of `DecisionViewport` (line 111) |
| `Shell.cleanup-wiring.test.tsx` | Remove mock (line 39) |
| `Shell.pbanner.test.tsx` | Remove mock (line 31) |
| `PToastSuccess_1624.test.tsx` | Remove mock (line 84) |
| `Shell.tab-routing_1639.test.tsx` | Remove mock (line 65) |
| `DecisionViewport.test.tsx` | **Retain** — tests the component itself (retained per scope) |
| `PdsSimpleSwaps_1634.test.tsx` | **Retain** — tests PDS component usage in DecisionViewport |

### Risk assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Leftover `pendingDR*` variables unused after removal | None — still consumed by DRStatusIndicator, DecisionsPage, and nav badge | N/A |
| Missing import warning | None — removal is clean deletion | Vitest + TypeScript will catch |
| Component file orphaned | Acceptable — brief explicitly retains it for potential reuse | N/A |

## 4. Recommendation

Proceed with removal. Confidence: **0.95**

This is a trivial deletion with no architectural implications. The component file is retained, DRStatusIndicator is independent, and the decisions tab provides the replacement surface. No challenger invocation needed (trivial scope).

Challenge: N/A — trivial removal, no design choice to challenge.

## 5. Follow-up Tasks

Single implementation task at `todo` status (via planner). No T2/T3 triggers — purely mechanical removal (T1).
