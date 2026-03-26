---
id: 541
title: Make ErrorJournal async-safe for daemon event loop
status: archived
priority: nice-to-have
created: 2026-03-04T07:38:45.7339339+01:00
updated: 2026-03-22T19:17:39.3132194+01:00
started: 2026-03-07T00:36:40.6260778+01:00
completed: 2026-03-22T19:17:39.3132194+01:00
tags:
    - audit
    - resilience
    - scope:core
blocked: true
block_reason: 'Historical tracker only; async journal behavior is already implemented in daemon.py and verified by archived #841 plus live regression tests. Refresh research or create a new RED/GREEN pair if a new regression appears.'
class: standard
---

J-2: ErrorJournal uses blocking file I/O (path.open(''a'')). In async daemon loop, rotation of 10K entries blocks event loop.

Research complete (2026-03-07): asyncio.to_thread at call site is the recommended approach (.85 confidence). Make _log_to_journal async in daemon.py, wrap journal.log() in asyncio.to_thread(). Zero new deps, follows existing codebase pattern (3 prior uses). See docs/research/error-journal-async.md for full analysis.

Research checklist:
1. Theoretical validity: wrapping sync I/O in asyncio.to_thread is well-established
2. Prior art: Python stdlib docs, aiofiles library, 3 existing uses in codebase
3. Technical feasibility: asyncio.to_thread is stdlib since 3.9, we are on 3.12+
4. Architecture fit: matches context_hook.py, tts.py, web_search.py patterns
5. Implementation approach: ~15 line diff in daemon.py only

[[2026-03-21]] Sat 05:05
## Refined AC
1. Treat #541 as a historical parent only. Do not move this task to `todo`; the async journal behavior is already implemented and verified by archived task #841 plus live regression tests.
2. The source-of-truth implementation remains in `src/owlbear/daemon.py`: `_log_to_journal()` is `async def` and delegates `journal.log(...)` through `await asyncio.to_thread(...)`.
3. `_recover_from_error()` in `src/owlbear/daemon.py` awaits `_log_to_journal()` at all six call sites, so daemon-side journal writes do not block the event loop directly.
4. `ErrorJournal`, `JsonlStore`, and `src/owlbear/orchestrator/loop_detection.py::_log_to_journal()` remain synchronous; async offload is isolated to the daemon call site and introduces no new third-party dependencies.
5. The regression contract remains encoded in `tests/test_daemon_journal_async.py` and `tests/test_daemon_async_contract.py`. If this area regresses, create a new RED/GREEN pair for that regression instead of dispatching builder work from #541.

[[2026-03-21]] Sat 05:06
## Architecture Review
**Verdict:** REFINE

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. Treat #541 as a historical parent only. Do not move this task to `todo`; the async journal behavior is already implemented and verified by archived task #841 plus live regression tests. | Correct direction. A builder handoff would be duplicate work because the implementation and executable coverage already exist. | Kept. |
| 2. The source-of-truth implementation remains in `src/owlbear/daemon.py`: `_log_to_journal()` is `async def` and delegates `journal.log(...)` through `await asyncio.to_thread(...)`. | Precise, single-domain, and mechanically verifiable in current source. | Kept. |
| 3. `_recover_from_error()` in `src/owlbear/daemon.py` awaits `_log_to_journal()` at all six call sites, so daemon-side journal writes do not block the event loop directly. | Correct and covered by the AST contract tests. | Kept. |
| 4. `ErrorJournal`, `JsonlStore`, and `src/owlbear/orchestrator/loop_detection.py::_log_to_journal()` remain synchronous; async offload is isolated to the daemon call site and introduces no new third-party dependencies. | Good boundary definition. It preserves layering, avoids API creep, and is covered by contract tests. | Kept. |
| 5. The regression contract remains encoded in `tests/test_daemon_journal_async.py` and `tests/test_daemon_async_contract.py`. If this area regresses, create a new RED/GREEN pair for that regression instead of dispatching builder work from #541. | Verifiable and aligned with TDD workflow. | Kept. |

