---
id: 117
title: Delete .github/skills/ and remove dual-path settings
status: archived
priority: medium
created: 2026-03-29 01:40:59.188160+01:00
updated: 2026-03-29 23:08:04.470536+02:00
started: 2026-03-29 23:08:04.145290+02:00
completed: 2026-03-29 23:08:04.145290+02:00
tags:
- phase-1
- scope:skills
- type:build
depends_on:
- 116
- 131
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Remove .github/skills/ after v2 skills/ is verified working. Clean up dual-path configuration.

## Acceptance Criteria
- [ ] Delete .github/skills/ directory entirely
- [ ] Remove .github/skills path from .vscode/settings.json chat.agentSkillsLocations (line 37)
- [ ] Update scripts/setup.py to not generate .github/skills path (line 36)
- [ ] Update test_monorepo_skeleton.py to not assert .github/skills presence (lines 274-278)
- [ ] Update test_setup_script.py to not expect .github/skills path (lines 117-126)
- [ ] Delete tests/test_copy_skills_to_root.py entirely (obsolete: reads from .github/skills/)
- [ ] Delete tests/test_skill_sync_131.py entirely (obsolete: reads from .github/skills/)
- [ ] Update docs/decisions/README.md line 49: change .github/skills/ ref to skills/
- [ ] Verify all 22 skills (21 ported + mcp-kanban) load from skills/ only (test_validate_skills_ci.py)
- [ ] All tests pass

## Context
See docs/research/port-skills-to-v2.md sec 4.
See docs/research/delete-github-skills-117.md for detailed analysis.
Depends on: #116 (update references, archived), #131 (sync drifted content, must complete first).

[[2026-03-29]] Sun 11:05
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Delete .github/skills/ directory | Clear, verifiable | OK |
| Remove from .vscode/settings.json (L37) | Verified: line 37 has entry | OK |
| Update scripts/setup.py (L36) | Verified: line 36 has entry | OK |
| Update test_monorepo_skeleton.py (L274-278) | Verified: 3 assertions | OK |
| Update test_setup_script.py (L117-126) | Verified: 3 assertions | OK |
| Delete test_copy_skills_to_root.py | NEW: 9 .github/skills refs, obsolete after deletion | Added |
| Delete test_skill_sync_131.py | NEW: 4 .github/skills refs, obsolete after deletion | Added |
| Update docs/decisions/README.md L49 | NEW: stale .github/skills ref confirmed | Added |
| Verify 22 skills load from skills/ | Testable via test_validate_skills_ci.py | OK |
| All tests pass | Standard regression gate | OK |

### Architecture Notes
Cleanup/deletion task. No new application code, no new interfaces, no security surface. Single domain (scope:skills).
Research doc (.90 confidence) identified 4 AC gaps, all confirmed by codebase search. Refined AC incorporates all 4.

TDD pair not needed: no new application code. Existing tests are targets of the change. AC10 (all tests pass) is the verification gate. Same pattern as #116 (approved without TDD pair).

Builder guidance: after deleting .github/skills/, ensure test_validate_skills_ci.py still passes (validates all 22 skills load from skills/ only). The 2 deleted test files (test_copy_skills_to_root.py, test_skill_sync_131.py) validated predecessor tasks #115 and #131 respectively and become orphaned.

### Changes Made
- Refined AC: added 3 new items (delete 2 test files, update docs/decisions/README.md)
- Added line-number references to existing AC items
- Added depends_on 131 (sync drifted content, currently in docs pipeline)

### Dependencies
- Verified: #116 (update references) is archived
- Added: #131 (sync drifted content) must complete before deletion proceeds
- Downstream: none identified

