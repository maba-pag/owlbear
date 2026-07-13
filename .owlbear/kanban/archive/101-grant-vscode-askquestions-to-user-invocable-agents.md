---
id: 101
title: Grant vscode/askQuestions to user-invocable agents (orchestrator, 
  kanban-planner, curator)
status: archived
priority: medium
created: 2026-03-28 13:34:40.547327+01:00
updated: 2026-03-29 12:01:31.231650+02:00
started: 2026-03-29 06:22:54.163854+02:00
completed: 2026-03-29 12:01:30.884800+02:00
tags:
- phase-2
- scope:agents
- config
depends_on:
- 108
- 123
class: standard
archival_reason: completed
archival_refs: []
---

## Acceptance Criteria

- [ ] orchestrator.agent.md YAML frontmatter tools list does NOT include vscode/askQuestions
- [ ] kanban-planner.agent.md YAML frontmatter tools list does NOT include vscode/askQuestions
- [ ] curator.agent.md YAML frontmatter tools list does NOT include vscode/askQuestions
- [ ] No .agent.md file in agents/ contains vscode/askQuestions in its YAML frontmatter tools list (grep guard)
- [ ] tests/test_grant_vscode_askquestions_to_user_invocable.py either deleted or TestFromAC_UserInvocableAgentsHaveAskQuestions class replaced with absence assertions

## Context

Original implementation granted askQuestions to 3 user-invocable agents. Reversed by project decision: OwlBear requires asynchronous user input (decision-requests skill), not blocking synchronous prompts. askQuestions would stall the automated dispatch pipeline.

See updated docs/research/vs-code-new-tools-evaluation.md section 4 for rationale.

## Architecture Notes

Files to change: agents/orchestrator.agent.md (line 19), agents/kanban-planner.agent.md (line 10), agents/curator.agent.md (line 10).
Each change is a single YAML frontmatter line edit removing vscode/askQuestions from the tools array.
Test file: tests/test_grant_vscode_askquestions_to_user_invocable.py (delete or rewrite).

[[2026-03-29]] Sun 06:34
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| orchestrator.agent.md does NOT include askQuestions | Clear, verifiable with grep | Kept |
| kanban-planner.agent.md does NOT include askQuestions | Clear, verifiable with grep | Kept |
| curator.agent.md does NOT include askQuestions | Clear, verifiable with grep | Kept |
| No .agent.md contains askQuestions in tools | Broader grep guard, verifiable | Refined from original vague AC4 |
| Test file deleted or rewritten | Clear, verifiable | Kept |

### Architecture Notes
- Single domain: scope:agents (agent YAML frontmatter only)
- No application code changes, no module layering concerns
- Each change is removing one token from a YAML tools array (3 files)
- Research doc (docs/research/vs-code-new-tools-evaluation.md section 4) provides clear rationale: OwlBear pipeline is fully automated, askQuestions would block dispatch loop
- Existing pattern: planner.agent.md already explicitly forbids askQuestions in its instructions
- Test file tests/test_grant_vscode_askquestions_to_user_invocable.py has existing infrastructure (_read_frontmatter helper, TestFromAC_PipelineAgentsExcludeAskQuestions) that can be adapted

### Changes Made
- Rewrote task body with refined AC: tightened AC4 to specify YAML frontmatter tools list, added Architecture Notes with exact file/line references
- Created #123 (Test: Revert askQuestions from all agents) for TDD RED phase
- Added #123 as dependency for #101

### Dependencies
- Created: #123 (TDD RED test task) at backlog
- No other dependencies needed (pure config reversion)

