# Simplifier Stance — Cockpit Memory Tab

## Core Observation

The user's stated pain is: "I want to browse, filter by agent, and delete entries." The proposed scope delivers a full CRUD UI with list/detail split, edit-with-downgrade, state machine replication, and a nav-rail badge. That is significantly more surface than the pain requires.

## Cuts

### 1. Drop Edit action entirely (HIGH confidence: 0.90)

Edit-with-form plus the approved → curated downgrade is the most complex feature proposed. It requires a form component, field validation, content-length enforcement, and a state transition that exists purely to maintain state-machine semantics. The user did not ask for editing — they asked for browsing and deleting. If a memory entry needs editing, the agent curation workflow already handles it. **Defer to P2 or never.**

### 2. Drop the separate Detail view — use expandable rows (HIGH confidence: 0.85)

Content is capped at 1024 characters. That is 1–2 short paragraphs. A separate route/view for this is over-built. An expandable row or inline panel showing rendered content + metadata is faster to build, easier to navigate (no back-button), and sufficient for the data volume. This also eliminates a route, a component, and the detail-level action-button layout.

### 3. Drop the nav-rail pending badge (MEDIUM confidence: 0.75)

There are 2 pending entries out of 103. The badge adds polling or cache-invalidation coupling for a count that is almost always zero. If the user is looking at memory, they open the tab. **Defer until tab infrastructure (#1638) proves the badge pattern for other tabs first.**

### 4. Move all filtering to the client side (HIGH confidence: 0.90)

At 50–500 entries with ≤1KB each, the entire dataset is under 500KB. One `GET /api/memories` returning everything, filtered in React, eliminates backend query parameters, pagination, and filter-state management on the server. The backend becomes trivially simple: one read-all endpoint, one delete endpoint, optionally one approve endpoint.

## Decomposition Pressure

Split into two phases:

**P1 — Browse + Delete (the actual ask)**
- Single backend endpoint: `GET /api/memories` (returns all entries)
- Single mutation endpoint: `DELETE /api/memories/{id}` (hard-delete pending, soft-delete others)
- Frontend: flat table/list with client-side filters (state, category, agent) and text search
- Expandable rows for content + metadata
- Route config entry in #1638 tab system

**P2 — Approve + Polish (earned by usage)**
- `POST /api/memories/{id}/approve` endpoint
- Approve button on curated entries
- Nav-rail pending badge (if the pattern exists from #1638)
- Any remaining state transitions

Edit stays deferred indefinitely — agent curation owns that workflow.

## Boundary Correction

**State machine replication risk is real but over-weighted in the framing.** P1 needs exactly one transition: active → deleted (soft-delete). That is a single field write (`state: deleted`), not a state machine. P2 adds one more: curated → approved. Calling this "state machine enforcement" inflates the perceived complexity. Implement each transition as a standalone guard, not a generalised FSM.

## Dependency Note

This entire feature is blocked on #1638 (tab infrastructure, still in research). Do not design the memory tab's routing, lazy-loading, or nav-rail integration in detail until #1638 lands. Design the data layer and components; let #1638 define the shell.

## Confidence

**0.85** — The four cuts are grounded in the stated pain vs. proposed scope gap. The main uncertainty is whether the user actually wants Approve in P1 (they didn't say so, but it's a natural companion to Delete).
