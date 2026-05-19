---
id: 849
title: 'Fix circular import: core/errors.py -> tools/__init__.py -> core/retry.py'
status: archived
priority: needed
created: 2026-03-18T12:40:02.2216171+01:00
updated: 2026-03-22T19:17:54.2078712+01:00
started: 2026-03-22T19:17:54.2078712+01:00
completed: 2026-03-22T19:17:54.2078712+01:00
tags:
    - bug
    - architecture
    - scope:core
blocked: true
block_reason: 'Resolved by archived #850/#860; historical tracker only. Refresh research before reopening.'
class: standard
---

Circular import root cause: `core/errors.py` imports `BlockedURLError` from `tools/browser/safety.py`, which creates a forbidden `core -> tools` dependency edge. The eager re-exports in `tools/__init__.py` expose that violation by pulling `github_api.py -> core/retry.py` during package import.

Blocks: #536 (CLI tests), #541 (daemon tests), #841 (auditor verification).

Research: see `docs/research/core-tools-circular-import.md`.

## Refined AC

1. The approved fix must remove the `owlbear.core.errors -> owlbear.tools.browser.safety` import edge rather than only masking the cycle with lazy imports, local imports inside `classify_error()`, or package API rollback.
2. The public browser-safety exception contract must remain explicit: `BlockedURLError` stays importable from `owlbear.tools.browser.safety`, or a separate migration task is created before any removal.
3. Regression coverage must prove that fresh-process `import owlbear.daemon` and `import owlbear.config` succeed without importing `owlbear.tools` first.
4. The workaround import in `tests/test_daemon_journal_async.py` must be removed as part of the same change that restores clean imports.
5. This backlog item cannot advance to `todo` until there is a preceding TDD task for the import regression.
6. The implementation contract must be single-domain. The current follow-up draft #850 is not architect-ready because it couples `core/` and `tools/` changes in one task; decompose or explicitly justify any ancillary compatibility re-export before approval.

[[2026-03-19]] Thu 14:15

## Architecture Review

**Verdict:** Refine

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Needs architect to scope the fix approach | Not verifiable and mixes root-cause and symptom-level options in one sentence | Rewrote the task body as explicit architectural AC |
| Research recommendation: move `BlockedURLError`, keep compatibility, add import smoke coverage | Sound root-cause direction, but it was not converted into a builder contract and had no TDD predecessor | Kept the direction, but left the task in backlog until decomposition is complete |

### Architecture Notes

- `src/owlbear/core/errors.py` currently imports `src/owlbear/tools/browser/safety.py`, which violates the architecture rule that `core/` must not import from `tools/`.
- `src/owlbear/tools/__init__.py` triggers the circular import by eagerly re-exporting `GitHubToolset`, which imports `core.retry`; this makes lazy `tools.__init__` a symptom workaround, not the preferred fix.
- `src/owlbear/memory/knowledge/__init__.py` shows that lazy package exports are a supported pattern in this repo, but here they would preserve the forbidden dependency edge instead of removing it.
- `tests/test_blocked_error_location.py` establishes an existing repo pattern for relocating an exception into the core error surface while keeping imports explicit and testable.
- No preceding test task exists for this implementation flow, so TDD compliance is not met.
- The current follow-up draft #850 also is not architect-ready because it spans both the `core` and `tools` domains and is already claimed by another agent, so I did not modify it.

### Changes Made

- Claimed #849 as `wren-mint`
- Rewrote #849 body with verifiable AC
- Left #849 in `backlog`; did not advance to `todo`

### Dependencies

- Verified: `docs/research/core-tools-circular-import.md`
- Verified: `src/owlbear/core/errors.py`, `src/owlbear/tools/__init__.py`, `src/owlbear/tools/browser/safety.py`, `tests/test_daemon_journal_async.py`, `tests/test_imports.py`
- Missing: preceding TDD task for the import regression
- Overlap noted: #850 exists in `ideation` and is claimed elsewhere

[[2026-03-19]] Thu 16:10

## Architecture Review

**Verdict:** REFINE

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1 | Still correct: the fix must remove the forbidden core -> tools edge instead of hiding it behind lazy or local imports. | Keep |
| 2 | Still correct: the browser-safety import contract must remain explicit during the exception relocation. | Keep |
| 3 | Still correct: clean-process import smoke is the required regression proof. | Keep |
| 4 | Still correct: the daemon journal workaround import must be removed in the same fix stream. | Keep |
| 5 | Stale: the missing RED predecessor now exists as #860. | Mark satisfied downstream |
| 6 | Stale: the single-domain implementation contract now lives in approved task #850, with broader tools cleanup separated into #857. | Mark satisfied downstream |

