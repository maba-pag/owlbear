---
id: 967
title: Emit QUESTION_PENDING from AskUserToolset and ApprovalGateToolset
status: archived
priority: important
created: 2026-03-23T05:13:56.003239+01:00
updated: 2026-03-25T12:39:50.9015233+01:00
started: 2026-03-25T12:39:23.4125212+01:00
completed: 2026-03-25T12:39:23.4125212+01:00
tags:
    - agent
    - hooks
    - ask_user
    - approval
    - scope:core
    - type:build
parent: 955
depends_on:
    - 962
    - 970
class: standard
---

## AC

### File targets

- src/owlbear/core/hooks.py
- src/owlbear/tools/ask_user.py
- src/owlbear/safety/gate.py
- src/owlbear/bootstrap/toolsets.py

### Acceptance criteria

- [ ] QuestionPendingData(TypedDict) added to hooks.py with keys: source (str, value 'ask_user' or 'approval_gate'), question (str), tool_name (NotRequired[str])
- [ ] Typed emit overload for Literal[HookEvent.QUESTION_PENDING] accepting QuestionPendingData added to HookRegistry
- [ ] QuestionPendingData exported in hooks.py __all__
- [ ] AskUserToolset.__init__ accepts hooks: HookRegistry | None = None; stored as self._hooks
- [ ] AskUserToolset.ask_user() emits QUESTION_PENDING once before any channel.receive(), with source='ask_user' and question= the formatted prompt text
- [ ] ApprovalGateToolset.call_tool() emits QUESTION_PENDING once before the approval channel.receive(), with source='approval_gate', question= the approval prompt fallback text, and tool_name= the gated tool name; skipped when approval is not required or tool is pre-granted
- [ ] build_toolsets() in bootstrap/toolsets.py passes hooks to AskUserToolset(channel, hooks=hooks)
- [ ] OwlBearSettings.notification_events default remains ['task_complete', 'on_error'] -- question_pending is NOT added to defaults

### Implementation guidance

- Follow emit_pre_tool_use pattern: guard with 'if hooks is not None' in AskUserToolset
- ApprovalGateToolset already has hooks field; emit directly via self.hooks.emit()
- QuestionPendingData follows existing TypedDict conventions (PreToolUseData, PostToolUseData)
- See docs/research/question-pending-emit-implementation.md for full analysis

### Research pointers

- docs/research/question-pending-default-hook-surface.md (parent)
- docs/research/question-pending-emit-implementation.md (this task)

[[2026-03-23]] Mon 23:03

## Architecture Review

__Verdict:__ APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| QuestionPendingData TypedDict | Research specifies fields; matches existing TypedDict conventions | Refined: keys spelled out in AC |
| Typed emit overload | Follows existing overload pattern for other HookEvents | Kept |
| __all__ export | Standard pattern | Kept |
| AskUserToolset hooks param | Follows TerminalToolset/GitLocalToolset pattern; optional with None guard | Kept |
| ask_user() emit once before receive | Option B from research; matches PRE_ pattern, KISS | Kept |
| call_tool() emit before approval receive | Already has hooks field; single emit before channel.receive() | Refined: clarified skip conditions |
| build_toolsets() wiring | Single LOC change at L305 | Kept |
| notification_events default unchanged | Verified: default is task_complete,on_error after #962 | Kept |

### Architecture Notes

- Module layering valid: tools/ imports from core/; bootstrap is assembly root
- ApprovalGateToolset already has hooks: HookRegistry; no constructor change needed
- AskUserToolset needs hooks: HookRegistry or None = None following TerminalToolset pattern
- ObservabilityHook.register() auto-subscribes to ALL HookEvent values; no wiring needed
- NotificationHook subscribes only to configured events; users opt-in for question_pending
- Hook emit is fire-and-forget; exceptions swallowed by HookRegistry; low risk
- Single domain: core (hooks infrastructure); ancillary touches to tools/ and bootstrap/ are wiring-only

### Changes Made

- Refined AC from single compound sentence into 8 individually verifiable lines
- Added file targets and implementation guidance sections
- Created test task #970 (TDD RED) at todo status
- Added depends_on: 970 to task #967

### Dependencies

- Verified: #962 (remove dead question_pending default) -- archived
- Added: #970 (test task, TDD RED) -- todo

[[2026-03-25]] Wed 09:15

## Builder Notes

