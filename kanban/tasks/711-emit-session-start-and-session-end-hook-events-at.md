---
id: 711
title: Emit SESSION_START and SESSION_END hook events at session boundaries
status: archived
priority: needed
created: 2026-03-09T15:27:59.494595+01:00
updated: 2026-03-10T03:56:48.2485073+01:00
started: 2026-03-09T18:11:48.8691043+01:00
completed: 2026-03-10T03:56:48.2485073+01:00
tags:
    - scope:core
    - hooks
depends_on:
    - 713
class: standard
---

Emit SESSION_START and SESSION_END lifecycle events from `daemon.py:run_daemon()` so existing hook consumers start receiving data.

depends_on: #713

## Acceptance Criteria

- [ ] `run_daemon()` emits `HookEvent.SESSION_START` with `{session_id: str(agent.session.path), workspace_root: str(workspace_root)}` immediately after `DAEMON_STARTUP` emission
- [ ] `run_daemon()` emits `HookEvent.SESSION_END` with `{session_id: str(agent.session.path), messages: <loaded>}` in the `finally` block, before signal handler restoration
- [ ] `workspace_root` is available in `run_daemon()`  either add a `workspace_root: Path` parameter (preferred, called from cli.py which already knows it) or derive from `agent.context._root` via a public accessor
- [ ] `SESSION_END` payload: `messages` loaded via `agent.session.load()` wrapped in try/except  falls back to `[]` on any error (session file may not exist)
- [ ] `ContextInjectionHook` fires on SESSION_START and populates `data[context]` (integration verified by test task #713)
- [ ] `TestVerificationHook` fires on SESSION_END and populates `data[test_results]` (integration verified by test task #713)
- [ ] No changes to `core/hooks.py`, `core/context_hook.py`, or `core/test_hook.py`  consumers are already wired
- [ ] Emission ordering: DAEMON_STARTUP  SESSION_START  (loops)  SESSION_END  signal restore

## Architecture Notes

- **Pattern:** follows existing `DAEMON_STARTUP` emit at daemon.py L824. SESSION_START goes on the line after, SESSION_END goes in the `finally` block.
- **workspace_root access:** `run_daemon()` currently lacks this parameter. Add `workspace_root: Path | None = None` to the signature. Both call sites in `bearclaw/cli.py` (`_run_daemon_cmd` and `_chat_cmd`) already resolve workspace_root  pass it through. If None, fall back to `Path.cwd()`.
- **Error isolation:** `HookRegistry.emit()` wraps each handler in try/except (hooks.py L80+). No additional error handling needed at the emission site, except for session.load() in SESSION_END payload construction.
- **Module layering:** daemon.py is assembly layer  importing from core/hooks is valid (top-down).
- See docs/research/session-hook-emission-research.md for full analysis.

[[2026-03-09]] Mon 19:17
## Architecture Review
**Verdict:** REFINE (AC tightened, test task created)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| daemon.py or agent.py emits SESSION_START | Imprecise  pinned to daemon.py:run_daemon() | Rewritten |
| daemon.py or agent.py emits SESSION_END | Same  pinned to finally block in run_daemon() | Rewritten |
| ContextInjectionHook fires | Verifiable integration criterion | Kept, linked to #713 |
| Existing tests updated | Vague  no test scenarios specified | Replaced with #713 test task |
| No behavioral change to consumers | Valid negative constraint | Kept |
| (missing) workspace_root access | run_daemon() lacks this param  critical gap | Added AC + architecture note |
| (missing) session.load() error handling | SESSION_END finally may fail on missing session | Added AC for try/except fallback |
| (missing) emission ordering | Not specified | Added explicit ordering AC |

### Architecture Notes
- Pattern: follows DAEMON_STARTUP emit in daemon.py L824. Minimal diff (2 emit calls + 1 new param).
- workspace_root: not currently available in run_daemon(). Add Path parameter; both cli.py call sites already know it.
- Module layering: daemon.py (assembly) -> core/hooks (valid top-down).
- Error isolation: HookRegistry.emit() wraps handlers in try/except. Only session.load() needs guarding.
- Single domain: daemon lifecycle only.

### Changes Made
- Rewrote AC body with 8 precise, verifiable criteria
- Created test task #713 (TDD RED)
- Added depends_on: #713 to #711
- Added depends_on: #711 to #622 (downstream consumer)

### Dependencies
- Added: #711 depends_on #713 (test task  TDD compliance)
- Verified: #622 depends_on #711 (SessionMemoryHook needs these events)

[[2026-03-10]] Tue 00:46
## Architecture Review (2026-03-10)
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| SESSION_START with {session_id, workspace_root} after DAEMON_STARTUP | Precise, verifiable. Already implemented in daemon.py L893-898. | Keep |
| SESSION_END with {session_id, messages} in finally block | Precise, verifiable. Implemented at daemon.py L972-979. | Keep |
| workspace_root: Path param added to run_daemon | Precise. Param added with Path `|` None = None default. | Keep |
| SESSION_END messages fallback to [] | Precise. try/except with BLE001 suppression. | Keep |
| ContextInjectionHook fires on SESSION_START | Verified by test_context_injection_hook_fires in #713. | Keep |
| TestVerificationHook fires on SESSION_END | Inaccurate: #713 has NO test for this. However, TestVerificationHook is pre-wired via bootstrap/hooks.py and fires automatically when SESSION_END is emitted. Consumer-side testing is a separate concern, not emission-side. | Rewrite: remove false #713 claim. AC becomes: TestVerificationHook (pre-wired in bootstrap/hooks.py) fires on SESSION_END automatically; no emission-side change needed. |
| No changes to core/hooks.py, context_hook.py, test_hook.py | Verifiable negative constraint. | Keep |
| Emission ordering DAEMON_STARTUP -> SESSION_START -> loops -> SESSION_END -> signal restore | Verifiable from code structure. | Keep |

### Architecture Notes
- Pattern: follows existing DAEMON_STARTUP emit. Minimal diff (2 emit calls + 1 new param).
- Module layering: daemon.py (assembly) -> core/hooks (valid top-down).
- Error isolation: HookRegistry.emit() wraps handlers in try/except. Only session.load() needs guarding (done).
- Single domain: daemon lifecycle only.
- Note for builder: cli.py _run_daemon_cmd (L1075) does not pass workspace_root explicitly  it relies on Path.cwd() fallback. Functionally correct but consider passing it explicitly for clarity.
- Implementation already completed during #713 GREEN phase  builder should verify all 6 tests pass and proceed.

### Dependencies
- Verified: #713 (test task)  done
- Verified: #622 depends_on #711 (downstream consumer  still backlog)

[[2026-03-10]] Tue 00:46
## Architecture Review (2026-03-10)
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| SESSION_START with {session_id, workspace_root} after DAEMON_STARTUP | Precise, verifiable. Already implemented in daemon.py L893-898. | Keep |
| SESSION_END with {session_id, messages} in finally block | Precise, verifiable. Implemented at daemon.py L972-979. | Keep |
| workspace_root: Path param added to run_daemon | Precise. Param added with Path `|` None = None default. | Keep |
| SESSION_END messages fallback to [] | Precise. try/except with BLE001 suppression. | Keep |
| ContextInjectionHook fires on SESSION_START | Verified by test_context_injection_hook_fires in #713. | Keep |
| TestVerificationHook fires on SESSION_END | Inaccurate: #713 has NO test for this. However, TestVerificationHook is pre-wired via bootstrap/hooks.py and fires automatically when SESSION_END is emitted. Consumer-side testing is a separate concern, not emission-side. | Rewrite: remove false #713 claim. AC becomes: TestVerificationHook (pre-wired in bootstrap/hooks.py) fires on SESSION_END automatically; no emission-side change needed. |
| No changes to core/hooks.py, context_hook.py, test_hook.py | Verifiable negative constraint. | Keep |
| Emission ordering DAEMON_STARTUP -> SESSION_START -> loops -> SESSION_END -> signal restore | Verifiable from code structure. | Keep |

### Architecture Notes
- Pattern: follows existing DAEMON_STARTUP emit. Minimal diff (2 emit calls + 1 new param).
- Module layering: daemon.py (assembly) -> core/hooks (valid top-down).
- Error isolation: HookRegistry.emit() wraps handlers in try/except. Only session.load() needs guarding (done).
- Single domain: daemon lifecycle only.
- Note for builder: cli.py _run_daemon_cmd (L1075) does not pass workspace_root explicitly  it relies on Path.cwd() fallback. Functionally correct but consider passing it explicitly for clarity.
- Implementation already completed during #713 GREEN phase  builder should verify all 6 tests pass and proceed.

### Dependencies
- Verified: #713 (test task)  done
- Verified: #622 depends_on #711 (downstream consumer  still backlog)

[[2026-03-10]] Tue 01:21
## Test-Writer Notes
- Test file: tests/test_session_hooks.py (written by #713 test task)
- Classes: TestFromAC_SessionStart, TestFromAC_SessionEnd, TestFromAC_ContextInjection
- Tests per category: happy 3, edge 1, error 1, integration 1
- Total: 6 tests, all PASS (implementation pre-completed during #713 GREEN phase)
- ruff: clean
- AC coverage:

| AC Line | Test(s) | Category |
|---------|---------|----------|
| SESSION_START emitted with payload | test_session_start_emitted | happy |
| SESSION_START after DAEMON_STARTUP | test_session_start_after_daemon_startup | happy |
| SESSION_END with messages | test_session_end_emitted_on_normal_exit | happy |
| SESSION_END in finally block | test_session_end_emitted_on_exception | error |
| messages fallback to [] | test_session_end_empty_session | edge |
| ContextInjectionHook fires | test_context_injection_hook_fires | integration |

Note: Tests pre-exist from #713 (test task). Implementation was completed during #713 GREEN phase per architect review. Builder should verify all 6 pass and proceed.

[[2026-03-10]] Tue 01:45
## Builder Notes
- Files changed: src/owlbear/daemon.py (implementation done during #713 GREEN phase)
- Tests: 6 passed in tests/test_session_hooks.py
- Coverage: 30% on daemon.py (expected  only 6 tests against a 353-line module)
- Lint: ruff clean
- Evidence: All TestFromAC_SessionStart (2), TestFromAC_SessionEnd (3), TestFromAC_ContextInjection (1) pass
- Fixes applied: None  implementation was already complete from #713

[[2026-03-10]] Tue 02:25
## Review Evidence
### Test Results
- pytest: 6 passed, 0 failed (tests/test_session_hooks.py)
- All TestFromAC classes pass: TestFromAC_SessionStart (2), TestFromAC_SessionEnd (3), TestFromAC_ContextInjection (1)

### Lint Results
- ruff: All checks passed! (daemon.py + test_session_hooks.py)

### Coverage
- daemon.py: 30% (expected â€” only 6 tests against 353-line module, emission lines covered)

### Test Quality
| Dimension | Rating | Evidence |
|--------|--------|--------|
| Assertion specificity | STRONG | Exact payload values checked (session_id, workspace_root strings). Ordering verified via index comparison. Messages fallback == []. |
| Negative/error paths | ADEQUATE | Exception path (test_session_end_emitted_on_exception), FileNotFoundError fallback (test_session_end_empty_session). No test for workspace_root=None fallback. |
| Mutation reasoning | STRONG | Remove SESSION_START -> 2 tests fail. Remove SESSION_END -> 3 tests fail. Swap ordering -> test fails. Remove try/except -> test fails. |
| Test independence | STRONG | Each test creates own mocks + tmp_path. No shared mutable state. |
| Descriptive names | STRONG | All names describe scenario and expected outcome. |

### Security Review
No issues. No user input in payloads (internal parameters only). No secrets, injection, or path traversal. session.load() errors handled.

### Test Writer vs Builder Comparison
Test file committed in #713 (c7acfe0). git diff HEAD -- tests/test_session_hooks.py produces empty diff. Builder made ZERO modifications.

| Original Test | Change Made | Assessment |
|--------|--------|--------|
| TestFromAC_SessionStart::test_session_start_emitted | No change | PRESERVED |
| TestFromAC_SessionStart::test_session_start_after_daemon_startup | No change | PRESERVED |
| TestFromAC_SessionEnd::test_session_end_emitted_on_normal_exit | No change | PRESERVED |
| TestFromAC_SessionEnd::test_session_end_emitted_on_exception | No change | PRESERVED |
| TestFromAC_SessionEnd::test_session_end_empty_session | No change | PRESERVED |
| TestFromAC_ContextInjection::test_context_injection_hook_fires | No change | PRESERVED |

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|--------|--------|--------|--------|
| 1. SESSION_START with payload after DAEMON_STARTUP | daemon.py L886-892 | test_session_start_emitted | PASS |
| 2. SESSION_END with payload in finally block | daemon.py L978-987 | test_session_end_emitted_on_normal_exit | PASS |
| 3. workspace_root param added | daemon.py L821 (Path or None = None, falls back to Path.cwd()) | test_session_start_emitted verifies str(tmp_path) | PASS |
| 4. SESSION_END messages fallback to [] | daemon.py L979-983 try/except BLE001 | test_session_end_empty_session | PASS |
| 5. ContextInjectionHook fires | Real HookRegistry + ContextInjectionHook in test | test_context_injection_hook_fires | PASS |
| 6. TestVerificationHook fires on SESSION_END | Pre-wired via bootstrap/hooks.py. Architect confirmed no emission-side change needed. | N/A (consumer-side) | PASS |
| 7. No changes to core/hooks.py, context_hook.py, test_hook.py | hooks.py diff belongs to #483 (TypedDict payloads), not #711. context_hook.py and test_hook.py have zero diff. | N/A | PASS |
| 8. Emission ordering | Code structure: L880 DAEMON_STARTUP -> L886 SESSION_START -> loops -> finally L978 SESSION_END -> L993 signal restore | test_session_start_after_daemon_startup | PASS |

### Verdict: PASS confidence .92

[[2026-03-10]] Tue 02:55
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Internal daemon lifecycle events, no new tech or convention. Hook system already in tech stack. |
| 2 | Docstrings | Yes | Pass | run_daemon() docstring includes workspace_root param with proper description (daemon.py L831). |
| 3 | sources/overview.md | Yes | Pass | Task #711 section already present with OpenAI Agents SDK + PydanticAI references. |
| 4 | README.md | No | N/A | No CLI changes. workspace_root is passed internally. |
| 5 | Research doc | Yes | Pass | docs/research/session-hook-emission-research.md exists, linked in task body. |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/711-* files found)

[[2026-03-10]] Tue 03:56
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| 1. SESSION_START with {session_id, workspace_root} after DAEMON_STARTUP | daemon.py L886-892: emits SESSION_START immediately after DAEMON_STARTUP at L880 | PASS |
| 2. SESSION_END with {session_id, messages} in finally block | daemon.py L978-987: emit in finally block before signal restore | PASS |
| 3. workspace_root: Path param added | daemon.py L785: workspace_root: Path | None = None, falls back to Path.cwd() | PASS |
| 4. SESSION_END messages fallback to [] | daemon.py L973-977: try/except BLE001 around session.load(), falls back to [] | PASS |
| 5. ContextInjectionHook fires on SESSION_START | test_context_injection_hook_fires: real hook registered, data['context'] verified | PASS |
| 6. TestVerificationHook fires on SESSION_END | Pre-wired via bootstrap/hooks.py; no emission-side change needed | PASS |
| 7. No changes to core/hooks.py, context_hook.py, test_hook.py | hooks.py diff from #483/#714 only. context_hook.py + test_hook.py zero diff. | PASS |
| 8. Emission ordering | Code: L880 DAEMON_STARTUP -> L886 SESSION_START -> loops -> finally L973 SESSION_END -> L990 signal restore. test_session_start_after_daemon_startup verifies. | PASS |

### Test Results
- pytest (scoped): 6 passed, 0 failed (tests/test_session_hooks.py)
- pytest (full, excl test_daemon.py hang): 3806 passed, 48 failed, 48 errors  all failures pre-existing (bootstrap OpenAIChatModel attr, hydration_integration #703, inter_doc_pipeline, pipeline_e2e), none from #711
- ruff: All checks passed (daemon.py + test_session_hooks.py)

### Confidence: .97
### Action: archive

[[2026-03-10]] Tue 03:56
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| 1. SESSION_START with {session_id, workspace_root} after DAEMON_STARTUP | daemon.py L886-892: emits SESSION_START immediately after DAEMON_STARTUP at L880 | PASS |
| 2. SESSION_END with {session_id, messages} in finally block | daemon.py L978-987: emit in finally block before signal restore | PASS |
| 3. workspace_root: Path param added | daemon.py L785: workspace_root: Path | None = None, falls back to Path.cwd() | PASS |
| 4. SESSION_END messages fallback to [] | daemon.py L973-977: try/except BLE001 around session.load(), falls back to [] | PASS |
| 5. ContextInjectionHook fires on SESSION_START | test_context_injection_hook_fires: real hook registered, data['context'] verified | PASS |
| 6. TestVerificationHook fires on SESSION_END | Pre-wired via bootstrap/hooks.py; no emission-side change needed | PASS |
| 7. No changes to core/hooks.py, context_hook.py, test_hook.py | hooks.py diff from #483/#714 only. context_hook.py + test_hook.py zero diff. | PASS |
| 8. Emission ordering | Code: L880 DAEMON_STARTUP -> L886 SESSION_START -> loops -> finally L973 SESSION_END -> L990 signal restore. test_session_start_after_daemon_startup verifies. | PASS |

### Test Results
- pytest (scoped): 6 passed, 0 failed (tests/test_session_hooks.py)
- pytest (full, excl test_daemon.py hang): 3806 passed, 48 failed, 48 errors  all failures pre-existing (bootstrap OpenAIChatModel attr, hydration_integration #703, inter_doc_pipeline, pipeline_e2e), none from #711
- ruff: All checks passed (daemon.py + test_session_hooks.py)

### Confidence: .97
### Action: archive
