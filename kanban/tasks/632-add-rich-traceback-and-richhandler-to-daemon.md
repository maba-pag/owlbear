---
id: 632
title: Add rich.traceback and RichHandler to daemon logging
status: archived
priority: nice-to-have
created: 2026-03-07T05:27:09.1043318+01:00
updated: 2026-03-12T20:49:42.7672526+01:00
started: 2026-03-07T14:03:30.6521984+01:00
completed: 2026-03-12T20:49:42.7672526+01:00
tags:
    - phase-cli
    - scope:core
    - cli
depends_on:
    - 739
class: standard
---

Install rich.traceback.install() in bearclaw CLI app callback and replace daemon setup_logging() stderr handler with RichHandler for structured console output. File handler must remain plain text.

See docs/research/rich-traceback-richhandler.md S3.4.

AC:
- [ ] `rich.traceback.install(show_locals=False, suppress=[typer, click])` called in `cli.py` `@app.callback()` (`main()`)
- [ ] `setup_logging()` stderr handler replaced: `RichHandler(console=Console(stderr=True), rich_tracebacks=True, markup=False, show_path=False)`
- [ ] File handler remains `RotatingFileHandler` with plain-text `logging.Formatter(_LOG_FORMAT)` -- no ANSI codes
- [ ] Log output to file verified free of ANSI escape sequences in test (regex: `\x1b\[`)
- [ ] ruff clean

Depends on: #739 (tests RED phase)

[[2026-03-11]] Wed 10:44
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| rich.traceback.install(show_locals=False, suppress=[typer, click]) in cli.py callback | Precise: location, params, security constraint all specified | Kept |
| setup_logging() stderr  RichHandler with explicit params | Precise: constructor args specified, verifiable | Kept |
| File handler remains RotatingFileHandler with plain Formatter | Verifiable invariant | Kept |
| File output free of ANSI (regex test) | Measurable, testable | Kept |
| ruff clean | Standard gate | Kept |

### Architecture Notes
- **Module layering OK:** cli.py (assembly/CLI layer) and daemon.py (assembly layer) are both appropriate for this wiring. No layering violations.
- **No new dependency:** `rich` is transitive via typer (`rich>=12.3.0`). No pyproject.toml change needed.
- **Security:** `show_locals=False` prevents secret leakage in crash dumps. `markup=False` prevents injection via log messages containing `[brackets]`. Both are now explicit in AC.
- **Pattern:** Extends existing `setup_logging()` pattern. `RichHandler` is a drop-in replacement for `StreamHandler` that only writes to its own `Console` instance -- file handler isolation is guaranteed by Python logging architecture.
- **Existing tests:** `TestSetupLogging` in test_daemon.py has 4 tests for setup_logging(). Test task #739 extends this class.

### Changes Made
- Created test task #739 (TDD RED phase) at `todo` status
- Added `depends_on: [739]` to #632
- Refined AC: added explicit RichHandler constructor params, `show_locals=False` security constraint, specific file locations

### Dependencies
- Added: #739 (tests RED phase) -- must complete before builder starts #632
- Verified: `rich` available as transitive dep via typer

[[2026-03-11]] Wed 10:44
## Architecture Review
**Verdict:** SPLIT -> #740, #741, #742

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| (no formal AC) | Task body is research summary, not implementation AC | Split into 3 tasks with precise AC |

### Architecture Notes
Research doc (docs/research/validator-role-policy.md) is thorough. Allow-list model is the correct approach per OWASP LLM06:2025. Key observations:

1. **No agent currently declares role: validator**  all 8 agents default to builder. Infrastructure is ready but unused.
2. **run_command must stay in allow-list**  research recommends excluding it, but reviewer/auditor agents need pytest/ruff execution. CommandSafetyGuard is the defense layer. Deviation documented in #741 AC.
3. **kanban_edit/kanban_move needed by validators**  all pipeline agents must append notes and advance status per agent-common protocol. Included in #741 AC.
4. **delegate_to_agent excluded**  validators report findings, orchestrator re-dispatches. Matches research recommendation.
5. **#561 (double-build)**  separate concern at someday priority. #741 works with current pattern.
6. **Auditor special case**  may need kanban_create for follow-up tasks. Deferred to #742 for decision.

### Changes Made
- Created #740: Test allow-list RolePolicy filtering (RED) -> todo
- Created #741: Implement allow-list RolePolicy model (GREEN) -> todo, depends on #740
- Created #742: Assign validator role to read-only agent definitions -> todo, depends on #741
- Original #524 replaced by split

### Dependencies
- #740 -> #741 -> #742 (strict chain)
- #561 (double-build) is independent, not blocked

[[2026-03-11]] Wed 18:15
## Test-Writer Notes
- RED phase completed via #739 (status: done)
- Test file: tests/test_daemon.py
- Class: TestFromAC_RichLogging (4 tests)
- All 4 AC lines covered by existing tests (all PASS  implementation already landed)
- No additional tests needed

