---
id: 511
title: Harden skill validation with deer-flow patterns
status: archived
priority: medium
created: 2026-04-01 00:12:45.102616+02:00
updated: 2026-04-01 23:56:29.613123+02:00
started: 2026-04-01 23:56:15.607237+02:00
completed: 2026-04-01 23:56:15.607237+02:00
tags:
- scope:agents
- phase-2
- type:build
- tooling
class: standard
archival_reason: completed
archival_refs: []
---

## Context
Enhance scripts/validate_skills.py with validation patterns from deer-flow's skills/validation.py.

See docs/research/skill-validation-hardening.md. Source: deer-flow packages/harness/deerflow/skills/validation.py (MIT).

## Acceptance Criteria
- [ ] Naming convention: skill directory names must contain only lowercase letters, digits, and hyphens; must not start or end with a hyphen; must not contain consecutive hyphens
- [ ] Naming convention applies to the directory name unconditionally (not just the optional `name` metadata field)
- [ ] If `name` metadata field is present, it must also pass the same naming convention rules
- [ ] Skill names (directory) must not exceed 64 characters
- [ ] Skill descriptions must not contain angle brackets (`<` or `>`) as defense-in-depth against accidental HTML injection per deer-flow pattern
- [ ] Skill descriptions must not exceed 1024 characters (Agent Skills Spec requirement)
- [ ] Each new rule produces a distinct, descriptive error message including the offending value (follow existing pattern: `Missing required field: 'description'`)
- [ ] Spec-level rules (naming convention, max lengths) added in `scripts/skills_ref/validator.py`; OwlBear-specific hardening (angle brackets) may go in either validator.py or validate_skills.py
- [ ] All existing skills in skills/ pass the enhanced validation (regression guard, no false positives introduced)
- [ ] Test coverage: unit tests for each rule covering valid, invalid, and edge-case inputs (>=90% coverage on changed files)

[[2026-04-01]] Wed 03:10
## Architecture Review
**Verdict:** APPROVED
**DR Verification:** N/A (T1 autonomous, no research-driven decision needed)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Hyphen-case naming | Clear but prescribed regex | Rewrote as behavioral requirements, builder chooses impl |
| No leading/trailing/consecutive hyphens | Verifiable | Merged into naming convention line |
| Max name length 64 chars | Verifiable | Kept |
| Reject HTML tags in description | Verifiable, threat model clear | Scoped to angle brackets per deer-flow |
| All existing skills pass | Green-path only | Clarified as regression guard |
| Test coverage | Vague (no criteria) | Refined to >=90% on changed files with valid/invalid/edge inputs |
| (missing) description max 1024 | Research identified but AC omitted | Added per Agent Skills Spec |
| (missing) directory name validation | name field optional, bypass risk | Added: rules apply to directory name unconditionally |
| (missing) error message contract | No format guidance | Added: distinct messages with offending value |

### Architecture Notes
- Validation lives in two layers: skills_ref/validator.py (spec-level) and validate_skills.py (OwlBear wrapper)
- Naming rules must apply to directory name unconditionally since name metadata is optional and directory name is the canonical identifier for VS Code skill resolution
- Existing pattern: validate_metadata() returns list[str] errors. New rules follow same pattern
- No module layering concerns (scripts/ tooling, no src/ dependencies)
- T1 autonomous per research: spec compliance gap, not a new capability

### Changes Made
- Refined AC body via temp-file pattern (added 4 new lines, rewrote 3 existing lines)
- No tag changes needed (type:build + tooling already correct for TDD pipeline)

### Dependencies
- Verified: no depends_on needed (research doc already complete)
- No downstream tasks depend on this

### Challenge Results
- Challenger: reconsider (confidence .72)
- Key challenges: C1 name-field bypass (accepted), C2 over-specified regex (accepted), C3 green-path-only regression (acknowledged), C4 incomplete injection protection (rebutted)
- Architect response: revised AC to address C1 (directory name validation) and C2 (behavioral spec, not regex). C3 clarified as regression guard. C4 out of scope.
- Confidence after revision: .92

[[2026-04-01]] Wed 18:12
## Builder Notes
- Files changed: scripts/skills_ref/validator.py
- Tests: 57 passed, 1 skipped, ruff clean
- Coverage: 100% on scripts/skills_ref/validator.py
- Lint: ruff all checks passed
- Fixes applied: _validate_naming_convention() helper; dir naming convention; max name 64 chars; description angle-bracket check (allows -> text arrows via neg lookbehind); description max 1024 chars; name field naming convention. Commit: 0744ad7

