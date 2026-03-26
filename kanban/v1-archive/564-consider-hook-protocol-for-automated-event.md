---
id: 564
title: Consider Hook protocol for automated event registration
status: archived
priority: someday
created: 2026-03-04T07:39:07.0113635+01:00
updated: 2026-03-21T17:02:12.7009776+01:00
started: 2026-03-07T04:29:50.1410163+01:00
completed: 2026-03-21T17:02:08.443779+01:00
tags:
    - audit
    - dry
    - hooks
class: standard
---

DECISION: Keep explicit hook registration. See docs/research/hook-protocol.md. The 8 hook classes (not 9 -- escalation.py deleted by #484) use 3 different registration patterns. Only 6/8 are uniform. Net LOC savings would be negative. KISS/YAGNI/Django all argue against auto-registration magic.

## AC

- [x] Decision documented: Keep explicit registration

[[2026-03-21]] Sat 13:08
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Decision documented: Keep explicit registration | Clear, verifiable no-op design decision. The task body and docs/research/hook-protocol.md already record the keep-explicit rationale. | Accept as-is |

### Architecture Notes
The codebase already centralizes hook wiring in src/owlbear/bootstrap/hooks.py via explicit per-class register calls in the assembly root. The existing hook classes are not uniform: src/owlbear/core/command_guard.py and src/owlbear/core/progress.py register a single handler directly; src/owlbear/tools/screenshot_hook.py registers a named method and also exposes unregister(); src/owlbear/core/notification_hook.py and src/owlbear/core/observability.py register per-event closures in loops. That variance makes an auto-registration protocol a net abstraction increase rather than a simplification. No new dependency, layering, security-surface, or interface contract is introduced by keeping the explicit pattern. TDD and failure-mode mapping are N/A because this is a decision-only task, not an implementation task.

### Changes Made
- Claimed task for architect review as architect-564
- Appended this Architecture Review section
- Moved task to todo

### Dependencies
- Verified existing assembly boundary: src/owlbear/bootstrap/hooks.py remains the single explicit hook wiring point
- Added/Removed/Verified: no implementation dependencies; no RED predecessor required because this task produces no code

[[2026-03-21]] Sat 13:40
## Test-Writer Notes
Non-implementation task (design decision — no code produced). The Architecture Review confirms TDD and failure-mode mapping are N/A. The sole AC line (decision documented) is already resolved via docs/research/hook-protocol.md. Passing through to builder with no test file.

[[2026-03-21]] Sat 14:13
## Builder Notes
- Non-implementation task — no code changes needed.
- AC verified: docs/research/hook-protocol.md exists (5614 bytes) and documents the keep-explicit-registration decision.
- Passing through to review.

[[2026-03-21]] Sat 14:59
## Review Evidence
## Review: #564 - Consider Hook protocol for automated event registration

### Test Results
- pytest: `uv run pytest tests/test_bootstrap.py -q --tb=short` => 158 passed, 1 failed (unrelated optional dependency: slack_sdk missing for Slack channel test)
- pytest (task-scoped): `uv run pytest tests/test_bootstrap.py -k TestBuildHooks -q --tb=short` => 13 passed, 0 failed, 146 deselected

### Lint Results
- ruff (broad scoped file set): `uv run ruff check src/owlbear/bootstrap/hooks.py tests/test_bootstrap.py` => 6 errors in pre-existing `tests/test_bootstrap.py` `# noqa: N801` directives (RUF100 at lines 1975, 1996, 2017, 2675, 2767, 2869)
- ruff (task module): `uv run ruff check src/owlbear/bootstrap/hooks.py` => All checks passed

### Coverage
- command: `uv run pytest tests/test_bootstrap.py -k TestBuildHooks --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short`
- module coverage: `src/owlbear/bootstrap/hooks.py` = 100% (32 statements, 0 missed)

### Pass 1 - CRITICAL
#### Security Review
- No security issues found in task scope.
- Evidence: task is decision-only with no implementation changes; explicit hook wiring remains in `src/owlbear/bootstrap/hooks.py` lines 42-60.

#### Test Integrity (TestFromAC comparison)
- N/A for #564. No TestFromAC classes were authored or modified for this task.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | Existing `TestBuildHooks` tests assert handler registration for concrete events; no new tests were introduced by #564. |
| Negative/error paths | ADEQUATE | Decision-only task; no new behavior introduced requiring new negative-path tests. |
| Mutation reasoning | ADEQUATE | If explicit registration calls were removed, `TestBuildHooks` event handler presence checks would fail. |
| Test independence | STRONG | Tests instantiate fresh settings/registry per test and do not share mutable fixture state. |
| Descriptive names | STRONG | Names such as `test_pre_tool_use_has_handler` and `test_observability_hook_with_workspace` are scenario-specific. |

#### Data Safety
- No data safety issues found. No persistence or concurrency logic was modified.

### Pass 2 - INFORMATIONAL
- Decision evidence is explicit and current in `docs/research/hook-protocol.md` lines 53-55 (recommendation to keep explicit registration).
- Hook assembly remains explicit and centralized in `src/owlbear/bootstrap/hooks.py` (`build_hooks`, lines 27-66).

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Decision documented: Keep explicit registration | `kanban/tasks/564-consider-hook-protocol-for-automated-event.md` line 22 checkbox + line 18 decision statement; `docs/research/hook-protocol.md` lines 53 and 55 recommendation text | N/A (documentation-only AC) | PASS |

### Verdict: PASS

### Action Taken
- kanban\kanban-md.exe edit 564 --status docs --release

[[2026-03-21]] Sat 16:04
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Decision-only task; no behavior or API change |
| 2 | Docstrings | No | N/A | No Python modules created or modified |
| 3 | sources/overview.md | Yes | Pass | Section already present (line 1447) with pluggy, blinker, Django entries |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/hook-protocol.md exists; linked in task body; no follow-up tasks needed (keep-explicit decision) |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/564-* files found)

