---
id: 962
title: Remove dead question_pending default hook configuration
status: archived
priority: important
created: 2026-03-23T04:16:01.0955089+01:00
updated: 2026-03-23T21:39:13.2462279+01:00
started: 2026-03-23T21:39:12.6920518+01:00
completed: 2026-03-23T21:39:12.6920518+01:00
tags:
    - agent
    - hooks
    - config
    - scope:core
    - type:build
parent: 955
depends_on:
    - 968
class: standard
---

See docs/research/question-pending-default-hook-surface.md. This task implements only the dead default-surface cleanup for question_pending; it does not add a new emitter or remove the enum.

## AC

- [ ] File: src/owlbear/config.py
- [ ] File: docs/architecture.md
- [ ] OwlBearSettings.notification_events default is exactly [task_complete, on_error]
- [ ] Explicit user configuration may still include question_pending; this task does not remove HookEvent.QUESTION_PENDING or reject explicit notification_events entries that match existing enum values
- [ ] Default build_hooks() wiring no longer installs a QUESTION_PENDING NotificationHook handler when OwlBearSettings() uses the default notification_events list
- [ ] docs/architecture.md no longer describes QUESTION_PENDING as a default or live NotificationHook runtime event; if the enum remains documented, it is marked as reserved/not currently emitted
- [ ] Historical research docs in docs/research/ and generic HookEvent/NotificationHook QUESTION_PENDING coverage remain unchanged in this task
- [ ] All tests from #968 pass
- [ ] ruff clean

## Scope Boundaries

- Do not add emit(HookEvent.QUESTION_PENDING, ...) anywhere in src/; that belongs to #967.
- Do not delete HookEvent.QUESTION_PENDING from src/owlbear/core/hooks.py.
- Do not broaden this cleanup into HookReaction executor wiring or notification dedup work; those belong to #957 and #963.
- Keep the regression proof focused on default notification_events staying a subset of HookEvent values currently emitted from src/owlbear.

## Research

- Doc: docs/research/question-pending-default-hook-surface.md
- Recommendation (.93): remove question_pending from default notification surfaces now, keep the enum, and restore a live default only after #967 adds real emit sites.
- Verified current seams: src/owlbear/config.py defaults notification_events to task_complete/question_pending/on_error; src/owlbear/core/hooks.py still defines HookEvent.QUESTION_PENDING; src/ has no emit(HookEvent.QUESTION_PENDING, ...) sites.
- Existing live surfaces to align: default OwlBearSettings() behavior, build_hooks() default registration, and docs/architecture.md's runtime event table.
- Follow-up: #967 emits QUESTION_PENDING from AskUserToolset and ApprovalGateToolset after this cleanup lands.

[[2026-03-23]] Mon 05:58

## Architecture Review