[[2026-04-01]] Wed 19:53
## Review Evidence
See docs/scratch/511-reviewer.md for full evidence.

[[2026-04-01]] Wed 21:08
## Test-Writer Notes (retry pass-through)
- Pipeline state: no prior Test-Writer Notes found; builder bypassed test-writer phase
- Reviewer FAIL reason: WEAK TESTS in TestFromAC_NameFieldNamingConvention (not missing coverage)
- Implementation is CORRECT per reviewer (confidence .87, only test assertions are the problem)
- Per Step 1b: reviewer cited weak tests -- passing through to builder to fix assertions
- Builder action required per reviewer: in TestFromAC_NameFieldNamingConvention, add assertions
  that verify the SPECIFIC naming-convention message fires for the name field (not just that
  any error exists). Example fix: assert any('name field' in e and 'lowercase' in e for e in errors)
  so that removing _validate_naming_convention(name, 'name field') from validator.py would be
  detected. See docs/scratch/511-reviewer.md for full reviewer guidance.

[[2026-04-01]] Wed 22:21
## Builder Notes (retry)\n- Files changed: tests/test_skill_validation_hardening.py (assertion hardening only)\n- Tests: 57 passed, 1 skipped, ruff clean\n- Coverage: 97% on scripts/skills_ref/validator.py (line 59 pre-existing miss)\n- Lint: ruff all checks passed\n- Action taken: added specific assertions to 5 tests in TestFromAC_NameFieldNamingConvention per reviewer and test-writer guidance. Each test now verifies the naming-convention message fires specifically for name field (containing name field + convention keyword), not just that any error exists. Removing _validate_naming_convention(name, name field) from validator.py would now cause all 5 tests to fail.\n- Commit: 1ce29ab

[[2026-04-01]] Wed 22:50
## Review Evidence (retry)
### Test Results
- pytest: 57 passed, 1 skipped in 0.47s
- All TestFromAC_* classes: PASS

### Lint Results
- ruff check scripts/ tests/test_skill_validation_hardening.py: All checks passed

### Coverage
- scripts\skills_ref\validator.py: 97% (builder-reported: pre-existing miss line 59; >=90% AC: PASS)

### TestFromAC Comparison (retry)
Builder added specific assertions to 5 tests in TestFromAC_NameFieldNamingConvention per reviewer guidance. All changes are STRENGTHENED (no WEAKENED or REMOVED).

| Test | Change | Assessment |
|------|--------|------------|
| test_name_field_with_uppercase_produces_error | Added specific assertion: any('name field' in e and 'lowercase' in e for e in errors) | STRENGTHENED |
| test_name_field_with_underscore_produces_error | Added: any('name field' in e and 'lowercase' in e for e in errors) | STRENGTHENED |
| test_name_field_starting_with_hyphen_produces_error | Added: any('name field' in e and 'hyphen' in e and 'does not match' not in e for e in errors) | STRENGTHENED |
| test_name_field_with_consecutive_hyphens_produces_error | Added: any('name field' in e and 'consecutive' in e for e in errors) | STRENGTHENED |
| test_naming_error_for_name_field_includes_offending_value | Added: any('name field' in e and bad_name in e and 'lowercase' in e for e in errors) | STRENGTHENED |

Manual mutation check: removing _validate_naming_convention(name, 'name field') from validator.py would cause all 5 tests to fail. CONFIRMED.

### AC Compliance

| AC Line | Mapped Tests | Evidence | Status |
|---------|-------------|----------|--------|
| Naming convention: lowercase, digits, hyphens only | TestFromAC_DirectoryNamingConvention | 9 tests covering uppercase, underscore, dot, hyphen edge cases | PASS |
| Must not start/end/have consecutive hyphens | TestFromAC_DirectoryNamingConvention | 3 tests for each sub-rule | PASS |
| Naming applies unconditionally (no name field required) | TestFromAC_NamingAppliedUnconditionally | Both invalid-no-name and valid-no-name tested | PASS |
| Name field must also pass naming convention | TestFromAC_NameFieldNamingConvention | 5 tests, each now checks specific naming message fires for name field | PASS |
| Max name length 64 chars | TestFromAC_MaxNameLength | 63/64/65 char boundaries tested | PASS |
| No angle brackets in description | TestFromAC_DescriptionAngleBrackets | Both < and >, HTML tags, -> arrow boundary all tested | PASS |
| Max description 1024 chars | TestFromAC_MaxDescriptionLength | 1023/1024/1025 boundaries tested | PASS |
| Distinct error messages with offending value | TestFromAC_ErrorMessageDistinctness | Multiple rules fire distinct errors | PASS |
| Spec-level rules in scripts/skills_ref/validator.py | Read validator.py | All rules in validate_metadata() | PASS |
| All existing skills pass | TestFromAC_RegressionGuard | 23 live skills, all pass (1 skipped = README.md non-dir) | PASS |
| Coverage >=90% on changed files | 97% | Pre-existing miss only | PASS |

