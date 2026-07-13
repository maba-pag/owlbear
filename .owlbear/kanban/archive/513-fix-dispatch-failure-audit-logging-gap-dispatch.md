---
id: 513
title: Fix dispatch failure audit logging gap — dispatch_entry never emits 
  CompletionEvent on failure
status: archived
priority: medium
created: 2026-04-01 06:00:49.887913+02:00
updated: 2026-04-01 21:23:15.757975+02:00
started: 2026-04-01 06:00:56.862906+02:00
completed: 2026-04-01 21:23:05.949818+02:00
tags:
- phase-2
- scope:orchestrator
class: standard
archival_reason: completed
archival_refs: []
---

## Context
Discovered during arch review of #500. dispatch_entry() in loop.py only emits CompletionEvent(outcome='success'). On AcpClientError or TimeoutError it returns False with no audit trail. The analysis detectors (high_error_rate_detector, repeated_failure_detector) filter on outcome=='failure' and can never trigger for dispatch-level failures.

## Acceptance Criteria
- [ ] When client.new_session() raises AcpClientError or TimeoutError, dispatch_entry() emits CompletionEvent(outcome='failure', error=str(exc), duration_ms=0, files_changed=[]) via audit_log before returning False; uses a generated session_id (e.g. uuid4().hex) for audit file routing since no real session exists
- [ ] When client.prompt() raises AcpClientError or TimeoutError, dispatch_entry() emits CompletionEvent(outcome='failure', error=str(exc), duration_ms=elapsed since t_start, files_changed=[]) via audit_log using the existing session_id before returning False
- [ ] Failure-path audit emission is skipped when audit_log is None (matching success-path guard)
- [ ] Failure-path log_completion calls wrapped in contextlib.suppress(OSError) (matching success-path pattern)
- [ ] Tests for both dispatch_entry failure paths verify CompletionEvent emission with outcome='failure' and populated error field
- [ ] Integration test feeds failure CompletionEvents into high_error_rate_detector and repeated_failure_detector and asserts AnalysisProposal output
- [ ] dispatch_entry return type (bool) unchanged; production changes confined to loop.py (audit models and detectors already support failure events correctly)

[[2026-04-01]] Wed 07:08
## Architecture Review
**Verdict:** APPROVED
**DR Verification:** N/A â€” T1 bug fix, no research origin

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| dispatch_entry emits CompletionEvent(outcome='failure') on AcpClientError/TimeoutError | Correct intent, but ambiguous: two distinct failure sites (new_session vs prompt) with different context | Rewritten into two explicit AC lines |
| Existing tests verify CompletionEvent emission | Correct scope, existing test classes identified | Kept, clarified both paths |
| high_error_rate/repeated_failure integration test | Clear and testable as-is | Kept |
| No change to bool return type | Clear constraint | Kept |
| (Missing) error field population | Not in original AC, needed for detectors | Added: error=str(exc) |
| (Missing) session_id strategy for new_session failure | Not in original AC, architectural constraint | Added: synthetic uuid4().hex |
| (Missing) audit_log=None guard | Implicit but should be explicit | Added |
| (Missing) contextlib.suppress(OSError) | Must match success-path pattern | Added |

### Architecture Notes
Bug fix in a single function: dispatch_entry() in packages/orchestrator/src/owlbear/orchestrator/loop.py. Two failure paths need CompletionEvent emission:

1. new_session() failure (line ~128): No session_id available. Builder should generate synthetic session_id (uuid4().hex) for audit file routing. AuditLog.log_completion works with any string session_id. No DispatchEvent is logged for this path (DispatchEvent requires session_id from real session). This is acceptable: detectors operate on CompletionEvents only.

2. prompt() failure (line ~150): session_id available. DispatchEvent already logged. Builder must capture t_end in except block to compute duration_ms.

Existing models already support this: CompletionEvent has outcome=Literal['success','failure'] and error: str or None. Detectors already filter on outcome=='failure'. No model or detector changes needed.

Coordination note: #434 (cycle_id) is in-progress and also modifies dispatch_entry. No formal dependency, but whichever lands second will face a merge conflict in the same function. Builder should check #434 status before starting.

### Changes Made
- Refined AC: disambiguated two failure paths, added session_id strategy, error field, guards, OSError suppression
- Original 4 AC lines expanded to 7 precise, testable lines

### Dependencies
- No new dependencies. No depends_on changes.
- Coordination: #434 (in-progress) touches same function, merge risk noted.

### Challenge Results
- Challenger: reconsider (confidence .55)
- Key challenges: (1) session_id unavailable on new_session failure path [accepted, resolved: synthetic uuid4().hex, no AuditLog changes needed]; (2) timing gap on prompt failure path [accepted, AC clarified]; (3) exception variable not captured [noted, trivial]; (4) #434 merge conflict risk [rebutted: no formal dependency, merge conflicts are normal development]
- Blind spots noted: orphaned CompletionEvent without DispatchEvent (acceptable, detectors work on CompletionEvents); files_changed on partial prompt failure (out of scope, safe default)
- Architect response: accepted 2/4 challenges and revised AC; rebutted merge dependency. Confidence in revised verdict: .90

