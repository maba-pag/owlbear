---
id: 682
title: 'Orchestrator rewrite: pure sequencer, zero cognitive work'
status: review
priority: needed
created: 2026-03-08T15:44:48.0586907+01:00
updated: 2026-03-09T16:21:01.2194337+01:00
started: 2026-03-08T18:02:00.1067761+01:00
tags:
    - scope:copilot
    - agent
    - phase-agent-arch
depends_on:
    - 680
    - 681
blocked: true
block_reason: 'Deliverable overwritten: commits 75afed4 and 7002e1f simplified the 8-step sequencer to 3-step loop, removing evaluate mode, WAVE_PLAN, retry_count, and pipeline chaining. Either restore 8-step version or update AC to match simplified design.'
class: standard
---

## Context
After planner (#680) and evaluator (#681) agents exist, the orchestrator must be stripped to a pure sequencer: call planner -> dispatch wave -> call evaluator -> execute decisions -> loop. No board reading, no result interpretation, no failure analysis. The orchestrator should be so simple it cannot degrade.

See docs/orchestrator-rewrite-sequencer-research.md for full research.

## Architecture Review
See docs/scratch/682-architect.md for full review.

## Acceptance Criteria

### Workflow structure
- [ ] Workflow has exactly 8 named steps: Plan, Track, Dispatch, Evaluate, Execute, Pipeline, Loop, Curate
- [ ] Step 1 (Plan): dispatch planner with scope filter, receive WAVE_PLAN
- [ ] Step 2 (Track): create manage_todo_list checklist from WAVE_PLAN contents
- [ ] Step 3 (Dispatch): move tasks to in-progress, issue parallel runSubagent calls per wave (one task per call)
- [ ] Step 4 (Evaluate): dispatch evaluator with collected subagent routing signals + per-task retry_count
- [ ] Step 5 (Execute): apply evaluator verdicts mechanically — ADVANCE: kanban-md move to target_status; RETRY: re-dispatch with evaluator's retry_hint + increment counter; BLOCK: kanban-md edit --block; ESCALATE: askQuestions to user
- [ ] Step 6 (Pipeline): for ADVANCE tasks, repeat dispatch->evaluate->execute for next pipeline stage (builder->reviewer->writer); each stage is a separate evaluator invocation
- [ ] Step 7 (Loop): next wave from WAVE_PLAN -> Step 3; if board changed significantly -> Step 1 (re-plan); if no work remains -> Step 8
- [ ] Step 8 (Curate): fire-and-forget curator dispatch if any tasks completed this session

### Cognitive removal (grep-verifiable in final file)
- [ ] Zero occurrences of `kanban-md list` or `kanban-md show` in workflow text
- [ ] Zero gate check instructions (status, dependency, atomicity, TDD, clarity) — all in planner
- [ ] Zero result interpretation logic — evaluator verdicts executed without judgment
- [ ] Zero failure analysis — evaluator determines RETRY/BLOCK/ESCALATE, orchestrator just executes
- [ ] No dependency DAG construction — planner builds it

### Context budget (constant-size invariants)
- [ ] No board state in orchestrator context — planner re-reads each cycle
- [ ] Subagent Channel A signals forwarded raw to evaluator dispatch prompt, not accumulated across waves
- [ ] Only retry_count (integer per task per pipeline stage) persists across retries
- [ ] Prior wave results discarded after evaluator processes them

### Frontmatter changes
- [ ] agents list includes `planner` and `evaluator` alongside existing agents
- [ ] tools list removes: edit/createDirectory, edit/createFile, edit/editFiles, edit/rename, search, web, microsoft/markitdown/*, read/problems, read/readFile
- [ ] tools list retains: agent, vscode/askQuestions, vscode/memory, execute/runInTerminal, execute/getTerminalOutput, execute/awaitTerminal, execute/killTerminal, read/terminalLastCommand, todo

### Critical rules
- [ ] Rule: never call kanban-md list or kanban-md show (planner's job)
- [ ] Rule: never interpret subagent output — forward to evaluator, execute evaluator verdicts (evaluator's job)
- [ ] Rule: never edit code or create files (no edit/* tools available)
- [ ] Rule: one task per subagent dispatch (carried forward)
- [ ] Rule: max 2 retries per task per pipeline stage before ESCALATE

### Signal contracts
- [ ] Orchestrator parses WAVE_PLAN from planner: WAVE N lines with #{id} {agent} summary entries, BLOCKED/SKIPPED sections (format defined in planner.agent.md output_format)
- [ ] Orchestrator parses evaluator verdicts: task_id, verdict (ADVANCE/RETRY/BLOCK/ESCALATE), target_status, retry_hint (format defined in evaluator.agent.md output_format)
- [ ] Orchestrator forwards subagent Channel A signals to evaluator without interpretation — raw text passthrough

### Carried-forward patterns
- [ ] Dispatch prompt hygiene preserved: provide task ID + AC + relevant files, never shell commands or procedure
- [ ] Parallel dispatch guidance preserved: all wave runSubagent calls in single tool-call block
- [ ] Examples section updated with sequencer-style good/bad examples (show plan->dispatch->evaluate->execute cycle)
- [ ] Self-critique checklist updated for sequencer workflow
- [ ] Boundaries section red flags updated: cognitive work (reading board, interpreting results) replaces current operational red flags

## Dependencies
depends_on: [680, 681]

Note: #689 (routing signals) is NOT a dependency — #682 supersedes it. After #682 is done, #689 should be re-evaluated for redundancy. See docs/scratch/682-architect.md.

## Notes
- The orchestrator should be so simple it cannot degrade. A for-loop doesn't hallucinate.
- No TDD task needed — this is an .agent.md file, not Python code.
- Integration test (manual verification of the sequencer loop end-to-end) recommended as a separate follow-up task.
- Pattern reference: planner.agent.md (WAVE_PLAN format), evaluator.agent.md (verdict format), agent-common.instructions.md (two-channel protocol).

[[2026-03-08]] Sun 19:11
## Builder Notes
- Files changed: .github/agents/orchestrator.agent.md (full rewrite)
- No TDD (agent definition file, not Python code)
- Verification: grep confirms 0 kanban-md list/show in workflow, 0 gate checks, 0 DAG construction
- 8 named steps: Plan, Track, Dispatch, Evaluate, Execute, Pipeline, Loop, Curate
- Frontmatter: planner+evaluator added to agents; edit/*, search, web, markitdown, read/problems, read/readFile removed from tools
- Critical rules: 5 rules matching AC (no board read, no interpretation, no edit, one-task-per-dispatch, max-2-retry)
- Signal contracts: WAVE_PLAN format, evaluator verdict format, Channel A raw passthrough all documented
- Context budget section enforces constant-size invariants
- Examples: 4 bad + 2 good sequencer-style examples
- Self-critique: pre-wave, post-wave, session-end checklists

[[2026-03-08]] Sun 19:15
## Review Evidence

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| 8 named steps | Steps 1-8: Plan, Track, Dispatch, Evaluate, Execute, Pipeline, Loop, Curate (lines 138-265) | PASS |
| Step 1 Plan | Line 140: runSubagent(planner, Plan: scope_filter) -> WAVE_PLAN | PASS |
| Step 2 Track | Line 154: manage_todo_list from WAVE_PLAN, retry_count=0 | PASS |
| Step 3 Dispatch | Lines 167-187: move to in-progress, parallel runSubagent, one task per call | PASS |
| Step 4 Evaluate | Lines 191-206: evaluator dispatched with raw Channel A + retry_count | PASS |
| Step 5 Execute | Lines 210-222: ADVANCE/RETRY/BLOCK/ESCALATE table, safety check retry>=2 | PASS |
| Step 6 Pipeline | Lines 226-241: builder->reviewer->writer progression, separate eval cycles | PASS |
| Step 7 Loop | Lines 245-253: next wave / re-plan / Step 8 branches | PASS |
| Step 8 Curate | Lines 257-265: fire-and-forget curator, final status report | PASS |
| Zero kanban-md list/show in workflow | grep: 0 hits in lines 136-267 (workflow section); all hits are prohibitions or bad_examples | PASS |
| Zero gate checks | grep gate/atomicity/TDD/clarity: 0 instructional; line 304 is a red-flag warning only | PASS |
| Zero result interpretation | grep interpret: all hits are prohibitions (lines 35,44,83,118,295,425) | PASS |
| Zero failure analysis | grep: 1 hit at line 305 is a red-flag warning against doing it | PASS |
| No DAG construction | grep dependency DAG/build DAG: 0 hits | PASS |
| No board state | Line 82: context_budget prohibits board state | PASS |
| Signals forwarded raw | Line 83 + Step 4 line 206: verbatim forwarding, no accumulation | PASS |
| Only retry_count persists | Line 84: only integer per task per stage persists | PASS |
| Prior wave results discarded | Line 85 + Step 7 line 251: explicit discard after evaluator processes | PASS |
| agents: planner+evaluator | Lines 7-8: planner and evaluator first in agents list | PASS |
| tools removes edit/search/web/etc | Lines 17-25: no edit/*, search, web, markitdown, problems, readFile | PASS |
| tools retains required set | Lines 17-25: agent, askQuestions, memory, execute/*, terminalLastCommand, todo all present | PASS |
| Rule: no list/show | Line 43: Never call kanban-md list or kanban-md show | PASS |
| Rule: no interpret | Line 44: Never interpret subagent output | PASS |
| Rule: no edit/create | Line 45: Never edit code or create files, no edit/* tools | PASS |
| Rule: one task per dispatch | Line 46: ONE task per subagent dispatch | PASS |
| Rule: max 2 retries | Line 47: Max 2 retries + safety check in Step 5 line 221 | PASS |
| WAVE_PLAN matches planner | Lines 87-106 match planner output_format: WAVE N / BLOCKED / SKIPPED / END_PLAN | PASS |
| Verdict matches evaluator | Lines 119-128 match evaluator output_format: task_id/verdict/target_status/confidence/reason/notes/retry_hint | PASS |
| Raw passthrough | Line 118 + Step 4 line 206: Do NOT parse, interpret, or act; forward verbatim | PASS |
| Dispatch prompt hygiene | Step 3 lines 173-177: provide WHAT never HOW, explicit include/exclude lists | PASS |
| Parallel dispatch guidance | Step 3 line 168: single parallel tool-call block | PASS |
| Sequencer-style examples | Lines 325-400: 4 bad (board read, interpret, second-guess, accumulate) + 2 good (clean cycle, escalate) | PASS |
| Self-critique checklist | Lines 418-432: pre-wave, post-wave, session-end sequencer checklists | PASS |
| Boundaries/red flags updated | Lines 290-327: cognitive red flags (board reading, interpreting, gate-checking, failure analysis, DAG building) | PASS |

### Test Quality
N/A -- agent definition file (.agent.md), no Python code or tests.

### Security
No secrets, credentials, or injection vectors. Agent file is pure markdown/YAML.

### Verdict: PASS confidence .95

[[2026-03-08]] Sun 19:17
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Agent behavior defined in .agent.md, not copilot-instructions.md; grep confirms zero orchestrator refs |
| 2 | Docstrings | No | N/A | No Python modules changed -- .agent.md file only |
| 3 | sources.md | Yes | Updated | #682 section (line 914) already existed; updated Where Used for 5 entries to include .github/agents/orchestrator.agent.md |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/orchestrator-rewrite-sequencer-research.md exists, linked from task body |
| 6 | Scratch files | Yes | Cleaned | Deleted docs/scratch/682-architect.md |

### Files Updated
- docs/sources.md (Where Used column for 5 #682 entries)

### Scratch Files Cleaned
- docs/scratch/682-architect.md

[[2026-03-08]] Sun 23:51
Wave 3, agent: auditor

[[2026-03-09]] Mon 16:20
## Audit
See docs/scratch/682-auditor.md for full evidence.
Confidence: .40
Action: reject to review - deliverable overwritten by commits 75afed4 and 7002e1f
