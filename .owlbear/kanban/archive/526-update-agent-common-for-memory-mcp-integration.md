---
id: 526
title: Update agent-common for memory-mcp integration
status: archived
priority: medium
created: 2026-04-01 16:11:31.013131+02:00
updated: 2026-04-03 19:38:24.986726+02:00
started: 2026-04-03 19:38:24.423798+02:00
completed: 2026-04-03 19:38:24.423798+02:00
tags:
- scope:agents
- phase-2
- agent
depends_on:
- 525
- 568
class: standard
archival_reason: completed
archival_refs: []
---

AC:
- [ ] AC1: New `## Institutional knowledge pre-flight` section in instructions/agent-common.instructions.md, placed directly above `## Resolved decision pre-flight`
  - Instructs agents to call `get_knowledge(agent_id=<agent_name>, limit=20, min_confidence=0.7)`
  - `agent_name` = the `name:` field from the agent's .agent.md frontmatter
  - Graceful degradation: if call fails, returns empty, or tool not available (agents without owlbear-memory/* access), proceed normally
  - Single call, not per-category
- [ ] AC2: `## Post-task reflection` section updated to add `record_learning` alongside existing `memory create` (dual-write during migration)
  - Each notable finding gets one `record_learning` call with: `agent_id=<agent_name>`, `scope_agent=<agent_name>`, `confidence=0.8`
  - Category mapping table (must appear in instruction text): problems_faced=knowledge, workarounds_applied=knowledge, patterns_discovered=behavior, time_sinks=context, quality_gaps=context
  - Error handling: if `record_learning` fails, `memory create` fallback still captures data; do not block task completion
  - Skippable when nothing notable happened (existing behavior preserved)
- [ ] AC3: New file `skills/mcp-memory/SKILL.md`
  - Frontmatter: `name: mcp-memory`, `user-invocable: false`
  - Documents server name `owlbearMemory` and all 5 tools: get_knowledge, record_learning, list_entries, set_approval_state, mark_for-deletion
  - Key params, return types, annotations, error handling for each tool
  - Usage examples: Step 0 pattern and post-task reflection pattern
  - Configuration: MEMORY_TOOLS_EXCLUDE, OWLBEAR_MEMORY_DB_PATH env vars
  - Follows mcp-kanban skill template structure (skills/mcp-kanban/SKILL.md)
- [ ] AC4: Memory governance in `.github/copilot-instructions.md` updated with four-tier model
  - /memories/ (user) unchanged
  - /memories/session/ (session) unchanged
  - /memories/repo/inbox/ (dual-write during migration, not yet deprecated)
  - mcp-memory owlbearMemory (agent institutional knowledge, canonical store)
  - Clear boundary: /memories/ = user-centric tool patterns and process pitfalls; mcp-memory = agent institutional knowledge
  - Existing migration command reference preserved

See docs/research/agent-common-memory-mcp-integration.md for full analysis.
See docs/research/memory-mcp-server-design.md sec 3G-3H for design.

[[2026-04-03]] Fri 16:56
## Architecture Review
**Verdict:** Approved (after refinement)
**DR Verification:** docs/decisions/resolved/387-memory-mcp-architecture.md approved: true

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| AC1 Step 0 get_knowledge | Vague: missing params, location, degradation | Rewritten with exact params, section placement, graceful degradation |
| AC2 Post-task dual-write | Missing: category mapping, scope_agent, error handling | Rewritten with mapping table, scope_agent=agent_name, fallback |
| AC3 mcp-memory skill | Vague: no template reference, wrong tool count (4 vs 5) | Rewritten with template ref, all 5 tools listed |
| AC4 Governance update | Vague: no tier model specified | Rewritten with four-tier model and boundary statement |

### Architecture Notes
No Python code produced. All deliverables are instruction markdown and skill markdown.

Files affected:
- instructions/agent-common.instructions.md (Step 0 above L121, post-task reflection at L189)
- .github/copilot-instructions.md (memory governance section L83-113)
- skills/mcp-memory/SKILL.md (new file, follows mcp-kanban template)

Patterns to follow: mcp-kanban skill structure (skills/mcp-kanban/SKILL.md), agent-common section conventions.

Critical refinement (from challenger C1): record_learning must pass scope_agent=agent_name alongside agent_id. Without this, entries store agent_id as source but scope_agent=NULL, causing all reflections to sort as global tier 4 instead of agent-specific tier 2 in get_knowledge retrieval.

Implementation has 5 tools (not 4 as research doc states): get_knowledge, record_learning, list_entries, set_approval_state, mark_for-deletion.

### Changes Made
- Rewrote all 4 AC lines with verifiable specifics
- Added agent tag for test-writer pass-through (no Python code)
- Added scope_agent=agent_name requirement to AC2 (challenger C1)
- Added graceful-degradation carveout for agents without owlbear-memory tool access (challenger C2)

### Dependencies
- Verified: #525 (Implement memory-mcp tools) archived
- Verified: #568 (Add owlbear-memory tool access) done
- Verified: DR #387 (memory-mcp architecture) approved: true

### Challenge Results
- Challenger: reconsider (confidence 0.60)
- Key challenges: (C1) scope_agent vs source semantic mismatch in record_learning, (C2) AC1 applies to all agents but challenger/code-reader/orchestrator lack tool access, (C3) non-impl pass-through undefined, (C4) 5 vs 4 tools in research doc
- Architect response: accepted C1 (added scope_agent=agent_name to AC2), accepted C2 (added graceful degradation carveout), rebutted C3 (agent tag IS the pass-through protocol per dispatch-planning skill), noted C4 (AC3 already lists all 5 tools). Revised confidence: .85

[[2026-04-03]] Fri 17:56
## Test-Writer Notes
- Non-implementation task (tagged `agent`) — no tests applicable.
- AC deliverables: instructions/agent-common.instructions.md, .github/copilot-instructions.md, skills/mcp-memory/SKILL.md
- Architecture Review confirms: No Python code produced. All deliverables are instruction markdown and skill markdown.
- Passing through to builder.

[[2026-04-03]] Fri 17:57
## Test-Writer Notes
- Non-implementation task (tagged agent) - no tests applicable.
- AC deliverables: instructions/agent-common.instructions.md, .github/copilot-instructions.md, skills/mcp-memory/SKILL.md
- Architecture Review confirms: No Python code produced. All deliverables are instruction markdown and skill markdown.
- Passing through to builder.

[[2026-04-03]] Fri 17:57
## Test-Writer Notes
- Non-implementation task (tagged agent) - no tests applicable.
- AC deliverables: instructions/agent-common.instructions.md, .github/copilot-instructions.md, skills/mcp-memory/SKILL.md
- Architecture Review confirms: No Python code produced. All deliverables are instruction markdown and skill markdown.
- Passing through to builder.

[[2026-04-03]] Fri 17:57
## Test-Writer Notes
- Non-implementation task (tagged agent) - no tests applicable.
- AC deliverables: instructions/agent-common.instructions.md, .github/copilot-instructions.md, skills/mcp-memory/SKILL.md
- Architecture Review confirms: No Python code produced. All deliverables are instruction markdown and skill markdown.
- Passing through to builder.

[[2026-04-03]] Fri 18:50
## Review Evidence
See docs/scratch/526-reviewer.md for full evidence.

[[2026-04-03]] Fri 19:04
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | Yes | Pass | Four-tier memory governance table at L85-92; boundary statement at L110; migration command at L116 - all updated by builder |
| 2 | Docstrings | No | N/A | No Python modules created or modified |
| 3 | docs/sources/overview.md | No | N/A | No external code patterns used; mcp-kanban template is internal |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | Yes | Pass | docs/research/agent-common-memory-mcp-integration.md exists and linked in task body |

### Files Updated
- None (all documentation already updated by builder)

### Scratch Files Cleaned
- docs/scratch/526-reviewer.md (deleted)

[[2026-04-03]] Fri 19:38
## Audit
### AC Verification
AC1 Institutional knowledge pre-flight: agent-common L125-137, section above Resolved decision pre-flight (L139), get_knowledge call, graceful degradation, single call. PASS
AC2 Post-task dual-write: agent-common L212-248, record_learning with agent_id, scope_agent, confidence=0.8, category mapping table, error handling, skip clause. PASS
AC3 mcp-memory SKILL.md: skills/mcp-memory/SKILL.md, frontmatter correct, 5 tools documented, params/returns/annotations, usage examples, MEMORY_TOOLS_EXCLUDE + OWLBEAR_MEMORY_DB_PATH config. PASS
AC4 Memory governance: copilot-instructions.md L85-116, four-tier table, boundary statement, inbox as dual-write, migration command preserved. PASS

### Test Results
- pytest: 3318 passed, 267 failed (all pre-existing, unrelated, no Python code in #526), 1 error (task #585 collection)
- ruff: N/A (no Python files modified)

### Architect Quality
- AC quality score: 4/5 (adequate after refinement; original AC needed rewriting but architect caught all issues)

### Deduction breakdown
- No deductions. All 4 AC lines verified with file-level evidence.

### Confidence: 1.0
### Action: archive

### Commits
- c7ed434 docs: agent-common.instructions.md, copilot-instructions.md, mcp-memory/SKILL.md (#526)
