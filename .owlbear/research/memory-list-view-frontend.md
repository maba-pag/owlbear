# Memory List View — Frontend Implementation Research

> **Owning task:** #1671 — P3-01: Memory list view with state/category/agent filters and text search
> **Date:** 2026-05-19 **Status:** Complete

## 1. Context and Question

Task #1671 requires a React route component at `/memories` that fetches memory entries from the cockpit API, renders them in a filterable list, and integrates with the tab infrastructure from #1639. The question: what patterns, components, and architecture to use for implementation given the existing codebase conventions.

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `serve/cockpit/web/src/routes.ts` | Codebase | 1.0 — exact route registration pattern |
| `serve/cockpit/web/src/hooks/usePollingFetch.ts` | Codebase | 0.9 — data fetching hook |
| `serve/cockpit/web/src/components/FilterPanel.tsx` | Codebase | 0.9 — PDS filter component patterns |
| `serve/cockpit/web/src/pages/DecisionsPage.tsx` | Codebase | 0.8 — lazy-loaded page skeleton pattern |
| `serve/cockpit/src/owlbear_cockpit/routes/memory.py` | Codebase | 1.0 — API response shape |
| `serve/memory/src/owlbear_memory/models.py` | Codebase | 1.0 — domain models (categories, states) |
| `.owlbear/briefs/draft-cockpit-memory-tab/brief.md` | Brief | 0.9 — design spec |
| PDS v4 docs (designsystem.porsche.com) | External | 0.8 — PMultiSelect/PTag usage guidance |

## 3. Analysis

### 3.1 Route Integration

Pattern is established in `routes.ts`:
```typescript
const MemoryTab = lazy(() => import('./pages/MemoryTab'))
// Add entry: { path: '/memories', label: 'Memory', icon: 'memory', component: MemoryTab, hasSidecar: false }
```
Component receives `KanbanBoardProps` for interface consistency (even if unused).

### 3.2 Data Fetching — Options

| Approach | Pros | Cons | Fit |
|----------|------|------|-----|
| **A: `usePollingFetch` + manual focus refetch** | Reuses existing hook; polling provides freshness | Needs custom `visibilitychange` listener since hook lacks focus-refetch | 0.85 |
| **B: Custom `useMemories` hook** | Can bundle fetch + focus + filter state | New hook, but small; avoids polling overhead when not needed | 0.80 |
| **C: Polling only (no focus refetch)** | Simplest | AC explicitly requires "refetch on window focus" | ❌ |

**Recommendation: Option A** — `usePollingFetch('/api/memories', { paused: true })` with `refetch()` called on `visibilitychange`. Set `paused: true` because no SSE channel exists for memory (brief says "no SSE in V1"). Use a short `useEffect` for the focus listener.

### 3.3 Client-Side Filtering

FilterPanel patterns show PDS web components require ref-based event binding:
- `PMultiSelect` fires `update` custom event with `detail.value: string[]`
- `PInputSearch` fires `input`/`change` with string value
- `PSelect` fires `update` with `detail.value: string`

Filter state shape:
```typescript
interface MemoryFilter {
  states: MemoryState[]     // default: ['pending', 'curated', 'approved']
  categories: string[]      // default: [] (all)
  agent: string             // default: '' (all)
  text: string              // default: ''
}
```

Client-side filter: entries are small (≤1024 chars each), no pagination needed.

### 3.4 Sort Order

State priority map per AC: pending=0, curated=1, approved=2, deleted=3. Within same state: `created_at` ascending.

### 3.5 PDS Components for Entry Rows

| Field | Component | Notes |
|-------|-----------|-------|
| Category chips | `PTag` | One per category, compact size |
| State badge | `PTag` with color prop | Color-coded: pending=notification, curated=primary, approved=success, deleted=neutral |
| Confidence | Plain text or `PText` | Format: "0.85" |
| Title | `PText` or heading | Primary label |
| scope_agents | `PText` secondary | Comma-joined list |

### 3.6 Empty States

Two distinct cases per AC:
1. No entries at all → "No memory entries yet"
2. Filters return nothing → "No entries match your filters" + clear-filters button (`PButton variant="secondary"`)

### 3.7 Parse Errors Indicator

API returns `parse_errors: number`. When > 0, show a subtle inline warning (PDS `PBanner` with `state="warning"` or a `PText` with warning color): "N entries couldn't be read".

### 3.8 Loading State

Consistent with KanbanBoard: `<div data-testid="loading-indicator">Loading…</div>` or `PSpinner` with aria-label.

## 4. Recommendation

**Confidence: 0.88** — Straightforward composition of existing patterns.

Implementation approach:
1. Create `pages/MemoryTab.tsx` with data fetch via `usePollingFetch` (paused) + visibilitychange refetch
2. Client-side filter state managed in component; PDS controls via refs + event listeners (matching FilterPanel pattern)
3. Entry rows as a presentational list; PTag for categories/state badges
4. Register route in `routes.ts` with lazy loading
5. No new dependencies needed — all PDS components already available in the project

**Challenge: FALLBACK — trivial composition task, no architectural decision required.**

### Testing Strategy

- Unit tests for filter logic (pure function: entries × filter → filtered entries)
- Component tests: render with mocked fetch, verify loading/empty/list states
- Integration test: route renders within Shell Suspense boundary

## 5. Follow-up Tasks

No additional follow-up tasks needed — task #1671 is already well-scoped with clear AC. The downstream task #1672 covers accordion detail and actions.
