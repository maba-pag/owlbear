# Context — Cockpit Memory Tab

## Problem (M1 — locked)

The memory system (ob-memory MCP) stores agent institutional knowledge as markdown files with YAML frontmatter in `.owlbear/memory/`, managed through a pending → curated → approved state machine. **103 entries exist** (56 curated, 30 approved, 15 deleted, 2 pending). The only interfaces are MCP tools (agent-driven) and agent curation prompts. There is no human-readable surface for browsing, reviewing, or acting on memory entries.

**Core pain:** The user wants a general overview of memories, the ability to filter by agent, and the ability to delete entries. Memory without visibility is a black box — the user cannot see or curate what agents "remember" without invoking MCP tools.

**Project type:** existing-feature/refactor — adding a new tab to an existing cockpit using tab infrastructure being built now (#1638).

## Current State

- **Memory engine**: `serve/mcp-memory/` — reads/writes markdown files from `store/memory/entries/`
- **Memory schema**: id, title, categories (enum), confidence (0.7–1.0), state, content (≤1024 chars), scope_agents, source_agent, timestamps
- **State machine**: pending → curated (when scoped) → approved (explicit promotion) → deleted (soft-delete for curated/approved, hard-delete for pending)
- **Cockpit**: FastAPI backend (`serve/cockpit/`) + React 19 frontend (`serve/cockpit/web/`). Uses Porsche Design System (PDS).
- **Tab system (in progress)**: #1638 builds multi-tab infrastructure — route config array, nav-rail, React Router, lazy loading, route-conditional sidecar. Memory tab explicitly named as planned follow-on. Adding a tab = adding a route config entry + component.
- **Architecture constraint**: cockpit cannot import MCP server packages. Must read memory files from disk directly (same pattern as kanban task files).
- **Scale expectation**: hundreds of entries (50–500) over time. Currently 14.

## Outcomes (M2 — locked)

**Target:** A polished Memory tab in the cockpit (plugging into #1638 route config) providing full visibility and control over agent institutional memory.

- **List view**: all entries sorted by state (pending first → curated → approved → deleted). Each row: title, categories (chips/badges), confidence, state badge (color-coded), scope_agents. Filter controls: state (multi-select), category (multi-select), scoped agent (dropdown). Text search across title and content.
- **Detail view**: full content (rendered markdown), all metadata (id, source_agent, scope_agents, categories, confidence, state, timestamps). Action buttons based on state.
- **Actions**: Approve (curated → approved), Edit (opens edit form, downgrades approved → curated), Delete (pending = hard delete from disk, curated/approved = soft delete to deleted state).
- **Backend**: new `/api/memories` routes reading `.owlbear/memory/` directly. State machine enforcement matching MCP tool behavior.
- **Integration**: route config entry, lazy-loaded, nav-rail button with pending count badge.
- **Desktop-only** (same as rest of cockpit).

**Deferred extensions:** bulk approve/delete, memory diff view, memory creation from cockpit, link memories to tasks, memory statistics dashboard.

## Active Tensions

- The tab infrastructure (#1638) is still in research status. Memory tab depends on that landing first.
- State machine enforcement: cockpit backend must replicate the engine's state transition logic without importing from mcp-memory. Risk of logic drift.
- Memory files live at `.owlbear/memory/` — cockpit needs a reader that parses YAML frontmatter + markdown body (similar to how kanban reads task files).
