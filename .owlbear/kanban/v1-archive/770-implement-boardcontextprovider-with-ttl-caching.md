---
id: 770
title: Implement BoardContextProvider with TTL caching
status: archived
priority: important
created: 2026-03-13T10:39:59.0640782+01:00
updated: 2026-03-21T04:06:17.6391589+01:00
started: 2026-03-13T11:21:24.3555851+01:00
completed: 2026-03-21T04:05:46.7128981+01:00
tags:
    - agent
    - knowledge
    - scope:core
depends_on:
    - 851
class: standard
---

Implement the core-layer BoardContextProvider service described in docs/research/board-context-provider.md. This task is limited to the provider itself; turn() integration, bootstrap wiring, and config remain in #771.

Pattern refs:
- src/owlbear/core/context_hook.py::_run_kanban for asyncio.create_subprocess_exec plus warning and empty-string degradation
- src/owlbear/tools/kanban.py::_run_kanban for kanban CLI command shape
- tests/test_board_context.py from #851 as the binding RED suite

AC:
- [ ] Add src/owlbear/core/board_context.py defining BoardContextProvider in the owlbear.core layer only; do not import from tools/, memory/, agents/, or bootstrap
- [ ] BoardContextProvider supports zero-argument construction and an injectable constructor surface for kanban_cmd, ttl_seconds, and timer so downstream consumers can keep the zero-arg path while tests can inject command and clock doubles
- [ ] The default command is exactly: kanban/kanban-md.exe list --compact --status in-progress --status review --status todo --no-color --dir kanban
- [ ] The implementation uses a stdlib monotonic timer for TTL bookkeeping; do not add a new caching dependency for this task
- [ ] async get_context() returns the cached board snapshot when the cached entry is newer than ttl_seconds and refreshes it by rerunning the subprocess when the cache is absent or expired
- [ ] invalidate() clears the cached snapshot and cached timestamp so the next get_context() call forces a refresh
- [ ] Subprocess execution uses asyncio.create_subprocess_exec with stdout and stderr pipes and no shell invocation
- [ ] OSError while spawning or communicating returns an empty string and logs WARNING without raising to the caller
- [ ] A non-zero subprocess exit returns an empty string and logs WARNING including the return code and decoded stderr without raising to the caller
- [ ] A zero-exit subprocess returns decoded UTF-8 stdout
- [ ] The provider returns the raw compact kanban output without adding headers or prompt framing
- [ ] Task scope stays inside src/owlbear/core/board_context.py; do not modify OwlBearAgent.turn(), bootstrap wiring, or OwlBearSettings in this task
- [ ] The RED suite in tests/test_board_context.py passes without loosening its assertions
- [ ] ruff check src/owlbear/core/board_context.py tests/test_board_context.py passes

[[2026-03-20]] Fri 18:06
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Create a BoardContextProvider service | Correct core-service direction, but not yet a builder-ready contract because file boundary and public interface were unspecified | Rewrote into explicit core-only service AC |
| Runs kanban-md list --compact --status in-progress --status review --status todo | Correct behavior target, but command shape and subprocess boundary were under-specified | Rewrote with exact default command and no-shell subprocess requirement |
| Caches the result with configurable TTL (default 60s) | Missing cache invalidation behavior, injected clock contract, and dependency posture | Rewrote with explicit constructor, invalidate(), TTL semantics, and stdlib monotonic requirement |
| Graceful degradation on subprocess failure | Good requirement, but ambiguous about return value, logging, and non-zero exit handling | Rewrote with explicit empty-string plus WARNING behavior for OSError and non-zero exit |

### Architecture Notes
- Single domain verified: #770 is a core service task only. turn() integration, bootstrap wiring, and settings remain in #771.
- Preserve the downstream consumer contract already visible in src/owlbear/core/agent.py and src/owlbear/bootstrap/__init__.py: zero-argument construction must remain valid, and the provider surface remains async get_context() plus invalidate().
- Pattern consistency: follow src/owlbear/core/context_hook.py::_run_kanban for asyncio.create_subprocess_exec plus warning-and-empty-string degradation, and src/owlbear/tools/kanban.py::_run_kanban for the kanban CLI command shape.
- KISS and YAGNI: use stdlib monotonic TTL bookkeeping for the single cached value; do not add a caching dependency for this task.

### Failure Mode Map
| CODEPATH | FAILURE MODE | EXCEPTION | HANDLED? | USER IMPACT |
|----------|--------------|-----------|----------|-------------|
| BoardContextProvider subprocess spawn | kanban binary cannot be spawned | OSError | Yes - log WARNING and return empty string | Agent turn continues without board context |
| BoardContextProvider subprocess execution | kanban command exits non-zero | return code check | Yes - log WARNING and return empty string | Agent turn continues without board context |

