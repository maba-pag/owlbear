---
id: 568
title: Add owlbear-memory tool access to all pipeline agents
status: archived
priority: medium
created: 2026-04-03 10:40:51.446723+02:00
updated: 2026-04-03 17:09:29.042953+02:00
started: 2026-04-03 17:06:30.636038+02:00
completed: 2026-04-03 17:06:30.636038+02:00
tags:
- scope:agents
- phase-2
- agent
class: standard
archival_reason: completed
archival_refs: []
---

Add 'owlbear-memory/*' to the tools: array in every pipeline agent .agent.md frontmatter that already holds MCP server wildcards. Prerequisite for #526 (agent-common memory-mcp integration). Without this, get_knowledge and record_learning calls fail silently because agents lack MCP tool access.

See docs/research/agent-common-memory-mcp-integration.md sec 3A.
See docs/research/add-owlbear-memory-tool-access.md.

AC:
- [ ] These 11 agents include 'owlbear-memory/*' in tools: architect, auditor, builder, curator, kanban-planner, planner, researcher, reviewer, scribe, test-writer, writer
- [ ] These 3 agents are NOT modified (no MCP wildcards by design): challenger, code-reader, orchestrator
- [ ] validate_agents.py passes
- [ ] No other frontmatter changes (surgical edit only)

Arch note: VS Code MCP tool patterns are server-level ('server/*') with no per-tool granularity. Read-only agents (challenger, code-reader) and the dispatch-only orchestrator are excluded to maintain their minimal-toolset invariant. These agents receive institutional knowledge context from their callers' dispatch prompts rather than direct MCP access.

[[2026-04-03]] Fri 11:05
## Research
See docs/research/add-owlbear-memory-tool-access.md
All 14 agents missing owlbear-memory/* in tools. validate_agents.py accepts /* patterns. CRITICAL: .vscode/mcp.json missing owlbear-memory server registration. Follow-up: #570/#571 (mcp.json registration). T1 autonomous.

[[2026-04-03]] Fri 11:27
## Architecture Review
**Verdict:** Approved (after refinement)
**DR Verification:** docs/decisions/resolved/387-memory-mcp-architecture.md approved: true

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| All 14 agents include owlbear-memory/* | Over-broad: violates least-privilege for 3 read-only/dispatch agents | Narrowed to 11 agents with existing MCP wildcards |
| validate_agents.py passes | Syntactic only (endswith /*), acceptable for config task | Keep |
| No other frontmatter changes | Verifiable, good surgical constraint | Keep |

### Architecture Notes
Established codebase invariant: challenger, code-reader, orchestrator have deliberately minimal toolsets with no MCP server wildcards. owlbear-memory/* grants both read (get_knowledge, list_entries) and write (record_learning, mark_for-deletion) access. VS Code MCP patterns are server-level only; no per-tool granularity. Excluding these 3 agents preserves least-privilege. They receive institutional knowledge via caller dispatch prompts.

Pattern to follow: append 'owlbear-memory/*' after 'owlbear-kanban/*' in the tools array of each target agent.

Note: #570 and #571 are duplicate tasks for mcp.json registration. Until one completes, these frontmatter edits are syntactically valid but functionally inert. This is acceptable as prep work.

### Changes Made
- Rewrote AC: narrowed from 14 to 11 agents, listed exclusions and rationale
- Added agent tag for test-writer pass-through

### Dependencies
- Verified: DR #387 (memory-mcp architecture) approved
- Noted: #570/#571 (mcp.json registration) at ideation, required for functional activation
- Upstream: #526 (agent-common integration) depends on this task

### Challenge Results
- Challenger: reconsider (confidence 0.60)
- Key challenges: (1) least-privilege violation granting write tools to read-only agents, (2) orchestrator does not need memory, (3) validate_agents.py is syntax-only
- Architect response: accepted challenges 1 and 2 by narrowing scope from 14 to 11 agents. Rebutted challenge 3: syntax validation is standard for config tasks, semantic correctness is verified by AC line listing specific agents.

[[2026-04-03]] Fri 14:44
## Review Evidence
See docs/scratch/568-reviewer.md for full evidence.

[[2026-04-03]] Fri 15:17
## Test-Writer Notes (retry)
- Retry reason: reviewer FAIL - AC4 test was LAX
- Test file: tests/test_memory_tool_access_568.py
- Added class: TestFromAC_SurgicalEditOnly (11 tests)
- Strategy: compare current tools vs git baseline 54c3710~1; assert diff = owlbear-memory/* only
- 1 FAIL: test_architect_surgical_edit_only (unauthorized edit/rename)
- 15 existing tests preserved (all PASS)
- ruff: clean
- Builder must remove edit/rename from agents/architect.agent.md tools array

[[2026-04-03]] Fri 15:40
## Builder Notes (retry)\n- Files changed: agents/architect.agent.md (1 line, removed edit/rename)\n- Fix: unauthorized edit/rename added by previous builder commit alongside owlbear-memory/*, violating AC4 surgical-edit-only\n- Tests: 26 passed, all TestFromAC_* green\n- Lint: ruff clean\n- Commit: 32f05fb

[[2026-04-03]] Fri 16:06
## Review Evidence (retry 2)
- pytest: 26 passed, 0 failed
- ruff: All checks passed!
- AC1 TestFromAC_MemoryToolPresent (11): PASS
- AC2 TestFromAC_MemoryToolAbsent (3): PASS
- AC3 TestFromAC_ValidateAgentsPasses (1): PASS
- AC4 TestFromAC_SurgicalEditOnly (11): diff vs 54c3710~1 = owlbear-memory/* only - PASS
- 11 target agents grep-confirmed, 3 excluded agents zero-matched
- architect.agent.md HEAD: no unauthorized edit/rename
- Security: config-only change, no new attack surface
- Verdict: PASS / Confidence: .95

[[2026-04-03]] Fri 17:06
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| 11 agents include owlbear-memory/* | grep confirmed all 11: architect auditor builder curator kanban-planner planner researcher reviewer scribe test-writer writer | PASS |
| 3 agents NOT modified | grep challenger code-reader orchestrator: zero matches | PASS |
| validate_agents.py passes | ran with all 14 agents, exit 0 | PASS |
| No other frontmatter changes | git show 54c3710 + 32f05fb: only owlbear-memory/* additions + fix for unauthorized edit/rename | PASS |

### Test Results
- pytest (task-specific): 26 passed, 0 failed
- pytest (full suite): 3300 passed, 238 failed (all failures from other tasks: quality-runner #264, rename-todo-to-todos, register-mcp #570, etc.)
- ruff: All checks passed

### Reviewer Evidence
Present and thorough. Two review rounds: first caught genuine AC4 violation (architect gained edit/rename), retry confirmed fix. Quality: high.

### Architect Quality: 4/5
AC was specific with exact agent lists and exclusions. Proper DR #387 reference. Architecture notes clear on least-privilege rationale. Minor gap: initial scope was over-broad (14 agents) before refinement to 11.

### Deduction breakdown
No deductions. All AC lines have specific evidence, lint clean, AC quality 4, reviewer evidence present, no in-scope test failures.
### Confidence: 1.0
### Action: archive

### Process Note
test_memory_tool_access_568.py has uncommitted retry changes (11 surgical-edit tests added by test-writer retry). Builder second commit (32f05fb) only included agent fix. Upstream commit gap.

[[2026-04-03]] Fri 17:09
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 2e2aa43 | test | tests/test_memory_tool_access_568.py | #568 |
| dbe8125 | chore | kanban/tasks/568-*.md | #568 |
