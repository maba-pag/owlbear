---
id: 98
title: 'Test: Port instruction files'
status: archived
priority: medium
created: 2026-03-28 03:53:35.197807+01:00
updated: 2026-03-29 05:22:53.736243+02:00
started: 2026-03-29 05:22:49.104272+02:00
completed: 2026-03-29 05:22:49.104272+02:00
tags:
- phase-1
- scope:docs
- type:test
- test
class: standard
archival_reason: completed
archival_refs: []
---

## Acceptance Criteria
- [ ] Test that instructions/ contains python.instructions.md, agent-common.instructions.md, research-docs.instructions.md, frontend.instructions.md
- [ ] Test each file has valid YAML frontmatter with applyTo and description fields
- [ ] Test python.instructions.md does NOT contain 'PydanticAI', 'BearClaw', or 'src/owlbear/' references
- [ ] Test .github/instructions/ directory does NOT exist
- [ ] Test .vscode/settings.json chat.instructionsFilesLocations does NOT include .github/instructions
- [ ] Test .github/copilot-instructions.md still exists
- [ ] Update or remove test_vscode_settings_instructions_files_locations_github in test_monorepo_skeleton.py

## Context
Test task for #10 (Port instruction files). Verifies the migration from .github/instructions/ to instructions/ completed correctly.

[[2026-03-28]] Sat 14:41
## Test-Writer Notes
- Test file: tests/test_port_instruction_files.py
- Also updated: tests/test_monorepo_skeleton.py (inverted test_vscode_settings_instructions_files_locations_github)
- Classes: TestFromAC_PortInstructionFiles
- Tests per category: presence 4, frontmatter 8, banned-refs 3, cleanup 2
- Total: 17 tests in new file, all FAIL; 1 updated test in monorepo skeleton also FAIL
- ruff: clean
- AC coverage:
  AC1 (4 files present): test_instruction_file_present x4
  AC2 (applyTo): test_instruction_file_frontmatter_has_apply_to x4
  AC2 (description): test_instruction_file_frontmatter_has_description x4
  AC3 (no PydanticAI/BearClaw/src-owlbear): 3 tests
  AC4 (.github-instructions removed): test_github_instructions_dir_removed
  AC5 (settings excludes .github path): test_vscode_settings_no_github_instructions_path
  AC6 (copilot-instructions.md exists): excluded - already passes on current HEAD
  AC7 (update monorepo test): inverted assertion in test_monorepo_skeleton.py

[[2026-03-28]] Sat 15:16
## Builder Notes
- Files changed: instructions/python.instructions.md (created, cleaned), instructions/agent-common.instructions.md (copied), instructions/research-docs.instructions.md (copied), instructions/frontend.instructions.md (copied), .vscode/settings.json (removed .github/instructions key)
- Deleted: .github/instructions/ directory
- Tests: 17 passed (test_port_instruction_files.py) + 1 updated test in test_monorepo_skeleton.py passes
- Lint: ruff clean
- Evidence: 17 passed in 0.20s; monorepo test 1 passed in 0.05s
- Fixes applied: Removed PydanticAI, BearClaw, src/owlbear/ references from python.instructions.md; updated Project layout section to reference monorepo structure

[[2026-03-28]] Sat 21:56
## Review Evidence
See docs/scratch/98-reviewer.md for full evidence.

[[2026-03-28]] Sat 22:45
## Test-Writer Notes (retry)
- Retry reason: reviewer FAIL was missing test for AC6 (.github/copilot-instructions.md still exists)
- Added: 1 new test (test_copilot_instructions_still_exists) to TestFromAC_PortInstructionFiles
- Test passes because implementation is already complete (retry cycle)
- Preserved: 17 existing tests (all PASS)
- Total: 18 tests, ruff clean

[[2026-03-29]] Sun 03:58
## Test-Writer Notes (retry 2)\n- Retry reason: task returned to todo with no new review evidence (no second review section)\n- All 18 tests in tests/test_port_instruction_files.py PASS (implementation committed in 5b98d21)\n- AC coverage complete: all 7 AC lines covered (AC6 test added in retry 1 is present and correct)\n- Builder uncommitted concern from first review is resolved (git log confirms commit)\n- No new failing tests needed. Passing through to builder for next review cycle.

[[2026-03-29]] Sun 04:26
## Builder Notes (retry 2 pass-through)
- Non-implementation pass-through: implementation committed in 5b98d21
- Tests: 18 passed (test_port_instruction_files.py) + 33 others (test_monorepo_skeleton.py etc) = 51 total
- Lint: ruff clean on tests/
- No code changes needed — all AC already satisfied

[[2026-03-29]] Sun 04:58
## Docs Gate
Checklist passed. copilot-instructions.md already accurate (instructions/ path correct, no .github/instructions reference). No Python modules changed. No external patterns. No CLI changes. No research doc. Scratch file docs/scratch/98-reviewer.md deleted. No files updated.

[[2026-03-29]] Sun 05:22
## Audit
### AC Verification
| AC Line | Evidence | Status |
|------|--------|------|
| AC1: 4 files in instructions/ | ls + 4 parametrized tests pass | PASS |
| AC2: frontmatter applyTo+description | spot-checked python.instructions.md L1-5, 8 tests pass | PASS |
| AC3: no PydanticAI/BearClaw/src-owlbear | 3 tests pass | PASS |
| AC4: .github/instructions removed | Test-Path False, 1 test pass | PASS |
| AC5: settings excludes .github path | 1 test pass | PASS |
| AC6: copilot-instructions.md exists | 1 test pass | PASS |
| AC7: update monorepo test | monorepo skeleton 33 tests pass | PASS |

### Test Results
- pytest (task): 51 passed (18 port-instruction + 33 monorepo-skeleton)
- pytest (full): 527 passed, 179 failed (all failures pre-existing, unrelated)
- ruff: clean

### AC Quality: 5/5
AC was specific, complete, each line maps to concrete tests. No gaps.

### Confidence: .97
### Action: archive
