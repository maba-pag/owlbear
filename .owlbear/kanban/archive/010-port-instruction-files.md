---
id: 10
title: Port instruction files
status: archived
priority: medium
created: 2026-03-26 17:20:03.836269+01:00
updated: 2026-03-29 03:45:30.926242+02:00
started: 2026-03-29 03:45:26.448526+02:00
completed: 2026-03-29 03:45:26.448526+02:00
tags:
- phase-1
- scope:docs
- type:build
depends_on:
- 7
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Migrate v1 instruction files to v2 `instructions/` directory, remove legacy references, and clean up the old location.

## Acceptance Criteria
- [ ] `instructions/python.instructions.md` exists with YAML frontmatter containing `applyTo` and `description`
- [ ] `instructions/agent-common.instructions.md` exists with YAML frontmatter containing `applyTo` and `description`
- [ ] `instructions/research-docs.instructions.md` exists with YAML frontmatter containing `applyTo` and `description`
- [ ] `instructions/frontend.instructions.md` exists with YAML frontmatter containing `applyTo` and `description`
- [ ] `python.instructions.md` does NOT contain 'PydanticAI', 'BearClaw', or 'src/owlbear/' references
- [ ] `.github/instructions/` directory does NOT exist (removed after migration)
- [ ] `.vscode/settings.json` `chat.instructionsFilesLocations` does NOT include `.github/instructions`
- [ ] `.github/copilot-instructions.md` exists as v2 root Copilot instructions
- [ ] `ruff check` passes on any Python files touched
- [ ] All 17 tests in `tests/test_port_instruction_files.py` pass

## Implementation Note
Work was substantially completed during test task #98's builder phase. Builder should verify all tests pass and confirm no regressions rather than re-implement.

## Context
Depends on #7 (monorepo skeleton, archived). Test task: #98.
Follow-up: #109 (stale README.md in instructions/).

[[2026-03-28]] Sat 22:14
## Architecture Review
Verdict: Approve

AC refined from 8 vague lines to 10 precise testable lines. Single-domain (scope:docs). Work already complete via #98 builder. See docs/scratch/10-architect.md for full evidence.

[[2026-03-29]] Sun 00:47
## Test-Writer Notes\n- Test coverage already complete via companion test task #98 (Test: Port instruction files)\n- Test file: tests/test_port_instruction_files.py (18 tests, all PASS)\n- Classes: TestFromAC_PortInstructionFiles\n- Implementation fully completed during #98 builder phase\n- All 18 tests pass against current HEAD (verified)\n- No new failing tests applicable: implementation is complete\n- Passing through to builder for final verification (uv run pytest plus ruff check)

[[2026-03-29]] Sun 01:55
## Review Evidence
Test: 18 passed. Lint: clean. Verdict: PASS (confidence .95)

[[2026-03-29]] Sun 01:55
### Test Results
- pytest: 18 passed, 0 failed (tests/test_port_instruction_files.py)
- Note: AC says 17 tests; 18 collected and all pass. Extra test covers copilot-instructions.md AC line.

### Lint Results
- ruff tests/test_port_instruction_files.py: All checks passed!

### Coverage
- No Python source files changed by this task (docs/config-only). Coverage N/A.

### Pass 1 CRITICAL
All 12 AC-mapped TestFromAC tests COVERED; all 18 TestFromAC methods PRESERVED.
Test quality all 5 dimensions STRONG. Security: no Python impl code, no security concerns.

### AC Compliance
- instructions/python.instructions.md: exists, applyTo='**/*.py', description present. PASS
- instructions/agent-common.instructions.md: exists, applyTo='**', description present. PASS
- instructions/research-docs.instructions.md: exists, applyTo='docs/research/*.md', description present. PASS
- instructions/frontend.instructions.md: exists, applyTo='src/**/ui/**,...', description present. PASS
- python.instructions.md no banned refs: test_no_pydanticai/bearclaw/src_owlbear all PASS
- .github/instructions/ removed: git shows D .github/instructions/*.md; test_github_instructions_dir_removed PASS
- .vscode/settings.json excludes .github/instructions: test_vscode_settings_no_github_instructions_path PASS
- .github/copilot-instructions.md exists: test_copilot_instructions_still_exists PASS
- ruff passes on Python files touched: All checks passed!
- All 17 tests pass (actual 18): pytest 18 passed, 0 failed

Confidence: .95

[[2026-03-29]] Sun 03:45
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| 4 instruction files exist w/ frontmatter | read_file confirmed applyTo+description in all 4 | PASS |
| python.instructions.md no banned refs | 18/18 tests pass (includes 3 negative tests) | PASS |
| .github/instructions/ removed | Test-Path returns False | PASS |
| .vscode/settings.json clean | test_vscode_settings_no_github_instructions_path PASS | PASS |
| .github/copilot-instructions.md exists | test_copilot_instructions_still_exists PASS | PASS |
| ruff check passes | All checks passed | PASS |
| All 17 tests pass (actual 18) | uv run pytest 18 passed in 0.06s | PASS |

### Test Results
- pytest (task-scoped): 18 passed, 0 failed
- pytest (full suite): 440 passed, 55 failed (all pre-existing in unrelated tasks)
- ruff: All checks passed

### Architect Quality
AC score: 5/5 -- 10 precise testable lines, clean implementation path, helpful implementation note.

### Confidence: .97
### Action: archive
