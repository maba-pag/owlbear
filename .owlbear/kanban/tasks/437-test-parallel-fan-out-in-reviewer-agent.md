---
id: 437
title: 'Test: parallel fan-out in reviewer agent'
status: todo
priority: important
created: 2026-03-30T21:47:34.6368074+02:00
updated: 2026-04-05T01:15:33.7175959+02:00
tags:
    - scope:agents
    - phase-2
    - test
class: standard
---

Test task for #265. Structural regression tests for reviewer.agent.md and w-code-review SKILL.md after parallel fan-out wiring.

## Acceptance Criteria

- [ ] Test that `reviewer.agent.md` frontmatter `agents:` field contains both `quality-runner` and `code-reader`
- [ ] Test that `reviewer.agent.md` frontmatter `tools:` list matches the current 16-entry baseline: vscode/memory, execute/testFailure, execute/getTerminalOutput, execute/awaitTerminal, execute/killTerminal, execute/createAndRunTask, execute/runInTerminal, execute/runTests, read/problems, read/readFile, read/viewImage, read/terminalLastCommand, agent, search, owlbear-kanban/*, owlbear-memory/*
- [ ] Test that `w-code-review SKILL.md` contains a `## Step 2.5` heading (parallel dispatch section)
- [ ] Test that `w-code-review SKILL.md` Step 8 section contains at least one of: Quality-Runner, Code-Reader, or subagent (synthesis from parallel reports)
- [ ] Test file uses `share/agents/` and `share/skills/` paths (not `.github/`); existing test `tests/test_reviewer_parallel_fan_out_437.py` must be corrected
- [ ] All 5 tests pass against current codebase (parent #265 implementation committed in e3871be)

## Test Pattern

Follow existing structural test pattern (see tests/test_disable_model_invocation.py): read file with pathlib, parse YAML frontmatter with regex, assert on content. Test class: `TestFromAC_ReviewerParallelFanOut`.

## File Paths (corrected)

- SUT: `share/agents/reviewer.agent.md`
- SUT: `share/skills/w-code-review/SKILL.md`
- Test: `tests/test_reviewer_parallel_fan_out_437.py` (exists, needs path + AC fixes)

## Notes

- Parent #265 implementation complete (status: review, commit e3871be)
- Blocking decisions 228-parallel-fan-out and 228-esub resolved (implementation proceeded)
- Test file currently errors on `FileNotFoundError` due to `.github/` paths
- AC2 corrected from 15 to 16 tools (`owlbear-memory/*` was missing from prior AC)
- AC1: test must assert both `quality-runner` AND `code-reader` (current test only checks quality-runner)

[[2026-03-30]] Mon 22:46
## Architecture Review (1st pass)
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

## Architecture Review (2nd pass)
See docs/scratch/437-architect.md for full evidence.

**Verdict:** APPROVE
- AC2: corrected tools count 15 to 16 (added owlbear-memory/*)
- AC5: added path correction requirement (.github/ to share/)
- AC6: replaced RED phase with "all tests pass after path fix"
- Removed obsolete blocking (decisions resolved, #265 in review)
- Challenge: FALLBACK (challenger agent not available)

[[2026-04-05]] Sun 01:15
APPROVED after REFINE: corrected AC (16 tools, path fix requirement, pass-not-fail), removed obsolete blocking. See docs/scratch/437-architect.md for full evidence.
