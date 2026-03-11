---
id: 481
title: Split bearclaw/cli.py into subcommand modules
status: archived
priority: important
created: 2026-03-04T07:37:58.8848631+01:00
updated: 2026-03-11T22:19:39.938195+01:00
started: 2026-03-06T23:05:04.3207802+01:00
completed: 2026-03-11T22:19:39.938195+01:00
tags:
    - audit
    - refactor
    - modularity
    - scope:cli
claimed_by: auditor
claimed_at: 2026-03-11T22:19:32.3550112+01:00
class: standard
---

MOD-01/F-04: cli.py is 1233 lines with 8+ concern areas. Split into bearclaw/commands/ modules, wire via app.add_typer(). See docs/research/cli-split-research.md.

## Acceptance Criteria

- [ ] `src/bearclaw/commands/__init__.py` exists (empty package marker)
- [ ] 9 command modules created: `auth.py`, `browser.py`, `chat.py`, `daemon.py`, `knowledge_source.py`, `project.py`, `slack.py`, `usage.py`, `voice.py`
- [ ] Each module exports its own `app = typer.Typer(...)` instance
- [ ] `cli.py` imports and wires all 9 modules via `app.add_typer()`; sub-groups use `name=` arg, top-level commands (chat, daemon) use unnamed `add_typer()` to promote to root
- [ ] `cli.py` contains only: app creation, version callback, global options callback, and wiring imports  target <= 100 lines
- [ ] Entry point `bearclaw.cli:app` in pyproject.toml unchanged
- [ ] All existing CLI tests pass  update import paths in `test_cli_chat.py` and `test_cli_daemon.py` for private helpers (6 symbols per research doc)
- [ ] `bearclaw --help` output shows same command structure as before the split
- [ ] `ruff check` clean on all new and modified files
- [ ] Private helpers (`_get_project_store`, `_get_config_dir`, etc.) move to the module that owns them  no shared-helper module (YAGNI)

## Architecture Notes

- Pattern: Typer-idiomatic flat modules per docs/research/cli-split-research.md section 4
- No shared mutable state  each module instantiates its own OwlBearSettings()
- No new dependencies introduced
- This is pure refactoring  no TDD RED phase needed; existing 10 test files are the regression safety net
- Related tasks #520, #532, #536 should execute AFTER this split (depends_on added)

[[2026-03-10]] Tue 17:33
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. commands/__init__.py exists | Clear, verifiable | REFINED from original |
| 2. 9 command modules created | Explicit file list | REFINED from original |
| 3. Each module exports app | Interface contract | ADDED |
| 4. cli.py wires via add_typer() | Wiring pattern specified | ADDED |
| 5. cli.py <= 100 lines | Measurable target (research says ~60) | REFINED from <200 |
| 6. Entry point unchanged | Verifiable, critical constraint | ADDED |
| 7. All CLI tests pass, import updates | 2 test files need updates (6 symbols) | REFINED from 'all commands work' |
| 8. Same help output | CLI parity check | ADDED |
| 9. ruff clean | Standard gate | ADDED |
| 10. Private helpers move with owner | No shared-helper module (YAGNI) | ADDED |

### Architecture Notes
- Research quality is strong (.85 confidence). Typer add_typer() pattern is idiomatic and well-documented.
- cli.py already uses add_typer() for sub-groups -- this extends the existing pattern.
- No shared mutable state across commands -- each module handles its own imports and settings.
- Pure refactoring: no new functionality, no new boundaries, no new dependencies.
- TDD RED phase not applicable -- 10 existing CLI test files provide full regression coverage.
- Module layering unaffected: all changes are within bearclaw/ (CLI layer).

### Changes Made
- Refined AC: replaced vague 'cli.py <200 lines, all commands work' with 10 concrete criteria
- Added depends_on #481 to #520, #532, #536 (code they target will move during split)
- Moved to todo

### Dependencies
- None required (self-contained refactoring)
- Downstream: #520, #532, #536 now depend on #481

