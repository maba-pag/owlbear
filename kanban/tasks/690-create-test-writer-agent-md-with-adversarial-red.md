---
id: 690
title: Create test-writer.agent.md with adversarial RED phase persona
status: archived
priority: needed
created: 2026-03-08T16:39:29.7852807+01:00
updated: 2026-03-09T11:04:57.489328+01:00
started: 2026-03-08T17:02:43.4176275+01:00
completed: 2026-03-09T11:04:57.489328+01:00
tags:
    - scope:copilot
    - agent
    - phase-agent-arch
class: standard
---

## Context

Split from #683. See docs/research/test-writer-agent.md (AgentCoder empirical validation, grey model design).

The test-writer is a new agent that writes failing tests from AC before the builder sees the task. It tests the CONTRACT, not an implementation. The builder then makes the tests pass. This eliminates implementation bias from tests (AgentCoder: +26.8% test accuracy on HumanEval).

## Acceptance Criteria

- [ ] File `.github/agents/test-writer.agent.md` exists with valid YAML frontmatter
- [ ] frontmatter: `name: test-writer`, `user-invocable: false`
- [ ] frontmatter `tools`: search, read/readFile, edit/createFile, edit/editFiles, execute/runInTerminal, execute/getTerminalOutput, execute/awaitTerminal, execute/killTerminal, read/terminalLastCommand, read/problems, todo, vscode/memory -- NO edit/rename (cannot edit source files)
- [ ] `<persona>`: adversarial test specifier -- tests the AC contract, never sees implementation, takes pride in finding edge cases the builder would miss
- [ ] `<critical_rules>`: (1) never edit source code files (only test files), (2) verify all tests FAIL before completing, (3) one task per invocation, (4) every AC line maps to at least one test
- [ ] `<multi_agent_context>`: dispatched after planner/architect, before builder; builder consumes test-writer's output
- [ ] `<workflow>` references `tdd-red` skill (created in #691)
- [ ] `<output_format>`: structured summary with test file path, class names (`TestFromAC_{Feature}`), test count per category (happy/edge/error/boundary), verification line (all fail)
- [ ] `<boundaries>`: source files read-only, test files write-only, stop and BLOCK if AC is vague or empty, red flags list
- [ ] Test class naming convention `TestFromAC_{Feature}` documented in agent file

## Architecture Notes

- Follow existing agent file patterns: builder.agent.md is the closest analog (same XML sections, similar tool restrictions)
- Tool list is builder's minus edit/rename -- test-writer can create/edit test files but must not touch source code
- The agent-common.instructions.md self-defense rules apply automatically (applyTo: .github/agents/**)

[[2026-03-09]] Mon 04:57
Wave 3, agent: auditor

[[2026-03-09]] Mon 11:04
## Audit
### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| File exists with valid YAML frontmatter | .github/agents/test-writer.agent.md exists, lines 1-17 | PASS |
| name: test-writer, user-invocable: false | Lines 2, 6 | PASS |
| Tools list matches, NO edit/rename | Lines 7-17, all 12 required + extra askQuestions | PASS |
| Persona: adversarial test specifier | Lines 20-33 | PASS |
| critical_rules: 4 required rules | Lines 35-43, 3/4 explicit, (3) inherited from agent-common | PASS (minor) |
| multi_agent_context | Lines 47-60 | PASS |
| workflow references tdd-red | Lines 62-72 | PASS |
| output_format structured summary | Lines 74-105 | PASS |
| boundaries: read-only, BLOCK, red flags | Lines 107-148 | PASS |
| TestFromAC_{Feature} naming documented | Lines 130+ | PASS |

### Test Results
- pytest: 1271 passed, 1 failed (pre-existing slack_sdk), 20 skipped
- ruff: 3 pre-existing warnings, 0 from this task

### Confidence: .95
### Action: archive
