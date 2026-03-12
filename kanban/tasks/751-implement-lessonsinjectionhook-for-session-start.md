---
id: 751
title: Implement LessonsInjectionHook for session-start context
status: archived
priority: nice-to-have
created: 2026-03-12T10:48:47.8860851+01:00
updated: 2026-03-12T22:48:30.6416599+01:00
started: 2026-03-12T22:32:22.3323961+01:00
completed: 2026-03-12T22:48:30.6416599+01:00
tags:
    - hooks
    - agent
    - scope:core
depends_on:
    - 761
claimed_by: builder
claimed_at: 2026-03-12T22:32:22.3323961+01:00
class: standard
---

Implement a SESSION_START hook that reads recent curated lessons from .owlbear/lessons/ and injects them into agent context.
Ref: docs/research/olanetsoft-workflow-research.md (task #747)
Follows ContextInjectionHook pattern (src/owlbear/core/context_hook.py).

AC:
- [ ] New class `LessonsInjectionHook` in `src/owlbear/core/lessons_hook.py`
- [ ] Constructor accepts `lessons_dir: Path | None` (default `Path('.owlbear/lessons')`) and `max_tokens: int` (default 500)
- [ ] `register(hooks)` registers on `HookEvent.SESSION_START`
- [ ] `__call__(data: SessionStartData)` reads all `.md` files from `lessons_dir`, sorted by mtime descending (newest first)
- [ ] Concatenates file contents newest-first, stopping when approximate token count (`len(text) // 4`) would exceed `max_tokens`; last file may be truncated at a newline boundary
- [ ] Stores result in `data['lessons']` (str); empty string when directory is missing or empty
- [ ] Never raises — logs warning on read errors and degrades to empty string
- [ ] `settings.lessons_injection_enabled: bool = False` added to `OwlBearSettings` in config.py
- [ ] Conditionally registered in `bootstrap/hooks.py` only when `settings.lessons_injection_enabled` is True (same pattern as session_memory_enabled)

[[2026-03-12]] Thu 20:03
## Architecture Review
**Verdict:** APPROVED (merged with duplicate #749)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| New hook class in core/lessons_hook.py | Clear, correct layer | Kept |
| Reads .md from lessons dir | Vague: no ordering, no missing-dir handling | Refined: mtime desc, empty on missing |
| Token-budgeted (max 500) | Vague: no counting method or truncation strategy | Refined: len//4, newline-boundary truncation |
| Registered in bootstrap/hooks.py | Clear, follows pattern | Refined: conditional on settings gate |
| Unit tests in test_lessons_hook.py | TDD violation: test AC on impl task | Moved to #761 (test task) |
| Gated behind settings flag | Clear | Kept, registration-level gate |

### Architecture Notes
- Follows ContextInjectionHook (context_hook.py) pattern exactly: same layer, same register() signature, same SESSION_START event
- Config gating follows session_memory_enabled precedent (default False, conditional registration in bootstrap/hooks.py)
- Module layering OK: core/ reads files only, no upward imports
- Security: reads local .md files from workspace-confined path only; no external I/O
- Duplicate #749 deleted (identical to #751; #751 is canonical per #747 review)

### Changes Made
- Deleted #749 (duplicate)
- Created #761 (TDD RED test task, status: todo)
- Added depends_on: [761] to #751
- Refined all AC lines for verifiability
- Removed test AC (moved to #761)

### Dependencies
- Added: #761 (test task, must complete before #751)
- Verified: no hard upstream dependency; .owlbear/lessons/ may be empty (hook degrades gracefully)

[[2026-03-12]] Thu 21:55
## Test-Writer Notes
- Test file: tests/test_lessons_hook.py
- Classes: TestFromAC_NeverRaises, TestFromAC_LessonsConfig, TestFromAC_BootstrapRegistration
- Tests per category: happy 0, edge 1, error 4, boundary 1, config 3
- Total: 9 tests, all FAIL
- ruff: clean
- AC coverage:

| AC Line | Test(s) | Category |
|---------|---------|----------|
| Never raises - logs warning on read errors | test_unreadable_file_logs_warning_and_continues | error |
| Never raises - logs warning on read errors | test_read_error_all_files_returns_empty | error |
| Never raises - logs warning on read errors | test_unicode_decode_error_logs_and_skips | error |
| Never raises - logs warning on read errors | test_stat_error_degrades_gracefully | edge |
| settings.lessons_injection_enabled: bool = False | test_setting_defaults_false | config |
| settings.lessons_injection_enabled: bool = False | test_setting_can_enable | config |
| settings.lessons_injection_enabled: bool = False | test_setting_via_env_var | config |
| Conditionally registered in bootstrap/hooks.py | test_build_hooks_registers_when_enabled | boundary |
| Conditionally registered in bootstrap/hooks.py | test_build_hooks_skips_when_disabled | boundary |

[[2026-03-12]] Thu 22:12
## Builder Notes
- Files changed: src/owlbear/core/lessons_hook.py, src/owlbear/config.py, src/owlbear/bootstrap/hooks.py
- Tests: 35 passed (26 pre-existing + 9 newly green), coverage 98% on lessons_hook.py
- Lint: ruff clean
- Changes:
  1. lessons_hook.py: Added try/except around stat() (extracted _sorted_md_files helper) and read_text() for never-raises error handling
  2. config.py: Added lessons_injection_enabled: bool = False field to OwlBearSettings
  3. bootstrap/hooks.py: Conditional LessonsInjectionHook registration when settings.lessons_injection_enabled is True

[[2026-03-12]] Thu 22:22
## Review Evidence

### Test Results
- pytest (scoped): 35 passed, 0 failed
- pytest (broader): 231 passed across daemon/cli/config/hooks/poll_dedup/lessons_hook â€” no regressions
- Full suite: pre-existing qdrant_client import hang blocks unscoped run (env issue, not task-related)

### Lint Results
- ruff: All checks passed (lessons_hook.py, config.py, bootstrap/hooks.py, test_lessons_hook.py)

### Coverage
- lessons_hook.py: 98% (1 line uncovered: elif last_nl==0 branch at L112 â€” first-char-newline edge case)
- bootstrap/hooks.py: 86%

### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact value checks (Path, int, string content, is False/True), token budget len//4 <= max_tokens |
| Negative/error paths | STRONG | PermissionError, OSError, UnicodeDecodeError, stat failure, missing dir, empty dir, non-.md files, zero budget |
| Mutation reasoning | STRONG | Removing everse=True breaks ordering test; removing exception handler breaks NeverRaises; changing default breaks config test |
| Test independence | STRONG | All tests use 	mp_path/monkeypatch â€” no shared mutable state |
| Descriptive names | STRONG | e.g. 	est_newest_file_content_appears_first, 	est_unreadable_file_logs_warning_and_continues |

### Security Review
- No hardcoded secrets
- No injection surfaces (reads local .md files only, no user input at runtime)
- No path traversal (glob from fixed dir, bootstrap uses default path)
- No insecure deserialization
- No new dependencies
- Logs expose only file paths and exception messages â€” no sensitive data

### Test Writer vs Builder Comparison
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_NeverRaises::test_unreadable_file_logs_warning_and_continues | No change | PRESERVED |
| TestFromAC_NeverRaises::test_read_error_all_files_returns_empty | No change | PRESERVED |
| TestFromAC_NeverRaises::test_unicode_decode_error_logs_and_skips | No change | PRESERVED |
| TestFromAC_NeverRaises::test_stat_error_degrades_gracefully | No change | PRESERVED |
| TestFromAC_LessonsConfig::test_setting_defaults_false | No change | PRESERVED |
| TestFromAC_LessonsConfig::test_setting_can_enable | No change | PRESERVED |
| TestFromAC_LessonsConfig::test_setting_via_env_var | No change | PRESERVED |
| TestFromAC_BootstrapRegistration::test_build_hooks_registers_when_enabled | No change | PRESERVED |
| TestFromAC_BootstrapRegistration::test_build_hooks_skips_when_disabled | No change | PRESERVED |

Builder added 26 additional tests in 7 new classes (constructor, register, mtime sorting, token budget, missing/empty dir, data population, hook registry integration). All strengthen coverage.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| New class LessonsInjectionHook in core/lessons_hook.py | [lessons_hook.py L23](src/owlbear/core/lessons_hook.py#L23) | TestFromACConstructor | PASS |
| Constructor: lessons_dir Path|None, max_tokens int, defaults | [L47-52](src/owlbear/core/lessons_hook.py#L47) | test_default_lessons_dir, test_default_max_tokens, test_none_uses_default | PASS |
| register(hooks) on SESSION_START | [L63-66](src/owlbear/core/lessons_hook.py#L63) | test_register_adds_to_session_start | PASS |
| __call__ reads .md sorted mtime desc | [L72-82](src/owlbear/core/lessons_hook.py#L72) _sorted_md_files | test_newest_file_content_appears_first, test_three_files_ordered | PASS |
| Token budget len//4, newline truncation | [L84-120](src/owlbear/core/lessons_hook.py#L84) _collect_lessons | test_budget_exceeded, test_last_file_truncated_at_newline, test_zero_budget | PASS |
| data['lessons'] = str; empty when missing/empty | [L58](src/owlbear/core/lessons_hook.py#L58) | test_missing_directory_returns_empty, test_empty_directory_returns_empty | PASS |
| Never raises â€” logs warning | [L80-81, L97-98](src/owlbear/core/lessons_hook.py#L80) try/except | test_unreadable_file_logs_warning, test_stat_error_degrades | PASS |
| settings.lessons_injection_enabled: bool = False | [config.py L304-310](src/owlbear/config.py#L304) | test_setting_defaults_false, test_setting_can_enable, test_setting_via_env_var | PASS |
| Conditional registration in bootstrap/hooks.py | [hooks.py L51-54](src/owlbear/bootstrap/hooks.py#L51) | test_build_hooks_registers_when_enabled, test_build_hooks_skips_when_disabled | PASS |

### Verdict: PASS
Confidence: .95

### Action Taken
kanban move 751 docs

[[2026-03-12]] Thu 22:32
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Internal hook + config flag; no tech stack or convention changes |
| 2 | Docstrings complete | Yes | Pass | Module, class, method docstrings present in lessons_hook.py; Field description on config.py |
| 3 | sources/overview.md | No | N/A | Internal pattern; Olanetsoft entry already under #747 |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | No | N/A | Research was #747; doc exists at docs/research/olanetsoft-workflow-research.md |

### Files Updated
- None

### Scratch Files Cleaned
- None
