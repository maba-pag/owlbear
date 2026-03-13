---
id: 716
title: Annotate hook consumers with typed payloads
status: archived
priority: important
created: 2026-03-09T23:01:27.5822872+01:00
updated: 2026-03-11T09:41:21.0236835+01:00
started: 2026-03-11T09:23:29.7228362+01:00
completed: 2026-03-11T09:41:21.0236835+01:00
tags:
    - phase-7
    - hooks
    - typing
    - refactor
depends_on:
    - 483
    - 715
claimed_by: auditor
claimed_at: 2026-03-11T09:41:14.3064193+01:00
class: standard
---

Remove isinstance(data, dict) boilerplate from 11 hook consumers.\n\n## Acceptance Criteria\n1. Update __call__ (or handler method) signatures in 11 consumers to use specific TypedDict param type:\n   - CommandSafetyGuard.__call__(data: PreToolUseData)\n   - URLSafetyGuard.__call__(data: PreToolUseData)\n   - AutoLintHook.__call__(data: PostToolUseData)\n   - ContextInjectionHook.__call__(data: SessionStartData)\n   - SubagentVerificationHook.__call__(data: SubagentCompleteData)\n   - TestVerificationHook.__call__(data: SessionEndData)\n   - RetrospectiveHook.__call__(data: TaskCompleteData)\n   - ProgressReporter.on_tool_complete(data: PostToolUseData)\n   - ScreenshotOnErrorHook.handle(data: OnErrorData)\n   - NotificationHook: dict[str, Any] (multi-event)\n   - ObservabilityHook: dict[str, Any] (multi-event)\n2. Remove isinstance(data, dict) early-return guards from all 11 consumers (13 occurrences total)\n3. Do NOT touch skills/registry.py isinstance guard (different concern)\n4. All existing hook tests pass; ruff check clean\n5. Zero runtime behavior changes beyond removing unreachable guard branches\n\n## Architecture Notes\n- HookRegistry.emit always passes dict - isinstance guards are dead code\n- NotificationHook._make_handler and ObservabilityHook._make_handler use closures that inject event; keep dict[str, Any] for these\n- See docs/research/typed-hook-payloads.md

[[2026-03-10]] Tue 22:45
## Architecture Review
**Verdict:** APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| AC1: 11 consumers typed | Precise. All 11 listed with exact TypedDict mappings. | Keep |
| AC2: Remove isinstance guards (13 total) | Intent clear. 1 remains in _make_handler closure. Sub-field checks correctly excluded. | Keep |
| AC3: Don't touch registry.py | Clear exclusion. | Keep |
| AC4: Tests pass, ruff clean | Standard quality gate. | Keep |
| AC5: Zero runtime behavior change | Guard branches were unreachable dead code. | Keep |

### Architecture Notes
- Module layering OK: tools/ importing TypedDicts from core/hooks.py is allowed direction.
- Single domain: hook consumer typing is one refactoring concern across 11 files.
- TDD compliance: #715 archived with 19 tests in tests/test_hook_consumer_types.py.
- Dep #483: all 9 TypedDicts available in core/hooks.py (archived).
- #715 builder overlap: src/ changes already implemented during #715. Builder should verify existing state.
- Minor test gap: NotificationHook._make_handler closure still has data: object + isinstance(data, dict). Builder should update to data: dict[str, Any] and remove isinstance.

### Dependencies
- Verified: #483 (TypedDict definitions) archived
- Verified: #715 (RED tests) archived

[[2026-03-11]] Wed 00:33
## Builder Notes

[[2026-03-11]] Wed 00:33
- Files changed: src/owlbear/core/notification_hook.py (2-line diff in _make_handler)
- Tests: 22 passed (test_hook_consumer_types), 65 across all hook test files
- Lint: ruff clean
- Change: _make_handler closure data: object -> data: dict[str, Any]; removed isinstance guard
- Evidence: 2 RED->GREEN (TestFromAC_MakeHandlerClosureTyping), 20 pre-passing unaffected

[[2026-03-11]] Wed 09:20
## Review Evidence

### Test Results
- pytest (scoped): 22 passed, 0 failed (test_hook_consumer_types.py)
- pytest (related hooks): 328 passed, 0 failed (11 hook test files)
- pytest (full suite, --ignore test_project_session.py): 1393 passed, 61 failed, 9 errors
  - All 61 failures and 9 errors are pre-existing (bootstrap module, browser_snapshot, content_safety_integration, daemon CLI) -- none related to #716

### Lint Results
- ruff: All checks passed! (12 files checked)

### Coverage
- Not directly applicable: tests are structural (get_type_hints, AST inspection), not runtime. Builder reported 100% on notification_hook.py from existing tests.

### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Every test uses `get_type_hints()` with `is` identity checks against exact TypedDict types; AST-based guard detection checks exact patterns |
| Negative/error paths | STRONG | Tests verify both positive (typed annotations) AND negative (isinstance guards absent); registry.py preservation test |
| Mutation reasoning | STRONG | Reverting type to `object` fails get_type_hints; re-adding isinstance guard fails AST checks |
| Test independence | STRONG | Each test imports fresh, no shared mutable state |
| Descriptive names | STRONG | e.g. `test_command_safety_guard_accepts_pre_tool_use_data`, `test_notification_hook_make_handler_closure_no_isinstance` |

