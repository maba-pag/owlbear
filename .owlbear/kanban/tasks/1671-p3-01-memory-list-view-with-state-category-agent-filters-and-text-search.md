---
id: 1671
title: 'P3-01: Memory list view with state/category/agent filters and text search'
status: backlog
priority: needed
created: 2026-05-18T17:43:52.849841+02:00
updated: 2026-05-19T10:22:50.585591+02:00
tags:
  - phase-3
  - scope:cockpit-web
  - frontend
parent: 1659
depends_on:
  - 1670
  - 1639
ac:
  - MemoryTab route component fetches GET /api/memories on mount and on window 
    focus, renders entries sorted by state priority 
    (pending→curated→approved→deleted) then created_at ascending; shows loading 
    skeleton during fetch
  - 'Client-side filter controls: state PMultiSelect (default selection: pending+curated+approved),
    category PMultiSelect, scoped-agent dropdown, PInputSearch text search matching
    against title and content fields'
  - Each entry row displays title, category PTag chips, confidence value, 
    color-coded state badge, and scope_agents list
  - 'Empty state handling: shows descriptive message when no entries exist ("No memory
    entries yet") and when active filters return no matches ("No entries match your
    filters" with clear-filters action)'
  - "Parse errors indicator: when API response parse_errors > 0, displays a subtle
    warning (\"N entries couldn't be read\") so the user knows some files are malformed"
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
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
