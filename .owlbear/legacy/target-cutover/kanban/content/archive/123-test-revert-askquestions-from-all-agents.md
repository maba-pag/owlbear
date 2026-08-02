---
id: 123
title: 'Test: Revert askQuestions from all agents'
status: archived
priority: medium
created: 2026-03-29 06:33:50.389824+02:00
updated: 2026-03-29 09:11:33.232099+02:00
started: 2026-03-29 09:11:28.725958+02:00
completed: 2026-03-29 09:11:28.725958+02:00
tags:
- phase-2
- scope:agents
- config
- test
class: standard
archival_reason: completed
archival_refs: []
---

## Acceptance Criteria

- [ ] Tests assert no .agent.md file in agents/ contains vscode/askQuestions in YAML frontmatter tools
- [ ] Tests assert orchestrator.agent.md, kanban-planner.agent.md, curator.agent.md specifically exclude vscode/askQuestions
- [ ] Tests fail on current HEAD (these 3 agents currently have vscode/askQuestions)
- [ ] Ruff clean

## Context

TDD RED phase for #101 reversion. Update or replace tests/test_grant_vscode_askquestions_to_user_invocable.py to assert absence instead of presence.

[[2026-03-29]] Sun 06:55
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| No .agent.md contains askQuestions in YAML frontmatter tools | Broad guard, verifiable via parametrized loop over agents/ | Kept |
| orchestrator, kanban-planner, curator specifically exclude askQuestions | Specific named assertions, verifiable | Kept |
| Tests fail on current HEAD | Verifiable: all 3 agents currently have askQuestions in frontmatter | Kept |
| Ruff clean | Standard lint gate | Kept |

### Architecture Notes
- Single domain: scope:agents (test assertions on .agent.md YAML frontmatter only)
- Existing infrastructure reusable: _read_frontmatter helper, TestFromAC_PipelineAgentsExcludeAskQuestions exclusion pattern in tests/test_grant_vscode_askquestions_to_user_invocable.py
- AC3 (fail on current HEAD) confirmed: grep shows askQuestions present in orchestrator.agent.md L19, kanban-planner.agent.md L10, curator.agent.md L10
- After reversion, pipeline exclusion tests become subsumed by the all-agents guard (AC1), but can be kept for clarity
- File may be renamed to reflect reversion, but that is an implementation detail

### Dependencies
- Verified: #101 (impl task) depends on #123 (this task) -- correct TDD order
- No missing dependencies

[[2026-03-29]] Sun 07:42
## Test-Writer Notes
- Test file: tests/test_grant_vscode_askquestions_to_user_invocable.py
- Classes: TestFromAC_NoAgentHasAskQuestions, TestFromAC_SpecificAgentsExcludeAskQuestions
- Tests per category: guard/parametrized 11, guard/named 3
- Total: 14 tests, 4 FAIL on current HEAD (kanban-planner.agent.md + curator.agent.md) âœ“
- ruff: clean
- AC coverage:
  - No .agent.md has vscode/askQuestions: test_no_agent_has_ask_questions[*] x11
  - orchestrator specifically excluded: test_orchestrator_does_not_have_ask_questions (guard, passes)
  - kanban-planner specifically excluded: test_kanban_planner_does_not_have_ask_questions (FAILS)
  - curator specifically excluded: test_curator_does_not_have_ask_questions (FAILS)
  - Tests fail on current HEAD: 4 failures confirmed âœ“
  - Ruff clean: confirmed âœ“

[[2026-03-29]] Sun 08:01
## Builder Notes
- Files changed: agents/kanban-planner.agent.md, agents/curator.agent.md
- Tests: 14 passed, 0 failed — all TestFromAC_* green
- Lint: ruff clean
- Evidence: Removed vscode/askQuestions from tools frontmatter in both files. 14 passed in 0.06s.
- Fixes applied: None — surgical removal of one tool entry per file

[[2026-03-29]] Sun 09:11
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| No .agent.md has askQuestions in YAML tools | grep across agents/ returns zero matches; 11 parametrized tests pass | PASS |
| orchestrator, kanban-planner, curator specifically exclude | 3 named tests pass in TestFromAC_SpecificAgentsExcludeAskQuestions | PASS |
| Tests fail on current HEAD | Test-writer notes confirm 4 FAIL before builder ran; builder notes confirm 14 pass after | PASS |
| Ruff clean | ruff check on test file: All checks passed | PASS |

### Test Results
- Task-specific: 14 passed, 0 failed (0.04s)
- Full suite: 649 passed, 91 failed (all pre-existing RED-phase failures in unrelated tasks: test_disable_model_invocation, test_rename_todo_to_todos, test_setup_script, etc.)
- ruff: clean

### Commit Integrity
- 2d74e2f test: revert askQuestions absence assertions (#123, test-writer)
- 42e9bf3 feat: revert askQuestions from kanban-planner and curator (#123, builder)

### Quality Gaps
- Missing Review Evidence and Docs Gate sections in task body (reviewer/writer may have been skipped)

### AC Quality: 4/5
AC was specific and testable. Minor gap: no mention of which files to edit, but reversion scope was clear from context.

### Confidence: .95
### Action: archive
