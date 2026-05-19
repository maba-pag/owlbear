---
id: 1671
title: 'P3-01: Memory list view with state/category/agent filters and text search'
status: in-progress
priority: needed
created: 2026-05-18T17:43:52.849841+02:00
updated: 2026-05-19T12:20:46.170334+02:00
tags:
  - phase-3
  - scope:cockpit-web
  - frontend
parent: 1659
depends_on:
  - 1670
  - 1639
ac:
  - 'MemoryTab (default export from pages/MemoryTab.tsx, lazy-loaded in routeConfig
    at /memories, hasSidecar: false) fetches GET /api/memories on mount and on document
    visibilitychange to visible; renders entries sorted by state priority (pending=0,
    curated=1, approved=2, deleted=3) then created_at asc; shows data-testid="memory-loading"
    while fetch is in-flight'
  - 'MemoryTab filter controls: state PMultiSelect (options: pending/curated/approved/deleted,
    initial: [pending,curated,approved]); category PMultiSelect (populated from distinct
    categories, initial empty=no filter); agent PSelect (populated from distinct scope_agents
    values, initial empty=no filter; entries with empty scope_agents pass agent filter
    regardless); PInputSearch matching title+content case-insensitive substring'
  - 'Filters combine as intersection: entry must satisfy all active filters to appear;
    selecting no options in a multi-select means that filter dimension is inactive
    (shows all)'
  - 'Each visible entry row renders: title as primary text, one PTag per category,
    confidence as decimal (e.g. "0.85"), state badge as PTag with variant (pending=warning,
    curated=info, approved=success, deleted=secondary), scope_agents as comma-joined
    string (empty array renders "All agents")'
  - 'Empty-state: (a) API returns zero entries shows "No memory entries yet"; (b)
    entries exist but filters match nothing shows "No entries match your filters"
    with clear-filters button (data-testid="clear-filters") resetting to AC2 initial
    values'
  - When API response parse_errors > 0, MemoryTab renders element with 
    data-testid="parse-errors-warning" containing text "{N} entries couldn't be 
    read" where N is the parse_errors value
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at: 2026-05-19T12:20:46.170334+02:00
archival_reason:
archival_refs: []
---
Brief: see parent #1659 and `.owlbear/briefs/draft-cockpit-memory-tab/brief.md`

## Scope

Implement the Memory tab list view as a route component that integrates into the tab infrastructure from #1638.

### In Scope
- MemoryTab route component at `/memories`
- Route config entry: path, label "Memory", icon
- Data fetch from GET /api/memories with loading state
- Refetch on tab/window focus
- Client-side filtering: state multi-select, category multi-select, agent dropdown, text search
- Sort: state priority order, then created_at within group
- Entry row rendering: title, category chips, confidence, state badge, scope_agents
- Lazy loaded via React.lazy() + Suspense (per tab infrastructure contract)

### Out of Scope
- Accordion detail view (P3-02)
- Action buttons (P3-02)
- Edit form (P3-02)
- SSE/live updates (deferred)
- Pending count badge on nav-rail (P3-02)

## Technical Context
- Tab infrastructure from #1639 provides route config array and component mounting
- PDS components: PMultiSelect, PTag, PInputSearch (Porsche Design System React)
- State badge colors: use PDS semantic tokens

[[2026-05-19T10:22:42+02:00]]
## Research

See `.owlbear/research/memory-list-view-frontend.md`

### Implementation Approach
- Route: `lazy(() => import('./pages/MemoryTab'))` → `{ path: '/memories', label: 'Memory', icon: 'memory', hasSidecar: false }`
- Data: `usePollingFetch('/api/memories', { paused: true })` + `visibilitychange` refetch (no SSE in V1)
- Filters: client-side; PMultiSelect for state/category, PSelect for agent, PInputSearch for text; ref+event pattern from FilterPanel
- Sort: state priority (pending=0, curated=1, approved=2, deleted=3) then created_at asc
- Rows: PTag for categories + state badge (color-coded), PText for title/confidence/agents
- Empty states: two variants (no data vs filter mismatch with clear button)
- Parse errors: subtle warning when parse_errors > 0
- Loading: div with data-testid="loading-indicator" or PSpinner