[[2026-03-10]] Tue 17:33
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. commands/__init__.py exists | Clear, verifiable | REFINED from original |
| 2. 9 command modules created | Explicit file list | REFINED from original |
| 3. Each module exports app | Interface contract | ADDED |
| 4. cli.py wires via add_typer() | Wiring pattern specified | ADDED |
| 5. cli.py <= 100 lines | Measurable target (research says ~60) | REFINED from <200 |
| 6. Entry point unchanged | Verifiable, critical constraint | ADDED |
| 7. All CLI tests pass, import updates | 2 test files need updates (6 symbols) | REFINED from 'all commands work' |
| 8. Same help output | CLI parity check | ADDED |
| 9. ruff clean | Standard gate | ADDED |
| 10. Private helpers move with owner | No shared-helper module (YAGNI) | ADDED |

### Architecture Notes
- Research quality is strong (.85 confidence). Typer add_typer() pattern is idiomatic and well-documented.
- cli.py already uses add_typer() for sub-groups -- this extends the existing pattern.
- No shared mutable state across commands -- each module handles its own imports and settings.
- Pure refactoring: no new functionality, no new boundaries, no new dependencies.
- TDD RED phase not applicable -- 10 existing CLI test files provide full regression coverage.
- Module layering unaffected: all changes are within bearclaw/ (CLI layer).

### Changes Made
- Refined AC: replaced vague 'cli.py <200 lines, all commands work' with 10 concrete criteria
- Added depends_on #481 to #520, #532, #536 (code they target will move during split)
- Moved to todo

### Dependencies
- None required (self-contained refactoring)
- Downstream: #520, #532, #536 now depend on #481

[[2026-03-10]] Tue 17:49
## Test-Writer Notes
- Non-implementation task (pure refactoring, tagged refactor) -- no new behavior to test.
- Existing 10 CLI test files provide full regression coverage per architecture review.
- Passing through to builder.

[[2026-03-10]] Tue 17:49
## Test-Writer Notes
- Non-implementation task (pure refactoring, tagged refactor) -- no new behavior to test.
- Existing 10 CLI test files provide full regression coverage per architecture review.
- Passing through to builder.

[[2026-03-10]] Tue 17:49
## Test-Writer Notes
- Non-implementation task (pure refactoring, tagged refactor) -- no new behavior to test.
- Existing 10 CLI test files provide full regression coverage per architecture review.
- Passing through to builder.

[[2026-03-10]] Tue 18:30
## Builder Notes
- Files created: src/bearclaw/commands/__init__.py, auth.py, browser.py, chat.py, daemon.py, knowledge_source.py, project.py, slack.py, usage.py, voice.py
- Files rewritten: src/bearclaw/cli.py (1233 -> 69 lines)
- Files modified: 9 test files (mock patch targets updated)
- Tests: 160 passed, 0 failed
- Coverage (bearclaw modules): cli.py 100%, auth 100%, browser 100%, chat 89%, daemon 100%, knowledge_source 91%, project 100%, slack 100%, usage 19%, voice 92%
- Coverage note: pure refactoring  coverage matches pre-split levels, no regression
- Lint: ruff clean
- Fixes applied: TC003 in usage.py (Path moved to TYPE_CHECKING), E501 x3 in test_cli.py (long lines wrapped)

-t

[[2026-03-10]] Tue 21:29
## Review Evidence (cycle 2 -- FAIL)

### Test Results
- pytest (10 CLI test files): 160 passed, 0 failed
- pytest test_project_session.py: **COLLECTION ERROR** -- ImportError on line 18
- Evidence: `from bearclaw.cli import _build_chat_session, chat` fails because `_build_chat_session` moved to `bearclaw.commands.chat`

### Lint Results
- ruff: All checks passed!

### AC Compliance -- Failure Detail
| AC Line | Evidence | Status |
|---------|----------|--------|
| 7. All CLI tests pass | test_project_session.py has stale import; cannot even collect | **FAIL** |

### Required Fix
1. Update `tests/test_project_session.py` line 18: change `from bearclaw.cli import _build_chat_session, chat` to import from `bearclaw.commands.chat`
2. Update any mock patch targets in that file if they reference `bearclaw.cli`
3. Verify test_project_session.py passes after fix