- Files changed: src/owlbear/bootstrap/toolsets.py
- Tests: red phase confirmed 1 failing assertion in TestFromAC_967_BuildToolsetsHooksWiring before fix; green phase now 22 passed in tests/test_967_question_pending_emit.py
- Coverage: scoped coverage run reports src/owlbear/bootstrap/toolsets.py at 55 percent, with src/owlbear/core/hooks.py at 88 percent, src/owlbear/tools/ask_user.py at 81 percent, and src/owlbear/safety/gate.py at 80 percent
- Lint: scoped ruff check passed for src/owlbear/bootstrap/toolsets.py and tests/test_967_question_pending_emit.py; repository-wide ruff currently has pre-existing RUF100 issues
- Evidence: failing assertion was AskUserToolset _hooks None in build_toolsets output; after fix the test module passed fully
- Fixes applied: build_toolsets now constructs AskUserToolset(channel, hooks=hooks)

[[2026-03-25]] Wed 11:23

## Review Evidence

### Test Results

- Task suite: tests/test_967_question_pending_emit.py passed 22 tests in 4.39 seconds.
- Dependency suite: tests/test_question_pending_emit.py passed 30 tests in 1.80 seconds.
- Bootstrap regression slice: tests/test_bootstrap.py classes TestBuildToolsets and TestApprovalWrapping passed 20 tests; 160 tests were deselected.
- Coverage run over the two question-pending suites passed 52 tests in 14.26 seconds. Relevant module coverage: src/owlbear/core/hooks.py 88 percent, src/owlbear/tools/ask_user.py 81 percent, src/owlbear/safety/gate.py 80 percent, src/owlbear/bootstrap/toolsets.py 55 percent, src/owlbear/config.py 70 percent. The bootstrap percentage is expected scoped-run noise on a large file; the changed line is exercised directly by TestFromAC_967_BuildToolsetsHooksWiring.test_ask_user_toolset_receives_hooks_from_build_toolsets.

### Lint Results

- uv run ruff check src/owlbear/bootstrap/toolsets.py tests/test_967_question_pending_emit.py passed with no findings.

### Critical Checks

- Test-writer coverage is sufficient when combined with dependency task #970 coverage. The task-specific file covers hook wiring and the main emit flow, while tests/test_question_pending_emit.py adds the exact type-annotation checks for QuestionPendingData and the exact fallback-text checks for ApprovalGate.
- Test integrity: git show for builder commit fdc0bc8 lists only src/owlbear/bootstrap/toolsets.py. git diff name-only between 35abc75 and fdc0bc8 produced no test-file changes for tests/test_967_question_pending_emit.py. Current worktree drift in that test file is formatting-only, so preservation was verified at commit level.
- Security review: no hardcoded secrets, injection paths, traversal risks, or unsafe deserialization in the reviewed change.
- Data safety review: the change only wires the existing HookRegistry into AskUserToolset during bootstrap; no new persistence path, race, or atomicity risk was introduced.
- Implementation-aware gap analysis: no untested behavioral path remained after the bootstrap slice. Non-destructive wrapping, approval wrapping order, shared approval session, empty-policy behavior, and the exact hook injection line in build_toolsets are exercised.

### AC Compliance

- QuestionPendingData TypedDict, QUESTION_PENDING emit overload, and export in hooks.py: PASS.
- AskUserToolset hook storage and QUESTION_PENDING emit before receive: PASS.
- ApprovalGateToolset QUESTION_PENDING emit and skip conditions: PASS.
- build_toolsets passes hooks to AskUserToolset: PASS.
- OwlBearSettings.notification_events default remains task_complete and on_error without question_pending by default: PASS.

### Verdict

- PASS with confidence .95.