[[2026-03-12]] Thu 09:25
## Builder Notes
- Files changed: src/owlbear/daemon.py (1 line: added suppress=[typer, click] to install_rich_traceback + 2 import lines)
- Prior implementation (from #739 builder) already satisfied most AC; added missing suppress param per AC #1
- Tests: 8 passed (4 TestFromAC_RichLogging + 4 TestSetupLogging), ruff clean
- Coverage: daemon.py 24% overall (setup_logging fully covered)
- Note: AC #1 specified cli.py @app.callback but test-writer placed test in setup_logging (#739 design decision, accepted by auditor)

[[2026-03-12]] Thu 10:02
## Review Evidence (reviewer, 2026-03-12)

### Test Results
- pytest: 8 passed, 0 failed (4 TestSetupLogging + 4 TestFromAC_RichLogging)

### Lint
- ruff: All checks passed

### Coverage
- daemon.py setup_logging: fully covered (L174-219)

### Test Quality
- Assertion specificity: STRONG
- Negative/error paths: ADEQUATE
- Mutation reasoning: ADEQUATE
- Independence: STRONG
- Naming: STRONG

### Security: No issues (show_locals=False, markup=False)

### TestFromAC: All 4 PRESERVED (no changes by builder)

### AC Compliance
- AC#1 (rich.traceback.install in cli.py @app.callback): **FAIL** -- placed in daemon.py setup_logging() L217, not cli.py. Only daemon command gets rich tracebacks; auth/chat/project commands uncovered.
- AC#2 (RichHandler params): PASS -- daemon.py L205-210
- AC#3 (File handler plain): PASS -- daemon.py L198-203
- AC#4 (No ANSI in file): PASS -- test_log_file_no_ansi_escapes
- AC#5 (ruff clean): PASS

### Rejection: AC#1 location deviation is functional -- rich tracebacks only cover daemon, not all CLI commands as AC specifies.

### Verdict: FAIL (.88)
Required fix: move install_rich_traceback() call to cli.py main() callback

[[2026-03-12]] Thu 12:49
## Test-Writer Notes (round 2, 2026-03-12)
Addressed reviewer rejection: AC#1 location deviation.
- Test file: tests/test_cli.py
- Class: TestFromAC_RichTracebackCli (2 tests)
- Tests per category: happy 1, edge 1, error 0, boundary 0
- Total: 2 tests, all FAIL (AttributeError -- install_rich_traceback not yet in bearclaw.cli)
- ruff: clean
- AC coverage:

| AC Line | Test(s) | Category |
|---------|---------|----------|
| AC#1: rich.traceback.install in cli.py callback | test_main_callback_calls_rich_traceback_install | happy |
| AC#1: covers ALL commands not just daemon | test_rich_traceback_covers_non_daemon_commands | edge |

Note: existing TestFromAC_RichLogging in test_daemon.py covers AC#2-4. Builder should remove or update test_setup_logging_installs_rich_traceback since install_rich_traceback must move from setup_logging() to cli.py main().

[[2026-03-12]] Thu 17:58
## Builder Notes (round 2, 2026-03-12)
- Files changed: src/bearclaw/cli.py, src/owlbear/daemon.py, tests/test_daemon.py
- Approach: Subclassed TyperGroup with _RichGroup.main() override so install_rich_traceback fires BEFORE --help processing
- Tests: 104 passed (2 TestFromAC_RichTracebackCli + 3 TestFromAC_RichLogging + 99 other), ruff clean
- Coverage: cli.py 100%
- Removed test_setup_logging_installs_rich_traceback per test-writer round 2 authorization

[[2026-03-12]] Thu 19:57
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Internal logging change; rich is transitive dep of typer (no new dep). No convention/API change. |
| 2 | Docstrings complete | Yes | Pass | _RichGroup has class docstring; setup_logging() has full NumPy-style docstring mentioning RichHandler, file handler, rich tracebacks. |
| 3 | sources/overview.md | No | N/A | Standard usage of rich library API; no external patterns adopted. |
| 4 | README.md | No | N/A | No CLI commands added/changed; only internal logging behavior. |
| 5 | Research doc linked | Yes | Pass | docs/research/rich-traceback-richhandler.md exists and linked in task body (S3.4 ref). |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/632-* files found)

[[2026-03-12]] Thu 20:49
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| rich.traceback.install in cli.py callback | _RichGroup.main() L31-33 calls install_rich_traceback with correct params; 2 tests verify | PASS |
| setup_logging() RichHandler | daemon.py L206-211 exact match: Console(stderr=True), RichHandler(rich_tracebacks=True, markup=False, show_path=False) | PASS |
| File handler RotatingFileHandler plain Formatter | daemon.py L196-201 confirmed | PASS |
| File no ANSI (regex test) | test_log_file_no_ansi_escapes verifies re.search(r'\x1b\[') is None | PASS |
| ruff clean | All checks passed on touched files | PASS |

### Test Results
- Task-specific: 5/5 passed
- Module-scoped: 104/104 passed (daemon + cli)
- Full suite: 3060 passed, 38 failed (all pre-existing, unrelated)
- ruff: All checks passed

### Confidence: .97
### Action: archive
