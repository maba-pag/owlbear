---
id: 387
title: Design per-agent institutional knowledge system via dedicated memory-mcp 
  server
status: archived
priority: medium
created: 2026-03-30 20:59:19.098327+02:00
updated: 2026-04-02 15:10:49.216033+02:00
started: 2026-04-02 15:10:48.818328+02:00
completed: 2026-04-02 15:10:48.818328+02:00
tags:
- research
- ' scope:agents'
- ' phase-2'
depends_on:
- 428
class: standard
archival_reason: completed
archival_refs: []
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

[[2026-04-02]] Thu 05:42
## Research
Doc: docs/research/memory-mcp-server-design.md (178 lines)
DR: docs/decisions/resolved/387-memory-mcp-architecture.md (approved: full architecture)

All 13 AC items addressed:
- Storage: SQLite + WAL (sec 3A)
- Schema: 12-field MemoryEntry (sec 3B)
- Scoping: 4D nullable agent x project matrix (sec 3C)
- Storage config: single-path, env var OWLBEAR_MEMORY_DB_PATH (sec 3D)
- Tools: get_knowledge, record_learning, list_entries, mark_for_deletion (sec 3E)
- Approval: pending/approved/deleted, user-only permanent delete (sec 3F)
- Auto-load: agent-common Step 0 calls get_knowledge (sec 3G)
- Write: record_learning at task end, dual-write during migration (sec 3H)
- Curation: curator uses list_entries + mark_for_deletion + cross-pollinate (sec 3I)
- Cross-project: single central DB, scope_project column (sec 3J)
- Deer-flow: patterns 1,2,4(custom),6 adopted per DR 428 (sec 3K)
- Migration: 5-phase gradual cutover (sec 3L)
- Follow-ups: #524 (scaffold), #525 (tools), #526 (agent-common), #527 (migration), #528 (curator design), #529 (set_approval_state), #530 (curator update), #531 (CLI wrapper)

Challenge: reconsider, revised confidence .78
Note: #499 is redundant (blocked, merge candidate) -- content incorporated into this research

Research complete, advancing to backlog

[[2026-04-02]] Thu 06:53
## Architecture Review
**Verdict:** Approve
**DR Verification:** docs/decisions/resolved/387-memory-mcp-architecture.md approved: true

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. Design memory-mcp architecture (storage, schema, API) | Research doc 3A (SQLite+WAL), 3B (12-field schema), 3E (4 tools) | Pass |
| 2. Design multi-dimensional scoping model | Research doc 3C (4D nullable agent x project matrix) | Pass |
| 3. Design configurable storage location | Research doc 3D (OWLBEAR_MEMORY_DB_PATH env var, central vs in-repo). Hybrid YAGNI'd with rationale -- user approved Option A in DR. | Pass |
| 4. Design agent-facing MCP tool interface | Research doc 3E (get_knowledge, record_learning, list_entries, mark_for_deletion) | Pass |
| 5. Design approval workflow | Research doc 3F (pending/approved/deleted, user-only permanent delete) | Pass |
| 6. Design auto-loading mechanism | Research doc 3G (agent-common Step 0 calls get_knowledge) | Pass |
| 7. Design write mechanism | Research doc 3H (record_learning replaces inbox, dual-write during migration) | Pass |
| 8. Design curation interface | Research doc 3I (list_entries + mark_for_deletion + cross-pollinate) | Pass |
| 9. Design cross-project knowledge aggregation | Research doc 3J (single central DB, scope_project column) | Pass |
| 10. Assess deer-flow patterns | Research doc 3K (patterns 1,2,4-custom,6 adopted per DR 428) | Pass |
| 11. Assess migration path | Research doc 3L (5-phase gradual cutover) | Pass |
| 12. Create decision request | DR at docs/decisions/resolved/387-memory-mcp-architecture.md, approved: true, decision: Option A | Pass |
| 13. Create follow-up tasks at ideation | #524-#531 created. #524 already at docs status. | Pass |

### Architecture Notes
Research is thorough (178-line design doc, 10 sources, all 13 AC items addressed). Design follows existing MCP server patterns consistently (AppContext, lifespan, SQLite+asyncio.to_thread, ToolAnnotations, env-var tool exclusion). DR approved by user as Option A (full architecture without dedup/token-budgeting). Follow-up implementation tasks properly decomposed into scaffold, tools, agent-common update, migration, and curator workflow.

Non-implementation task tagged research -- test-writer pass-through applies.

Downstream notes for implementation task architects:
- Implementation tasks should include graceful degradation if mcp-memory is unavailable at Step 0 (blind spot from challenge)
- #529 (set_approval_state) extends the 4-tool design to 5 tools based on #528 curator analysis -- natural evolution, not contradiction
- #499 is blocked and redundant (content incorporated into #387). Board hygiene: should be archived or deleted by next auditor cycle.

