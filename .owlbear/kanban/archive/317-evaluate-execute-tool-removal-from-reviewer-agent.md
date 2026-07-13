---
id: 317
title: Evaluate execute/* tool removal from reviewer agent
status: archived
priority: medium
created: 2026-03-30 20:32:19.163898+02:00
updated: 2026-04-03 03:41:06.268215+02:00
started: 2026-04-03 03:40:11.910115+02:00
completed: 2026-04-03 03:40:11.910115+02:00
tags:
- scope:agents
- phase-2
- research
class: standard
archival_reason: completed
archival_refs: []
---

After Quality-Runner is wired in and validated, evaluate whether the reviewer agent can drop execute/* tools entirely. The reviewer only uses terminal for pytest and ruff — both now handled by Quality-Runner. Removing execute/* tools would enforce the read-only boundary more strictly. Requires validation that no edge-case terminal usage exists. See docs/research/quality-runner-wiring.md.

[[2026-03-30]] Mon 23:48
## Research
Full analysis: docs/research/reviewer-execute-tool-removal.md

**Verdict (.80 confidence):** Remove all 7 execute/* tools + read/terminalLastCommand.
- pytest/ruff/coverage replaced by Quality-Runner subagent
- kanban-md.exe replaced by owlbear-kanban/* MCP tools (full parity confirmed)
- execute/runTests was explicitly forbidden by skill (deadlocks) yet still listed
- Subagent tools are independent of parent (VS Code docs confirmed)
- Parallel fan-out (#265) compatible with removal

**Follow-up tasks created:**
- #457 Remove execute/* tools from reviewer agent (depends on #264)
- #458 Test: Remove execute/* tools from reviewer agent (depends on #457)

[[2026-03-30]] Mon 23:48
## Research
Full analysis: docs/research/reviewer-execute-tool-removal.md

**Verdict (.80 confidence):** Remove all 7 execute/* tools + read/terminalLastCommand.
- pytest/ruff/coverage replaced by Quality-Runner subagent
- kanban-md.exe replaced by owlbear-kanban/* MCP tools (full parity confirmed)
- execute/runTests was explicitly forbidden by skill (deadlocks) yet still listed
- Subagent tools are independent of parent (VS Code docs confirmed)
- Parallel fan-out (#265) compatible with removal

**Follow-up tasks created:**
- #457 Remove execute/* tools from reviewer agent (depends on #264)
- #458 Test: Remove execute/* tools from reviewer agent (depends on #457)

[[2026-04-02]] Thu 23:41
## Architecture Review
**Verdict:** APPROVED
**DR Verification:** docs/decisions/resolved/317-reviewer-execute-tool-removal.md approved: true

### AC Assessment
Research/evaluation task with implicit deliverable criteria verified:
- Research doc at docs/research/reviewer-execute-tool-removal.md: Complete (7 sources, 8 analysis sections, 3 options)
- Recommendation: Option A at .80 confidence, all terminal usage categories covered
- Follow-up tasks: #457 (impl, depends #264) and #458 (test, depends #457) exist at ideation
- T3 decision request: docs/decisions/resolved/317-reviewer-execute-tool-removal.md approved: true

### Architecture Notes
- Research thorough: full terminal usage inventory (9 categories), MCP parity (7 cmds), subagent independence (VS Code docs), risk assessment (4 risks)
- Decision request correctly classified as T3 (security/process change)
- Follow-up tasks at ideation will get their own architect review
- #457 architect: research doc Section 4 requires 3-5 successful reviewer cycles validation period. Add to #457 AC.
- #457 architect: #264 AC retains fallback, #457 removes it. Two-phase approach is intentional. Make explicit.
- Planner: #263 may still be blocked by resolved decision 228. Verify and unblock.

### Changes Made
- Added research tag for test-writer pass-through
- Moved backlog to todo

### Dependencies
- No direct deps. Chain: decision 228 unblocks #263 unblocks #430 unblocks #264 unblocks #457 unblocks #458

### Challenge Results
- Challenger: reconsider
- Confidence in original: .55
- Key challenges: frozen dep chain, validation period gap, self-authored AC, fallback contradiction, MCP handoff gap, missing tag
- Architect response: Accepted tag fix and handoff gap. Rebutted frozen-chain (planner scope) and self-authored-AC (standard for research). Acknowledged validation period and fallback as #457 concerns. APPROVE stands.

[[2026-04-03]] Fri 00:41
## Test-Writer Notes
- Non-implementation task (tagged research) — no tests applicable.
- Passing through to builder.

[[2026-04-03]] Fri 01:34
## Builder Notes
- Non-implementation task: no code changes needed.
- Passing through to review.

[[2026-04-03]] Fri 02:30
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Research-only task; no behavior, API, or convention change |
| 2 | Docstrings | No | N/A | No Python modules created or modified |
| 3 | docs/sources/overview.md | Yes | Pass | Two VS Code sources already logged under Task 317 section at lines 286-289 |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | Yes | Pass | docs/research/reviewer-execute-tool-removal.md exists, linked in task body, follow-up tasks 457 and 458 created |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/317-* files existed)

[[2026-04-03]] Fri 03:40
## Audit
### AC Verification (Research Task)
| Criterion | Evidence | Status |
|-----------|----------|--------|
| Research doc exists | docs/research/reviewer-execute-tool-removal.md (committed at 5e96e18) | PASS |
| Follow-up tasks created at ideation | #457 (ideation, depends #264), #458 (ideation, depends #457) | PASS |
| Follow-up tasks link back | #457 body: 'See docs/research/reviewer-execute-tool-removal.md' | PASS |
| Decision request resolved | docs/decisions/resolved/317-reviewer-execute-tool-removal.md approved: true | PASS |
| Sources attributed | docs/sources/overview.md lines 282-289 (2 VS Code sources under Task #317) | PASS |

### Pipeline Evidence
- Architect: APPROVED with challenger review (confidence .55 on challenge, APPROVE stands)
- Test-Writer: pass-through (research task)
- Builder: pass-through (no code changes)
- Writer: docs gate 5/5 passed

### Test Results
- pytest: 2682 passed, 240 failed, 8 skipped (all failures in unrelated RED-phase tests for other tasks)
- ruff: 3 pre-existing violations (E902 broken src path, PT018 x2 in test_necessity_check_196.py) â€” none from #317

### AC Quality (Architect)
Score: 4/5 â€” Implicit research AC correctly identified by architect. Thorough challenger review. Good downstream notes for #457. Minor: no explicit AC lines in original task body (research tasks rely on implicit criteria).

### Deduction breakdown
- -.02 Missing reviewer evidence section (no Review Evidence in task body)
### Confidence: .98
### Action: archive

[[2026-04-03]] Fri 03:41
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| b2b895f | chore | kanban/tasks/317-*.md | #317 |