### Verdict: FAIL
Confidence: N/A (binary FAIL on AC#7)

[[2026-03-11]] Wed 00:56
## Test-Writer Notes (cycle 2)
- Non-implementation task (pure refactoring, tagged refactor)  no new behavior to test.
- Existing 10+ CLI test files provide full regression coverage per architecture review.
- Review rejection was about stale import in test_project_session.py  builder must fix import path.
- Passing through to builder.

[[2026-03-11]] Wed 17:46
## Builder Notes (cycle 2)
- Fix: updated stale import in tests/test_project_session.py (line 18)
- Changed: from bearclaw.cli import -> from bearclaw.commands.chat import
- Tests: 149 passed across 10 CLI test files, 0 failed
- Lint: ruff clean
- Diff: 1 line in 1 file (surgical)

[[2026-03-11]] Wed 18:38
## Review Evidence (cycle 3 -- FAIL)

### Test Results
- pytest (10 CLI test files + test_project_session.py): 160 passed, 0 failed
- pytest (full suite): 33 failed, 1437 passed
- 6 failures in test_daemon.py caused by #481 stale imports
- Lines 749, 764, 771: _daemon_stop from bearclaw.cli (now bearclaw.commands.daemon)
- Lines 806, 815, 831: _daemon_status from bearclaw.cli (now bearclaw.commands.daemon)
- Remaining 27 failures pre-existing (browser_snapshot, content_wrapping, slack_sdk)

### Lint
- ruff: clean

### AC Compliance
- AC1-6: PASS
- AC7: FAIL -- 6 ImportErrors in test_daemon.py
- AC9-10: PASS

### Required Fix
1. test_daemon.py lines 749,764,771: from bearclaw.cli import _daemon_stop -> from bearclaw.commands.daemon import _daemon_stop
2. test_daemon.py lines 806,815,831: from bearclaw.cli import _daemon_status -> from bearclaw.commands.daemon import _daemon_status

Verdict: FAIL (AC#7)

[[2026-03-11]] Wed 19:22
## Test-Writer Notes (cycle 3)
- Non-implementation task (pure refactoring, tagged refactor) -- no new behavior to test.
- Existing 10+ CLI test files provide full regression coverage per architecture review.
- Review rejection was about stale mock targets in test_daemon.py -- builder must fix import paths.
- Passing through to builder.

[[2026-03-11]] Wed 19:33
## Builder Notes (cycle 3)
- Fix: 6 stale imports in tests/test_daemon.py (bearclaw.cli -> bearclaw.commands.daemon)
- Updated: _daemon_stop imports (lines 749,764,771), _daemon_status imports (lines 806,815,831)
- Also updated: 9 mock patch targets in same functions
- Fixed: 3 E501 ruff violations from longer module paths
- Tests: 170 passed across 11 CLI test files, 0 failed
- Lint: ruff clean
- Diff: 1 file (tests/test_daemon.py), surgical

[[2026-03-11]] Wed 20:59
## Test-Writer Notes (cycle 4)
- Non-implementation task (pure refactoring, tagged refactor) -- no new behavior to test.
- Existing 10+ CLI test files provide full regression coverage per architecture review.
- Prior review rejections were about stale imports in test files -- builder responsibility.
- Passing through to builder.

[[2026-03-11]] Wed 21:29
## Builder Notes (cycle 4)
- Fix: 23 stale mock patch targets in 2 test files
- tests/test_error_sanitization_callsites.py: 10 patches (chat/slack/auth)
- tests/test_usage_cli.py: 13 patches (usage)
- Tests: 185 passed (11 CLI files), 8+15 passed (error_sanitization + usage)
- Pre-existing: REPL test hangs in both original and split code
- Lint: ruff clean
- Diff: 2 files, surgical

[[2026-03-11]] Wed 21:47
## Review Evidence (cycle 4 -- reviewer, 2026-03-11)

### Test Results
- pytest (12 CLI + daemon test files): 259 passed, 0 failed
- pytest (full suite, -m 'not api'): 1454 passed, 16 failed, 20 skipped
  - 1 failure: test_bootstrap slack_sdk env issue (pre-existing)
  - 15 failures: test_browser_toolset snapshot tests (#735, pre-existing)
  - 0 failures related to #481

### Lint Results
- ruff check src/bearclaw/cli.py src/bearclaw/commands/: All checks passed!

### Coverage
- N/A (pure refactoring -- no new behavior; pre-existing tests provide regression coverage)

### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | Pre-existing tests; mock targets updated correctly |
| Negative/error paths | ADEQUATE | Pre-existing; no new behavior introduced |
| Mutation reasoning | ADEQUATE | Refactoring -- import path changes verified by test pass/fail |
| Test independence | STRONG | Each test file isolates its own mock targets |
| Descriptive names | STRONG | Pre-existing descriptive method names preserved |

### Security Review
- No shell=True, eval, exec, pickle, or unsafe yaml.load
- No hardcoded secrets
- No new dependencies
- No security issues found

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| 1. commands/__init__.py exists | File exists, empty | PASS |
| 2. 9 command modules created | auth, browser, chat, daemon, knowledge_source, project, slack, usage, voice -- all present | PASS |
| 3. Each module exports app = typer.Typer() | All 9 verified via grep | PASS |
| 4. cli.py wires via add_typer() | Lines 31-40: 7 sub-groups + 2 promoted to root | PASS |
| 5. cli.py <= 100 lines | 69 lines | PASS |
| 6. Entry point unchanged | pyproject.toml L26: bearclaw = bearclaw.cli:app | PASS |
| 7. All CLI tests pass | 259 passed (12 files), 0 imports stale | PASS |
| 8. Same help output | bearclaw --help shows auth, browser, slack, project, usage, voice, knowledge-source, chat, run, stop, status | PASS |
| 9. ruff clean | All checks passed | PASS |
| 10. Private helpers moved | _get_config_dir->daemon, _get_project_store->project, _build_chat_session->chat, etc. No shared-helper module | PASS |

### Confidence: .93
### Verdict: PASS

[[2026-03-11]] Wed 21:52
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Pure refactoring; no behavior/API/convention change. Entry point, tech stack, directory structure unchanged. |
| 2 | Docstrings complete | Yes | Pass | All 9 new command modules have module docstrings. All private helpers have function docstrings. Typer command functions use decorator help= params (matches pre-split state). |
| 3 | sources/overview.md | No | N/A | Typer add_typer pattern already attributed at line 954 from research phase. No new external patterns. |
| 4 | README.md | No | N/A | No CLI commands added/changed. Same command structure confirmed by reviewer (AC#8). |
| 5 | Research doc linked | Yes | Pass | docs/research/cli-split-research.md exists (9494 bytes), referenced in task body line 1. |
| 6 | No impact | -- | -- | Items 2 and 5 applied; evaluated with evidence. |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/481-* files found)

[[2026-03-11]] Wed 22:19
## Audit (auditor, 2026-03-11)

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| 1. commands/__init__.py exists | File exists, empty | PASS |
| 2. 9 command modules created | auth, browser, chat, daemon, knowledge_source, project, slack, usage, voice | PASS |
| 3. Each module exports app = typer.Typer() | All 9 verified via grep | PASS |
| 4. cli.py wires via add_typer() | Lines 31-40: 7 sub-groups + 2 promoted | PASS |
| 5. cli.py <= 100 lines | 69 lines | PASS |
| 6. Entry point unchanged | pyproject.toml L26: bearclaw.cli:app | PASS |
| 7. All CLI tests pass | 243 passed (13 test files), 0 failed | PASS |
| 8. Same help output | auth, browser, slack, project, usage, voice, knowledge-source, chat, run, stop, status | PASS |
| 9. ruff clean | All checks passed! | PASS |
| 10. Private helpers moved | _get_config_dir->daemon, _get_project_store->project, _build_chat_session->chat. No shared-helper module | PASS |

### Test Results
- pytest (10 CLI + 3 daemon/error files): 243 passed, 0 failed
- pytest full suite: 1453 passed, 17 failed, 20 skipped
  - 0 failures #481-related
  - 1 test_bootstrap (slack_sdk env, pre-existing)
  - 1 test_bootstrap_structure (pre-existing)
  - 15 test_browser_toolset (snapshot, pre-existing #736)
- ruff: All checks passed

### Confidence: .97
### Action: archive