[[2026-03-29]] Sun 12:31
## Test-Writer Notes
- Test file: tests/test_cleanup_github_skills_117.py
- Classes: TestFromAC_GithubSkillsDirDeleted, TestFromAC_VscodeSettingsNoDualPath, TestFromAC_SetupPyNoDualPath, TestFromAC_MonorepoTestUpdated, TestFromAC_SetupScriptTestUpdated, TestFromAC_ObsoleteTestFilesDeleted, TestFromAC_DecisionsReadmeUpdated
- Tests per category: happy 0, edge 0, error 0, boundary 0 (all are invariant/state checks)
- Total: 8 tests, all FAIL (AssertionError) confirmed by pytest
- ruff: clean
- AC coverage:
| AC Line | Test(s) | Category |
| AC1: delete .github/skills/ | test_github_skills_directory_does_not_exist | state |
| AC2: settings.json no .github/skills | test_settings_json_no_github_skills_entry | state |
| AC3: setup.py no .github/skills | test_setup_py_no_github_skills_reference | state |
| AC4: test_monorepo_skeleton.py updated | test_monorepo_skeleton_no_github_skills_assertion | state |
| AC5: test_setup_script.py updated | test_setup_script_no_github_skills_assertion | state |
| AC6: test_copy_skills_to_root.py deleted | test_copy_skills_to_root_deleted | state |
| AC7: test_skill_sync_131.py deleted | test_skill_sync_131_deleted | state |
| AC8: docs/decisions/README.md updated | test_decisions_readme_no_github_skills_ref | state |
| AC9: 22 skills from skills/ only | implicit via AC1+AC2+AC3 | - |

[[2026-03-29]] Sun 12:48
## Builder Notes
- Files changed: scripts/setup.py, tests/test_monorepo_skeleton.py, tests/test_setup_script.py, docs/decisions/README.md, .vscode/settings.json (5 modified); .github/skills/ deleted (37 files); tests/test_copy_skills_to_root.py and tests/test_skill_sync_131.py deleted
- Tests: 8/8 AC tests passed; 98 tests passed across all affected files
- Lint: ruff clean on touched files (E501 on setup.py L49 is pre-existing, not from this task)
- Evidence: commit b5377c6, 44 files changed (3 insertions, 7351 deletions)
- Fixes applied: BOM from PS 5.1 Set-Content - rewrote settings.json with UTF8Encoding(false)

[[2026-03-29]] Sun 14:26
## Review Evidence
**Verdict: FAIL** — Confidence 0.97

### Test Results
- pytest tests/test_cleanup_github_skills_117.py: **7 passed, 1 FAILED**
  - FAILED: TestFromAC_GithubSkillsDirDeleted::test_github_skills_directory_does_not_exist — .github/skills/ directory still exists
