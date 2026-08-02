---
id: 430
title: 'Test: Wire Quality-Runner into pipeline agents'
status: archived
priority: medium
created: 2026-03-30 21:24:44.643360+02:00
updated: 2026-04-05 04:01:58.195202+02:00
started: 2026-04-05 04:01:58.195202+02:00
completed: 2026-04-05 04:01:58.195202+02:00
tags:
- scope:agents
- phase-2
- test
depends_on:
- 263
class: standard
archival_reason: completed
archival_refs: []
---

Test task for #264. Verify Quality-Runner wiring in agent frontmatter and skill files.

## Acceptance Criteria

- [ ] Test verifies builder, reviewer, auditor, test-writer agent.md files have quality-runner in agents array
- [ ] Test verifies agents array is not empty (no leftover agents: [])
- [ ] Test verifies tdd-workflow, code-review, task-verification, tdd-red SKILL.md files contain Quality-Runner invocation references
- [ ] Test verifies each updated skill retains fallback section with direct uv run commands
- [ ] Test verifies no execute/* tools were removed from any of the 4 agents
- [ ] All tests fail before #264 implementation (RED phase)

## Files to create

- tests/test_quality_runner-wiring_264.py

## Patterns to follow

- tests/test_disable_model_invocation.py (frontmatter parsing, AGENTS_DIR, _get_frontmatter helper)

[[2026-04-03]] Fri 19:47
## Test-Writer Notes
- Test file: tests/test_quality_runner-wiring_264.py
- Classes: TestFromAC_AgentsArrayHasQualityRunner, TestFromAC_AgentsArrayNotEmpty, TestFromAC_SkillsContainQualityRunnerInvocation, TestFromAC_SkillsRetainFallbackSection, TestFromAC_ExecuteToolsPreservedWithQualityRunner
- Total: 22 tests, all FAIL
- ruff: clean
- AC coverage: AC1=5 tests (quality-runner in agents array), AC2=4 tests (not empty, preserves scribe), AC3=5 tests (skills invocation refs), AC4=4 tests (fallback sections), AC5=4 tests (execute/* tools preserved)

[[2026-04-04]] Sat 23:21
## Builder Notes
- Files changed: .github/agents/reviewer.agent.md, .github/skills/tdd-workflow/SKILL.md, .github/skills/code-review/SKILL.md, .github/skills/task-verification/SKILL.md, .github/skills/tdd-red/SKILL.md
- RED verified: 34 failed before implementation
- GREEN: 54 passed, 0 failed
- ruff: clean (no Python files touched; 3 pre-existing violations in unrelated test files)
- Coverage: N/A — all changes are markdown/config files, no Python modules
- Commit: 6fc1c59

### Changes
1. reviewer.agent.md: added quality-runner to agents array (was [code-reader, scribe], now [code-reader, scribe, quality-runner])
2. Created .github/skills/tdd-workflow/SKILL.md — new combined TDD workflow skill with QR invocation (mode: scoped, test_paths, lint_paths, fallback)
3. Created .github/skills/code-review/SKILL.md — code review skill with QR invocation (mode: scoped, test_paths, fallback + pytest-and-linting)
4. Created .github/skills/task-verification/SKILL.md — exit gate skill with QR invocation (mode: full, fallback + pytest-and-linting)
5. Created .github/skills/tdd-red/SKILL.md — RED phase skill with QR invocation (mode: scoped, fallback + pytest-and-linting)

Note: builder, auditor, test-writer agents already had quality-runner in their agents arrays prior to this task. Only reviewer was missing it.

[[2026-04-05]] Sun 00:25
## Review Evidence

### Tests
`uv run pytest tests/test_quality_runner_wiring_264.py -v --tb=short`
**22 passed, 0 failed** (0.20s)

### Lint
`uv run ruff check tests/test_quality_runner_wiring_264.py`
**All checks passed.**

### Coverage
N/A — all implementation changes are markdown/config files (.agent.md, SKILL.md). No Python modules touched.

### Commit Integrity
Builder claimed commit: `6fc1c59`
Confirmed in history: "feat: wire quality-runner into reviewer agent and add skill files (#430, builder)"
Files in commit: reviewer.agent.md + 4 new SKILL.md files only. Test file not touched by builder. ✓

### TestFromAC Integrity
Test file was created by commit `7b2aed2` (test-writer) and later path-corrected by `2d1e9ca` (audit refactor: `agents/` → `.github/agents/`, `skills/` → `.github/skills/`). Diff verified — only path constants changed, no assertions weakened. All TestFromAC classes fully intact.

| Original Test Class | Change Made | Assessment |
|---------------------|-------------|------------|
| TestFromAC_AgentsArrayHasQualityRunner | Path constant corrected | PRESERVED |
| TestFromAC_AgentsArrayNotEmpty | Path constant corrected | PRESERVED |
| TestFromAC_SkillsContainQualityRunnerInvocation | Path constant corrected | PRESERVED |
| TestFromAC_SkillsRetainFallbackSection | Path constant corrected | PRESERVED |
| TestFromAC_ExecuteToolsPreservedWithQualityRunner | Path constant corrected | PRESERVED |

### Security
No attack surface — tests read markdown/config files only. No secrets, injection, or path traversal risk.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: builder/reviewer/auditor/test-writer have quality-runner | reviewer.agent.md: `agents: [code-reader, scribe, quality-runner]`; all 4 agent files verified by passing tests | TestFromAC_AgentsArrayHasQualityRunner (5 tests) | ✓ COVERED |
| AC2: agents array not empty | reviewer preserves scribe; test-writer no longer empty; 4 tests pass | TestFromAC_AgentsArrayNotEmpty (4 tests) | ✓ COVERED |
| AC3: tdd-workflow/code-review/task-verification/tdd-red have QR invocation | All 4 SKILL.md files confirmed to contain `quality-runner` (read directly + tests pass) | TestFromAC_SkillsContainQualityRunnerInvocation (5 tests) | ✓ COVERED |
| AC4: skills retain fallback with uv run | All 4 SKILL.md files have fallback heading + `uv run` commands (verified via read) | TestFromAC_SkillsRetainFallbackSection (4 tests) | ✓ COVERED |
| AC5: no execute/* tools removed | reviewer.agent.md retains all 7 execute/* tools; 4 agent tests pass | TestFromAC_ExecuteToolsPreservedWithQualityRunner (4 tests) | ✓ COVERED |
| AC6: all tests fail in RED phase | Commit 7b2aed2 is test-writer commit; builder notes "34 failed before implementation" | Meta-AC — verified by prior cycle | ✓ COVERED |

### Test Quality
- Assertion specificity: ADEQUATE — string-presence checks are appropriate for config/markdown verification
- Negative coverage: AC2 includes `agents: []` absence check ✓
- Mutation reasoning: removing quality-runner → fails AC1/AC5; removing execute tool → fails AC5; deleting fallback heading → fails AC4 ✓
- Test independence: filesystem reads only, no shared mutable state ✓
- Naming: fully descriptive (`test_reviewer_agents_contains_quality_runner`) — STRONG ✓

### Builder Process
Single clean cycle — 1 Builder Notes block, no retries, no loop pattern.

### Deductions
None. All AC covered, tests pass, lint clean, commit verified, TestFromAC intact.

**Confidence: .97 → PASS**

[[2026-04-05]] Sun 00:44
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | reviewer.agent.md + 4 SKILL.md files created. copilot-instructions.md describes skills directory generically (no individual enumeration) — no update required. |
| 2 | Module docstrings | No | N/A | No Python modules created or modified. Only markdown/config files changed. Test file is not a public module. |
| 3 | External attribution | No | N/A | sources/overview.md already has §Quality-Runner Wiring (Task #264) with full attribution. This test task used no new external sources. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | No | N/A | Test task — no research phase. Parent #264 research doc (docs/research/quality-runner-wiring.md) already exists and is linked. |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/430-* files found)

[[2026-04-05]] Sun 04:01
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: 4 agents have quality-runner | 5 tests pass (TestFromAC_AgentsArrayHasQualityRunner) | PASS |
| AC2: agents array not empty | 4 tests pass (TestFromAC_AgentsArrayNotEmpty) | PASS |
| AC3: 4 skills contain QR invocation | 5 tests pass (TestFromAC_SkillsContainQualityRunnerInvocation) | PASS |
| AC4: skills retain fallback with uv run | 4 tests pass (TestFromAC_SkillsRetainFallbackSection) | PASS |
| AC5: no execute/* tools removed | 4 tests pass (TestFromAC_ExecuteToolsPreservedWithQualityRunner) | PASS |
| AC6: RED phase verified | Builder notes: "34 failed before implementation"; commit 7b2aed2 is test-writer commit | PASS |

### Test Results
- pytest (task-scoped): 22 passed, 0 failed (0.13s)
- pytest (full suite): pre-existing RED failures in unrelated tests; zero failures in #430 scope
- ruff: All checks passed

### Architect Quality: 4/5
Specific, testable AC lines. Clear file targets and pattern reference.

### Deduction Breakdown
No deductions. All AC evidenced, lint clean, reviewer detailed, no task-scope failures.

### Confidence: .98
### Action: archive
