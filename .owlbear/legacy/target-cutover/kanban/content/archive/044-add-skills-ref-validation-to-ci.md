---
id: 44
title: Add skills-ref validation to CI
status: archived
priority: medium
created: 2026-03-26 18:55:53.178981+01:00
updated: 2026-04-04 07:30:31.295705+02:00
started: 2026-04-04 07:30:31.295705+02:00
completed: 2026-04-04 07:30:31.295705+02:00
tags:
- phase-1
- scope:skills
- scope:build
- type:build
depends_on:
- 84
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Integrate agentskills.io skills-ref validator as a pre-commit hook with vendor-field error filtering.

See docs/research/skills-ref-ci-validation.md for full analysis.

## Acceptance Criteria
- [ ] `skills-ref==0.1.1` added as dev dependency (`uv add --dev skills-ref==0.1.1`)
- [ ] `scripts/validate_skills.py` exists and: (a) discovers all `.github/skills/*/SKILL.md` directories, (b) runs skills-ref validation on each, (c) filters errors for known VS Code vendor extension fields (`user-invocable`, `argument-hint`, `disable-model-invocation`), (d) prints non-filtered errors to stderr, (e) exits 0 if no real errors remain after filtering and exits 1 otherwise
- [ ] `repo: local` pre-commit hook added to `.pre-commit-config.yaml` with `id: validate-skills` that runs `python scripts/validate_skills.py`
- [ ] All 21 current skills pass the filtered validation (`pre-commit run validate-skills --all-files` exits 0)

## Architecture Notes
- Existing pre-commit config has 5 repos; add `repo: local` entry (standard pattern for custom scripts)
- Script uses skills-ref Python API or subprocess CLI wrapper; either is acceptable
- Pin `skills-ref==0.1.1` because package is labeled "for demonstration purposes only"
- When agentskills spec adds vendor extension support, simplify to raw `agentskills validate` without filter
- No `scripts/` directory exists yet; builder creates it
- Merged from #83 (deleted as duplicate)

[[2026-03-27]] Fri 04:57
## Research
Key findings: skills-ref v0.1.1 (PyPI: agentskills CLI) validates spec compliance but rejects VS Code vendor fields (user-invocable, argument-hint, disable-model-invocation). 11/21 OwlBear skills fail due to user-invocable: false. Recommended: pre-commit hook with vendor-field error filter. Follow-up: #83. Doc: docs/research/skills-ref-ci-validation.md


## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| skills-ref==0.1.1 dev dep | Specific version, correct install command | Keep |
| scripts/validate_skills.py with filter | Clear inputs/outputs/exit codes; 5 sub-criteria all testable | Keep |
| repo: local pre-commit hook | Follows existing .pre-commit-config.yaml pattern (5 repos); id specified | Keep |
| All 21 skills pass filtered validation | Empirically verifiable via pre-commit run | Keep |

### Architecture Notes
- Merged #83 (duplicate follow-up from research) into #44; deleted #83
- Created test task #84 (TDD red phase) with 4 AC lines covering valid/vendor-field/spec-error/exit-code scenarios
- #44 now depends_on #84 (tests first)
- Script location `scripts/validate_skills.py` is a new directory; acceptable for build tooling scripts
- No module layering concerns: standalone script, not part of application packages
- Security surface: processes local files only, invokes a local Python package, no network or user input
- Package risk acknowledged: skills-ref "for demonstration purposes only"; pinned to ==0.1.1

### Changes Made
- Refined AC from 4 vague lines to 4 precise, testable lines
- Merged #83 into #44 (deleted #83 as duplicate)
- Created #84 (Test: skills-ref validation script) at todo
- Added depends_on: #84 to #44

### Dependencies
- Added: #84 (test task, TDD red phase)
- Removed: #83 (deleted duplicate)
- No other deps required; skills-ref is a new dev dependency (no existing package conflict)

[[2026-03-29]] Sun 12:39
## Test-Writer Notes
- Test file: tests/test_ci_integration.py
- Classes: TestFromAC_ScriptAutoDiscovery
- Tests per category: 4 auto-discovery contract tests
- Total: 4 tests, all FAIL via AssertionError (exit code 1 / usage message in stderr)
- ruff: clean
- AC coverage:
  - AC1 (skills-ref in pyproject.toml): already satisfied by #84 builder; no failing tests possible
  - AC2(a) (auto-discover .github/skills/*): test_no_args_exits_zero_when_all_skills_valid, test_no_args_produces_no_stderr_output, test_no_args_does_not_print_usage_message
  - AC2(b-e) (filter logic, stderr, exit codes): covered by test_validate_skills.py (#84)
  - AC3 (pre-commit hook config): already satisfied; hook exists with correct entry
  - AC4 (all 21 skills pass via pre-commit): test_no_args_exit_code_matches_explicit_skill_dirs
- Root cause: main() exits 1 with usage error when called with no args. Builder must add auto-discovery of .github/skills/* when argv is empty.

[[2026-03-30]] Mon 17:45
## Test-Writer Notes (path fix, 2026-03-30)\n- Fixed _SKILLS_DIR from .github/skills to skills/ (actual location; research doc was wrong).\n- All 4 tests now fail with AssertionError (correct RED state); FileNotFoundError resolved.\n- ruff: clean\n- 4 tests FAIL, 0 PASS

[[2026-03-30]] Mon 21:55
## Builder Notes
- Conflict: test_validate_skills.py::TestFromAC_ExitCode::test_exit_code_one_no_arguments (task #84) asserts exit code 1 when no args given, directly contradicting test_ci_integration.py::TestFromAC_ScriptAutoDiscovery::test_no_args_exits_zero_when_all_skills_valid (task #44) which requires exit 0.
- No implementation can satisfy both simultaneously.
- Implementation attempted: added auto-discovery of skills/ when argv is empty. Result: 4 task-44 tests PASS, 1 task-84 test FAILS.
- Resolution needed: test-writer must delete or update test_exit_code_one_no_arguments in test_validate_skills.py (it was written for old behavior that task #44 explicitly supersedes).
- Ruff: clean
- Files changed: scripts/validate_skills.py (auto-discovery in main()); reverted pending resolution.
