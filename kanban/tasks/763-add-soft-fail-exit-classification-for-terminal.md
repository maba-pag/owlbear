---
id: 763
title: Add soft-fail exit classification for terminal commands
status: archived
priority: nice-to-have
created: 2026-03-12T21:40:09.2923504+01:00
updated: 2026-03-13T18:48:52.6372031+01:00
started: 2026-03-13T18:48:51.9962351+01:00
completed: 2026-03-13T18:48:51.9962351+01:00
tags:
    - scope:core
    - tooling
depends_on:
    - 765
class: standard
---

Implement soft-fail exit classification for terminal commands (GREEN phase).
See docs/research/claude-context-mode.md S3d.3.
Depends on #765 (test task).

AC:
- [ ] Add soft_fail: bool = False field to TerminalResult frozen dataclass (default preserves backward compat)
- [ ] Add classify_exit to __all__ exports
- [ ] classify_exit(exit_code: int, stdout: str) -> bool pure function in terminal.py
- [ ] Returns True when exit_code == 1 and stdout.strip() is non-empty
- [ ] run_command() populates soft_fail field via classify_exit() after decoding stdout
- [ ] _run_command_wrapper annotates exit_code line with (soft-fail) when result.soft_fail is True
- [ ] All tests from #765 pass (GREEN phase)
- [ ] ruff clean

[[2026-03-13]] Fri 09:01
## Architecture Review
**Verdict:** APPROVED (split into TDD pair)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Add soft_fail: bool field to TerminalResult | Good but missing default | Refined: `soft_fail: bool = False` for backward compat |
| classify_exit(exit_code, stdout) -> bool | Clear signature, pure function | Kept  added `__all__` export requirement |
| Returns True when exit_code == 1 and stdout non-empty | `non-empty` ambiguous re whitespace | Refined: `stdout.strip()` is non-empty |
| _run_command_wrapper annotates (soft-fail) | Clear and verifiable | Kept |
| run_command() populates soft_fail | Clear | Kept  specified `after decoding stdout` |
| Tests cover scenarios | Tests bundled with impl  TDD violation | Split into #765 (RED) + #763 (GREEN) |

### Architecture Notes
- **Pattern match:** `classify_exit()` follows `_truncate()` pattern (module-level pure function in terminal.py). Make it public since callers may use it directly.
- **Dataclass compat:** `TerminalResult` is `frozen=True, slots=True`. Adding `soft_fail: bool = False` at the end preserves all existing callers (4 positional args + keyword default).
- **No layer violation:** All changes within `tools/terminal.py`  same layer, no new imports.
- **Whitespace edge case:** `stdout.strip()` prevents whitespace-only output (e.g. trailing newline) from triggering soft-fail.

### Changes Made
- Created #765 (RED test task) with 9 AC lines
- Refined #763 AC (added default, __all__, stdout.strip(), ruff clean)
- Added #763 depends_on #765
- Moved #765 -> todo, #763 -> todo

### Dependencies
- #765 (tests) must complete before #763 (impl)
- No external dependencies  self-contained within terminal.py

-t

[[2026-03-13]] Fri 09:01
## Architecture Review
**Verdict:** APPROVED (split into TDD pair)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Add soft_fail: bool field to TerminalResult | Good but missing default | Refined: `soft_fail: bool = False` for backward compat |
| classify_exit(exit_code, stdout) -> bool | Clear signature, pure function | Kept  added `__all__` export requirement |
| Returns True when exit_code == 1 and stdout non-empty | `non-empty` ambiguous re whitespace | Refined: `stdout.strip()` is non-empty |
| _run_command_wrapper annotates (soft-fail) | Clear and verifiable | Kept |
| run_command() populates soft_fail | Clear | Kept  specified `after decoding stdout` |
| Tests cover scenarios | Tests bundled with impl  TDD violation | Split into #765 (RED) + #763 (GREEN) |

### Architecture Notes
- **Pattern match:** `classify_exit()` follows `_truncate()` pattern (module-level pure function in terminal.py). Make it public since callers may use it directly.
- **Dataclass compat:** `TerminalResult` is `frozen=True, slots=True`. Adding `soft_fail: bool = False` at the end preserves all existing callers (4 positional args + keyword default).
- **No layer violation:** All changes within `tools/terminal.py`  same layer, no new imports.
- **Whitespace edge case:** `stdout.strip()` prevents whitespace-only output (e.g. trailing newline) from triggering soft-fail.

### Changes Made
- Created #765 (RED test task) with 9 AC lines
- Refined #763 AC (added default, __all__, stdout.strip(), ruff clean)
- Added #763 depends_on #765
- Moved #765 -> todo, #763 -> todo

### Dependencies
- #765 (tests) must complete before #763 (impl)
- No external dependencies  self-contained within terminal.py

[[2026-03-13]] Fri 13:46
## Test-Writer Notes

[[2026-03-13]] Fri 13:46
- Tests already written under #765 (TDD pair, now done).
- Test file: tests/test_soft_fail_exit.py
- Classes: TestFromAC_ClassifyExit, TestFromAC_TerminalResultSoftFail, TestFromAC_RunCommandSoftFail, TestFromAC_WrapperSoftFailAnnotation
- Total: 20 tests covering all 8 AC lines.
- No additional tests needed; passing through to builder.

[[2026-03-13]] Fri 17:04
## Builder Notes
- Files changed: none (implementation already present in commit 53033e1 from #764)
- Tests: 20 passed (TestFromAC_ClassifyExit 11, TestFromAC_TerminalResultSoftFail 3, TestFromAC_RunCommandSoftFail 4, TestFromAC_WrapperSoftFailAnnotation 3)
- Lint: ruff clean
- Coverage: 62% on tools/terminal.py (classify_exit and soft_fail paths fully covered; misses are truncation and timeout paths unrelated to this AC)
- Evidence: all 20 TestFromAC tests GREEN, no code changes required
- Fixes applied: None -- all AC items already implemented in terminal.py (soft_fail field, classify_exit export+function, run_command population, wrapper annotation)

[[2026-03-13]] Fri 17:56
## Review Evidence
See docs/scratch/763-reviewer.md for full evidence.
Verdict: PASS (confidence .95)

[[2026-03-13]] Fri 18:48
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| soft_fail: bool = False on TerminalResult | terminal.py L57 | PASS |
| classify_exit in __all__ | terminal.py L35 | PASS |
| classify_exit(exit_code, stdout) -> bool | terminal.py L60 | PASS |
| Returns True when exit_code==1 and stdout.strip() non-empty | terminal.py L70 | PASS |
| run_command() populates soft_fail | terminal.py L263 | PASS |
| _run_command_wrapper annotates (soft-fail) | terminal.py L181-182 | PASS |
| All tests from #765 pass | 20/20 + 37 terminal_tools passed | PASS |
| ruff clean | All checks passed | PASS |

### Test Results
- pytest (scoped): 57 passed
- pytest (full): 3226 passed, 23 failed (all pre-existing)
- ruff: clean

### Confidence: .97
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 53033e1 | feat | terminal.py | #764 (includes #763 impl) |
| 1694abd | feat | test_soft_fail_exit.py, terminal.py docstring | #763 |
