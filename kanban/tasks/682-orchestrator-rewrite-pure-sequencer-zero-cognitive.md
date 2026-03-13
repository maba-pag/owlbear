---
id: 682
title: 'Orchestrator rewrite: pure sequencer, zero cognitive work'
status: archived
priority: needed
created: 2026-03-08T15:44:48.0586907+01:00
updated: 2026-03-11T09:39:24.7821581+01:00
started: 2026-03-08T18:02:00.1067761+01:00
completed: 2026-03-11T09:39:24.7821581+01:00
tags:
    - scope:copilot
    - agent
    - phase-agent-arch
depends_on:
    - 680
claimed_by: builder
claimed_at: 2026-03-11T09:26:29.1082376+01:00
class: standard
---

## Context
The orchestrator is a pure mechanical sequencer: call planner, dispatch wave, check for crashes, re-plan. No board reading, no result interpretation, no failure analysis. The orchestrator should be so simple it cannot degrade.

See .github/skills/orchestration/SKILL.md for the canonical 3-step workflow.
See docs/research/orchestrator-rewrite-sequencer.md for full research.
See docs/research/evaluator-agent-final-disposition.md for evaluator supersession rationale.

## Acceptance Criteria

### Workflow structure
- [ ] Workflow has exactly 3 named steps: Plan, Dispatch, Loop
- [ ] Step 1 (Plan): dispatch planner with scope filter + failure context from prior cycle; receive JSON plan (`{dispatch:[...],blocked:[...]}`)
- [ ] Step 2 (Dispatch): dispatch in waves of <=4 parallel `runSubagent` calls; retry crashed agents once; record second-crash as failure
- [ ] Step 3 (Loop): pass failure context to planner, re-plan from fresh board state; stop when `dispatch` array is empty; fire-and-forget curator dispatch if any tasks reached `done`

### Cognitive removal (grep-verifiable in final file)
- [ ] Zero occurrences of `kanban-md list` or `kanban-md show` in workflow text
- [ ] Zero gate check instructions (status, dependency, atomicity, TDD, clarity) -- all in planner
- [ ] Zero result interpretation -- orchestrator checks only success vs crash, not signal content
- [ ] Zero failure analysis -- planner sees unchanged tasks as stale next cycle
- [ ] No dependency DAG construction -- planner builds it
- [ ] Zero evaluator references -- no `evaluator` dispatch, no verdict parsing, no evaluator in agents list

### Context budget (constant-size invariants)
- [ ] No board state in orchestrator context -- planner re-reads each cycle
- [ ] Subagent Channel A signals are diagnostic only -- not parsed, not forwarded, not accumulated
- [ ] Only failure context (task IDs of double-crashed agents) persists across cycles
- [ ] Prior cycle results discarded after planner receives failure context