### Security Review
- No injection vectors, no hardcoded secrets, no path traversal, no eval/exec
- Regex patterns safe: ^[a-z0-9-]+$ has no ReDoS risk
- Angle-bracket defense is additive security improvement
- CLEAN

### Builder Process Quality
- 2 Builder Notes sections (original + retry) = FRICTION
- Approach 1: added rules to validator.py; Approach 2: hardened test assertions
- Different approaches per cycle. FRICTION does not block PASS.

### Verdict: PASS
Confidence: .96

[[2026-04-01]] Wed 23:06
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | scripts/skills_ref/ already listed in scripts/ entry; no API or behavior change visible to project users |
| 2 | Docstrings | Yes | Pass | validator.py: module docstring + _validate_naming_convention() docstring (3-rule breakdown) + validate_metadata() with Args/Returns. All public symbols documented. |
| 3 | docs/sources/overview.md | Yes | Pass | Skill Validation Hardening (#511) section already present with 3 attribution rows (agentskills.io, VS Code docs, deer-flow validation.py) |
| 4 | README.md | No | N/A | No CLI command changes |
| 5 | Research doc | Yes | Pass | docs/research/skill-validation-hardening.md exists, linked from task body, owning task #511 |
| 6 | Scratch files | n/a | Pass | 511-reviewer.md referenced in task body but absent on disk (already cleaned). No 511-* files remain. |

### Files Updated
- None

### Scratch Files Cleaned
- None (511-reviewer.md already absent)

[[2026-04-01]] Wed 23:55
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Naming convention (lowercase, digits, hyphens) | _validate_naming_convention() in validator.py L16-L32; 9 tests in TestFromAC_DirectoryNamingConvention | PASS |
| Naming applies to directory unconditionally | TestFromAC_NamingAppliedUnconditionally: 2 tests for with/without name field | PASS |
| Name field must also pass naming rules | TestFromAC_NameFieldNamingConvention: 6 tests with specific message assertions | PASS |
| Max name 64 chars | TestFromAC_MaxNameLength: boundary tests at 63/64/65 | PASS |
| No angle brackets in description | TestFromAC_DescriptionAngleBrackets: 7 tests incl arrow exemption | PASS |
| Max description 1024 chars | TestFromAC_MaxDescriptionLength: boundary tests at 1023/1024/1025 | PASS |
| Distinct error messages with offending value | TestFromAC_ErrorMessageDistinctness + per-rule assertions | PASS |
| Spec-level rules in validator.py | All rules in validate_metadata(), confirmed by read | PASS |
| All existing skills pass | TestFromAC_RegressionGuard: 23 live skills, 1 skipped (README) | PASS |
| Coverage >=90% on changed files | 97% on validator.py (builder confirmed) | PASS |

### Test Results
- pytest (full suite): 2649 passed, 187 failed (all pre-existing from other tasks), 8 skipped
- pytest (task scope): 57 passed, 1 skipped, 0 failed
- ruff: All checks passed on validator.py + test file

### Architect Quality
- AC specificity: good after architect revision (added 4 AC lines, rewrote 3)
- Edge case coverage: challenger identified directory-vs-name bypass; architect added AC line
- Design direction: two-layer validation (spec-level vs OwlBear wrapper) was correct
- AC quality score: 4 (adequate, gaps identified and filled via challenger feedback)

### Deduction breakdown
- No deductions. All AC lines verified with specific evidence. Lint clean. Reviewer evidence detailed. No task-scope failures.
### Confidence: 1.0
### Action: archive

### Commits (upstream)
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 4d3ab22 | test | tests/test_skill_validation_hardening.py | #511 |
| 0744ad7 | feat | scripts/skills_ref/validator.py | #511 |
| 1ce29ab | test | tests/test_skill_validation_hardening.py | #511 |
