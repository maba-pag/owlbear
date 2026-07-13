---
id: 166
title: Delete empty .github/agents/ and clean stale settings
status: archived
priority: medium
created: 2026-03-29 19:49:25.970990+02:00
updated: 2026-03-30 05:14:20.806918+02:00
started: 2026-03-30 05:13:15.796433+02:00
completed: 2026-03-30 05:13:15.796433+02:00
tags:
- phase-1
- scope:docs
- type:build
depends_on:
- 186
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Remove the empty .github/agents/ directory and clean up stale .github/* references in setup.py and settings.json.

## AC
- [ ] Delete .github/agents/ directory (confirmed empty; .github/ itself retains copilot-instructions.md, dependabot.yml, prompts/ and stays)
- [ ] Remove `.github/agents` entry from .vscode/settings.json `chat.agentFilesLocations` dict
- [ ] Remove `{rel}/.github/agents` mapping from scripts/setup.py `create_vscode_settings()` `owlbear_keys[chat.agentFilesLocations]` dict
- [ ] Remove `{rel}/.github/instructions` mapping from scripts/setup.py `create_vscode_settings()` `owlbear_keys[chat.instructionsFilesLocations]` dict
- [ ] Update tests/test_setup_script.py: `test_agent_files_locations_has_root_and_github_paths` -- remove `.github/agents` assertion, rename to `test_agent_files_locations_has_root_path`
- [ ] Update tests/test_setup_script.py: `test_instructions_locations_has_root_and_github_paths` -- remove `.github/instructions` assertion, rename to `test_instructions_locations_has_root_path`
- [ ] All tests in tests/test_setup_script.py pass
- [ ] `ruff check scripts/setup.py tests/test_setup_script.py` clean

## Context
See docs/research/github-v1-cleanup.md sec 3. setup.py L42 was deferred from #111. .github/instructions/ does not exist (already absent). .github/ retains other files: copilot-instructions.md, dependabot.yml, prompts/.

## Files touched
- .github/agents/ (delete)
- .vscode/settings.json (edit L33 area)
- scripts/setup.py (edit L35, L42 area in create_vscode_settings)
- tests/test_setup_script.py (edit test_agent_files_locations_has_root_and_github_paths, test_instructions_locations_has_root_and_github_paths)

[[2026-03-29]] Sun 20:39
## Architecture Review
**Verdict:** APPROVED (after AC refinement)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Delete .github/agents/ | Verified empty, parent dir has other files | Kept, clarified parent stays |
| Remove .github/agents from settings.json | L33 confirmed present | Kept as-is |
| Remove .github/agents from setup.py L35 | Confirmed in owlbear_keys dict | Kept, added function name |
| Remove .github/instructions from setup.py L42 | Confirmed stale, dir does not exist | Kept, added function name |
| Verify setup.py tests still pass | WRONG: tests assert paths ARE present, will break | Replaced with explicit test update AC lines |

### Architecture Notes
Cleanup task, no new interfaces or codepaths. Single domain (config/tooling).

Key finding: test_setup_script.py tests test_agent_files_locations_has_root_and_github_paths (L109) and test_instructions_locations_has_root_and_github_paths (L131) assert .github paths ARE present. Original AC5 was self-contradictory. Refined AC now lists exact test methods to update.

Created TDD test task #186 to flip assertions to RED before builder cleanup. Pattern consistency: follows same approach as #117 (test_cleanup_github_skills_117.py).

### Changes Made
- Refined AC: replaced vague AC5 with 2 explicit test-update lines + pass/lint checks
- Added file-touched section with exact edit targets
- Created #186 (Test: Delete empty .github/agents/) at todo
- Added depends_on 186 to #166

### Dependencies
- Added: #186 (test task, RED phase) -- #166 depends on it
- No other deps needed; #111 (predecessor) already done

[[2026-03-30]] Mon 03:00
## Test-Writer Notes\n- Test file: tests/test_cleanup_github_agents_166.py\n- Classes: TestFromAC_GithubAgentsDirDeleted, TestFromAC_VscodeSettingsNoDualPath\n- Tests per category: happy 0, edge 0, error 0, boundary 0, state 2\n- Total: 2 tests, all FAIL (AssertionError) against current HEAD\n- ruff: clean\n- AC3/AC4 (setup.py): already covered by existing tests in test_setup_script.py (green since #186)\n- AC5/AC6 (test renames): already completed by task #186 pipeline\n- AC coverage:\n  AC1 (.github/agents/ deleted): test_github_agents_directory_does_not_exist\n  AC2 (settings.json no .github/agents): test_settings_json_no_github_agents_entry

[[2026-03-30]] Mon 05:12
## Audit
See docs/scratch/166-auditor.md for full evidence.

### Confidence: .98
### Action: archive

[[2026-03-30]] Mon 05:13
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: Delete .github/agents/ | Test-Path returns False | PASS |
| AC2: Remove from settings.json | Select-String no match | PASS |
| AC3: Remove .github/agents from setup.py | grep no match, handled by dep #186 commit 4363856 | PASS |
| AC4: Remove .github/instructions from setup.py | grep no match, handled by dep #186 commit 4363856 | PASS |
| AC5: Rename test (agents) | test_agent_files_locations_has_root_path_only at L108 (minor name deviation: added _only suffix) | PASS |
| AC6: Rename test (instructions) | test_instructions_locations_has_root_path_only at L130 (minor name deviation: added _only suffix) | PASS |
| AC7: All tests pass | 62/62 passed in 4.16s | PASS |
| AC8: ruff clean | All checks passed | PASS |

### Test Results
- pytest (task-scoped): 62 passed, 0 failed
- pytest (full suite): 1109 passed, 139 failed (all pre-existing, none in #166 scope)
- ruff: clean

### AC Quality: 4/5
Architect correctly identified test contradiction in original AC and created dep #186. Clear file-touched section. Minor: exact test names deviated slightly (builder added _only suffix, arguably better).

### Deduction breakdown
- Start: 1.00
- Missing reviewer evidence section in task body: -.02
### Confidence: .98
### Action: archive

## Commits
5b43277 chore: archive task #166 (#166, auditor) -- kanban board files

[[2026-03-30]] Mon 05:14
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 5b43277 | chore | kanban/tasks/166-*.md, activity.jsonl | #166 |