### Security Review
- No security issues. Pure typing refactor: removes dead isinstance guards, adds TypedDict annotations. No new attack surface, no external input changes, no secrets.

### Test Writer vs Builder Comparison
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_ConsumerParamAnnotations (11 tests) | No change | PRESERVED |
| TestFromAC_NoIsinstanceGuards (8 tests) | No change | PRESERVED |
| TestFromAC_MakeHandlerClosureTyping (2 tests) | NEW -- added by builder for arch review gap | STRENGTHENED |
| TestFromAC_RegistryGuardPreserved (1 test) | NEW -- added by builder for AC3 verification | STRENGTHENED |
| Docstring header | Updated task refs from `#715` to `#715 + #716` | PRESERVED |

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: 11 consumers typed | git diff shows all 11 `__call__`/handler signatures updated | TestFromAC_ConsumerParamAnnotations (11 tests) | PASS |
| AC2: Remove isinstance guards (13 total) | grep `isinstance(data, dict)` across src/owlbear/ returns only registry.py | TestFromAC_NoIsinstanceGuards (8 tests) + TestFromAC_MakeHandlerClosureTyping (1 test) | PASS |
| AC3: Don't touch skills/registry.py | grep confirms guard at registry.py:155 | TestFromAC_RegistryGuardPreserved | PASS |
| AC4: Tests pass, ruff clean | 22 passed, ruff exit 0 | Full test run + ruff check | PASS |
| AC5: Zero runtime behavior change | isinstance guards were unreachable; removal is no-op | Existing 328 hook tests still pass | PASS |

### Verdict: PASS (confidence .95)

[[2026-03-11]] Wed 09:20
## Review Evidence

### Test Results
- pytest (scoped): 22 passed, 0 failed (test_hook_consumer_types.py)
- pytest (related hooks): 328 passed, 0 failed (11 hook test files)
- pytest (full suite, --ignore test_project_session.py): 1393 passed, 61 failed, 9 errors
  - All 61 failures and 9 errors are pre-existing (bootstrap module, browser_snapshot, content_safety_integration, daemon CLI) -- none related to #716

### Lint Results
- ruff: All checks passed! (12 files checked)

### Coverage
- Not directly applicable: tests are structural (get_type_hints, AST inspection), not runtime. Builder reported 100% on notification_hook.py from existing tests.

### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Every test uses `get_type_hints()` with `is` identity checks against exact TypedDict types; AST-based guard detection checks exact patterns |
| Negative/error paths | STRONG | Tests verify both positive (typed annotations) AND negative (isinstance guards absent); registry.py preservation test |
| Mutation reasoning | STRONG | Reverting type to `object` fails get_type_hints; re-adding isinstance guard fails AST checks |
| Test independence | STRONG | Each test imports fresh, no shared mutable state |
| Descriptive names | STRONG | e.g. `test_command_safety_guard_accepts_pre_tool_use_data`, `test_notification_hook_make_handler_closure_no_isinstance` |

### Security Review
- No security issues. Pure typing refactor: removes dead isinstance guards, adds TypedDict annotations. No new attack surface, no external input changes, no secrets.

### Test Writer vs Builder Comparison
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_ConsumerParamAnnotations (11 tests) | No change | PRESERVED |
| TestFromAC_NoIsinstanceGuards (8 tests) | No change | PRESERVED |
| TestFromAC_MakeHandlerClosureTyping (2 tests) | NEW -- added by builder for arch review gap | STRENGTHENED |
| TestFromAC_RegistryGuardPreserved (1 test) | NEW -- added by builder for AC3 verification | STRENGTHENED |
| Docstring header | Updated task refs from `#715` to `#715 + #716` | PRESERVED |

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: 11 consumers typed | git diff shows all 11 `__call__`/handler signatures updated | TestFromAC_ConsumerParamAnnotations (11 tests) | PASS |
| AC2: Remove isinstance guards (13 total) | grep `isinstance(data, dict)` across src/owlbear/ returns only registry.py | TestFromAC_NoIsinstanceGuards (8 tests) + TestFromAC_MakeHandlerClosureTyping (1 test) | PASS |
| AC3: Don't touch skills/registry.py | grep confirms guard at registry.py:155 | TestFromAC_RegistryGuardPreserved | PASS |
| AC4: Tests pass, ruff clean | 22 passed, ruff exit 0 | Full test run + ruff check | PASS |
| AC5: Zero runtime behavior change | isinstance guards were unreachable; removal is no-op | Existing 328 hook tests still pass | PASS |

### Verdict: PASS (confidence .95)

[[2026-03-11]] Wed 09:23
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Typing refactor only, no behavior/API/convention change |
| 2 | Docstrings complete | Yes | Pass | All 11 consumer classes + handler methods have accurate docstrings (verified via search) |
| 3 | sources/overview.md | No | N/A | No external patterns used; internal TypedDicts from core/hooks.py |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/typed-hook-payloads.md exists and linked in AC body |

### Files Updated
- None

### Scratch Files Cleaned
- Deleted docs/scratch/716-full.txt

[[2026-03-11]] Wed 09:41
## Audit
Confidence: .97 -- all 5 AC verified with direct evidence.
Action: archive
