---
id: 437
title: 'Test: parallel fan-out in reviewer agent'
status: backlog
priority: important
created: 2026-03-30T21:47:34.6368074+02:00
updated: 2026-03-30T22:46:37.0192062+02:00
tags:
    - scope:agents
    - phase-2
    - test
blocked: true
block_reason: 'Blocked by pending decisions: 228-parallel-fan-out and 228-esub-utility-subagents. Do not dispatch until both are approved.'
class: standard
---

Test task for #265. Validate structural changes to reviewer.agent.md and code-review SKILL.md after parallel fan-out wiring.

## Acceptance Criteria

- [ ] Test that reviewer.agent.md frontmatter `agents:` field contains both `quality-runner` and `code-reader`
- [ ] Test that reviewer.agent.md frontmatter `tools:` list matches the current baseline (15 entries: vscode/memory, execute/testFailure, execute/getTerminalOutput, execute/awaitTerminal, execute/killTerminal, execute/createAndRunTask, execute/runInTerminal, execute/runTests, read/problems, read/readFile, read/viewImage, read/terminalLastCommand, agent, search, owlbear-kanban/*)
- [ ] Test that code-review SKILL.md contains a `## Step 2.5` heading (parallel dispatch section)
- [ ] Test that code-review SKILL.md Step 8 section contains at least one of: Quality-Runner, Code-Reader, or subagent (synthesis from parallel reports)
- [ ] All tests fail before implementation (RED phase)

## Test Pattern

Follow existing structural test pattern (see tests/test_disable_model_invocation.py): read file with pathlib, parse YAML frontmatter with regex, assert on content. Test class: `TestFromAC_ReviewerParallelFanOut`.

## Blocking

Blocked by same decisions as parent #265: 228-parallel-fan-out and 228-esub-utility-subagents (both pending approval). Do not implement until both are approved.

[[2026-03-30]] Mon 22:46
## Architecture Review
**Verdict:** REFINE

### AC Assessment
- agents field contains quality-runner and code-reader: Testable, kept as-is
- tools list unchanged from baseline: Was vague, rewritten with all 15 tools listed explicitly
- SKILL.md contains Step 2.5 heading: Testable, kept as-is
- Step 8 references synthesis: Was vague, rewritten to require Quality-Runner/Code-Reader/subagent keyword
- All tests fail before impl (RED): Standard TDD, kept

### Architecture Notes
Existing test pattern in tests/test_disable_model_invocation.py. Wrong depends_on removed (#263, #307 belong to #265, not this test task). Blocked for pending decisions 228-parallel-fan-out and 228-esub-utility-subagents. Note: #265 should add depends_on #437 to enforce TDD ordering.

### Changes Made
- Rewrote body: exact baseline tools, Step 8 match criteria, test class name, pattern reference
- Removed depends_on #263, #307
- Added block for pending decisions
