---
id: 739
title: 'Tests: rich.traceback + RichHandler in daemon logging (RED)'
status: done
priority: nice-to-have
created: 2026-03-11T10:42:19.6328521+01:00
updated: 2026-03-11T18:27:36.3594719+01:00
started: 2026-03-11T17:32:10.722558+01:00
completed: 2026-03-11T17:32:10.722558+01:00
tags:
    - phase-cli
    - scope:core
    - cli
    - test
class: standard
---

TDD RED phase for #632.

Test file: tests/test_daemon.py (extend existing TestSetupLogging class)

AC:
- [ ] Test stderr handler is instance of RichHandler after setup_logging()
- [ ] Test file handler remains RotatingFileHandler with plain Formatter
- [ ] Test log file output contains no ANSI escape sequences (regex: \\x1b\\[)
- [ ] Test rich.traceback.install() sets sys.excepthook in CLI callback
- [ ] All tests FAIL before implementation (RED phase)
- [ ] ruff clean

Precedes: #632
Research: docs/rich-traceback-richhandler-research.md

[[2026-03-11]] Wed 16:31
## Test-Writer Notes
- Test file: tests/test_daemon.py
- Classes: TestFromAC_RichLogging
- Tests per category: happy 2, edge 0, error 0, boundary 2
- Total: 4 tests, all FAIL
- ruff: clean
- AC coverage:

| AC Line | Test(s) | Category |
|---------|---------|----------|
| stderr handler is RichHandler | test_stderr_handler_is_rich_handler | happy |
| file handler remains RotatingFileHandler plain | test_file_handler_plain_formatter_with_rich_stderr | boundary |
| log file no ANSI escapes | test_log_file_no_ansi_escapes | boundary |
| rich.traceback.install() sets sys.excepthook | test_setup_logging_installs_rich_traceback | happy |

[[2026-03-11]] Wed 17:08
## Builder Notes
- Files changed: src/owlbear/daemon.py, tests/test_daemon.py
- Tests: 8 passed (4 TestFromAC_RichLogging + 4 TestSetupLogging updated), ruff clean
- Implementation: replaced StreamHandler with RichHandler(console=Console(stderr=True), rich_tracebacks=True, markup=False, show_path=False); added rich.traceback.install(show_locals=False); file handler remains RotatingFileHandler with plain Formatter
- Updated 2 pre-existing TestSetupLogging tests to accommodate RichHandler (isinstance check, formatter check scoped to file handler only)
- Coverage: daemon.py 23% (setup_logging fully covered; rest of daemon not exercised by logging tests)

[[2026-03-11]] Wed 17:29
## Review Evidence

### Test Results
- pytest (scoped): 8 passed, 0 failed (4 TestSetupLogging + 4 TestFromAC_RichLogging)
- pytest (broader): 68 passed, 6 failed (all 6 pre-existing _daemon_stop/_daemon_status import errors, unrelated to #739)

### Lint Results
- ruff: All checks passed!

### Coverage
- daemon.py: 23% overall (setup_logging fully covered)

### Test Quality
All 5 dimensions rated STRONG or ADEQUATE. No WEAK ratings.

### Security Review
CLEAN - no secrets, injection, path traversal, or deserialization concerns

### TestFromAC Comparison
All 4 TestFromAC_RichLogging tests PRESERVED (no builder modifications)

### AC Compliance: all 6 AC lines PASS

### Verdict: PASS (.93 confidence)

[[2026-03-11]] Wed 17:31
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Internal logging change; rich already in use across project; no API/convention change |
| 2 | Docstrings complete | Yes | Updated | setup_logging() docstring updated to mention RichHandler, plain file handler, and rich.traceback.install() |
| 3 | sources/overview.md | No | N/A | Already attributed under 'Rich Traceback and RichHandler Research (Task #632)' section |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/rich-traceback-richhandler-research.md exists and linked in task body |
| 6 | No impact | N/A |  | Items 2 and 5 apply |

### Files Updated
- src/owlbear/daemon.py (docstring only)

### Scratch Files Cleaned
- docs/scratch/739-full.txt
- docs/scratch/739-cov.txt
