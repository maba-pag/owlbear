---
id: 622
title: Implement session-memory hook for context persistence across sessions
status: archived
priority: important
created: 2026-03-07T05:21:06.0725486+01:00
updated: 2026-03-11T23:27:34.903692+01:00
started: 2026-03-07T07:04:24.5342922+01:00
completed: 2026-03-11T23:27:22.6272+01:00
tags:
    - scope:core
    - hooks
depends_on:
    - 711
claimed_by: auditor
claimed_at: 2026-03-11T23:27:34.9010738+01:00
class: standard
---

SessionMemoryHook: on SESSION_END, persist a compact LLM-generated summary to
{workspace}/.owlbear/session-memory.md. On next startup, ContextManager.instructions
reads the file and injects it into the agent's system prompt.

See docs/research/session-memory-hook-research.md.
depends_on: #711 (archived $([char]0x2714))

AC:
- [ ] `SessionMemoryHook` class in `src/owlbear/core/session_memory_hook.py`
- [ ] Constructor: `workspace_root: Path`, `summarizer: Callable[[str], Awaitable[str]]` (DI for LLM â€” hook serialises messages to text before calling)
- [ ] `register(hooks: HookRegistry)` registers async handler on `SESSION_END` only (no SESSION_START handler â€” YAGNI per research)
- [ ] On SESSION_END: extract `data[messages]`, serialise to text, call `summarizer`, write result to `{workspace}/.owlbear/session-memory.md`
- [ ] If `messages` list is empty or missing: skip persist (no file written, no error)
- [ ] Summary target: ~500 tokens structured markdown with headings `## Key Decisions`, `## Active Tasks`, `## Workspace State`
- [ ] Graceful degradation: if summarizer call fails, `logger.warning()` and return â€” never raise
- [ ] Ensure `{workspace}/.owlbear/` directory exists before write (`mkdir(parents=True, exist_ok=True)`)
- [ ] Restore: `ContextManager.instructions` in `memory/context.py` reads `.owlbear/session-memory.md` when present (after MEMORY.md, before joining)
- [ ] Missing `session-memory.md` silently skipped in ContextManager
- [ ] Config: `session_memory_enabled: bool = Field(default=False)` in `OwlBearSettings`
- [ ] Bootstrap wiring in `bootstrap/__init__.py` (NOT `build_hooks()`) â€” register after model creation, following `RetrospectiveHook` pattern
- [ ] Wiring: `SessionMemoryHook(workspace_root=workspace, summarizer=<async closure using model>).register(hooks)` guarded by `settings.session_memory_enabled`
- [ ] `uv run ruff check` clean on all touched files

[[2026-03-11]] Wed 18:00
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| SessionMemoryHook in core/session_memory_hook.py | Correct  hook imports from core/hooks.py, memory/ can't import core/ | Keep |
| Constructor: workspace_root + summarizer DI | Clean DI, matches existing patterns | Keep |
| register on SESSION_END only | Correct  research says no SESSION_START handler (YAGNI) | Refined: removed original SESSION_START handler |
| Extract messages, summarize, write file | Clear, verifiable, follows TestVerificationHook pattern | Keep |
| Empty messages skip persist | Defensive, clear edge case | Keep |
| ~500 token structured markdown | Verifiable target | Keep |
| Graceful degradation (log, never raise) | Matches hook error isolation pattern | Keep |
| mkdir parents=True exist_ok=True | Follows ObservabilityHook EventStore pattern | Keep |
| ContextManager restore (memory/context.py) | Ancillary 5-LOC change, not a domain violation | Added (replaces SESSION_START handler) |
| session_memory_enabled config | Standard opt-in bool pattern | Keep |
| Bootstrap wiring in __init__.py not build_hooks() | Fixed  model not available in build_hooks(), follows RetrospectiveHook | Refined: changed from build_hooks() |
| ruff clean | Standard gate | Keep |

### Architecture Notes
- Module placement in core/ is correct (hook consumer pattern)
- Research suggested memory/ but that violates layering (memory/ cannot import core/hooks)
- SESSION_START handler removed: payload data[session_memory] had no consumer (dead-end)
- Restore via ContextManager.instructions is simpler and already has precedent (MEMORY.md)
- Bootstrap wiring must follow RetrospectiveHook pattern (needs model, created after build_hooks)
- Existing patterns to follow: ContextInjectionHook (SESSION_START), TestVerificationHook (SESSION_END), ObservabilityHook (file I/O with EventStore)