### Architecture Notes

- Verified against src/owlbear/core/errors.py, src/owlbear/tools/browser/safety.py, and src/owlbear/tools/**init**.py that the architectural issue is still the forbidden core -> tools import edge.
- Verified #860 now provides the missing TDD predecessor and #850 is already architect-approved as the narrow implementation task.
- Verified #857 holds the broader owlbear.tools package side-effect cleanup separately.
- Because #860 and #850 now carry the executable contract, #849 is a stale umbrella task. It should remain in backlog and should not be dispatched directly to a builder.

### Changes Made

- Claimed #849 after the prior claim exceeded the board's 1h timeout.
- Appended a follow-up architecture review noting that the original backlog blockers are now resolved downstream.
- Left #849 in backlog for tracker continuity; no builder handoff was created from this task.

### Dependencies

- Added/Removed/Verified: verified #860 (RED predecessor), #850 (approved GREEN task), and #857 (separate tools cleanup)

[[2026-03-19]] Thu 16:50
[[2026-03-19]] Thu

## Architecture Review

**Verdict:** REFINE

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1 | Still the correct root-cause requirement, but the executable implementation contract already lives in #850. | Keep #849 as a tracker only; do not dispatch from this task |
| 2 | Still valid compatibility scope and already codified concretely in #850 as the browser-safety re-export requirement. | Satisfied downstream by #850 |
| 3 | Still valid regression proof and already codified in RED task #860 plus GREEN task #850. | Satisfied downstream by #860 and #850 |
| 4 | Still valid cleanup scope and already codified in #860 and #850. | Satisfied downstream by #860 and #850 |
| 5 | Satisfied: a preceding TDD task now exists as #860 and is currently in progress. | Keep #849 in backlog; no direct builder handoff |
| 6 | Satisfied: the single-domain core implementation task is #850, while broader tools package cleanup is separated into #857 and narrowed further by #859. | Keep the split; #849 remains an umbrella task |

### Architecture Notes

- Verified in src/owlbear/core/errors.py that core still imports BlockedURLError from src/owlbear/tools/browser/safety.py, so the root cause remains the forbidden core -> tools dependency edge until #850 lands.
- Verified in src/owlbear/tools/browser/safety.py that BlockedURLError is still defined in the tool layer, and src/owlbear/core/exceptions.py does not yet contain it.
- Verified in src/owlbear/tools/**init**.py that eager package re-exports still import GitHubToolset, so broader package side-effect cleanup remains correctly separated under #857 and #859 instead of being folded back into #849.
- Verified in tests/test_blocked_url_error_location.py and tests/test_daemon_journal_async.py that the RED coverage for dependency inversion and removal of the daemon import workaround is already written under #860.
- Verified docs/research/core-tools-circular-import.md still supports the dependency-inversion direction, while the historical blocker list in #849 is now stale because #536, #541, and #841 are archived.
- Because the executable contracts now live downstream, #849 should remain in backlog for tracker continuity and should not be dispatched directly to a builder.

### Changes Made

- Claimed #849 as architect-gpt54
- Appended this review clarifying that #849 is a stale umbrella task after the #860, #850, #857, and #859 decomposition
- Left #849 in backlog and did not move it to todo

### Dependencies

- Added/Removed/Verified: verified docs/research/core-tools-circular-import.md, #860 (RED predecessor, in progress), #850 (approved GREEN task in todo), #857 (tools-side umbrella), and #859 (narrow tools-side follow-up)

[[2026-03-19]] Thu 17:28

## Architecture Review

**Verdict:** REFINE

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1 | Still the correct root-cause requirement, but the executable implementation contract already lives in #850. | Keep #849 as a tracker only; do not dispatch a builder from this task |
| 2 | Still valid compatibility scope, and the explicit browser-safety contract is already narrowed concretely in #850. | Satisfied downstream by #850 |
| 3 | Still valid regression proof, and the clean-process import contract now has a dedicated RED task plus the dependent GREEN task. | Satisfied downstream by #860 and #850 |
| 4 | Still valid cleanup scope, and the daemon workaround removal is already part of the RED/GREEN split. | Satisfied downstream by #860 and #850 |
| 5 | Satisfied: a preceding TDD task exists as #860, and #850 already depends on it. | Keep #849 in backlog; no direct builder handoff |
| 6 | Satisfied: the single-domain implementation task is #850, while tools-package side-effect work remains separated in #857 and #859. | Keep the split; #849 remains a non-executable umbrella task |

### Architecture Notes

- Verified against `src/owlbear/core/errors.py` and `src/owlbear/core/exceptions.py` that the architectural defect is still the forbidden `core -> tools` dependency edge, but the concrete fix contract has already been narrowed into #850.
- Verified against `src/owlbear/tools/browser/safety.py` that the public `BlockedURLError` import surface is still tool-facing today, which is exactly the compatibility concern #850 captures.
- Verified against `src/owlbear/tools/__init__.py` that eager package re-exports are still a separate tools-side concern, so folding that work back into #849 would reintroduce cross-domain scope.
- Verified against `tests/test_blocked_url_error_location.py` and `tests/test_daemon_journal_async.py` that the regression coverage and workaround-removal contract already exist downstream, making #849 redundant as a builder handoff.
- Verified via `docs/research/core-tools-circular-import.md` and task state that the architecturally correct decomposition is now: #860 for RED coverage, #850 for the core-layer dependency inversion, and #857/#859 for optional tools-package follow-up.
- Because the executable contract already exists elsewhere, moving #849 to `todo` would duplicate #850, weaken atomicity, and create ambiguity for the builder. This task should remain in `backlog` as a tracker only.

### Changes Made

- Claimed #849 as `architect-849`
- Appended this architecture review clarifying that #849 is now a tracker rather than an implementation handoff
- Left #849 in `backlog`
- Released my claim after writing the review

### Dependencies

- Added/Removed/Verified: verified `docs/research/core-tools-circular-import.md`, #860 (RED predecessor), #850 (approved GREEN task), #857 (tools-side follow-up), and #859 (lazy-export ideation follow-up)

[[2026-03-19]] Thu 18:30

## Architecture Review

**Verdict:** REFINE

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1 | Satisfied in the workspace: src/owlbear/core/errors.py now imports BlockedURLError from owlbear.core.exceptions, so the forbidden core -> tools edge described by #849 is no longer present in current source. | Keep #849 as a tracker only; do not create a duplicate builder handoff |
| 2 | Satisfied in the workspace: src/owlbear/tools/browser/safety.py imports and re-exports BlockedURLError from owlbear.core.exceptions, so the browser-safety import contract remains explicit. | Keep compatibility scope downstream in #850 only |
| 3 | Satisfied by regression evidence: tests/test_blocked_url_error_location.py now covers fresh-process daemon/config imports, and a fresh Python process currently imports owlbear.daemon and owlbear.config successfully with no manual owlbear.tools pre-seeding. | No new implementation work should dispatch from #849 |
| 4 | Satisfied downstream: tests/test_daemon_journal_async.py no longer pre-seeds owlbear.tools before importing owlbear.daemon. | Keep #849 out of todo |
| 5 | Satisfied: the preceding TDD task exists as #860 and already carries RED, builder, and review evidence. | Keep #849 in backlog as a tracker only |
| 6 | Satisfied: the executable single-domain implementation contract lives in #850, while tools-side follow-up remains split into #857 and #859. | Do not dispatch a builder from #849 |

### Architecture Notes

- Verified in src/owlbear/core/errors.py and src/owlbear/core/exceptions.py that BlockedURLError now lives in the core layer, so the architecture violation described at the top of #849 has already been removed from the workspace.
- Verified in src/owlbear/tools/browser/safety.py that the tool-layer module imports the exception from core and preserves the explicit browser-safety import surface.
- Verified in tests/test_blocked_url_error_location.py that the regression contract now includes both the structural no-import assertion and fresh-subprocess daemon/config import smoke.
- Verified in tests/test_daemon_journal_async.py that the historical import owlbear.tools workaround has been removed.
- Verified via a fresh interpreter command that import owlbear.daemon and import owlbear.config currently succeed without manual tools pre-seeding.
- Verified task state: #860 is in docs, #850 remains todo, and #857/#859 continue to carry separate tools-side scope. Because the implementation already exists in the workspace, moving #849 to todo would now duplicate work and blur ownership rather than clarify it.

### Changes Made

- Claimed #849 as architect-gpt54-review
- Appended this review after re-checking current code, tests, and downstream task state
- Left #849 in backlog
- Released my claim after writing the review

### Dependencies

- Added/Removed/Verified: verified docs/research/core-tools-circular-import.md, #860 (TDD predecessor with RED/GREEN evidence), #850 (narrow core-domain implementation contract), #857 (tools-side tracker), and #859 (tools-side implementation candidate)

[[2026-03-20]] Fri 11:09

## Architecture Review

**Verdict:** REFINE

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1 | Satisfied in the current workspace: src/owlbear/core/errors.py imports BlockedURLError from owlbear.core.exceptions, so the forbidden core -> tools edge described by #849 is already removed. | Keep #849 as a tracker only; do not create a duplicate builder handoff |
| 2 | Satisfied in the current workspace: src/owlbear/tools/browser/safety.py imports BlockedURLError from owlbear.core.exceptions, which preserves the explicit browser-safety import contract. | Keep compatibility scope downstream in #850 only |
| 3 | Satisfied by current regression evidence: tests/test_blocked_url_error_location.py covers fresh-process daemon/config imports, and a fresh interpreter now imports owlbear.daemon and owlbear.config successfully without pre-seeding owlbear.tools. | No new implementation work should dispatch from #849 |
| 4 | Satisfied in the current workspace: tests/test_daemon_journal_async.py no longer pre-seeds owlbear.tools before importing owlbear.daemon. | Keep #849 out of todo |
| 5 | Satisfied: the preceding TDD task exists as #860 and already contains RED, builder, and review evidence. | Keep #849 in backlog as a tracker only |
| 6 | Satisfied: the executable single-domain contract lives in #850, while tools-side follow-up remains separated in #857 and #859. | Do not dispatch a builder from #849 |

### Architecture Notes

- Verified in src/owlbear/core/errors.py and src/owlbear/core/exceptions.py that the original architecture violation for #849 is no longer present in current source.
- Verified in src/owlbear/tools/browser/safety.py that the tool-layer import surface remains explicit even after the exception relocation.
- Verified in tests/test_blocked_url_error_location.py and tests/test_daemon_journal_async.py that the regression proof and workaround removal are already encoded in downstream tasks.
- Verified with a fresh Python process that import owlbear.daemon and import owlbear.config both succeed without manually importing owlbear.tools first.
- Verified task state: #860 is in docs, #850 remains the narrow core-domain implementation contract in todo, and #857/#859 continue to isolate tools-side work.
- Because the executable contract and evidence already exist elsewhere, moving #849 to todo would duplicate scope and weaken atomicity. This task should remain in backlog as a tracker only.

### Changes Made

- Claimed #849 as stone-pearl
- Appended this review after re-checking source, tests, import behavior, and downstream task state
- Left #849 in backlog
- Released my claim after writing the review

### Dependencies

- Added/Removed/Verified: verified docs/research/core-tools-circular-import.md, #860 (TDD predecessor with RED/GREEN evidence), #850 (narrow core-domain implementation contract), #857 (tools-side tracker), and #859 (tools-side implementation follow-up)

[[2026-03-20]] Fri 12:31
[[2026-03-20]] Fri

## Architecture Review

**Verdict:** REFINE

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1 | Satisfied in current source: src/owlbear/core/errors.py now imports BlockedURLError from owlbear.core.exceptions, so the forbidden core -> tools edge is gone. | Keep #849 as a tracker only; do not create a duplicate builder handoff |
| 2 | Satisfied in current source: src/owlbear/tools/browser/safety.py preserves the explicit browser-safety import path by re-exporting BlockedURLError from core. | Keep compatibility scope on #850 |
| 3 | Satisfied by current regression guard: tests/test_blocked_url_error_location.py plus a fresh-process import probe both show owlbear.daemon and owlbear.config import cleanly without owlbear.tools pre-seeding. | No new implementation work should dispatch from #849 |
| 4 | Satisfied in current tests: tests/test_daemon_journal_async.py no longer pre-seeds owlbear.tools. | Keep #849 out of todo |
| 5 | Satisfied: the RED predecessor exists as archived task #860. | Keep #849 in backlog as a tracker only |
| 6 | Satisfied: the executable single-domain implementation contract remains isolated in #850, while tools-side follow-up stays split into #857 and #859. | Do not dispatch a builder from #849 |

### Architecture Notes

- Verified against src/owlbear/core/errors.py, src/owlbear/core/exceptions.py, and src/owlbear/tools/browser/safety.py that the original architecture violation for #849 is already removed in the workspace.
- Verified against tests/test_blocked_url_error_location.py and tests/test_daemon_journal_async.py that the regression proof and workaround removal are already encoded and no longer belong on #849 as a direct builder handoff.
- Verified with the clean-process import probe that owlbear.config, owlbear.daemon, and owlbear.core.exceptions.BlockedURLError now load correctly in a fresh interpreter.
- Verified task state: #850 is the active single-domain implementation task in progress, #860 is archived as its RED predecessor, and #857/#859 continue to isolate the separate tools-side scope.
- Moving #849 to todo would now duplicate #850, weaken atomicity, and create ambiguous ownership for the builder/reviewer pipeline. This task should remain in backlog as a tracker only.

### Changes Made

- Claimed #849 as `architect-gpt54-0320`
- Appended this architecture review after re-checking source, regression tests, import behavior, and downstream task state
- Left #849 in `backlog`
- Released my claim after writing the review

### Dependencies

- Added/Removed/Verified: verified docs/research/core-tools-circular-import.md, #850 (active core-domain implementation task), #860 (archived RED predecessor), #857 (tools-side tracker), and #859 (tools-side ideation follow-up)

[[2026-03-20]] Fri 13:22

## Architecture Review

**Verdict:** REFINE

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1 | Satisfied in current source: src/owlbear/core/errors.py now imports BlockedURLError from owlbear.core.exceptions, so the forbidden core -> tools edge is removed. | Keep #849 as a tracker only; do not create a duplicate builder handoff |
| 2 | Satisfied in current source: src/owlbear/tools/browser/safety.py imports and re-exports BlockedURLError from owlbear.core.exceptions, so the explicit browser-safety import contract remains intact. | Keep compatibility scope downstream; do not widen #849 |
| 3 | Satisfied downstream: tests/test_blocked_url_error_location.py and archived task #860 already carry the clean-process import regression proof. | No new implementation work should dispatch from #849 |
| 4 | Satisfied in current tests: tests/test_daemon_journal_async.py no longer pre-seeds owlbear.tools before importing owlbear.daemon. | Keep #849 out of todo |
| 5 | Satisfied: archived task #860 is the completed RED predecessor for the import regression. | TDD ordering is already met downstream |
| 6 | Satisfied: #850 is the narrow core-domain implementation task and is now in review, while #857 and #859 keep tools-side scope separate. | Keep the decomposition; #849 remains a non-executable umbrella task |

### Architecture Notes

- Verified against src/owlbear/core/errors.py, src/owlbear/core/exceptions.py, and src/owlbear/tools/browser/safety.py that the original core -> tools violation described by #849 is already removed from current source.
- Verified against tests/test_blocked_url_error_location.py and tests/test_daemon_journal_async.py that the regression proof and workaround removal are already encoded downstream.
- Verified task state: #860 is archived as the RED predecessor, #850 has advanced to review as the executable core-domain task, and #857/#859 continue to isolate the separate tools-side concern.
- Moving #849 to todo would now duplicate #850, weaken atomicity, and create ambiguous ownership for the builder/reviewer pipeline. This task should remain in backlog as a tracker only.

### Changes Made

- Claimed #849 as architect-849-review-20260320
- Appended this architecture review after verifying source, tests, research, and downstream task state
- Left #849 in backlog
- Released my claim after writing the review

### Dependencies

- Added/Removed/Verified: verified docs/research/core-tools-circular-import.md, #850 (review), #860 (archived RED predecessor), #857 (tools-side tracker), and #859 (tools-side ideation follow-up)

[[2026-03-20]] Fri 14:19

## Architecture Review

**Verdict:** REFINE

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1 | Satisfied in current source: src/owlbear/core/errors.py now imports BlockedURLError from owlbear.core.exceptions, so the forbidden core -> tools edge is removed. | Keep #849 as a tracker only; do not create a duplicate builder handoff |
| 2 | Satisfied in current source: src/owlbear/tools/browser/safety.py imports and re-exports BlockedURLError from owlbear.core.exceptions, so the explicit browser-safety import contract remains intact. | Keep compatibility scope downstream; do not widen #849 |
| 3 | Satisfied downstream: tests/test_blocked_url_error_location.py plus archived RED task #860 already carry the clean-process import regression proof. | No new implementation work should dispatch from #849 |
| 4 | Satisfied in current tests: tests/test_daemon_journal_async.py no longer pre-seeds owlbear.tools before importing owlbear.daemon. | Keep #849 out of todo |
| 5 | Satisfied: the required TDD predecessor exists as archived task #860. | Keep #849 in backlog as a tracker only |
| 6 | Satisfied: the executable single-domain contract remains isolated in #850, while tools-side follow-up stays separate in #857 and #859. | Do not dispatch a builder from #849 |

### Architecture Notes

- Verified in src/owlbear/core/errors.py, src/owlbear/core/exceptions.py, and src/owlbear/tools/browser/safety.py that the original architecture violation described by #849 is already removed in the current workspace.
- Verified in tests/test_blocked_url_error_location.py and tests/test_daemon_journal_async.py that the regression proof and workaround removal are already encoded downstream.
- Verified downstream task state: #850 is in docs, #860 is archived, and the separate tools-side scope remains isolated in #857 and #859.
- Because the executable contract and evidence already live downstream, moving #849 to todo would duplicate scope and create ambiguous ownership for the builder/reviewer pipeline.
- #849 should remain in backlog as a tracker only until the broader task graph is closed elsewhere.

### Changes Made

- Claimed #849 as architect-gpt54-0320c
- Appended this architecture review after re-checking source, tests, research, and downstream task state
- Left #849 in backlog
- Released my claim after writing the review

### Dependencies

- Added/Removed/Verified: verified docs/research/core-tools-circular-import.md, #850 (docs), #860 (archived), #857 (backlog), and #859 (ideation)

[[2026-03-20]] Fri 15:13

## Architecture Review

**Verdict:** REFINE

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1 | Satisfied in current source: src/owlbear/core/errors.py imports BlockedURLError from owlbear.core.exceptions, so the forbidden core -> tools edge is removed. | Keep #849 as a tracker only; do not create a duplicate builder handoff |
| 2 | Satisfied in current source: src/owlbear/tools/browser/safety.py imports and re-exports BlockedURLError from owlbear.core.exceptions, preserving the browser-safety import surface. | Keep compatibility scope downstream; do not widen #849 |
| 3 | Satisfied by current regression proof: tests/test_blocked_url_error_location.py encodes clean-process daemon/config imports, and a fresh uv run python probe succeeds. | No new implementation work should dispatch from #849 |
| 4 | Satisfied in current tests: tests/test_daemon_journal_async.py no longer pre-seeds owlbear.tools before importing owlbear.daemon. | Keep #849 out of todo |
| 5 | Satisfied: #860 is archived as the completed RED predecessor. | TDD ordering is already met downstream |
| 6 | Satisfied: #850 is done as the narrow core-domain implementation, while #857 and #859 still isolate tools-side follow-up. | Keep the decomposition; #849 remains a non-executable umbrella task |

### Architecture Notes

- Verified against src/owlbear/core/errors.py, src/owlbear/core/exceptions.py, and src/owlbear/tools/browser/safety.py that the original core -> tools violation described by #849 is already removed from current source.
- Verified against tests/test_blocked_url_error_location.py and tests/test_daemon_journal_async.py that the regression proof and daemon-workaround removal are already encoded downstream.
- Verified with a fresh-process uv run python import probe that owlbear.config, owlbear.daemon, and owlbear.core.exceptions.BlockedURLError currently load without manual owlbear.tools pre-seeding.
- Verified task state: #850 is done, #860 is archived, and #857/#859 continue to isolate separate tools-side scope.
- Moving #849 to todo would duplicate already-completed scope, weaken atomicity, and create ambiguous ownership. Keep this task in backlog as a tracker only.

### Changes Made

- Claimed #849 as architect-review-849-20260320
- Appended this architecture review after re-checking source, regression tests, import behavior, and downstream task state
- Left #849 in backlog
- Released my claim after writing the review

### Dependencies

- Added/Removed/Verified: verified docs/research/core-tools-circular-import.md, #850 (done), #860 (archived RED predecessor), #857 (backlog tools-side tracker), and #859 (ideation tools-side follow-up)

[[2026-03-20]] Fri 15:52

## Architecture Review

**Verdict:** REFINE

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1 | Satisfied in current source: src/owlbear/core/errors.py imports BlockedURLError from owlbear.core.exceptions, so the forbidden core -> tools edge described by #849 is already removed. | Keep #849 as a tracker only; do not create a duplicate builder handoff |
| 2 | Satisfied in current source: src/owlbear/tools/browser/safety.py imports and re-exports BlockedURLError from owlbear.core.exceptions, preserving the explicit browser-safety import surface. | Keep compatibility scope downstream; do not widen #849 |
| 3 | Satisfied by current regression proof: tests/test_blocked_url_error_location.py plus a fresh uv-run interpreter probe show owlbear.config and owlbear.daemon import cleanly without owlbear.tools pre-seeding. | No new implementation work should dispatch from #849 |
| 4 | Satisfied in current tests: tests/test_daemon_journal_async.py no longer relies on an owlbear.tools pre-seeding workaround before importing owlbear.daemon. | Keep #849 out of todo |
| 5 | Satisfied: archived task #860 already exists as the RED predecessor for this regression. | TDD ordering is already met downstream |
| 6 | Satisfied: #850 is done as the narrow core-domain implementation task, while #857 and #859 continue to isolate tools-side follow-up. | Keep the decomposition; #849 remains a non-executable umbrella task |

### Architecture Notes

- Verified against src/owlbear/core/errors.py, src/owlbear/core/exceptions.py, and src/owlbear/tools/browser/safety.py that the original core -> tools violation described by #849 is already removed from current source.
- Verified against tests/test_blocked_url_error_location.py that the clean-process import regression remains covered at the task-contract level.
- Verified with a fresh uv run python probe that owlbear.config, owlbear.daemon, and owlbear.core.exceptions.BlockedURLError load cleanly without manually importing owlbear.tools first.
- Verified board state: #850 is done, #860 is archived as the RED predecessor, #857 remains the separate backlog task for tools **init** side effects, and #859 remains the ideation follow-up for lazy exports.
- Moving #849 to todo would now duplicate already-completed scope, weaken atomicity, and create ambiguous ownership. It should remain in backlog as a tracker only.

### Changes Made

- Claimed #849 as architect-gpt54-20260320e
- Appended this architecture review after re-checking current source, regression coverage, import behavior, and downstream task state
- Left #849 in backlog

### Dependencies

- Added/Removed/Verified: verified docs/research/core-tools-circular-import.md, #850 (done), #860 (archived RED predecessor), #857 (backlog tools-side tracker), and #859 (ideation tools-side follow-up)

[[2026-03-20]] Fri 16:37

## Architecture Review

**Verdict:** REFINE

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1 | Satisfied in current source: src/owlbear/core/errors.py imports BlockedURLError from owlbear.core.exceptions, so the forbidden core -> tools edge described by #849 is already removed. | Keep #849 as a tracker only; do not create a duplicate builder handoff |
| 2 | Satisfied in current source: src/owlbear/tools/browser/safety.py imports and re-exports BlockedURLError from owlbear.core.exceptions, preserving the explicit browser-safety import surface. | Keep compatibility scope downstream; do not widen #849 |
| 3 | Satisfied by current regression proof: tests/test_blocked_url_error_location.py plus a fresh uv-run interpreter probe show owlbear.config and owlbear.daemon import cleanly without owlbear.tools pre-seeding. | No new implementation work should dispatch from #849 |
| 4 | Satisfied in current tests: tests/test_daemon_journal_async.py no longer relies on an owlbear.tools pre-seeding workaround before importing owlbear.daemon. | Keep #849 out of todo |
| 5 | Satisfied: archived task #860 already exists as the RED predecessor for this regression. | TDD ordering is already met downstream |
| 6 | Satisfied: the executable single-domain contract formerly associated with this fix has already landed downstream, while tools-side follow-up remains isolated in #857 and #859. | Keep the decomposition; #849 remains a non-executable umbrella task |

### Architecture Notes

- Verified against src/owlbear/core/errors.py, src/owlbear/core/exceptions.py, and src/owlbear/tools/browser/safety.py that the original core -> tools violation described by #849 is already removed from current source.
- Verified against tests/test_blocked_url_error_location.py and tests/test_daemon_journal_async.py that the regression proof and daemon-workaround removal are already encoded downstream.
- Verified with a fresh uv run python probe that owlbear.config, owlbear.daemon, and owlbear.core.exceptions.BlockedURLError load cleanly without manually importing owlbear.tools first.
- Verified board state: #850 is archived as the completed core-domain implementation line, #860 is archived as the RED predecessor, #857 remains in ideation for broader tools-package side effects, and #859 remains in backlog as the narrowed tools-side follow-up.
- Moving #849 to todo would now duplicate completed scope, weaken atomicity, and create ambiguous ownership for the builder and reviewer pipeline. It should remain in backlog as a tracker only.

### Changes Made

- Claimed #849 as architect-gpt54-20260320f
- Appended this architecture review after re-checking current source, regression coverage, import behavior, and downstream task state
- Left #849 in backlog

### Dependencies

- Added/Removed/Verified: verified docs/research/core-tools-circular-import.md, #850 (archived core-domain implementation lineage), #860 (archived RED predecessor), #857 (ideation tools-side tracker), and #859 (backlog tools-side follow-up)

[[2026-03-20]] Fri 18:01

## Architecture Review

**Verdict:** REFINE

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1 | Satisfied in current source: src/owlbear/core/errors.py imports BlockedURLError from owlbear.core.exceptions, so the forbidden core -> tools edge described by #849 is already removed. | Keep #849 as a tracker only; do not create a duplicate builder handoff. |
| 2 | Satisfied in current source: src/owlbear/tools/browser/safety.py imports and re-exports BlockedURLError from owlbear.core.exceptions, so the explicit browser-safety import contract remains intact. | Keep compatibility work closed under archived task #850. |
| 3 | Satisfied by current evidence: archived RED task #860 covers the clean-process regression, and a fresh .venv\\Scripts\\python.exe probe now imports owlbear.config and owlbear.daemon successfully without owlbear.tools pre-seeding. | No new implementation work should dispatch from #849. |
| 4 | Satisfied in current tests: tests/test_daemon_journal_async.py no longer pre-seeds owlbear.tools before importing owlbear.daemon. | Keep #849 out of todo. |
| 5 | Satisfied: the required TDD predecessor exists as archived task #860. | TDD ordering is already met downstream. |
| 6 | Satisfied and narrowed further: #850 is archived, #857 has been sent back to ideation as stale research, and #859 is now the tools-side tracker with child tasks #878 (RED) and #879 (GREEN). | Preserve the split; #849 remains a non-executable umbrella task. |

### Architecture Notes

- Verified in src/owlbear/core/errors.py, src/owlbear/core/exceptions.py, and src/owlbear/tools/browser/safety.py that the original architecture violation described by #849 is already removed in the current workspace.
- Verified in tests/test_blocked_url_error_location.py and tests/test_daemon_journal_async.py that the regression proof and workaround removal already live downstream in the completed #860/#850 path.
- Verified with a fresh subprocess probe that import owlbear.config and import owlbear.daemon now succeed without manually importing owlbear.tools first.
- Verified #857 is now blocked in ideation because its original config side-effect AC no longer reproduces; the remaining package-root lazy-export work is isolated under #859 and its child tasks #878 and #879.
- Moving #849 to todo would now duplicate completed core-layer work, weaken atomicity, and create ambiguous ownership for the builder/reviewer pipeline.

### Changes Made

- Claimed #849 as architect-gpt54-20260320-final2.
- Appended this architecture review after re-checking current source, test coverage, fresh-process import behavior, and downstream task state.
- Left #849 in backlog as a tracker-only task.

### Dependencies

- Added/Removed/Verified: verified #850 (archived), #860 (archived), #857 (ideation, blocked), #859 (backlog tracker), #878 (RED child exists), and #879 (GREEN child exists).

[[2026-03-21]] Sat 02:36
[[2026-03-21 Sa 02:36]]

## Architecture Review

**Verdict:** BLOCK

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1 | Satisfied in current source: src/owlbear/core/errors.py imports BlockedURLError from owlbear.core.exceptions, so the forbidden core -> tools edge described by #849 is already removed. | Do not dispatch implementation from #849; archived task #850 is the source of truth for the fix. |
| 2 | Satisfied in current source: src/owlbear/tools/browser/safety.py imports and re-exports BlockedURLError from owlbear.core.exceptions, preserving the explicit browser-safety import contract. | Keep compatibility work closed under archived task #850 rather than reopening #849. |
| 3 | Satisfied by current evidence: archived RED task #860 covers the clean-process regression, and a fresh .venv\\Scripts\\python.exe probe now imports owlbear.daemon and owlbear.config successfully without owlbear.tools pre-seeding. | No new implementation work should dispatch from #849. |
| 4 | Satisfied in current tests: tests/test_daemon_journal_async.py no longer pre-seeds owlbear.tools before importing owlbear.daemon. | Keep this requirement closed under the archived #860/#850 path. |
| 5 | Satisfied: the required TDD predecessor exists as archived task #860. | TDD ordering is already met downstream; #849 no longer belongs in backlog flow. |
| 6 | Satisfied and superseded: #850 and #860 are archived, #857 is blocked in ideation as stale research, and #859 with child tasks #878 and #879 now isolates the separate tools-side follow-up. | Remove #849 from the active backlog and require refreshed research before any future reopening. |

### Architecture Notes

- Verified in src/owlbear/core/errors.py, src/owlbear/core/exceptions.py, and src/owlbear/tools/browser/safety.py that the original core -> tools architecture violation described by #849 is already removed in the current workspace.
- Verified in tests/test_blocked_url_error_location.py and tests/test_daemon_journal_async.py that the regression proof and workaround removal already live in the completed #860/#850 path.
- Verified with a fresh subprocess probe that import owlbear.daemon and import owlbear.config now succeed without manually importing owlbear.tools first, and BlockedURLError resolves from owlbear.core.exceptions.
- Verified board state: #850 and #860 are archived as the completed core-domain implementation line, while the remaining tools-package work is isolated under #859 and its child tasks #878 and #879.
- Leaving #849 in backlog has already caused repeated architect redispatch on a task whose executable contract is complete. The correct next state is blocked ideation: historical tracker only, refresh research or create a new task if a new regression appears.

### Changes Made

- Appended this architecture review after re-checking current source, regression coverage, fresh-process import behavior, and downstream task state.
- Moved #849 from backlog to ideation and applied an explicit block so it leaves the active implementation queue.
- Released the claim as part of the status change.

### Dependencies

- Added/Removed/Verified: verified #850 (archived), #860 (archived), #857 (ideation, blocked), #859 (backlog tracker), #878 (RED child in review), and #879 (GREEN child in todo).