**Verdict:** Refine

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| remove question_pending from default notification | Sound goal, but the original one-line AC did not bind the change to the actual default seam in src/owlbear/config.py or to default build_hooks() registration behavior | Rewrote into explicit default-setting and default-registration requirements |
| remove question_pending from HookReaction example surfaces | Too vague because the current codebase has no live HookReaction runtime surface yet; docs/research/* are historical artifacts, while docs/architecture.md is the current runtime doc that misstates the event | Narrowed the doc surface to docs/architecture.md and excluded research-history docs |
| tests proving the default event set references only live emissions | Correct invariant, but it lacked a RED predecessor and did not say how to prove live emission mechanically | Created #968 as the required RED task and bound the regression to HookEvent values emitted from src/owlbear emit sites |

### Architecture Notes

- src/owlbear/config.py is the only runtime default source for notification_events; src/owlbear/bootstrap/hooks.py already consumes that list via NotificationHook, so the cleanup should stay at the config/default-surface layer instead of deleting HookEvent.QUESTION_PENDING.
- src/owlbear/core/hooks.py should remain unchanged in this task: keeping the enum preserves explicit configuration and the follow-up emitter work in #967.
- The only current non-historical live doc surface found in the workspace is docs/architecture.md. docs/research/* documents are historical analysis artifacts and should not be rewritten by this build card.
- This remains one core-domain cleanup: config default, bootstrap default registration, and matching runtime docs are ancillary seams of the same hook-default contract.
- No new security boundary is introduced; the main regression risk is silently reintroducing a dead default, so the emitted-event-subset test is the right guardrail.

### Changes Made

- Created #968 Test question_pending default hook cleanup.
- Rewrote #962 into explicit AC and scope-boundary sections.
- Added dependency: #962 depends on #968.

### Dependencies

- Added: #968 as the RED predecessor for #962.
- Verified: #967 remains the follow-up task that adds real QUESTION_PENDING emitters after this cleanup.
- Verified: HookEvent.QUESTION_PENDING remains defined in src/owlbear/core/hooks.py and still has generic registry/notification test coverage outside this task.

[[2026-03-23]] Mon 16:00

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| File: src/owlbear/config.py | Correct runtime seam for the default notification contract. Current HEAD already matches the target default list. | Keep |
| File: docs/architecture.md | Correct live documentation seam; this is the only current architecture surface still describing QUESTION_PENDING as a live runtime notification event. | Keep |
| OwlBearSettings.notification_events default is exactly [task_complete, on_error] | Precise and mechanically verifiable from the settings default plus #968 regression coverage. | Keep |
| Explicit user configuration may still include question_pending; this task does not remove HookEvent.QUESTION_PENDING or reject explicit notification_events entries that match existing enum values | Correct boundary between default cleanup and enum/API removal. Existing explicit-registration coverage already proves the enum remains usable when configured. | Keep |
| Default build_hooks() wiring no longer installs a QUESTION_PENDING NotificationHook handler when OwlBearSettings() uses the default notification_events list | Precise and tied to the real registration seam in src/owlbear/bootstrap/hooks.py. | Keep |
| docs/architecture.md no longer describes QUESTION_PENDING as a default or live NotificationHook runtime event; if the enum remains documented, it is marked as reserved/not currently emitted | Precise documentation contract and consistent with current runtime reality: the enum exists, but src/ has no QUESTION_PENDING emit site today. | Keep |
| Historical research docs in docs/research/ and generic HookEvent/NotificationHook QUESTION_PENDING coverage remain unchanged in this task | Good anti-scope-creep guardrail; it preserves research history and generic explicit-event coverage. | Keep |
| All tests from #968 pass | Correct TDD dependency gate. #968 is archived and already supplies the RED contract for this cleanup. | Keep |
| ruff clean | Standard quality gate for a narrow config and docs alignment change. | Keep |

### Architecture Notes

- src/owlbear/config.py is the single runtime default seam for notification_events, and src/owlbear/bootstrap/hooks.py passes settings.notification_events directly into NotificationHook(...).register(hooks). The AC correctly binds the cleanup to those two seams.
- src/owlbear/core/hooks.py still defines HookEvent.QUESTION_PENDING, and generic explicit-registration coverage already exists in tests/test_hooks.py and tests/test_notification_hook.py. Keeping enum preservation in scope and emitter work out of scope is the right separation from #967.
- docs/architecture.md is the only live architecture surface still presenting QUESTION_PENDING as a runtime NotificationHook event. Leaving docs/research/* untouched keeps the task surgical and preserves historical analysis.
- #968 is archived and satisfies the required RED predecessor. That preserves TDD sequencing for #962.
- Current HEAD already matches the default config seam recorded in this task. Downstream work must preserve that contract and only complete the remaining alignment surfaces; do not reopen enum removal, HookReaction expansion, or new emitters here.
- This remains one core-domain cleanup. The documentation update is ancillary to the same hook-default contract, not a separate docs-domain feature.

### Changes Made

- Claimed #962 as architect.
- Verified docs/research/question-pending-default-hook-surface.md against current config, hook, bootstrap, and documentation seams.
- Verified archived dependency #968 and current repo state before approving.
- Appended this Architecture Review section.

### Dependencies

- Added/Removed/Verified: verified #968 archived as the RED predecessor; verified #967 remains the later emitter task; verified no dependency cycle introduced.

[[2026-03-23]] Mon 16:48

## Test-Writer Notes

- Test file: tests/test_config.py
- Classes: TestFromAC_ArchitectureDocQuestionPendingCleanup
- Tests per category: happy 0, edge 0, error 0, boundary 1
- Total: 1 test, all FAIL
- ruff: new additions clean (8 pre-existing RUF100 unrelated, per #968 notes)
- AC coverage:

  | AC Line | Test(s) | Category |
  |---------|---------|----------|
  | docs/architecture.md no longer describes QUESTION_PENDING as a live/default NotificationHook runtime event | test_architecture_doc_does_not_list_question_pending_as_live_notification_event | boundary |
  | OwlBearSettings default + explicit config + build_hooks registration | Covered by archived #968 tests (all green, part of suite) | happy/edge |

[[2026-03-23]] Mon 17:11

## Builder Notes

- Files changed: docs/architecture.md (1 line)
- Tests: 5 passed (TestFromAC_QuestionPendingDefaultCleanup x4 + TestFromAC_ArchitectureDocQuestionPendingCleanup x1)
- Lint: ruff clean on task-scoped files
- Evidence: 5 passed in 0.50s; commit 0164a7d
- Fixes applied: docs/architecture.md line 266 changed NotificationHook to '_(reserved not currently emitted)_'; config.py default was already [task_complete, on_error]

[[2026-03-23]] Mon 17:49

## Review Evidence\n- reviewer sanity append test

[[2026-03-23]] Mon 17:50

## Review Evidence

### Test Results

- `uv run pytest tests/test_config.py::TestFromAC_QuestionPendingDefaultCleanup tests/test_bootstrap.py::TestFromAC_QuestionPendingDefaultHook tests/test_config.py::TestFromAC_ArchitectureDocQuestionPendingCleanup -q --tb=short` -> 7 passed, 0 failed.
- `uv run pytest tests/test_hooks.py::TestHookEvent::test_has_question_pending tests/test_hooks.py::TestNewHookEventsEmitRegister::test_question_pending_emit tests/test_notification_hook.py::TestNotificationHookRegister::test_registers_on_all_configured_events -q --tb=short` -> 3 passed, 0 failed.

### Lint Results

- `uv run ruff check src/ tests/` -> 216 pre-existing `RUF100` findings in unrelated files.
- `uv run ruff check src/owlbear/config.py src/owlbear/bootstrap/hooks.py src/owlbear/core/hooks.py tests/test_config.py` -> All checks passed.

[[2026-03-23]] Mon 17:50

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

- Default list AC covered by `TestFromAC_QuestionPendingDefaultCleanup::test_default_notification_events_excludes_question_pending` (exact equality assertion).
- Explicit opt-in AC covered by `test_env_var_question_pending_explicit_opt_in_while_default_excludes_it`, `test_direct_constructor_question_pending_explicit_opt_in_while_default_excludes_it`, and `TestFromAC_QuestionPendingDefaultHook::test_explicit_question_pending_config_registers_handler_while_default_excludes_it`.
- build_hooks default-registration AC covered by `TestFromAC_QuestionPendingDefaultHook::test_default_build_hooks_registers_task_complete_and_on_error_not_question_pending`.
- docs semantics AC covered by `TestFromAC_ArchitectureDocQuestionPendingCleanup::test_architecture_doc_does_not_list_question_pending_as_live_notification_event`.
- #968 gate AC satisfied: all #968 tests in the combined run passed (6/6).

#### Security Review

- No security issues found. Builder commit scope is docs-only (`git show --stat --oneline 0164a7d` => only docs/architecture.md).

#### Test Integrity

- `git show --name-only --pretty=format:%H%n%s 0164a7d` confirms builder did not modify TestFromAC classes; TestFromAC methods are PRESERVED.

#### Test Quality

- Assertion specificity: STRONG.
- Negative/error-path coverage: ADEQUATE.
- Mutation resistance: STRONG.
- Test independence: STRONG.
- Naming quality: STRONG.

#### Data Safety

- No data safety issues found.

#### Implementation-Aware Gaps

- No significant untested paths for this task's implementation delta (documentation alignment only).

[[2026-03-23]] Mon 17:51

### AC Compliance

| AC Line | Evidence | Status |
|---|---|---|
| File: src/owlbear/config.py | `src/owlbear/config.py` default is `notification_events=[task_complete, on_error]` | PASS |
| File: docs/architecture.md | `docs/architecture.md` row marks QUESTION_PENDING as `_(reserved - not currently emitted)_` | PASS |
| Default list exactly [task_complete, on_error] | Verified in source + TestFromAC default-list test passed | PASS |
| Explicit config may include question_pending | Env-var/direct-constructor/build_hooks explicit tests passed; `HookEvent.QUESTION_PENDING` still exists in `src/owlbear/core/hooks.py` | PASS |
| Default build_hooks wiring excludes QUESTION_PENDING handler | Verified by TestFromAC build_hooks default-registration test | PASS |
| docs no longer present QUESTION_PENDING as live/default runtime notification | Verified by docs TestFromAC + commit diff in 0164a7d | PASS |
| Historical docs and generic QUESTION_PENDING coverage unchanged | Commit scope for 0164a7d is docs/architecture.md only; generic enum/notification tests passed | PASS |
| All tests from #968 pass | Combined run includes and passes both #968 TestFromAC classes | PASS |
| ruff clean | Task-scoped ruff check passed | PASS |

### Verdict: PASS

- Confidence: .95

[[2026-03-23]] Mon 18:15

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Builder commit (0164a7d) only updates docs/architecture.md. No behavior, API, or convention change visible to copilot-instructions.md tech stack tables. |
| 2 | Docstrings | No | N/A | Builder commit only touched docs/architecture.md; no Python module was modified. notification_events field in config.py already has description in Field(). |
| 3 | docs/sources/overview.md | No | N/A | No external patterns or attribution used in this task. |
| 4 | README.md | No | N/A | No CLI commands changed. |
| 5 | Research doc linked | Yes | Pass | docs/research/question-pending-default-hook-surface.md exists and is referenced in task body. Follow-up #967 created. |
| 6 | Scratch files | Yes | Done | Deleted docs/scratch/962-body.tmp, docs/scratch/962-research.tmp, docs/scratch/962-test-task.tmp. |

### Files Updated

- None

### Scratch Files Cleaned

- docs/scratch/962-body.tmp
- docs/scratch/962-research.tmp
- docs/scratch/962-test-task.tmp

[[2026-03-23]] Mon 21:39

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| File: src/owlbear/config.py | Exists, notification_events default at L311 | PASS |
| File: docs/architecture.md | Exists, QUESTION_PENDING row at L266 | PASS |
| Default is exactly [task_complete, on_error] | Verified in source: `default=[task_complete, on_error]` | PASS |
| Explicit config may still include question_pending; enum preserved | HookEvent.QUESTION_PENDING at hooks.py L146 | PASS |
| Default build_hooks() excludes QUESTION_PENDING handler | test_default_build_hooks passed | PASS |
| docs no longer presents QUESTION_PENDING as live/default | Marked `_(reserved - not currently emitted)_` | PASS |
| Historical research docs and generic coverage unchanged | Builder commit 0164a7d touches only docs/architecture.md | PASS |
| All tests from #968 pass | 7/7 passed in 1.70s | PASS |
| ruff clean | All checks passed on task-scoped files | PASS |

### Test Results

- pytest (task-scoped): 7 passed, 0 failed
- pytest (full suite): 3963 passed, 91 failed (all pre-existing: numpy version, CLI refactors, agent_registry signature)
- ruff: clean on task-scoped files

### Architect Quality

- AC specificity: Excellent - all lines mechanically verifiable
- Edge case coverage: Scope boundaries explicitly defined, no improvisation needed
- Design direction: Architect correctly identified config + docs as the two seams
- AC quality score: 5/5

### Review Evidence Check

- Reviewer produced detailed AC compliance table with PASS verdict at .95 confidence
- Pass 1 CRITICAL section includes test-writer coverage, security review, test integrity, and test quality assessments

### Confidence: .97

### Action: archive
