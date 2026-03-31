---
id: 387
title: Design per-agent institutional knowledge system via dedicated memory-mcp server
status: ideation
priority: needed
created: 2026-03-30T20:59:19.0983269+02:00
updated: 2026-03-30T21:18:28.1015015+02:00
tags:
    - research
    - ' scope:agents'
    - ' phase-2'
depends_on:
    - 428
class: standard
---

## Context

Currently, all pipeline agents write lessons-learned to a shared inbox (`/memories/repo/inbox/`), which the curator periodically triages. This system captures pitfalls and process patterns but has three gaps:
1. **Not agent-scoped** — every agent reads the same shared memory; builder sees reviewer-specific insights and vice versa
2. **Not git-tracked** — `/memories/repo/` is VS Code-local; knowledge doesn't travel with the project
3. **No automatic loading** — agents must be told to read memory; there's no "load my knowledge at task start" step
4. **Not cross-project** — knowledge learned in one project doesn't benefit agents working on another project

The goal is per-agent institutional knowledge that accumulates conclusions (not conversations), is structured, automatically served to agents at task start, curated periodically, and accumulates across projects.

**Proposed direction (from user discussion):** A dedicated **memory-mcp server** (separate from knowledge-mcp which handles domain graph/vector search). The MCP server abstracts all complexity — agents interact with simple tools (`get_my_knowledge`, `record_learning`), the server handles multi-dimensional scoping, approval state, cross-project aggregation, and token budgeting behind the scenes.

**Key architecture decisions (from user):**
- **Separate memory-mcp server** — not embedded in knowledge-mcp. Domain knowledge (entities, documents, graph) and agent institutional memory (conclusions, patterns, gotchas) are different concerns.
- **Multi-dimensional scoping model:**
  - General (all agents, all projects) — "uv run python -m pytest is more reliable than uv run pytest"
  - Project-specific (all agents, this project) — "this project uses Protocol-based DI"
  - Agent-specific (one agent, all projects) — "builder: always verify tests FAIL before implementing"
  - Agent+project-specific (one agent, this project) — "builder: packages/knowledge uses bare --cov only"
- **Configurable storage location** — default: all knowledge in central OwlBear installation (`../owlbear/data/memory/`). Configurable per MCP config to: (a) put project-specific scopes in-repo for team collaboration, (b) keep everything in-repo for self-contained projects. This enables team cooperation on a shared repo while keeping personal/general knowledge central.
- **Approval workflow** — agents write "pending" entries, user or curator upgrades to "approved/permanent". Agents may read both (with different weighting or filtering).
- **Agent-transparent interface** — the agent sees simple tools, not the underlying storage structure. The MCP server returns curated, token-budgeted instructions. The agent doesn't know whether a memory came from general, project, or agent-specific scope.
- **Build MCP server, then migrate** — keep current `/memories/repo/` inbox working while building the new server. Switch agents over once the MCP server is ready and tested.

**Related work:**
- deer-flow's memory system uses LLM-based fact extraction with confidence scores, categories, deduplication — see #386 for full analysis
- Current OwlBear memory governance in `copilot-instructions.md`
- Current lessons-learned workflow in `agent-common.instructions.md`
- Subagent nesting research in #228 (memory loading/writing could use subagent patterns)
- Current MCP server patterns in `packages/mcp-kanban/` and `packages/mcp-knowledge/`

## Acceptance Criteria

- [ ] Design the memory-mcp server architecture: storage backend (SQLite? JSON? YAML?), schema for entries (id, scope, agent, category, conclusion, evidence, confidence, approval_state, timestamps), API surface (MCP tools exposed to agents)
- [ ] Design the multi-dimensional scoping model: how entries are tagged with scope (general / project / agent / agent+project), how queries filter by scope, how the server determines "current project" and "current agent" at query time
- [ ] Design the configurable storage location: MCP server config schema for choosing central-OwlBear vs in-repo vs hybrid storage, how project-specific paths are resolved, how team-shared vs personal knowledge is separated
- [ ] Design the agent-facing MCP tool interface: what tools are exposed (e.g., `get_knowledge`, `record_learning`, `list_my_entries`), what parameters each takes, what the response format looks like (structured? prose? token-budgeted?)
- [ ] Design the approval workflow: entry lifecycle (pending -> approved -> permanent, or pending -> rejected/pruned), who can approve (user via CLI, curator agent, or both), how pending vs approved entries are weighted when served to agents
- [ ] Design the auto-loading mechanism: how agents receive their knowledge at task start. Options: (a) agent skill workflow calls MCP tool as step 0, (b) MCP tool injects into system prompt at session start, (c) agent-common instruction tells agents to call the tool
- [ ] Design the write mechanism: how agents record learnings at task end. Should this replace or supplement the current `/memories/repo/inbox/` pattern?
- [ ] Design the curation interface: how the curator reviews pending entries, promotes/prunes, cross-pollinates (copy agent-specific insight to general scope when broadly relevant), and manages token budgets per scope
- [ ] Design the cross-project knowledge aggregation: how the central OwlBear store merges knowledge from multiple projects, handles conflicts, and serves relevant entries when an agent starts work on a different project
- [ ] Assess deer-flow's memory patterns (from #386) for applicable ideas — especially LLM-based fact extraction, confidence scoring, fact deduplication, and debounced update queue
- [ ] Assess migration path from current `/memories/repo/` inbox and established repo memory files to the new system
- [ ] Create a decision request with the proposed architecture for user approval before implementation
- [ ] Create follow-up implementation tasks at ideation
