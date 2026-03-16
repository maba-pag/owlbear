---
id: 805
title: Tests for _cli_error helper
status: archived
priority: nice-to-have
created: 2026-03-14T20:56:49.161519+01:00
updated: 2026-03-16T05:06:58.7348671+01:00
started: 2026-03-16T05:06:41.0111612+01:00
completed: 2026-03-16T05:06:41.0111612+01:00
tags:
    - test
    - scope:cli
    - type:test
depends_on:
    - 481
class: standard
---

Test task paired with #532. Function will be defined in src/bearclaw/commands/__init__.py per #532 AC.

## AC
- [ ] Test that _cli_error(msg) writes 'Error: {msg}' to stderr and raises typer.Exit(code=1)
- [ ] Test NoReturn annotation is present (inspect check)
- [ ] Parametrize message arg with >=3 formats representative of actual usage (plain string, f-string interpolation result, empty string)
- [ ] ruff clean

Note: Existing CLI tests (test_cli_browser.py, test_cli.py, test_cli_auth.py, etc.) already cover error paths at call sites. Migration regression is covered by #532 AC (all existing CLI tests pass). This task tests the helper function itself.

[[2026-03-15]] Sun 04:11
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| _cli_error(msg) writes 'Error: {msg}' to stderr + raises Exit(1) | Clear, verifiable with capsys or CliRunner stderr capture | Keep |
| NoReturn annotation present (inspect check) | Clear, verifiable via inspect.get_type_hints | Keep |
| Parametrize across representative call sites | Vague -- 'call sites' conflates unit test with migration regression | Refined to '>=3 message formats' |
| ruff clean | Standard gate | Keep |

### Architecture Notes
- Single domain: scope:cli test. No core/ or memory/ changes.
- Module layering: tests import from bearclaw.commands (correct).
- TDD compliance: this IS the TDD RED task preceding #532.
- Pattern consistency: follows existing CLI test patterns (CliRunner, exit_code + output assertions).
- Existing CLI tests already cover error-exit behavior at all 23 call sites. This task tests the helper function itself -- no overlap.
- Security surface: none.
- KISS: removed vague 'call sites' framing from AC 3. Parametrize is scoped to message formats only.

### Changes Made
- Refined AC 3: 'Parametrize across representative call sites' -> 'Parametrize message arg with >=3 formats (plain, f-string result, empty)'
- Added note clarifying existing test coverage vs this task's scope
- Added import location pointer (src/bearclaw/commands/__init__.py)

### Dependencies
- Verified: #481 (CLI split) -- archived, satisfied
- Verified: #532 depends_on #805 -- correct TDD ordering

[[2026-03-15]] Sun 04:29
## Test-Writer Notes
- Test file: tests/test_cli_error_helper.py
- Classes: TestFromAC_CliErrorBehavior, TestFromAC_CliErrorNoReturnAnnotation, TestFromAC_CliErrorMessageFormats
- Tests per category: happy 5, edge 1, error 0, boundary 4
- Total: 10 tests, all FAIL (ImportError)
- ruff: clean

[[2026-03-15]] Sun 04:38
## Builder Notes
- Implementation: src/bearclaw/commands/__init__.py
- 8/10 tests PASS, 2 FAIL due to test-writer bugs:
  1. inspect.get_type_hints does not exist (should be typing.get_type_hints)
  2. empty-string test: strip() removes trailing space, impossible match
- BLOCKED awaiting test fixes

[[2026-03-15]] Sun 12:41
## Test-Writer Notes (v2)
Implementation already exists (#532 archived). Tests verified against live code.
- Test file: tests/test_cli_error_helper.py
- Classes: TestFromAC_CliErrorBehavior, TestFromAC_CliErrorNoReturnAnnotation, TestFromAC_CliErrorMessageFormats
- Total: 10 AC tests, all PASS
- ruff: clean

[[2026-03-15]] Sun 13:55
## Builder Notes
- Non-implementation task: _cli_error already exists in src/bearclaw/commands/__init__.py (from #532)
- Tests: 32 passed, 0 failed
- Coverage: commands/__init__.py 100%
- Lint: ruff clean
- No code changes needed  implementation pre-existed

[[2026-03-15]] Sun 14:29
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Pure test task for private helper; no behavior/API change |
| 2 | Docstrings complete | No | N/A | _cli_error already has docstring; test file has module docstring |
| 3 | sources/overview.md | No | N/A | No external patterns; standard pytest usage |
| 4 | README.md | No | N/A | No CLI command changes |
| 5 | Research doc linked | No | N/A | No research phase for this test task |
| 6 | No impact | Yes | Pass | Test-only task with no docs impact |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/805-* files found)

[[2026-03-15]] Sun 14:29
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Pure test task for private helper; no behavior/API change |
| 2 | Docstrings complete | No | N/A | _cli_error already has docstring; test file has module docstring |
| 3 | sources/overview.md | No | N/A | No external patterns |
| 4 | README.md | No | N/A | No CLI command changes |
| 5 | Research doc linked | No | N/A | No research phase |
| 6 | No impact | Yes | Pass | Test-only task with no docs impact |

### Files Updated
- None

### Scratch Files Cleaned
- None

[[2026-03-16]] Mon 05:06
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| _cli_error(msg) writes 'Error: {msg}' to stderr + raises typer.Exit(code=1) | typer.echo(f'Error: {msg}', err=True) + raise typer.Exit(code=1) commands/__init__.py L10-11; TestFromAC_CliErrorBehavior 5 tests | PASS |
| NoReturn annotation present | -> NoReturn at L8; test uses get_type_hints() | PASS |
| Parametrize >=3 message formats | 4 params in TestFromAC_CliErrorMessageFormats: plain, f-string, empty, long | PASS |
| ruff clean | All checks passed | PASS |

### Test Results
- pytest: environment-wide hang (owlbear.config import blocks pytest startup -- affects all tasks in this session). Builder evidence: 32/32 passed, ruff clean.
- ruff: All checks passed

### Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 8dc0f5d | chore | src/bearclaw/commands/__init__.py, tests/test_cli_error_helper.py | #532 |

### Confidence: .95
### Action: archive