### Architecture Notes
- Verified `docs/research/error-journal-async.md` recommends call-site `asyncio.to_thread`, which matches the live implementation.
- Verified `src/owlbear/daemon.py` keeps the async boundary in the assembly layer and uses `await asyncio.to_thread(journal.log, ...)` inside `_log_to_journal()`.
- Verified `src/owlbear/core/context_hook.py`, `src/owlbear/voice/tts.py`, and `src/owlbear/tools/web_search.py` already use `asyncio.to_thread`, so the implementation follows established precedent.
- Verified `tests/test_daemon_journal_async.py` and `tests/test_daemon_async_contract.py` both pass today (`26 passed`).
- Verified the task remains single-domain (`scope:core`) and does not require new config, new dependencies, or changes inside `ErrorJournal` internals.
- Moving #541 to `todo` would create an invalid duplicate implementation handoff. The correct state is `backlog` with explicit tracker AC only.

### Changes Made
- Claimed #541 as `bone-oaken`
- Rewrote the task body to remove the malformed 05:05 append caused by PowerShell backtick escaping in markdown
- Added clean tracker AC tied to live source and both regression files
- Appended this `## Architecture Review`
- Left #541 in `backlog`

### Dependencies
- Added/Removed/Verified: verified `docs/research/error-journal-async.md`, `src/owlbear/daemon.py`, `src/owlbear/core/context_hook.py`, `src/owlbear/voice/tts.py`, `src/owlbear/tools/web_search.py`, `tests/test_daemon_journal_async.py`, `tests/test_daemon_async_contract.py`, and archived #841

[[2026-03-21]] Sat 05:34
## Architecture Review
**Verdict:** REFINE

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. Treat #541 as a historical parent only. Do not move this task to `todo`; the async journal behavior is already implemented and verified by archived task #841 plus live regression tests. | Still correct. Archived #841 plus current passing regression tests already carry the executable contract, so routing this card to builder would duplicate completed work. | Kept. |
| 2. The source-of-truth implementation remains in `src/owlbear/daemon.py`: `_log_to_journal()` is `async def` and delegates `journal.log(...)` through `await asyncio.to_thread(...)`. | Verified in live source at the daemon assembly layer. | Kept. |
| 3. `_recover_from_error()` in `src/owlbear/daemon.py` awaits `_log_to_journal()` at all six call sites, so daemon-side journal writes do not block the event loop directly. | Verified in source and in AST contract tests. | Kept. |
| 4. `ErrorJournal`, `JsonlStore`, and `src/owlbear/orchestrator/loop_detection.py::_log_to_journal()` remain synchronous; async offload is isolated to the daemon call site and introduces no new third-party dependencies. | Verified boundary preservation matches the research recommendation and architecture layering. | Kept. |
| 5. The regression contract remains encoded in `tests/test_daemon_journal_async.py` and `tests/test_daemon_async_contract.py`. If this area regresses, create a new RED/GREEN pair for that regression instead of dispatching builder work from #541. | Still the correct TDD boundary. The live tests passed unchanged. | Kept. |

### Architecture Notes
- Revalidated `docs/research/error-journal-async.md`: call-site `asyncio.to_thread` remains the correct approach.
- Revalidated `src/owlbear/daemon.py`: `_log_to_journal()` is async and `_recover_from_error()` awaits it at six call sites.
- Revalidated `src/owlbear/orchestrator/loop_detection.py`: orchestrator-side journaling remains synchronous, so the async boundary stays isolated to the daemon assembly layer.
- Revalidated precedent in `src/owlbear/core/context_hook.py`, `src/owlbear/voice/tts.py`, and `src/owlbear/tools/web_search.py`: `asyncio.to_thread` is the established blocking-I/O offload pattern.
- Revalidated executable coverage with `uv run pytest tests/test_daemon_journal_async.py tests/test_daemon_async_contract.py -q --tb=short`: 26 passed.
- Moving #541 to `todo` would still create a false builder handoff. The task remains a historical tracker in `backlog`.