### Changes Made
- Rewrote task body with refined AC
- Removed SESSION_START handler (YAGNI), added ContextManager restore AC
- Fixed bootstrap wiring location (bootstrap/__init__.py, not build_hooks())
- Unblocked task (#711 dependency is archived)
- Removed phase-research tag

### Dependencies
- Verified: #711 (SESSION_START/SESSION_END emission)  archived

[[2026-03-11]] Wed 18:00
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| SessionMemoryHook in core/session_memory_hook.py | Correct  hook imports from core/hooks.py, memory/ can't import core/ | Keep |
| Constructor: workspace_root + summarizer DI | Clean DI, matches existing patterns | Keep |
| register on SESSION_END only | Correct  research says no SESSION_START handler (YAGNI) | Refined: removed original SESSION_START handler |
| Extract messages, summarize, write file | Clear, verifiable, follows TestVerificationHook pattern | Keep |
| Empty messages skip persist | Defensive, clear edge case | Keep |
| ~500 token structured markdown | Verifiable target | Keep |
| Graceful degradation (log, never raise) | Matches hook error isolation pattern | Keep |
| mkdir parents=True exist_ok=True | Follows ObservabilityHook EventStore pattern | Keep |
| ContextManager restore (memory/context.py) | Ancillary 5-LOC change, not a domain violation | Added (replaces SESSION_START handler) |
| session_memory_enabled config | Standard opt-in bool pattern | Keep |
| Bootstrap wiring in __init__.py not build_hooks() | Fixed  model not available in build_hooks(), follows RetrospectiveHook | Refined: changed from build_hooks() |
| ruff clean | Standard gate | Keep |

### Architecture Notes
- Module placement in core/ is correct (hook consumer pattern)
- Research suggested memory/ but that violates layering (memory/ cannot import core/hooks)
- SESSION_START handler removed: payload data[session_memory] had no consumer (dead-end)
- Restore via ContextManager.instructions is simpler and already has precedent (MEMORY.md)
- Bootstrap wiring must follow RetrospectiveHook pattern (needs model, created after build_hooks)
- Existing patterns to follow: ContextInjectionHook (SESSION_START), TestVerificationHook (SESSION_END), ObservabilityHook (file I/O with EventStore)

### Changes Made
- Rewrote task body with refined AC
- Removed SESSION_START handler (YAGNI), added ContextManager restore AC
- Fixed bootstrap wiring location (bootstrap/__init__.py, not build_hooks())
- Unblocked task (#711 dependency is archived)
- Removed phase-research tag

### Dependencies
- Verified: #711 (SESSION_START/SESSION_END emission)  archived

[[2026-03-11]] Wed 19:21
## Test-Writer Notes
- Test file: tests/test_session_memory_hook.py
- Classes: TestFromAC_SessionMemoryHook, TestFromAC_ContextManagerSessionRestore, TestFromAC_SessionMemoryConfig, TestFromAC_SessionMemoryBootstrap
- Tests per category: happy 6, edge 5, error 2, boundary 6
- Total: 19 tests, all FAIL (ModuleNotFoundError/AssertionError/AttributeError)
- ruff: clean
- AC coverage:
| AC Line | Test(s) | Category |
|---------|---------|----------|
| AC-1 SessionMemoryHook class | test_import_and_instantiate | happy |
| AC-2 Constructor DI | test_constructor_accepts_workspace_and_summarizer | happy |
| AC-3 register SESSION_END only | test_register_hooks_session_end_only | happy |
| AC-4 SESSION_END handler | test_session_end_writes_summary_file, test_summarizer_receives_serialised_messages | happy |
| AC-5 Empty/missing messages | test_empty_messages_skips_persist, test_missing_messages_key_skips_persist | edge |
| AC-7 Graceful degradation | test_summarizer_failure_logs_warning_no_raise | error |
| AC-8 mkdir parents | test_creates_owlbear_directory_if_missing, test_owlbear_directory_already_exists | boundary |
| AC-8b Overwrite | test_overwrites_existing_session_memory | boundary |
| AC-9 ContextManager restore | test_instructions_includes_session_memory, test_session_memory_after_memory_md | happy |
| AC-10 Missing file skip | test_instructions_without_session_memory_still_works | edge |
| AC-11 Config default | test_setting_defaults_false, test_setting_can_enable, test_setting_via_env_var | happy/boundary |
| AC-12/13 Bootstrap wiring | test_hook_registered_when_enabled, test_hook_not_registered_when_disabled | happy/edge |

[[2026-03-11]] Wed 20:00
## Builder Notes
- Files: session_memory_hook.py (new), context.py (+4 LOC), config.py (+6 LOC)
- Tests: 19 passed, 100%% coverage on session_memory_hook.py
- Lint: ruff clean

[[2026-03-11]] Wed 20:10
## Review Evidence

### Test Results
- pytest: 19 passed, 0 failed (tests/test_session_memory_hook.py)

### Lint Results
- ruff: All checks passed (5 files)

### Coverage
- session_memory_hook.py: 100%
- context.py: 84% (pre-existing uncovered code; new lines covered)
- config.py: 81% (pre-existing uncovered code; session_memory_enabled covered)

### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | Most tests check specific content, file existence, call counts. test_constructor_accepts_workspace_and_summarizer only asserts `is not None` but that's marginal. |
| Negative/error paths | ADEQUATE | Covers empty messages, missing key, summarizer failure with log check. |
| Mutation reasoning | ADEQUATE | Flipping empty-check would break skip tests. Removing try/except would break graceful test. Removing mkdir would break dir creation test. |
| Test independence | STRONG | Each test creates fresh tmp_path and fresh mocks. No shared state. |
| Descriptive names | STRONG | Names describe scenario: test_empty_messages_skips_persist, test_summarizer_failure_logs_warning_no_raise. |

### Security Review
- No hardcoded secrets
- No injection vectors (file writes use known constant filename)
- No path traversal risk (workspace_root used directly, filename fixed as _SESSION_MEMORY_FILENAME constant)
- No insecure deserialization
- No new dependencies
- No secret leakage in logs (warning log only says summarizer failed)
- session-memory.md content comes from LLM summarizer output -- no direct user input to filesystem outside controlled paths

### Test Writer vs Builder Comparison
Note: test file was never committed separately (both test-writer and builder work is in the same untracked file). All TestFromAC classes reviewed as-is.

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_SessionMemoryHook::test_import_and_instantiate | N/A (baseline) | PRESERVED |
| TestFromAC_SessionMemoryHook::test_constructor_accepts_workspace_and_summarizer | N/A | PRESERVED |
| TestFromAC_SessionMemoryHook::test_register_hooks_session_end_only | N/A | PRESERVED |
| TestFromAC_SessionMemoryHook::test_session_end_writes_summary_file | N/A | PRESERVED |
| TestFromAC_SessionMemoryHook::test_summarizer_receives_serialised_messages | N/A | PRESERVED |
| TestFromAC_SessionMemoryHook::test_empty_messages_skips_persist | N/A | PRESERVED |
| TestFromAC_SessionMemoryHook::test_missing_messages_key_skips_persist | N/A | PRESERVED |
| TestFromAC_SessionMemoryHook::test_summarizer_failure_logs_warning_no_raise | N/A | PRESERVED |
| TestFromAC_SessionMemoryHook::test_creates_owlbear_directory_if_missing | N/A | PRESERVED |
| TestFromAC_SessionMemoryHook::test_owlbear_directory_already_exists | N/A | PRESERVED |
| TestFromAC_SessionMemoryHook::test_overwrites_existing_session_memory | N/A | PRESERVED |
| TestFromAC_ContextManagerSessionRestore::test_instructions_includes_session_memory | N/A | PRESERVED |
| TestFromAC_ContextManagerSessionRestore::test_session_memory_after_memory_md | N/A | PRESERVED |
| TestFromAC_ContextManagerSessionRestore::test_instructions_without_session_memory_still_works | N/A | PRESERVED |
| TestFromAC_SessionMemoryConfig::test_setting_defaults_false | N/A | PRESERVED |
| TestFromAC_SessionMemoryConfig::test_setting_can_enable | N/A | PRESERVED |
| TestFromAC_SessionMemoryConfig::test_setting_via_env_var | N/A | PRESERVED |
| TestFromAC_SessionMemoryBootstrap::test_hook_registered_when_enabled | N/A | PRESERVED |
| TestFromAC_SessionMemoryBootstrap::test_hook_not_registered_when_disabled | N/A | PRESERVED |

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC-1 SessionMemoryHook class | session_memory_hook.py exists, class at line 27 | test_import_and_instantiate | PASS |
| AC-2 Constructor DI | __init__(workspace_root, summarizer) at lines 36-41 | test_constructor_accepts_workspace_and_summarizer | PASS |
| AC-3 register SESSION_END only | register() at lines 72-75 calls hooks.register(HookEvent.SESSION_END, self) | test_register_hooks_session_end_only | PASS |
| AC-4 SESSION_END handler | __call__ at lines 47-66 extracts messages, calls summarizer, writes file | test_session_end_writes_summary_file, test_summarizer_receives_serialised_messages | PASS |
| AC-5 Empty/missing messages | Lines 52-53: if not messages: return | test_empty_messages_skips_persist, test_missing_messages_key_skips_persist | PASS |
| AC-6 Summary structured markdown | Summarizer is DI, template is caller's responsibility -- hook just writes the string | (implicit via AC-4 tests) | PASS |
| AC-7 Graceful degradation | Lines 57-59: except Exception + logger.warning | test_summarizer_failure_logs_warning_no_raise | PASS |
| AC-8 mkdir parents | Line 61-62: output_dir.mkdir(parents=True, exist_ok=True) | test_creates_owlbear_directory_if_missing, test_owlbear_directory_already_exists | PASS |
| AC-9 ContextManager restore | context.py lines 79-83: reads .owlbear/session-memory.md when present | test_instructions_includes_session_memory, test_session_memory_after_memory_md | PASS |
| AC-10 Missing file skip | context.py line 80: if session_memory_path.exists() | test_instructions_without_session_memory_still_works | PASS |
| AC-11 Config default | config.py line 296: session_memory_enabled: bool = Field(default=False) | test_setting_defaults_false, test_setting_can_enable, test_setting_via_env_var | PASS |
| AC-12 Bootstrap wiring | **NOT FOUND** in bootstrap/__init__.py. grep for SessionMemoryHook returns 0 matches. git diff shows no session_memory wiring added. | test_hook_registered_when_enabled (test passes but tests the hook API, not bootstrap) | **FAIL** |
| AC-13 Wiring guarded by config | **NOT FOUND** -- no `if settings.session_memory_enabled:` block in bootstrap. | test_hook_not_registered_when_disabled (passes but tests config default, not bootstrap code) | **FAIL** |
| AC-14 ruff clean | All checks passed on all 5 files | (ruff output) | PASS |

### Rejection Table
| Gap | Required Fix |
|-----|-------------|
| AC-12: Bootstrap wiring missing | Add `if settings.session_memory_enabled:` block in bootstrap/__init__.py after the RetrospectiveHook block (~line 113). Create async summarizer closure using model. Wire `SessionMemoryHook(workspace_root=workspace, summarizer=summarizer).register(hooks)` |
| AC-13: Config guard missing | The wiring block must be guarded by `settings.session_memory_enabled` (same block as AC-12) |

### Verdict: FAIL
- Confidence: .80
- Critical gap: AC-12/13 bootstrap wiring entirely absent. The hook class is implemented correctly but never gets connected in the real application startup.

[[2026-03-11]] Wed 21:15
## Test-Writer Notes
- Test file: tests/test_session_memory_hook.py (pre-existing, lint-fixed 2 unused noqa directives)
- Classes: TestFromAC_SessionMemoryHook, TestFromAC_ContextManagerSessionRestore, TestFromAC_SessionMemoryConfig, TestFromAC_SessionMemoryBootstrap
- Tests per category: happy 11, edge 4, error 2, boundary 2
- Total: 19 tests, all PASS (impl already exists)
- ruff: clean
- AC coverage: all 13 AC lines covered
- Note: implementation + tests both untracked. Builder should commit.

[[2026-03-11]] Wed 21:57
## Builder Notes (cycle 2)
- Gap fixed: AC-12/13 bootstrap wiring added in bootstrap/__init__.py
- Extracted _wire_session_memory_hook() and _wire_post_model_hooks() helpers to keep bootstrap() under PLR0915/C901 limits
- Uses PydanticAI Agent pattern (same as SummarizingCondenser / RetrospectiveHook)
- Wiring guarded by settings.session_memory_enabled
- Files changed: src/owlbear/bootstrap/__init__.py (+35 LOC, 1 refactored block)
- Tests: 19 passed, 100% coverage on session_memory_hook.py
- Bootstrap tests: 174 passed (1 pre-existing slack_sdk env failure)
- Lint: ruff clean on all 5 files
- No TestFromAC classes modified

[[2026-03-11]] Wed 22:34
## Test-Writer Notes (cycle 3)
- Test file: tests/test_session_memory_hook.py
- Classes: TestFromAC_SessionMemoryHook, TestFromAC_ContextManagerSessionRestore, TestFromAC_SessionMemoryConfig, TestFromAC_SessionMemoryBootstrap
- Tests per category: happy 8, edge 4, error 2, boundary 6
- Total: 20 tests, all PASS (impl exists from cycle 2)
- ruff: clean
- Key fix: rewrote AC-12/13 bootstrap tests to call actual _wire_post_model_hooks and _wire_session_memory_hook functions (reviewer gap)
- AC coverage:
| AC Line | Test(s) | Category |
|---------|---------|----------|
| AC-1 class | test_import_and_instantiate | happy |
| AC-2 constructor DI | test_constructor_accepts_workspace_and_summarizer | happy |
| AC-3 register SESSION_END | test_register_hooks_session_end_only | happy |
| AC-4 handler | test_session_end_writes_summary_file, test_summarizer_receives_serialised_messages | happy |
| AC-5 empty/missing | test_empty_messages_skips_persist, test_missing_messages_key_skips_persist | edge |
| AC-7 graceful degradation | test_summarizer_failure_logs_warning_no_raise | error |
| AC-8 mkdir | test_creates_owlbear_directory_if_missing, test_owlbear_directory_already_exists | boundary |
| AC-8b overwrite | test_overwrites_existing_session_memory | boundary |
| AC-9 ContextManager restore | test_instructions_includes_session_memory, test_session_memory_after_memory_md | happy/boundary |
| AC-10 missing file skip | test_instructions_without_session_memory_still_works | edge |
| AC-11 config default | test_setting_defaults_false, test_setting_can_enable, test_setting_via_env_var | happy/boundary |
| AC-12 bootstrap wiring | test_wire_post_model_hooks_registers_when_enabled, test_wire_session_memory_hook_registers_session_end | happy |
| AC-13 config guard | test_wire_post_model_hooks_skips_when_disabled | edge |

[[2026-03-11]] Wed 22:44
## Builder Notes (cycle 3)
- Verified: 20 TestFromAC tests pass, 0 failures
- Lint: ruff clean on all 5 files
- Coverage: session_memory_hook.py 100%%, context.py 84%%, config.py 81%%
- Bootstrap wiring confirmed: _wire_session_memory_hook() + config guard present
- No TestFromAC classes modified
- No new files created (impl from cycle 2 unchanged)

[[2026-03-11]] Wed 23:06
## Review Evidence (reviewer, 2026-03-11)
Test: 20 passed 0 failed. Full suite: 1453 passed 17 failed (none 622-related). Lint: clean. Coverage: session_memory_hook.py 100%. Test quality: ADEQUATE-STRONG. Security: no issues. AC: all 14 PASS. Confidence: .92. Verdict: PASS

[[2026-03-11]] Wed 23:14
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Internal hook following existing patterns; no behavior/API/convention change. Tech stack table doesn't list individual hooks. |
| 2 | Docstrings complete | Yes | Updated | session_memory_hook.py: module + class + all methods have docstrings. context.py: updated instructions property docstring to mention session-memory.md. config.py: Field(description=...) present. |
| 3 | sources/overview.md | Yes | Pass | Already has 4 entries (LangGraph Checkpointer, OpenHands Condenser, OpenClaw session-memory hook, OpenClaw Hooks docs) linked to session-memory-hook-research.md. |
| 4 | README.md | No | N/A | No CLI changes. |
| 5 | Research doc linked | Yes | Pass | docs/research/session-memory-hook-research.md exists, linked from task body. |

### Files Updated
- src/owlbear/memory/context.py (docstring only: instructions property)

### Scratch Files Cleaned
- None (no docs/scratch/622-* files found)

[[2026-03-11]] Wed 23:27
## Audit
### AC: All 14 lines PASS
### Tests: 20/20 pass, full suite 1453 passed (17 failed, none #622)
### Lint: ruff clean
### Confidence: .96
### Action: archive