### Frontmatter changes
- [ ] agents list: planner + 9 execution agents (kanban-planner, researcher, architect, test-writer, builder, reviewer, writer, auditor, curator) -- no evaluator
- [ ] tools list removes: edit/createDirectory, edit/createFile, edit/editFiles, edit/rename, search, web, microsoft/markitdown/*, read/problems, read/readFile
- [ ] tools list retains: agent, vscode/askQuestions, vscode/memory, execute/runInTerminal, execute/getTerminalOutput, execute/awaitTerminal, execute/killTerminal, read/terminalLastCommand, todo

### Critical rules
- [ ] Rule: never call kanban-md list or kanban-md show (planner's job)
- [ ] Rule: never interpret subagent output -- check only success vs crash
- [ ] Rule: never edit code or create files (no edit/* tools)
- [ ] Rule: one task per subagent dispatch
- [ ] Rule: max 1 retry per crashed agent, then record as failure for planner

### Signal contracts
- [ ] Orchestrator parses planner JSON plan: `dispatch` array with `(id, agent)` tuples, `blocked` array (informational)
- [ ] Subagent Channel A signals are diagnostic -- orchestrator does NOT parse or route based on them
- [ ] Only binary success/crash status matters to the orchestrator

### Carried-forward patterns
- [ ] Dispatch prompt contains ONLY task ID -- never AC text, shell commands, or procedures
- [ ] Parallel dispatch: all wave `runSubagent` calls in single tool-call block
- [ ] Examples updated with 3-step style good/bad examples (plan->dispatch->loop, no evaluator)
- [ ] Self-critique checklist updated for 3-step workflow
- [ ] Boundaries section red flags: cognitive work (reading board, interpreting results, parsing signals)

### Source of truth
- [ ] Agent file cross-references `.github/skills/orchestration/SKILL.md` as canonical workflow definition

## Dependencies
depends_on: [680]

## Notes
- The orchestrator should be so simple it cannot degrade. A for-loop doesn't hallucinate.
- No TDD task needed -- this is an .agent.md file, not Python code.
- Evaluator concept superseded -- see docs/research/evaluator-agent-final-disposition.md
- Pattern reference: planner.agent.md (JSON plan format), agent-common.instructions.md (two-channel protocol), orchestration SKILL.md (3-step workflow).

[[2026-03-10]] Tue 22:35
## Architecture Review
**Verdict:** APPROVED (via merge with #737)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Remove Step 4/5 evaluator | Done - full AC rewritten to 3-step design | Rewritten |
| Align with 3-step design | Done - Plan/Dispatch/Loop matches orchestration SKILL.md | Rewritten |
| Remove #681 from depends_on | Done - depends_on now [680] only | Updated |
| Reference SKILL.md as source of truth | Done - Source of truth section added | Added |

### Architecture Notes
- Evaluator concept superseded per docs/research/evaluator-agent-final-disposition.md
- orchestration SKILL.md is canonical 3-step design; agent file must match
- #737 merged: its AC was the architect's job (kanban edits), not builder work
- #682 moved back to backlog for re-implementation against updated AC
- No TDD task needed - this is an .agent.md file, not Python code

### Changes Made
- `kanban-md edit 682 --body <new-3-step-AC> --remove-dep 681 -t`
- `kanban-md move 682 backlog`
- `kanban-md delete 737 -y` (merged)

### Dependencies
- Verified: #680 (planner) -- archived
- Removed: #681 (evaluator) -- superseded, in ideation

[[2026-03-10]] Tue 22:35
## Architecture Review
**Verdict:** APPROVED (via merge with #737)
Evaluator removed, 3-step AC, #681 dep removed, moved to backlog for re-implementation.

[[2026-03-11]] Wed 00:04
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| 3 named steps: Plan, Dispatch, Loop | Precise, matches SKILL.md canonical design | OK |
| Step 1 (Plan): dispatch planner with scope + failure context | Clear interface contract, matches planner JSON output | OK |
| Step 2 (Dispatch): waves <=4, retry once, record failure | Precise error handling spec | OK |
| Step 3 (Loop): re-plan, stop when empty, curator dispatch | Clear termination condition | OK |
| Zero kanban-md list/show | Grep-verifiable negative constraint | OK |
| Zero gate check instructions | Grep-verifiable | OK |
| Zero result interpretation | Grep-verifiable | OK |
| Zero failure analysis | Grep-verifiable | OK |
| No dependency DAG construction | Grep-verifiable | OK |
| Zero evaluator references | Grep-verifiable; evaluator.agent.md already deleted | OK |
| No board state in context | Invariant matching SKILL.md context budget | OK |
| Channel A signals diagnostic only | Matches agent-common two-channel protocol | OK |
| Only failure context persists | Minimal state across cycles | OK |
| Prior cycle results discarded | Matches SKILL.md | OK |
| agents list: planner + 9, no evaluator | Enumerated, verifiable in frontmatter | OK |
| tools list removes edit/*, search, web, etc. | Current file already lacks these; AC ensures no regression | OK |
| tools list retains agent, terminal, memory, todo | Matches current file | OK |
| 5 critical rules | All verifiable by grep or structural inspection | OK |
| Signal contracts (JSON plan, Channel A, binary) | Precise, matches planner output format | OK |
| Dispatch prompt ONLY task ID | Matches SKILL.md step 2 | OK |
| Parallel dispatch in single block | Structural requirement, verifiable | OK |
| Examples with 3-step style | Good/bad examples required | OK |
| Self-critique checklist | Required for consistency | OK |
| Boundaries red flags: cognitive work | Defensive guardrails | OK |
| Cross-references SKILL.md as source of truth | Ensures drift detection | OK |

### Architecture Notes
- SKILL.md (orchestration) is the canonical 3-step design  agent file must be a faithful implementation
- Planner already produces JSON `{dispatch:[...],blocked:[...]}` matching the AC signal contract
- evaluator.agent.md already deleted; only orchestrator frontmatter ref remains (line 8: `- evaluator`)
- Current file has 8-step evaluator-based design (~400 lines)  full rewrite required
- No TDD needed: this is a .agent.md file, not Python code
- Current tools list already matches the target (no edit/*, search, web); AC prevents regression
- Builder must replace entire workflow/persona/signal_contracts/boundaries/examples sections

### Dependencies
- Verified: #680 (planner agent)  archived
- Removed (prior review): #681 (evaluator)  superseded, in ideation

[[2026-03-11]] Wed 00:22
## Test-Writer Notes
- Non-implementation task (.agent.md file rewrite)  no tests applicable.
- Task notes confirm: 'No TDD task needed -- this is an .agent.md file, not Python code.'
- Passing through to builder.