-t

[[2026-04-01]] Wed 07:08
## Architecture Review
**Verdict:** APPROVED
**DR Verification:** N/A â€” T1 bug fix, no research origin

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| dispatch_entry emits CompletionEvent(outcome='failure') on AcpClientError/TimeoutError | Correct intent, but ambiguous: two distinct failure sites (new_session vs prompt) with different context | Rewritten into two explicit AC lines |
| Existing tests verify CompletionEvent emission | Correct scope, existing test classes identified | Kept, clarified both paths |
| high_error_rate/repeated_failure integration test | Clear and testable as-is | Kept |
| No change to bool return type | Clear constraint | Kept |
| (Missing) error field population | Not in original AC, needed for detectors | Added: error=str(exc) |
| (Missing) session_id strategy for new_session failure | Not in original AC, architectural constraint | Added: synthetic uuid4().hex |
| (Missing) audit_log=None guard | Implicit but should be explicit | Added |
| (Missing) contextlib.suppress(OSError) | Must match success-path pattern | Added |

### Architecture Notes
Bug fix in a single function: dispatch_entry() in packages/orchestrator/src/owlbear/orchestrator/loop.py. Two failure paths need CompletionEvent emission:

1. new_session() failure (line ~128): No session_id available. Builder should generate synthetic session_id (uuid4().hex) for audit file routing. AuditLog.log_completion works with any string session_id. No DispatchEvent is logged for this path (DispatchEvent requires session_id from real session). This is acceptable: detectors operate on CompletionEvents only.

2. prompt() failure (line ~150): session_id available. DispatchEvent already logged. Builder must capture t_end in except block to compute duration_ms.

Existing models already support this: CompletionEvent has outcome=Literal['success','failure'] and error: str or None. Detectors already filter on outcome=='failure'. No model or detector changes needed.

Coordination note: #434 (cycle_id) is in-progress and also modifies dispatch_entry. No formal dependency, but whichever lands second will face a merge conflict in the same function. Builder should check #434 status before starting.

### Changes Made
- Refined AC: disambiguated two failure paths, added session_id strategy, error field, guards, OSError suppression
- Original 4 AC lines expanded to 7 precise, testable lines

### Dependencies
- No new dependencies. No depends_on changes.
- Coordination: #434 (in-progress) touches same function, merge risk noted.

### Challenge Results
- Challenger: reconsider (confidence .55)
- Key challenges: (1) session_id unavailable on new_session failure path [accepted, resolved: synthetic uuid4().hex, no AuditLog changes needed]; (2) timing gap on prompt failure path [accepted, AC clarified]; (3) exception variable not captured [noted, trivial]; (4) #434 merge conflict risk [rebutted: no formal dependency, merge conflicts are normal development]
- Blind spots noted: orphaned CompletionEvent without DispatchEvent (acceptable, detectors work on CompletionEvents); files_changed on partial prompt failure (out of scope, safe default)
- Architect response: accepted 2/4 challenges and revised AC; rebutted merge dependency. Confidence in revised verdict: .90

[[2026-04-01]] Wed 18:16
## Builder Notes
- Files changed: packages/orchestrator/src/owlbear/orchestrator/loop.py (+29 lines)
- Tests: 26 passed; loop.py overall 52% (dispatch_entry paths fully covered)
- Lint: ruff clean
- Fixes applied: Added CompletionEvent(outcome='failure') emission on both failure paths. new_session failure: synthetic uuid4().hex session_id, duration_ms=0. prompt failure: real session_id, duration_ms=elapsed. Both guarded by audit_log is not None + contextlib.suppress(OSError).
- Commit: fe73035

[[2026-04-01]] Wed 19:51
## Review Evidence

### Test Results
- pytest: 26 passed, 0 failed (tests/test_dispatch_failure_audit_513.py)

### Lint Results
- ruff: All checks passed!

### Coverage
- loop.py: 51% overall (51 is consistent with builder-reported 52%; dispatch_entry failure paths fully exercised; uncovered lines are for dispatch_sequential, dispatch_parallel, and the main loop function  not in scope of this task)

### Test-Writer Audit (AC-to-test coverage)