[[2026-05-19T10:22:50+02:00]]
Research complete. Straightforward frontend composition — all patterns (route registration, lazy loading, PDS filter components, usePollingFetch, ref-based event binding) already established in codebase. No new dependencies needed. Confidence: 0.88. Research doc: .owlbear/research/memory-list-view-frontend.md. No follow-up tasks required — downstream work already scoped in #1672.

[[2026-05-19T11:00:27+02:00]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single component (MemoryTab) with one concern: display + filter memory list |
| Interface clarity | PASS (after refinement) | AC refined with exact PDS component names, TagVariant mappings, testids, filter defaults, and intersection semantics |
| Dependency correctness | PASS | #1670 (cockpit API) archived, #1639 (tab routing) archived; both completed |
| Module layering | PASS | pages/MemoryTab imports from hooks/ and PDS; follows DecisionsPage leaf-component pattern. No upward imports |
| TDD compliance | PASS | proof_bundle=behavioral routes to test-writer for full TDD |
| KISS/YAGNI | PASS | Composition of existing patterns: routeConfig registration, usePollingFetch, FilterPanel ref+event, PTag variants |
| Premise challenge | PASS | No existing memory UI in cockpit; required by parent #1659 Brief |
| Pattern consistency | PASS | Follows routes.ts lazy loading, KanbanBoardProps interface, FilterPanel PDS patterns, cardVariants TagVariant usage |
| Security surface | PASS | Client-side only; GET request with no user input forwarded to API |
| Single domain | PASS | cockpit-web frontend domain only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| GET /api/memories | Network error / 500 | fetch rejection | Yes (usePollingFetch onError) | Loading state persists or error handling |
| visibilitychange refetch | Tab hidden during fetch | AbortController in hook | Yes | No-op, next visibility triggers refetch |
| Filter with zero matches | No entries pass | N/A | Yes → AC5 empty state (b) | Clear message + clear-filters button |
| parse_errors > 0 | Malformed memory files | N/A | Yes → AC6 warning banner | Subtle warning with count |

### Design Diverge
- Trigger: SKIPPED — single viable approach. Research compared 3 data-fetch options; Option A (usePollingFetch paused + visibilitychange) dominates on reuse and AC match.

### Challenge Results
- Challenger: reconsider (confidence 0.64)
- Findings: (1) AC2/AC4/AC5 fail B1 — feature areas not concrete targets; (2) AC2 missing empty-selection semantics and clear-filters reset definition; (3) AC3/AC5 missing PDS literal contracts (TagVariant values, parse-error component); (4) scope_agents sentinel values (empty array) not addressed in filter semantics
- Architect response: ACCEPTED and REFINED — all valid. Rewrote 5 AC lines into 6 precise lines: named MemoryTab as target in all, enumerated TagVariant per state, specified testids (memory-loading, clear-filters, parse-errors-warning), defined filter defaults and reset behavior, added intersection semantics, specified empty scope_agents pass-through rule.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE (after REFINE)
### Action Taken: Refined 5 AC lines into 6 precise lines addressing all challenger findings. Enumerated PDS TagVariant mappings, added testid anchors, defined filter intersection semantics and defaults, specified scope_agents empty-array behavior. Advanced backlog → todo.

[[2026-05-19T12:13:15+02:00]]
## Test-Writer Notes
- Test file: serve/cockpit/web/src/__tests__/MemoryTab_1671.test.tsx
- Classes: TestFromAC_MemoryTabRoute, TestFromAC_MemoryTabMount, TestFromAC_MemoryTabSort, TestFromAC_MemoryTabFilters, TestFromAC_MemoryTabFilterIntersection, TestFromAC_MemoryTabRowRendering, TestFromAC_MemoryTabEmptyStates, TestFromAC_MemoryTabParseErrors
- Tests per category: happy 27, edge 9, error 0, boundary 3
- Total: 39 tests, all FAIL
- Failure mode: module resolution error — pages/MemoryTab.tsx does not exist; routeConfig lacks /memories entry
- ESLint: clean
