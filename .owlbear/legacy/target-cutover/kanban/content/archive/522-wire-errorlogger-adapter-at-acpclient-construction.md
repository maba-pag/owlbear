---
id: 522
title: Wire ErrorLogger adapter at AcpClient construction sites
status: archived
priority: medium
created: 2026-04-01 15:15:04.161398+02:00
updated: 2026-04-10 02:14:58.286651+02:00
started: 2026-04-06 07:08:31.396061+02:00
completed: 2026-04-10 02:14:58.286651+02:00
tags:
- phase-2
- scope:orchestrator
- type:build
depends_on:
- 521
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Create an _ErrorLogger adapter bridging ErrorJournal to the _ErrorLogger Protocol and pass it at AcpClient construction sites.

## AC
- [ ] Adapter class implementing _ErrorLogger Protocol that delegates to ErrorJournal.log() with bound session_id — place in error_journal.py (cohesive with adapted object)
- [ ] session_id: use a fixed immutable sentinel string ('pre-session' or empty string, builder documents choice). Do NOT use a mutable instance attribute — concurrent dispatch_entry() calls via asyncio.gather() in _dispatch_parallel() share the same AcpClient and will race.
- [ ] AcpClient construction in orchestrate() (loop.py) passes error_logger= adapter instance
- [ ] orchestrate() accepts optional error_journal: ErrorJournal | None parameter (follow AuditLog injection pattern); default path: .owlbear/error-journal.jsonl
- [ ] Unit tests verify adapter delegates correctly (mock ErrorJournal, assert log() called with expected args including sentinel session_id)
- [ ] No changes to acp_client.py (Protocol already defined by #521)

Follow-up from #148 arch review. Without this task, _ErrorLogger injection is dead code.
See .owlbear/research/errorlogger-adapter-wiring-522.md for full analysis.

[[2026-04-06]] Mon 01:14
## Research
- Research doc: .owlbear/research/errorlogger-adapter-wiring-522.md
- Sources: 8 studied, 5 high-relevance (all internal codebase)
- Recommendation: Class adapter in error_journal.py, fixed 'pre-session' sentinel, wired at orchestrate() (confidence: .85)
- Follow-up tasks created: none — existing AC covers full scope
- Decision requests: none

## Challenge Results
- Challenger: reconsider (confidence 0.82)
- Confidence in original: .85
- Key challenges: mutable session_id races under parallel asyncio.gather() dispatch
- Researcher response: accepted — revised to fixed sentinel (concurrency-safe), mutable approach removed

[[2026-04-06]] Mon 01:33
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Adapter creation + wiring are tightly coupled — adapter is useless without wiring |
| Interface clarity | PASS (refined) | AC#2 now explicitly prohibits mutable session_id; AC#4 specifies AuditLog injection pattern |
| Dependency correctness | PASS | Updated depends_on from #148 (archived/redundant) to #521 (actual Protocol implementer) |
| Module layering | PASS | error_journal.py adapter wraps ErrorJournal (same package); loop.py consumes it — correct direction |
| TDD compliance | PASS | Pipeline flow: test-writer processes at todo before builder |
| KISS/YAGNI | PASS | ~10 LOC class adapter, follows existing patterns, no speculative features |
| Premise challenge | PASS | _ErrorLogger injection is dead code without this adapter — task fills a real gap |
| Pattern consistency | PASS | Follows AuditLog injection pattern (loop.py L430) and _CancelSignal Protocol pattern (acp_client.py) |
| Security surface | PASS | Local file I/O only, no new system boundaries |
| Single domain | PASS | scope:orchestrator — adapter, journal, and wiring all in orchestrator package |

### Challenge Results
- Challenger: proceed (confidence 0.88)
- Architect response: accepted — applied two recommended refinements (AC#2 concurrency constraint, dependency #148 to #521)

### AC Refinements Applied
1. AC#2: Added explicit prohibition on mutable session_id with asyncio.gather() race rationale
2. AC#4: Specified AuditLog injection pattern and default path (.owlbear/error-journal.jsonl)
3. AC#1: Specified placement in error_journal.py
4. AC#5: Added mock/assert specifics for test-writer clarity
5. AC#6: Updated Protocol attribution from #148 to #521
6. Dependency: replaced depends_on #148 (archived/redundant) with #521 (actual implementer)

### Codebase Evidence
- _ErrorLogger Protocol: acp_client.py L43-46
- AcpClient constructor: acp_client.py L89-97 (error_logger kwarg at L94)
- ErrorJournal.log(): error_journal.py L48-56 (session_id gap confirmed)
- Construction site: loop.py L471 — AcpClient(conn) with no error_logger
- AuditLog precedent: loop.py L430 — audit_log parameter on orchestrate()
- Concurrency: _dispatch_parallel() uses asyncio.gather() — shared AcpClient instance

### Verdict: APPROVE (refined)
### Action Taken: Refined 6 AC lines for precision, updated dependency graph, advancing to todo

[[2026-04-06]] Mon 01:34
Architecture review complete. AC refined (6 lines tightened), dependency updated #148 to #521, all 10 criteria PASS. Challenger: proceed at 0.88. Advancing to todo.

[[2026-04-06]] Mon 03:13
## Test-Writer Notes
- Test file: tests/test_errorlogger_adapter_wiring_522.py
- Classes: TestFromAC_ErrorLoggerAdapter, TestFromAC_OrchestrateWiring
- Tests per category: happy 5, edge 2, boundary 6, wiring 4
- Total: 17 tests, all FAIL (ImportError: cannot import name 'ErrorLoggerAdapter')
- ruff: clean
- AC coverage: AC#1 (adapter class) — 12 tests; AC#2 (sentinel) — 4 tests; AC#3 (AcpClient wiring) — 2 tests; AC#4 (orchestrate param + default path) — 3 tests; AC#6 (constraint, not testable)
- Note: VS Code file tools blocked by path guard bug on absolute Windows paths; file written via PowerShell terminal (documented workaround)

[[2026-04-06]] Mon 06:37
## Builder Notes

### Files Changed
- `serve/orchestrator/src/owlbear_orchestrator/error_journal.py` — added `ErrorLoggerAdapter` class (~18 LOC)
- `serve/orchestrator/src/owlbear/orchestrator/loop.py` — added import, `error_journal=` param on `orchestrate()`, default `ErrorJournal` creation, `ErrorLoggerAdapter` wiring into `AcpClient`

### Implementation
- `ErrorLoggerAdapter`: class-level `_SESSION_ID = "pre-session"` sentinel (concurrency-safe, immutable). All 3 args (`category`, `method`, `message`) keyword-only. Delegates `str(category)` to `ErrorJournal.log()`.
- `orchestrate()`: added `error_journal: ErrorJournal | None = None` param (follows AuditLog injection pattern). When `None`, creates `ErrorJournal(Path(".owlbear/error-journal.jsonl"))`. Passes `ErrorLoggerAdapter(error_journal)` as `error_logger=` to `AcpClient(conn, ...)`.

### Test Results
- Target: 17/17 passed (all `TestFromAC_*`)
- Regression: 70 passed (serve/orchestrator/tests + test_error_journal + test_acp_client)
- No `TestBuilderDiscovered` tests required (no edge cases missed)

### Lint
- ruff: clean on both changed files

### Coverage
- `ErrorLoggerAdapter` new lines fully covered; pre-existing `ErrorJournal` methods at 55% overall (covered by `test_error_journal.py`)
- `loop.py` new wiring lines covered; overall module coverage low from pre-existing code (own test suite)

### Commit
- `23f0cc1` feat(orchestrator): add ErrorLoggerAdapter and wire into orchestrate() (#522)

[[2026-04-06]] Mon 06:46
## Review Evidence

### Test Results
- pytest (task tests): **17 passed, 0 failed** (`tests/test_errorlogger_adapter_wiring_522.py`)
- pytest (regression): **105 passed** — all `test_orchestrate_*` and `test_acp_client` tests pass. 8 pre-existing failures in `TestFromAC_WaveAssembly` / `TestFromAC_FormatPrompt` (unrelated to changed files; waves.py / format logic not touched by this task).

### Lint
- **Clean** on all changed files (`error_journal.py`, `loop.py`, `test_errorlogger_adapter_wiring_522.py`)
- 5 pre-existing violations in `mcp-kanban/server.py` and its test — out of scope, not introduced by this task.

### Coverage
- `owlbear_orchestrator.error_journal`: 55% (new `ErrorLoggerAdapter` class fully exercised; pre-existing `ErrorJournal` methods covered by separate `test_error_journal.py`)
- `owlbear.orchestrator.loop`: 90% (meets threshold)
- `owlbear_orchestrator.acp_client`: 99%

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage
| AC Line | Mapped Test(s) | Would Fail If AC Violated? | Verdict |
|---------|---------------|--------------------------|---------|
| AC#1 — adapter in error_journal.py, delegates to ErrorJournal.log() | `test_log_error_calls_journal_log`, `test_log_error_forwards_*` (×3), `test_log_error_all_error_categories_delegate` | Yes — mock.assert_called_once() and kwargs checks catch missing delegation | COVERED |
| AC#2 — fixed immutable sentinel 'pre-session' class constant | `test_sentinel_session_id_is_non_empty_string`, `test_sentinel_same_on_every_call`, `test_sentinel_not_derived_from_instance_state` | Yes — checks sentinel is non-empty, identical across calls, identical across instances | COVERED |
| AC#3 — AcpClient receives error_logger= adapter | `test_orchestrate_passes_error_logger_to_acp_client`, `test_orchestrate_uses_provided_error_journal_for_adapter` | Yes — inspects call_args.kwargs["error_logger"] and exercises delegation | COVERED |
| AC#4 — orchestrate() error_journal param + default path | `test_orchestrate_accepts_error_journal_parameter`, `test_orchestrate_error_journal_defaults_to_none`, `test_orchestrate_default_error_journal_path` | Yes — signature inspection and patched ErrorJournal constructor call check | COVERED |
| AC#5 — tests with mock + assert | All 17 tests use _make_mock_journal() + assert at least one specific kwarg | Yes | COVERED |
| AC#6 — no changes to acp_client.py | N/A (structural constraint) | acp_client.py absent from changed files list | COVERED |

#### Security Review
- No hardcoded secrets, tokens, or credentials.
- No injection vectors (no SQL/shell/template construction).
- No path traversal (`Path(".owlbear/error-journal.jsonl")` is a hardcoded literal).
- No insecure deserialization.
- No new external dependencies.
- **No issues.**

#### Test Integrity
| Original Test | Change Made | Assessment |
|--------------|------------|-----------|
| All 17 `TestFromAC_*` methods | No modifications detected — test file matches test-writer's output | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|---------|
| Assertion specificity | STRONG | All tests assert specific values: `kwargs["method"] == "new_session"`, `sentinel == sentinel2`, `Path(path_arg) == Path(".owlbear/error-journal.jsonl")` |
| Negative/error-path coverage | STRONG | Edge tests cover empty message and empty method forwarding |
| Manual mutation reasoning | STRONG | Removing category forwarding fails `test_log_error_forwards_category_as_string_value`; swapping sentinel fails `test_sentinel_same_on_every_call` |
| Test independence | STRONG | Each test creates its own `_make_mock_journal()` and adapter instance |
| Descriptive test names | STRONG | All names describe intent clearly |

#### Data Safety
- `_SESSION_ID` is a class-level constant — no shared mutable state between concurrent calls. Concurrency concern from architecture review fully addressed.
- **No issues.**

#### Implementation-Aware Gaps
- `log_error()` has 3 parameters; happy-path, edge-case (empty strings), and boundary tests all exercise the full call path.
- Default `ErrorJournal` creation in subprocess path is covered by `test_orchestrate_default_error_journal_path`.
- Early-return `client is not None` path in `orchestrate()` is not a new code path; pre-existing coverage applies.
- **No untested paths in new code.**

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- `log_error()` uses `category: object` (wider than Protocol's `category: ErrorCategory`) — type-safe under contravariance for structural subtyping, no action needed.
- Coverage on `error_journal.py` overall shows 55%; the missing lines are pre-existing `load()` / `_rotate()` methods covered by `test_error_journal.py`, not a gap in this task's scope.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC#1 — adapter in error_journal.py delegates to ErrorJournal.log() | `error_journal.py:104–118` — `ErrorLoggerAdapter._journal.log(...)` | `test_log_error_calls_journal_log` | PASS |
| AC#2 — immutable class-level sentinel `_SESSION_ID = "pre-session"` | `error_journal.py:106` — `_SESSION_ID = "pre-session"` class attribute | `test_sentinel_not_derived_from_instance_state` | PASS |
| AC#3 — AcpClient(conn, error_logger=ErrorLoggerAdapter(...)) | `loop.py:472` — `AcpClient(conn, error_logger=ErrorLoggerAdapter(error_journal))` | `test_orchestrate_passes_error_logger_to_acp_client` | PASS |
| AC#4 — orchestrate() error_journal param, None default, .owlbear/error-journal.jsonl | `loop.py:432` — `error_journal: ErrorJournal | None = None`; `loop.py:469–470` — default creation | `test_orchestrate_error_journal_defaults_to_none`, `test_orchestrate_default_error_journal_path` | PASS |
| AC#5 — mock-based delegation tests with sentinel session_id | 17 passing tests in `test_errorlogger_adapter_wiring_522.py` | All 17 | PASS |
| AC#6 — no changes to acp_client.py | acp_client.py absent from changed file list; `_ErrorLogger` Protocol at acp_client.py:40–46 unchanged | N/A | PASS |

### Confidence: .95
### Verdict: PASS

[[2026-04-06]] Mon 06:51
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A | `orchestrate()` gained optional `error_journal` param; new `ErrorLoggerAdapter` class added. `copilot-instructions.md` is 5 lines (Project Identity only — no internal API tables to update). No change needed. |
| 2 | Module docstrings | Yes | Verified | `error_journal.py`: `ErrorLoggerAdapter` has accurate class docstring (sentinel rationale, concurrency safety) and `log_error()` method docstring. `loop.py`: `orchestrate()` docstring updated by builder with `error_journal:` arg entry including default path. All public API accurate. |
| 3 | External attribution | No | N/A | Task body confirms "all internal codebase" — 8 sources studied, 5 high-relevance, all internal. No `.owlbear/sources/overview.md` update needed. |
| 4 | CLI changes | No | N/A | `orchestrate()` is an internal Python entry point, not a CLI command. `README.md` has no CLI entry for it. No update needed. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/errorlogger-adapter-wiring-522.md` exists. Linked from task body: "See .owlbear/research/errorlogger-adapter-wiring-522.md". Follow-up tasks: none (existing AC covered full scope — confirmed in Research section). |

### Files Updated
- None — all docs accurate as-is.

### Scratch Files Cleaned
- None — no `.owlbear/scratch/522-*` files found.

[[2026-04-06]] Mon 07:08
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC#1 — adapter in error_journal.py delegates to ErrorJournal.log() | error_journal.py L98-118: ErrorLoggerAdapter class, log_error() calls self._journal.log() | PASS |
| AC#2 — immutable class-level sentinel 'pre-session' | error_journal.py L106: _SESSION_ID = "pre-session" (class constant, not instance attr) | PASS |
| AC#3 — AcpClient(conn, error_logger=adapter) | loop.py L472: AcpClient(conn, error_logger=ErrorLoggerAdapter(error_journal)) | PASS |
| AC#4 — orchestrate() error_journal param, None default, .owlbear/error-journal.jsonl | loop.py L432: error_journal: ErrorJournal or None = None; L469-470: default ErrorJournal creation | PASS |
| AC#5 — mock-based delegation tests with sentinel session_id | 17/17 tests pass in test_errorlogger_adapter_wiring_522.py | PASS |
| AC#6 — no changes to acp_client.py | Last commit touching acp_client.py: f594bdd (rename), not #522 | PASS |

### Test Results
- pytest (task + regression): 199 passed, 1 failed, 7 skipped (36s)
- 1 failure: test_list_tasks_raises_tool_error_on_non_zero_rc in mcp-kanban test_server.py (pre-existing, out of scope)
- ruff: clean on all changed files

### Architect Quality: 5/5
All 6 AC lines specific and testable. Concurrency constraint (AC#2) proactively addressed from challenge result. Dependency correctly updated #148 to #521. Builder needed zero TestBuilderDiscovered tests.

### Deduction Breakdown
- AC lines with no evidence: 0 (all 6 verified) — no deduction
- Lint violations: 0 — no deduction
- AC quality: 5/5 — no deduction
- Reviewer evidence section: present, detailed, PASS at .95 — no deduction
- Full-suite failures in task scope: 0 — no deduction

### Confidence: .98
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 4b8826b | test | tests/test_errorlogger_adapter_wiring_522.py | #522 |
| 23f0cc1 | feat | error_journal.py, loop.py | #522 |

[[2026-04-10]] Fri 02:14
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC#1 — adapter in error_journal.py delegates to ErrorJournal.log() | error_journal.py L98-118: ErrorLoggerAdapter class with log_error() calling self._journal.log() | PASS |
| AC#2 — immutable class-level sentinel 'pre-session' | error_journal.py L106: _SESSION_ID = "pre-session" (class constant) | PASS |
| AC#3 — AcpClient(conn, error_logger=adapter) | loop.py L472: AcpClient(conn, error_logger=ErrorLoggerAdapter(error_journal)) | PASS |
| AC#4 — orchestrate() error_journal param, None default, .owlbear/error-journal.jsonl | loop.py L428: error_journal: ErrorJournal or None = None; L469-470: default creation | PASS |
| AC#5 — mock-based delegation tests with sentinel session_id | 17/17 tests pass in test_errorlogger_adapter_wiring_522.py | PASS |
| AC#6 — no changes to acp_client.py | acp_client.py absent from #522 commits (last touch: f594bdd rename) | PASS |

### Test Results
- pytest (task): 17 passed, 0 failed
- pytest (related modules): 69 passed (test_error_journal + test_acp_client)
- pytest (full suite): 3054 passed, 277 failed, 18 skipped — all failures pre-existing (wave-assembly, mcp-kanban, planner, hooks); 0 failures in task scope
- ruff: clean on all changed files

### Architect Quality: 5/5
All 6 AC lines specific and testable. Concurrency constraint (AC#2) proactively addressed. Dependency correctly updated. Zero builder improvisation needed.

### Deduction Breakdown
- AC lines with no evidence: 0 — no deduction
- Lint violations: 0 — no deduction
- AC quality: 5/5 — no deduction
- Reviewer evidence: present, detailed, PASS at .95 — no deduction
- Full-suite failures in task scope: 0 — no deduction

### Confidence: .98
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 4b8826b | test | tests/test_errorlogger_adapter_wiring_522.py | #522 |
| 23f0cc1 | feat | error_journal.py, loop.py | #522 |