[[2026-03-21]] Sat 17:01
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Decision documented: Keep explicit registration | docs/research/hook-protocol.md committed (42ff2c6), recommendation section (.80 confidence: Keep Explicit). Task body records decision inline. No follow-up tasks needed — doc explicitly states no implementation recommended. | PASS |

### Test Results
- pytest: 3723 passed, 97 failed (all pre-existing systemic: numpy compat, bootstrap signature changes), 20 skipped — none related to #564
- ruff: hooks.py clean

### Research Task Checks
- Research doc exists: YES (docs/research/hook-protocol.md)
- Follow-up tasks created or no-action justified: YES (doc states no implementation recommended)
- Task body links to doc: YES

### Confidence: .97
### Action: archive

[[2026-03-21]] Sat 17:01
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Decision documented: Keep explicit registration | docs/research/hook-protocol.md committed (42ff2c6), recommendation section (.80 confidence: Keep Explicit). Task body records decision inline. No follow-up tasks needed -- doc explicitly states no implementation recommended. | PASS |

### Test Results
- pytest: 3723 passed, 97 failed (all pre-existing systemic: numpy compat, bootstrap signature changes), 20 skipped -- none related to #564
- ruff: hooks.py clean

### Research Task Checks
- Research doc exists: YES (docs/research/hook-protocol.md)
- Follow-up tasks created or no-action justified: YES (doc states no implementation recommended)
- Task body links to doc: YES

### Confidence: .97
### Action: archive

[[2026-03-21]] Sat 17:02
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Decision documented: Keep explicit registration | docs/research/hook-protocol.md committed (42ff2c6), recommendation section (.80 confidence: Keep Explicit). Task body records decision inline. No follow-up tasks needed -- doc explicitly states no implementation recommended. | PASS |

### Test Results
- pytest: 3723 passed, 97 failed (all pre-existing systemic: numpy compat, bootstrap signature changes), 20 skipped -- none related to #564
- ruff: hooks.py clean

### Research Task Checks
- Research doc exists: YES (docs/research/hook-protocol.md)
- Follow-up tasks created or no-action justified: YES (doc states no implementation recommended)
- Task body links to doc: YES

### Confidence: .97
### Action: archive