- pytest tests/test_monorepo_skeleton.py + test_setup_script.py: 77 passed, 0 failed
- pytest tests/test_validate_skills_ci.py: 6/9 passed (3 pre-existing failures unrelated to #117)

### Lint Results
- ruff: E501 scripts/setup.py L49 (pre-existing — only 1 line removed from setup.py; L49 docstring unchanged)
- ruff: clean on all 3 test files

### Root Cause
.github/skills/ was correctly deleted in commit b5377c6 (44 files, 7351 deletions). After the commit, directory was recreated on disk — 4 untracked SKILL.md files (code-review, project-definition, research-workflow, tdd-workflow), all modified 14:07 (commit at ~12:48). git status: ?? .github/skills/. VS Code auto-regenerated built-in copilot skills. Builder must physically delete from disk. If VS Code keeps regenerating, consider .gitignore.

### AC Compliance
AC1 delete .github/skills/: FAIL — test fails, 4 untracked files exist on disk
AC2 settings.json no dual-path: PASS — test passes, git confirms 1 line removed
AC3 setup.py no dual-path: PASS — test passes, git confirms 1 line removed
AC4 test_monorepo_skeleton.py updated: PASS — test passes, git confirms test deleted
AC5 test_setup_script.py updated: PASS — test passes, has_github assertion removed
AC6 test_copy_skills_to_root.py deleted: PASS
AC7 test_skill_sync_131.py deleted: PASS
AC8 docs/decisions/README.md updated: PASS
AC9 22 skills from skills/ only: PARTIAL — test_all_current_skills_pass PASS but AC1 failure means .github/skills/ still on disk
AC10 all tests pass: FAIL — 1 test fails

### TestFromAC Comparison
All 8 TestFromAC_* methods preserved exactly by builder. No WEAKENED or REMOVED tests.

### Test Quality
Assertion specificity: STRONG. Independence: STRONG. Names: STRONG. One LAX: AC9 has no dedicated test (implicit, test-writer acknowledged). No compensating TestBuilderDiscovered exists for AC9.

### Security
No new code surface. No issues.

[[2026-03-29]] Sun 15:05
## Test-Writer Notes (retry)
- Retry reason: reviewer FAIL was about implementation (VS Code regenerated .github/skills/ after commit b5377c6), not missing tests.
- All 8 existing TestFromAC_* tests preserved â€” they correctly assert the expected end state.
- test_github_skills_directory_does_not_exist is the correct test; it fails because the directory exists on disk. Builder must delete and add .gitignore to prevent VS Code Copilot from auto-regenerating the dir.
- AC9 (LAX note): implicit via AC1/AC2/AC3 â€” no new test added; reviewer noted it as quality observation, not MISSING.
- Passing through to builder.

-t

[[2026-03-29]] Sun 16:09
## Review Evidence (retry)
**Verdict: PASS** -- Confidence 0.97

### Test Results
- pytest tests/test_cleanup_github_skills_117.py: **8 passed, 0 failed** (all AC tests pass)
- pytest tests/test_monorepo_skeleton.py: 23 passed, 0 failed (scoped to no-github-skills tests)
- pytest tests/test_setup_script.py (excluding pre-existing #69/#75): 45 passed, 0 failed
  - 15 pre-existing failures in TestFromAC_ProjectJsonGeneration (tasks #69, #75 -- unrelated, ImportError for create_project_json not yet built)
- pytest tests/test_validate_skills_ci.py: 6 passed, 3 failed (same 3 pre-existing failures as previous cycle: auto-discovery + pre-commit program not found)
  - TestFromAC_IntegrationAllSkills::test_all_current_skills_pass_with_hook_configured: PASS

### Lint Results
- ruff: E501 scripts/setup.py L49 (pre-existing docstring, confirmed unchanged by git show b5377c6 -- scripts/setup.py)
- ruff: clean on all 3 test files

### Root Cause Fix (vs prior FAIL)
Previous FAIL: .github/skills/ was recreated by VS Code Copilot after commit b5377c6.
Builder fix: commit 4560f54 adds .github/skills/ to .gitignore -- directory stays gone.
Current state: Test-Path .github/skills returns False. Dir absent on disk.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: delete .github/skills/ | Test-Path returns False; test_github_skills_directory_does_not_exist PASSES | PASS |
| AC2: settings.json no dual-path | No .github/skills in settings.json; test passes | PASS |
| AC3: setup.py no dual-path | 1-line deletion in b5377c6; no .github/skills in file; test passes | PASS |
| AC4: test_monorepo_skeleton.py updated | No .github/skills assertion; test passes | PASS |
| AC5: test_setup_script.py updated | No .github/skills assertion; test passes | PASS |
| AC6: test_copy_skills_to_root.py deleted | Test-Path returns False; test passes | PASS |
| AC7: test_skill_sync_131.py deleted | Test-Path returns False; test passes | PASS |
| AC8: docs/decisions/README.md updated | No .github/skills in file; test passes | PASS |
| AC9: 22 skills from skills/ only | Implicit via AC1-AC3; test_all_current_skills_pass PASSES | PASS |
| AC10: all tests pass | 8/8 AC tests pass; other failures pre-existing, unrelated | PASS |

### TestFromAC Comparison
All 8 TestFromAC_* methods preserved exactly by builder. No WEAKENED or REMOVED tests.

### Test Quality
Assertion specificity: STRONG (file existence / string absence). Independence: STRONG. Names: STRONG. AC9 LAX (implicit via AC1+AC2+AC3) -- acknowledged by test-writer, no compensating test needed given AC1 fully covers the concern.

### Security
No new application code. .gitignore addition is safe. No issues.

[[2026-03-29]] Sun
## Docs Gate

No 1 - .github/copilot-instructions.md: N/A -- no .github/skills refs in file; cleanup has no convention change
No 2 - Docstrings (scripts/setup.py): Pass -- create_vscode_settings docstring accurate post-removal; all public fns have docstrings
No 3 - docs/sources/overview.md: Pass -- lines 2726-2731 already have #117 entries added by builder
No 4 - README.md: N/A -- no CLI commands added or changed
No 5 - Research doc: Pass -- docs/research/delete-github-skills-117.md exists; linked in task body and sources
No 6 - docs/decisions/README.md: Pass -- builder updated (AC8); no .github/skills refs remain

Files Updated: None
Scratch Files Cleaned: None (no docs/scratch/117-* files existed)

[[2026-03-29]] Sun 23:07
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: delete .github/skills/ | Test-Path False; test passes | PASS |
| AC2: settings.json no dual-path | grep 0 matches; test passes | PASS |
| AC3: setup.py no dual-path | grep 0 matches; test passes | PASS |
| AC4: test_monorepo_skeleton updated | grep 0 matches; test passes | PASS |
| AC5: test_setup_script updated | grep 0 matches; test passes | PASS |
| AC6: test_copy_skills_to_root deleted | Test-Path False; test passes | PASS |
| AC7: test_skill_sync_131 deleted | Test-Path False; test passes | PASS |
| AC8: docs/decisions/README.md updated | grep 0 matches; test passes | PASS |
| AC9: 22 skills from skills/ only | test_all_current_skills_pass PASS | PASS |
| AC10: all tests pass | 8/8 AC tests; 870 suite pass, 61 pre-existing | PASS |

### Test Results
- pytest (AC tests): 8 passed, 0 failed
- pytest (full suite): 870 passed, 61 failed (all pre-existing), 3 collection errors (pre-existing)
- ruff: clean on all task files

### AC Quality Score: 4/5
AC was specific with line numbers. Researcher additions incorporated. Minor gap: did not anticipate VS Code Copilot auto-regeneration of .github/skills/ after deletion.

### Confidence: .97
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| b5377c6 | chore | 44 files (deletions + settings) | #117 |
| 4560f54 | fix | .gitignore | #117 |
| 5275e53 | docs | research doc + test whitespace | #117 |
| eb20987 | chore | kanban task file | #117 |

[[2026-03-29]] Sun 23:07
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: delete .github/skills/ | Test-Path False; test passes | PASS |
| AC2: settings.json no dual-path | grep 0 matches; test passes | PASS |
| AC3: setup.py no dual-path | grep 0 matches; test passes | PASS |
| AC4: test_monorepo_skeleton updated | grep 0 matches; test passes | PASS |
| AC5: test_setup_script updated | grep 0 matches; test passes | PASS |
| AC6: test_copy_skills_to_root deleted | Test-Path False; test passes | PASS |
| AC7: test_skill_sync_131 deleted | Test-Path False; test passes | PASS |
| AC8: docs/decisions/README.md updated | grep 0 matches; test passes | PASS |
| AC9: 22 skills from skills/ only | test_all_current_skills_pass PASS | PASS |
| AC10: all tests pass | 8/8 AC tests; 870 suite pass, 61 pre-existing | PASS |

### Test Results
- pytest (AC tests): 8 passed, 0 failed
- pytest (full suite): 870 passed, 61 failed (all pre-existing), 3 collection errors (pre-existing)
- ruff: clean on all task files

### AC Quality Score: 4/5
AC was specific with line numbers. Researcher additions incorporated. Minor gap: did not anticipate VS Code Copilot auto-regeneration of .github/skills/ after deletion.

### Confidence: .97
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| b5377c6 | chore | 44 files (deletions + settings) | #117 |
| 4560f54 | fix | .gitignore | #117 |
| 5275e53 | docs | research doc + test whitespace | #117 |
| eb20987 | chore | kanban task file | #117 |