[[2026-03-29]] Sun 09:28
## Test-Writer Notes
- Test file: tests/test_grant_vscode_askquestions_to_user_invocable.py
- Classes: TestFromAC_NoAgentHasAskQuestions, TestFromAC_SpecificAgentsExcludeAskQuestions
- Total: 14 tests, all PASS (implementation completed via #123)
- ruff: clean (verified in #123 audit)
- Pass-through: Task #123 was the architect-created TDD RED phase task for #101. Full RED-GREEN cycle completed and archived. All AC items satisfied on current HEAD:
  - AC1: orchestrator.agent.md: vscode/askQuestions absent from tools frontmatter
  - AC2: kanban-planner.agent.md: vscode/askQuestions absent
  - AC3: curator.agent.md: vscode/askQuestions absent
  - AC4: No .agent.md in agents/ contains vscode/askQuestions (11 parametrized tests passing)
  - AC5: TestFromAC_UserInvocableAgentsHaveAskQuestions replaced with absence assertions by #123
- No new tests written; no new failing tests needed. Builder will verify no changes required.

[[2026-03-29]] Sun 09:57
## Builder Notes
- Non-implementation task â€” no code changes needed.
- Tests: 14 passed (TestFromAC_NoAgentHasAskQuestions + TestFromAC_SpecificAgentsExcludeAskQuestions), all AC satisfied by #123.
- Lint: ruff clean on agents/ and test file.
- Passing through to review.

-t

[[2026-03-29]] Sun 10:44
## Review Evidence

### Test Results
- pytest: 14 passed, 0 failed (TestFromAC_NoAgentHasAskQuestions x11, TestFromAC_SpecificAgentsExcludeAskQuestions x3)

### Lint Results
- ruff agents/ tests/test_grant_vscode_askquestions_to_user_invocable.py: All checks passed!

### Coverage
- Config-only task (YAML frontmatter edits); no application source files changed. Coverage not applicable.

### Test-Writer Audit
All 5 AC lines have mapped TestFromAC_* tests. Each asserts TOOL_NAME not in frontmatter -- would fail if askQuestions were re-introduced. All COVERED.

### TestFromAC Comparison
Builder was a non-implementation pass-through; no TestFromAC_* modifications. Not applicable.

### Security Review
No application code changes. Agent YAML frontmatter only. No security concerns.

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| orchestrator.agent.md tools excludes vscode/askQuestions | File read: tools: [vscode/memory, read/readFile, agent, todos] -- no askQuestions | PASS |
| kanban-planner.agent.md tools excludes vscode/askQuestions | File read: tools array has no askQuestions entry | PASS |
| curator.agent.md tools excludes vscode/askQuestions | File read: tools array has no askQuestions entry | PASS |
| No .agent.md contains askQuestions (grep guard) | grep: no matches; 11 parametrized tests PASS | PASS |
| Test file rewritten with absence assertions | File has TestFromAC_NoAgentHasAskQuestions + TestFromAC_SpecificAgentsExcludeAskQuestions; original TestFromAC_UserInvocableAgentsHaveAskQuestions absent | PASS |

### Test Quality
- Assertion specificity: STRONG
- Parametrized breadth: STRONG (all 11 agent files)
- Independence: STRONG
- Naming: STRONG

### Verdict: PASS
Confidence: .96

[[2026-03-29]] Sun 11:05
## Docs Gate

[[2026-03-29]] Sun 11:05
### Checklist

All items evaluated with evidence.

1. .github/copilot-instructions.md - No / N/A: Pure YAML frontmatter removal; no behavior change to project conventions. Verified: grep found no askQuestions reference in copilot-instructions.md.
2. Docstrings - No / N/A: No Python modules modified - only .agent.md YAML and test file.
3. docs/sources/overview.md - No / N/A: No new external patterns used; VS Code Cheat Sheet already logged by task 95.
4. README.md - No / N/A: No CLI changes.
5. Research doc linked - Yes / Pass: docs/research/vs-code-new-tools-evaluation.md exists with section 4 rationale; linked from task body.
6. Scratch files - N/A / Clean: No docs/scratch/101-* files found.

### Files Updated
- None

### Scratch Files Cleaned
- None

[[2026-03-29]] Sun 12:01
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| orchestrator.agent.md tools excludes askQuestions | tools: [vscode/memory, read/readFile, agent, todos] at L19 | PASS |
| kanban-planner.agent.md tools excludes askQuestions | grep: zero matches | PASS |
| curator.agent.md tools excludes askQuestions | grep: zero matches | PASS |
| No .agent.md contains askQuestions (grep guard) | grep agents/*.agent.md: zero matches; 11 parametrized tests pass | PASS |
| Test file rewritten with absence assertions | TestFromAC_NoAgentHasAskQuestions + TestFromAC_SpecificAgentsExcludeAskQuestions present; original class absent | PASS |

### Test Results
- pytest (task-specific): 14 passed, 0 failed
- pytest (full suite): 81 failed, 784 passed -- all failures pre-existing (test_rename_todo_to_todos, test_scratch_dir_enforcement, test_v2_test_infrastructure, test_validate_skills_ci), none related to #101
- ruff: All checks passed

### Architect Quality
- AC specificity: 5/5 -- all 5 AC lines are concrete, verifiable conditions
- Edge case coverage: adequate -- grep guard (AC4) covers future regressions
- Design direction: clean -- pointed to exact file/line, created #123 for TDD RED
- AC quality score: 5

### Confidence: .97
### Action: archive