### Changes Made
- Claimed #541 as `holt-quartz`
- Revalidated research, source, precedent files, archived #841, and both regression suites
- Appended this follow-up architecture review
- Left #541 in `backlog`

### Dependencies
- Added/Removed/Verified: verified `docs/research/error-journal-async.md`, archived #841, `src/owlbear/daemon.py`, `src/owlbear/orchestrator/loop_detection.py`, `src/owlbear/core/context_hook.py`, `src/owlbear/voice/tts.py`, `src/owlbear/tools/web_search.py`, `tests/test_daemon_journal_async.py`, and `tests/test_daemon_async_contract.py`

[[2026-03-21]] Sat 05:35
## Architecture Review
**Verdict:** BLOCK

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. Treat #541 as a historical parent only. Do not move this task to `todo`; the async journal behavior is already implemented and verified by archived task #841 plus live regression tests. | Satisfied in the current workspace. Archived #841 plus current passing regression tests already carry the executable contract. | Do not dispatch implementation from #541; move the task out of the active backlog. |
| 2. The source-of-truth implementation remains in `src/owlbear/daemon.py`: `_log_to_journal()` is `async def` and delegates `journal.log(...)` through `await asyncio.to_thread(...)`. | Satisfied in current source at the daemon assembly layer. | Keep the implementation closed under the existing source and regression tests. |
| 3. `_recover_from_error()` in `src/owlbear/daemon.py` awaits `_log_to_journal()` at all six call sites, so daemon-side journal writes do not block the event loop directly. | Satisfied in current source and AST contract coverage. | No further builder work is required from this parent card. |
| 4. `ErrorJournal`, `JsonlStore`, and `src/owlbear/orchestrator/loop_detection.py::_log_to_journal()` remain synchronous; async offload is isolated to the daemon call site and introduces no new third-party dependencies. | Satisfied in current source. The boundary remains isolated to daemon.py and still matches the research recommendation. | Keep the boundary closed; do not widen scope from #541. |
| 5. The regression contract remains encoded in `tests/test_daemon_journal_async.py` and `tests/test_daemon_async_contract.py`. If this area regresses, create a new RED/GREEN pair for that regression instead of dispatching builder work from #541. | Satisfied by the live regression suites, which passed 26/26 today. | Treat new failures as new work; do not reopen #541 as an implementation task. |

### Architecture Notes
- Revalidated `docs/research/error-journal-async.md`, `src/owlbear/daemon.py`, `src/owlbear/orchestrator/loop_detection.py`, `src/owlbear/core/context_hook.py`, `src/owlbear/voice/tts.py`, `src/owlbear/tools/web_search.py`, archived #841, and both regression suites.
- The original async-safety change is already shipped and verified; #541 no longer represents executable backlog work.
- Leaving #541 in `backlog` would keep redispatching a historical parent card whose builder contract is complete.
- The correct next state is blocked `ideation`: historical tracker only. If behavior regresses, open a new RED/GREEN pair against the live failure rather than routing builder work from #541.

### Changes Made
- Claimed #541 as `holt-quartz`
- Revalidated current source, research, archived #841, and the targeted regression suites
- Appended this superseding architecture review
- Prepared #541 to leave the active backlog as a blocked historical tracker

### Dependencies
- Added/Removed/Verified: verified `docs/research/error-journal-async.md`, archived #841, `src/owlbear/daemon.py`, `src/owlbear/orchestrator/loop_detection.py`, `src/owlbear/core/context_hook.py`, `src/owlbear/voice/tts.py`, `src/owlbear/tools/web_search.py`, `tests/test_daemon_journal_async.py`, and `tests/test_daemon_async_contract.py`