| AC Line | Mapped Test(s) | Would Fail If Violated? | Verdict |
|---------|---------------|------------------------|---------|
| AC1: new_session failure emits CompletionEvent(outcome='failure') | TestFromAC_DispatchFailureNewSession::test_new_session_acperror_emits_completion_event_failure | Yes | COVERED |
| AC1: TimeoutError variant | TestFromAC_DispatchFailureNewSession::test_new_session_timeout_emits_completion_event_failure | Yes | COVERED |
| AC1: error=str(exc) | TestFromAC_DispatchFailureNewSession::test_new_session_failure_error_field_contains_exception_message | Yes | COVERED |
| AC1: duration_ms=0 | TestFromAC_DispatchFailureNewSession::test_new_session_failure_duration_ms_is_zero | Yes | COVERED |
| AC1: files_changed=[] | TestFromAC_DispatchFailureNewSession::test_new_session_failure_files_changed_is_empty | Yes | COVERED |
| AC1: uuid4().hex session_id routing | TestFromAC_DispatchFailureNewSession::test_new_session_failure_uses_synthetic_session_id_for_routing | Yes | COVERED |
| AC2: prompt failure emits CompletionEvent(outcome='failure') | TestFromAC_DispatchFailurePrompt::test_prompt_acperror_emits_completion_event_failure | Yes | COVERED |
| AC2: duration_ms=elapsed | TestFromAC_DispatchFailurePrompt::test_prompt_failure_duration_ms_is_nonnegative | Only asserts >= 0 (inherent mock limitation) | LAX |
| AC2: real session_id routing | TestFromAC_DispatchFailurePrompt::test_prompt_failure_uses_real_session_id_for_routing | Yes - checks == real-session-xyz | COVERED |
| AC3: audit_log=None guard -- no emission | TestFromAC_DispatchFailureAuditNoneGuard::test_new_session_failure_no_audit_log_returns_false | Implicitly yes -- None.log_completion would raise AttributeError | COVERED |
| AC4: OSError suppression on new_session path | TestFromAC_DispatchFailureOSErrorSuppression::test_new_session_failure_oserror_in_log_completion_suppressed | Yes | COVERED |
| AC4: OSError suppression on prompt path | TestFromAC_DispatchFailureOSErrorSuppression::test_prompt_failure_oserror_in_log_completion_suppressed | Yes | COVERED |
| AC4: non-OSError propagates | TestFromAC_DispatchFailureOSErrorSuppression::test_new_session_failure_non_oserror_in_log_completion_propagates | Yes | COVERED |
| AC6: high_error_rate_detector fires on failure events | TestFromAC_DispatchFailureDetectorIntegration::test_high_error_rate_detector_fires_on_dispatch_failure_events | Yes | COVERED |
| AC6: repeated_failure_detector fires on failure events | TestFromAC_DispatchFailureDetectorIntegration::test_repeated_failure_detector_fires_on_dispatch_failure_events | Yes | COVERED |
| AC7: return type bool unchanged | TestFromAC_DispatchReturnType::test_dispatch_entry_failure_path_returns_false_and_emits_event | Yes | COVERED |

LAX note: test_prompt_failure_duration_ms_is_nonnegative checks >= 0. With an instant mock, elapsed time is ~0ms anyway; this is an inherent test limitation, not a fixable test design issue. Implementation is visibly correct (t_end captured in except block). No compensating TestBuilderDiscovered test. Note only -- does not block PASS.

### TestFromAC Comparison
Builder did not modify any TestFromAC_* classes. All 6 classes and all methods preserved as written.

### Security Review
- No hardcoded secrets, no injection, no path traversal
- uuid4().hex for synthetic session IDs: correct and safe
- str(exc) in error field: acceptable for audit logs (no sensitive data exposed)
- No new dependencies added
CLEAN

### Builder Process Quality
1 Builder Notes section. CLEAN.

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: new_session failure emits CompletionEvent(outcome='failure') | loop.py lines ~130-143: except (AcpClientError, TimeoutError) block, outcome='failure', duration_ms=0, files_changed=[], error=str(exc), uuid4().hex | PASS |
| AC2: prompt failure emits CompletionEvent with elapsed duration_ms | loop.py lines ~163-176: t_end=time.monotonic() in except block, duration_ms=int((t_end-t_start)*1000), real session_id | PASS |
| AC3: audit_log=None guard | Both failure except blocks gated by if audit_log is not None | PASS |
| AC4: contextlib.suppress(OSError) | Both failure log_completion calls wrapped in with contextlib.suppress(OSError) | PASS |
| AC5: Tests verify both failure paths | 26 tests covering both sites, outcome, error, duration, files_changed, session_id routing, OSError suppression | PASS |
| AC6: Integration test for detectors | TestFromAC_DispatchFailureDetectorIntegration feeds failure CompletionEvents to both detectors and asserts AnalysisProposal output | PASS |
| AC7: Return type bool unchanged, changes confined to loop.py | dispatch_entry still returns bool; only loop.py modified | PASS |

### Verdict: PASS
Confidence: .91

[[2026-04-01]] Wed 20:12
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | T1 internal bug fix; no behavior/API/convention change visible to agents or users |
| 2 | Docstrings | Yes | Pass | dispatch_entry() docstring already accurate: mentions CompletionEvent, bool return, AcpClientError/TimeoutError on False path |
| 3 | docs/sources/overview.md | No | N/A | No external patterns used |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | T1 bug fix, no research origin |
| 6 | No impact | Yes | Pass | Bug fix with no documentation implications |

### Files Updated
- None

### Scratch Files Cleaned
- None found