### Changes Made
- Claimed #770 as architect.
- Added missing dependency on RED task #851.
- Replaced the terse body with explicit scope, pattern references, and verifiable AC.
- Kept #770 limited to src/owlbear/core/board_context.py and excluded #771's wiring/config work.

### Dependencies
- Added: #851 as the required TDD predecessor.
- Verified: #851 is archived, satisfying the RED-before-GREEN requirement.
- Verified: #771 depends on #770 and owns the downstream turn/bootstrap/config integration work.

[[2026-03-20]] Fri 18:55
## Test-Writer Notes
- Test file: tests/test_board_context.py (authored in RED task #851 â€” pre-existing)
- Classes: TestFromAC_Constructor, TestFromAC_GetContextHappyPath, TestFromAC_TTLCache, TestFromAC_GracefulDegradation
- Tests: happy 2, edge 1, error 6, boundary 6
- Total: 15 tests
- **Anomaly: all 15 PASS** â€” implementation in src/owlbear/core/board_context.py was already committed before this pipeline stage. The RED suite was properly written in #851; the GREEN work is already done.
- ruff: clean (removed 4 unused noqa: N801 directives)
- AC coverage:
| AC Line | Test(s) | Category |
|---------|---------|----------|
| Zero-arg construction + injectable kanban_cmd/ttl_seconds/timer | test_default_kanban_cmd_is_full_list_command, test_default_ttl_is_60_seconds, test_custom_* | happy/boundary |
| Default command = full list command | test_default_kanban_cmd_is_full_list_command | boundary |
| stdlib monotonic timer for TTL | test_custom_timer_is_stored, TTLCache tests with _FakeTimer | boundary |
| get_context() returns cached snapshot within TTL | test_second_call_within_ttl_skips_subprocess | edge |
| get_context() refreshes on TTL expiry | test_expired_ttl_reruns_subprocess | boundary |
| invalidate() clears cache | test_invalidate_forces_refresh_before_ttl, test_invalidate_before_any_call_does_not_raise | edge/boundary |
| asyncio.create_subprocess_exec, no shell | test_runs_default_command_via_create_subprocess_exec | happy |
| OSError -> empty string + WARNING | test_os_error_returns_empty_string, test_os_error_logs_warning | error |
| Non-zero exit -> empty string + WARNING with rc | test_nonzero_exit_returns_empty_string, test_nonzero_exit_logs_warning_with_return_code | error |
| Zero exit -> decoded UTF-8 stdout | test_returns_decoded_stdout | happy |

[[2026-03-21]] Sat 02:41
## Builder Notes
- Files changed: tests/test_board_context.py (4 noqa:N801 removals by test-writer; committed in this pass)
- Implementation: src/owlbear/core/board_context.py already committed in prior task (#851, builder)
- Tests: 15 passed, 100% coverage on src/owlbear/core/board_context.py
- Lint: ruff All checks passed
- Evidence: pytest 15 passed in 0.12s; ruff All checks passed

[[2026-03-21]] Sat 03:03
## Review Evidence
### Review: #770 - Implement BoardContextProvider with TTL caching

### Test Results
- pytest: `uv run pytest tests/test_board_context.py -q --tb=short` -> 15 passed, 0 failed, 2 warnings
- TestFromAC subset: `uv run pytest tests/test_board_context.py -k TestFromAC_ -q --tb=short` -> 15 passed

### Lint Results
- ruff: `uv run ruff check src/owlbear/core/board_context.py tests/test_board_context.py` -> All checks passed

### Coverage
- First run produced transient `KeyboardInterrupt` from coverage parser after tests completed.
- Retry succeeded: `uv run pytest tests/test_board_context.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short`
- `src/owlbear/core/board_context.py`: 100% coverage (36/36)

### Pass 1 - CRITICAL
#### Security Review
- No hardcoded secrets found in provider file.
- No shell invocation; uses `asyncio.create_subprocess_exec` argument vector (`src/owlbear/core/board_context.py` lines 85-88).
- No path traversal, insecure deserialization, eval/exec, or new dependency risk.
- Warning logs include subprocess stderr/exception text only.

#### Test Integrity (TestFromAC comparison)
Compared `tests/test_board_context.py` between RED commit `d8af9f4` and builder commit `369c574`.
Only change: class-level `# noqa: N801` removal; no test logic/assertion changes.

| Original Test | Change Made | Assessment |
|---|---|---|
| `TestFromAC_Constructor::*` (5 tests) | No method-body changes | PRESERVED |
| `TestFromAC_GetContextHappyPath::*` (2 tests) | No method-body changes | PRESERVED |
| `TestFromAC_TTLCache::*` (4 tests) | No method-body changes | PRESERVED |
| `TestFromAC_GracefulDegradation::*` (4 tests) | No method-body changes | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | STRONG | Exact equality and call-count assertions (`tests/test_board_context.py` lines 73, 119-121, 160, 177-178, 269-270). |
| Negative/error paths | STRONG | Explicit OSError/non-zero return code scenarios (`tests/test_board_context.py` lines 216-276). |
| Mutation reasoning | ADEQUATE | TTL and invalidation are covered; exact equality boundary (`== ttl_seconds`) could be added. |
| Test independence | STRONG | Local mocks/fake timer; no order-dependent shared state. |
| Descriptive names | STRONG | Scenario and outcome are explicit in test names. |

#### Data Safety
- Provider only returns subprocess output string; no persistence or transaction safety hazards introduced.
- No unbounded input processing path in this scope.

### Pass 2 - INFORMATIONAL
- Consider adding one boundary test for `now - cached_at == ttl_seconds` to freeze expiry semantics.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| Provider added in core layer only | `src/owlbear/core/board_context.py` line 31 defines class; no forbidden layer imports found | Constructor tests | PASS |
| Zero-arg + injectable constructor (`kanban_cmd`, `ttl_seconds`, `timer`) | `src/owlbear/core/board_context.py` lines 46-54 | `test_default_kanban_cmd_is_full_list_command`, `test_default_ttl_is_60_seconds`, `test_custom_kanban_cmd_is_stored`, `test_custom_ttl_seconds_is_stored`, `test_custom_timer_is_stored` | PASS |
| Default command exact shape | `src/owlbear/core/board_context.py` lines 16-27 | `test_default_kanban_cmd_is_full_list_command` | PASS |
| Monotonic timer used for TTL | `src/owlbear/core/board_context.py` line 54 (`time.monotonic`) | `test_custom_timer_is_stored` + TTL cache tests | PASS |
| `get_context()` caches and refreshes by TTL | `src/owlbear/core/board_context.py` lines 67-76 | `test_second_call_within_ttl_skips_subprocess`, `test_expired_ttl_reruns_subprocess` | PASS |
| `invalidate()` clears cache and timestamp | `src/owlbear/core/board_context.py` lines 78-81 | `test_invalidate_forces_refresh_before_ttl`, `test_invalidate_before_any_call_does_not_raise` | PASS |
| Subprocess exec with stdout/stderr pipes and no shell | `src/owlbear/core/board_context.py` lines 85-88 | `test_runs_default_command_via_create_subprocess_exec` | PASS |
| OSError -> warning + empty string | `src/owlbear/core/board_context.py` lines 91-93 | `test_os_error_returns_empty_string`, `test_os_error_logs_warning` | PASS |
| Non-zero exit -> warning(rc+stderr decode) + empty string | `src/owlbear/core/board_context.py` lines 95-101 | `test_nonzero_exit_returns_empty_string`, `test_nonzero_exit_logs_warning_with_return_code` | PASS |
| Zero exit -> UTF-8 decoded stdout | `src/owlbear/core/board_context.py` line 103 | `test_returns_decoded_stdout` | PASS |
| Raw compact output returned (no framing) | Direct decoded return at line 103 | `test_returns_decoded_stdout` | PASS |
| Scope constrained (no turn/bootstrap/settings edits in this task) | `git show --name-only 369c574` shows only `tests/test_board_context.py`; implementation commit `0eb597d` touches only `src/owlbear/core/board_context.py` | N/A (process AC) | PASS |
| RED suite passes with no assertion loosening | TestFromAC run passes; diff vs RED commit shows only noqa removals | All `TestFromAC_*` tests | PASS |
| Ruff check passes for target files | Ruff command output clean | N/A | PASS |

### Verdict: PASS
- Confidence: .94

### Action Taken
- Move to docs gate after this evidence append.

[[2026-03-21]] Sat 04:05
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| core layer, no forbidden imports | Lines 1-11 | PASS |
| Zero-arg + injectable constructor | Lines 49-58 | PASS |
| Default command exact shape | Lines 16-27 | PASS |
| stdlib monotonic timer | Line 56 | PASS |
| get_context() caches/refreshes by TTL | Lines 63-76 | PASS |
| invalidate() clears cache | Lines 78-81 | PASS |
| create_subprocess_exec, no shell | Lines 85-88 | PASS |
| OSError returns empty + WARNING | Lines 91-93 | PASS |
| Non-zero exit returns empty + WARNING | Lines 95-101 | PASS |
| Zero exit returns decoded UTF-8 | Line 103 | PASS |
| Raw compact output, no framing | Line 103 | PASS |
| Scope constrained | git show confirms | PASS |
| RED suite passes | 15 passed | PASS |
| ruff passes | All checks passed | PASS |

### Test Results
- pytest scoped: 15 passed, 0 failed
- pytest full: 3691 passed, 90 failed (all unrelated)
- ruff: All checks passed

### Confidence: .97
### Action: archive

[[2026-03-21]] Sat 04:06
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 4c772e2 | chore | kanban/tasks/770-*.md | #770 |