[[2026-03-25]] Wed 12:07

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | Yes | Updated | Added QUESTION_PENDING emit facts to Runtime row (AskUserToolset + ApprovalGateToolset, wired in #967, opt-in via notification_events) |
| 2 | Docstrings complete | Yes | Updated | Added hooks param to AskUserToolset class docstring Args section; ask_user() and ApprovalGateToolset.call_tool() docstrings already accurate |
| 3 | docs/sources/overview.md | Yes | Pass | Section already present with Celery + Prefect source attributions |
| 4 | README.md | No | N/A | No CLI commands added or changed |
| 5 | Research doc linked | Yes | Pass | docs/research/question-pending-emit-implementation.md exists; linked in task body |

### Files Updated

- .github/copilot-instructions.md (Runtime row - QUESTION_PENDING emitters documented)
- src/owlbear/tools/ask_user.py (AskUserToolset docstring - hooks param added)

### Scratch Files Cleaned

- docs/scratch/967-builder-notes.tmp (deleted)
- docs/scratch/967-research.tmp (deleted)

[[2026-03-25]] Wed 12:39

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| QuestionPendingData TypedDict in hooks.py | hooks.py L137-143: functional TypedDict with source(str), question(str), tool_name(NotRequired[str]) | PASS |
| Typed emit overload for QUESTION_PENDING | hooks.py L266-270: overload accepting QuestionPendingData | PASS |
| QuestionPendingData in __all__ | hooks.py L32: present in __all__ | PASS |
| AskUserToolset accepts hooks param | ask_user.py L71: hooks: HookRegistry or None = None; L79: self._hooks = hooks | PASS |
| ask_user() emits before receive | ask_user.py L117:_emit_question_pending(prompt) called before channel.receive(); L130-136: guards with if self._hooks is None | PASS |
| ApprovalGateToolset.call_tool() emits before receive | gate.py L109-115: payload with source=approval_gate, question=text_fallback, tool_name=name; emit before channel.receive() at L118; skipped when approval not required (L95 returns early) | PASS |
| build_toolsets passes hooks | toolsets.py L331: AskUserToolset(channel, hooks=hooks) | PASS |
| notification_events default unchanged | config.py L313-314: default=['task_complete', 'on_error'] -- no question_pending | PASS |

### Test Results

- Task suite: 22 passed in 3.24s (tests/test_967_question_pending_emit.py)
- Full suite: 4279 passed, 160 failed, 2 skipped in 197.88s
- Full suite failures: all pre-existing (RED-phase imports, async plugin edge cases); 0 failures in test_967 or related modules
- 3 collection errors ignored: test_entity_extractor_corpus.py, test_improvement_proposals.py, test_security_audit_log.py (pre-existing RED-phase)

### Lint Results

- ruff: 1 finding -- E501 in ask_user.py L59 (docstring line 128 chars, added by writer commit 0dbb83c); cosmetic only, no functional impact

### Architect Quality

- AC specificity: 8 individually verifiable lines with concrete type names, field names, source values, and skip conditions
- Edge case coverage: skip conditions for ApprovalGateToolset explicitly specified in AC
- Design direction: architecture notes accurately described existing patterns (emit_pre_tool_use, TerminalToolset hooks param); builder needed only 1 LOC change
- AC quality score: 5 (specific, complete, clean implementation)

### Upstream Commits

- fdc0bc8 feat: wire ask-user hooks in build_toolsets (#967, builder) -- src/owlbear/bootstrap/toolsets.py
- 0dbb83c docs: update docs for QUESTION_PENDING emit (#967, writer) -- copilot-instructions.md, ask_user.py docstring

### Confidence: .97

### Action: archive

[[2026-03-25]] Wed 12:39

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| QuestionPendingData TypedDict in hooks.py | hooks.py L137-143: functional TypedDict with source(str), question(str), tool_name(NotRequired[str]) | PASS |
| Typed emit overload for QUESTION_PENDING | hooks.py L266-270: overload accepting QuestionPendingData | PASS |
| QuestionPendingData in __all__ | hooks.py L32: present in __all__ | PASS |
| AskUserToolset accepts hooks param | ask_user.py L71: hooks: HookRegistry or None = None; L79: self._hooks = hooks | PASS |
| ask_user() emits before receive | ask_user.py L117:_emit_question_pending(prompt) called before channel.receive(); L130-136: guards with if self._hooks is None | PASS |
| ApprovalGateToolset.call_tool() emits before receive | gate.py L109-115: payload with source=approval_gate, question=text_fallback, tool_name=name; emit before channel.receive() at L118; skipped when approval not required (L95 returns early) | PASS |
| build_toolsets passes hooks | toolsets.py L331: AskUserToolset(channel, hooks=hooks) | PASS |
| notification_events default unchanged | config.py L313-314: default=['task_complete', 'on_error'] -- no question_pending | PASS |

### Test Results

- Task suite: 22 passed in 3.24s (tests/test_967_question_pending_emit.py)
- Full suite: 4279 passed, 160 failed, 2 skipped in 197.88s
- Full suite failures: all pre-existing (RED-phase imports, async plugin edge cases); 0 failures in test_967 or related modules
- 3 collection errors ignored: test_entity_extractor_corpus.py, test_improvement_proposals.py, test_security_audit_log.py (pre-existing RED-phase)

### Lint Results

- ruff: 1 finding -- E501 in ask_user.py L59 (docstring line 128 chars, added by writer commit 0dbb83c); cosmetic only, no functional impact

### Architect Quality

- AC specificity: 8 individually verifiable lines with concrete type names, field names, source values, and skip conditions
- Edge case coverage: skip conditions for ApprovalGateToolset explicitly specified in AC
- Design direction: architecture notes accurately described existing patterns (emit_pre_tool_use, TerminalToolset hooks param); builder needed only 1 LOC change
- AC quality score: 5 (specific, complete, clean implementation)

### Upstream Commits

- fdc0bc8 feat: wire ask-user hooks in build_toolsets (#967, builder) -- src/owlbear/bootstrap/toolsets.py
- 0dbb83c docs: update docs for QUESTION_PENDING emit (#967, writer) -- copilot-instructions.md, ask_user.py docstring

### Confidence: .97

### Action: archive

[[2026-03-25]] Wed 12:39

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| d1fe5b6 | chore | kanban/tasks/967-*.md | #967 |
