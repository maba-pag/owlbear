# First-Principles Stance — Cockpit Memory Tab

## Irreducible Core

The user's actual need reduces to two claims:

1. **Visibility.** "I want to see what agents remember" — read-only rendering of memory entries.
2. **Pruning.** "…and delete some" — remove entries that shouldn't persist.

Everything else in the proposal is inherited structure from the MCP tool surface, not from user need.

## Assumptions Challenged

### A1 — Edit and Approve belong in the human UI

**Challenge: Neither was in the stated need; both are agent-workflow actions smuggled into the user surface.**

The MCP tool `approve_memory` exists so agents promote entries through a curation pipeline. The MCP tool `curate_memory` exists so agents refine content. The user asked to browse and delete. Adding Edit (with the approved→curated downgrade rule) and Approve (curated→approved) imports the full agent lifecycle into a human UI. This triples the mutation surface (delete-only → delete + approve + edit) and forces the cockpit to replicate the complete state machine.

**Test:** Would the user's stated pain ("memory is a black box") persist if Edit and Approve were absent? No. They'd have visibility and pruning. Approve and Edit are quality-of-life additions at best, and their cost (state machine duplication, form validation, content editing UI) is disproportionate to a V1 goal of "see and clean up."

**Recommendation:** Defer Edit and Approve to the same "deferred extensions" list that already holds bulk ops and creation. If they prove necessary, they earn their own scope.

### A2 — The cockpit must own mutation logic

**Challenge: The architecture constraint ("no MCP imports") is being read as "no MCP communication," but those are different things.**

The proposal assumes the cockpit must independently read memory files, parse YAML frontmatter, validate models, enforce state transitions, and write files — replicating ~150 lines of engine + tools code. The architecture rule exists to prevent compile-time coupling between `serve/cockpit` and `serve/mcp-memory`. But the cockpit could call the running MCP server as a client (JSON-RPC over stdio or HTTP) without importing its packages. The kanban board already lives in a separate MCP server that the cockpit reads directly — but kanban's schema is stable and old. Memory's schema is younger and the state machine is still being refined (the `_drop_legacy_approval_state` validator is evidence of recent evolution).

If delete is the only mutation (per A1), the duplication shrinks to two rules: pending → hard-delete, non-pending → soft-delete with `state: deleted`. That's trivial to keep in sync. But if Edit and Approve stay in scope, the duplication surface includes the full transition map, content validation, enum matching, and downgrade logic — and drift becomes a real maintenance cost.

**Test:** Would a read-only cockpit + MCP-client mutations satisfy the need? Yes, if the MCP server is running when the cockpit is. Since the cockpit already assumes the MCP servers are up (it reads kanban files that MCP manages), this is not a new assumption.

**Recommendation:** If the team insists on direct file I/O for mutations, limit mutations to delete-only. The state machine duplication risk is proportional to mutation surface, not to read surface.

### A3 — Filtering UI is necessary at 103 entries

**Challenge: The filtering proposal (multi-select state, multi-select category, agent dropdown, text search) is designed for a scale the system hasn't reached.**

103 entries. 14 active (non-deleted). The framing says "expected to grow to 50–500" but the system has been running long enough to produce 103 entries and only 14 are active. A flat list sorted by state, with browser-native Ctrl+F, handles this scale. Multi-select filters are significant frontend effort (PDS filter components, URL state management, API query parameters) for a list that fits on 2–3 screens.

**Test:** At what entry count does filtering become essential rather than nice-to-have? Probably 200+ active entries. The current active count is ~14.

**Recommendation:** Ship V1 with state-grouped rendering (pending first, then curated, then approved, then deleted — collapsible) and native text search. Add filter controls when active entry count exceeds a threshold that makes scrolling painful.

### A4 — Detail view is a separate route

**Challenge: With content capped at 1024 characters, an expand-in-place pattern may be sufficient.**

The proposal assumes a list→detail navigation pattern (two routes). Memory content is constrained to ≤1024 characters — roughly one paragraph. Metadata is ~6 fields. This doesn't warrant a full-page detail view. An expandable row or side panel showing content + metadata eliminates a route, a loading state, and back-navigation UX.

**Test:** Is there any memory content that requires a dedicated page to render? At 1024 chars max, no.

### A5 — The tab infrastructure dependency is load-bearing

**Challenge: Is waiting for #1638 necessary, or is it inherited sequencing?**

The framing treats the tab infrastructure (#1638, still in research) as a hard prerequisite. But the memory tab's value — visibility into memory entries — doesn't require a tab system. It could ship as a standalone route (`/memories`) and be moved into the tab system later when #1638 lands. The tab migration is additive (add a route config entry), not structural.

**Conclusion:** The dependency is scheduling convenience, not architectural necessity.

## What the Framing Gets Right

- **Direct file reading for the read path.** The cockpit reading `.owlbear/memory/*.md` directly (same as kanban tasks) is the right call. It avoids runtime coupling and the read-side parsing is straightforward YAML frontmatter.
- **Desktop-only scope.** Correct for an internal tool.
- **Deferring creation.** Creating memory entries from the cockpit would require the full MCP tool surface. Right to defer.

## Confidence

**0.82** — The core need (visibility + delete) is clear and well-scoped. The proposal inflates it with agent-workflow actions that the user didn't request. The state machine duplication risk is real but self-inflicted by mutation scope. Shrink the mutation surface and the risk largely disappears.

## Summary

The irreducible product is: **a read-only list of memory entries, grouped by state, with delete capability.** The proposal's Edit, Approve, filtering UI, and detail-view routing are inherited from the MCP tool surface and anticipated scale rather than earned by current user need. Ship the minimal surface; let usage reveal what's actually missing.