### Changes Made
- Verified all 13 AC items against research doc sections
- Verified DR approved: true at docs/decisions/resolved/387-memory-mcp-architecture.md
- Verified dependency #428 archived
- Moving to todo with release

### Dependencies
- Verified: #428 (deer-flow deep dive) archived
- Noted: #499 blocked as redundant merge candidate (not blocking)

### Challenge Results
- Challenger: reconsider
- Confidence in original: .85
- Key challenges: C1 (follow-ups ran ahead of formal approval), C2 (patterns 3/5 not declined with follow-up), C3 (5th tool from #529 outdates 4-tool design), C4 (hybrid YAGNI'd without explicit DR note), C5 (#499 debris)
- Architect response: C1 rebutted (DR user-approval was the real implementation gate, not backlog-to-todo of research task). C2 rebutted (user chose Option A over B in DR, declining patterns 3/5 -- no follow-up for rejected options). C3 accepted as natural evolution (design docs are snapshots, implementation tasks have own AC). C4 rebutted (YAGNI documented in research and user approved Option A). C5 accepted as board hygiene note.
- Revised confidence: .88

[[2026-04-02]] Thu 08:11
## Test-Writer Notes

[[2026-04-02]] Thu 08:11
- Non-implementation task (tagged research) -- no tests applicable.

[[2026-04-02]] Thu 08:11
- Passing through to builder.

[[2026-04-02]] Thu 11:54
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Research/design task -- no behavior change yet. mcp-memory refs already in copilot-instructions (tech stack L59, conventions L69, directory L179) from follow-up scaffold task #524 |
| 2 | Docstrings | No | N/A | No Python modules created or modified -- pure design task |
| 3 | docs/sources/overview.md | Yes | Pass | Section 'memory-mcp Server Architecture Design (Task #387)' present at L120-125 with Mem0 and DR #428 sources |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/memory-mcp-server-design.md exists (178 lines, 10 sources, all 13 AC items). DR at docs/decisions/resolved/387-memory-mcp-architecture.md approved. Follow-up tasks #524-#531 confirmed created per task body |
| 6 | Scratch files | No | Pass | No docs/scratch/387-* files found |

### Files Updated
- None

### Scratch Files Cleaned
- None

[[2026-04-02]] Thu 15:10
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| 1. Storage/schema/API design | Research doc 3A (SQLite+WAL), 3B (12-field), 3E (4 tools) | PASS |
| 2. Multi-dimensional scoping | Research doc 3C (4D nullable agent x project) | PASS |
| 3. Configurable storage location | Research doc 3D (OWLBEAR_MEMORY_DB_PATH) | PASS |
| 4. Agent-facing MCP tool interface | Research doc 3E (get_knowledge, record_learning, list_entries, mark_for_deletion) | PASS |
| 5. Approval workflow | Research doc 3F (pending/approved/deleted, user-only permanent delete) | PASS |
| 6. Auto-loading mechanism | Research doc 3G (agent-common Step 0) | PASS |
| 7. Write mechanism | Research doc 3H (record_learning, dual-write migration) | PASS |
| 8. Curation interface | Research doc 3I (list_entries + mark_for_deletion + cross-pollinate) | PASS |
| 9. Cross-project aggregation | Research doc 3J (single central DB, scope_project) | PASS |
| 10. Deer-flow pattern assessment | Research doc 3K (patterns 1,2,4-custom,6 per DR 428) | PASS |
| 11. Migration path | Research doc 3L (5-phase gradual cutover) | PASS |
| 12. Create decision request | docs/decisions/resolved/387-memory-mcp-architecture.md approved: true | PASS |
| 13. Follow-up tasks at ideation | #524-#531 confirmed on board, all reference research doc | PASS |

### Research Task Verification
- Research doc: docs/research/memory-mcp-server-design.md (178 lines, 10 sources)
- DR: docs/decisions/resolved/387-memory-mcp-architecture.md (approved: true, Option A)
- Follow-ups: #524 (docs), #525 (backlog), #526 (ideation), #527 (in-progress), #528 (backlog), #529-531 (ideation)
- Attribution: docs/sources/overview.md L120-125
- Deliverables committed: 82821ac

### Test Results
- pytest: 2363 passed, 285 failed, 8 skipped. Zero failures in task scope (pure research, no code changes).
- ruff: 2 violations in test_necessity_check_196.py (unrelated to task)

### Architect Quality
- AC specificity: 13 AC items, each maps to a specific research doc section. No vague criteria.
- Edge cases: None missed. Challenger surfaced 5 challenges, all addressed.
- Design direction: Architecture Review approved with thorough AC mapping.
- AC quality score: 5/5

### Deduction breakdown
No deductions. All 13 AC lines have specific evidence. No lint issues in scope. AC quality 5. No reviewer section expected (research task pass-through). No test failures in scope.

### Confidence: .98
### Action: archive
