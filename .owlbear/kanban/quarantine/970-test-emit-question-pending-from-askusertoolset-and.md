---
id: 970
title: 'Test: Emit QUESTION_PENDING from AskUserToolset and ApprovalGateToolset'
status: archived
priority: important
created: 2026-03-23T23:02:00.8991678+01:00
updated: 2026-03-24T10:01:37.5868429+01:00
started: 2026-03-24T10:01:32.6050518+01:00
completed: 2026-03-24T10:01:32.6050518+01:00
tags:
    - agent
    - hooks
    - ask_user
    - approval
    - scope:core
    - type:test
    - test
parent: 955
depends_on:
    - 962
class: standard
---

## AC

### File target

- tests/test_question_pending_emit.py (or similar)

### Acceptance criteria (TDD RED)

- [ ] Test QuestionPendingData has required keys: source (str), question (str), tool_name (NotRequired[str])
- [ ] Test AskUserToolset.ask_user() emits QUESTION_PENDING with source='ask_user' and question= formatted prompt before channel.receive()
- [ ] Test AskUserToolset with hooks=None does not error on ask_user() call
- [ ] Test ApprovalGateToolset.call_tool() emits QUESTION_PENDING with source='approval_gate', question= prompt text, and tool_name= gated tool name before approval channel.receive()
- [ ] Test ApprovalGateToolset.call_tool() does NOT emit QUESTION_PENDING when approval is not required
- [ ] Test ApprovalGateToolset.call_tool() does NOT emit QUESTION_PENDING when tool is pre-granted
- [ ] Test OwlBearSettings().notification_events default does NOT include 'question_pending'
- [ ] All tests FAIL (RED phase -- implementation does not exist yet)

[[2026-03-24]] Tue 00:35

## Test-Writer Notes

- Test file: tests/test_question_pending_emit.py

- Classes: TestFromAC_QuestionPendingData, TestFromAC_AskUserEmitsQuestionPending, TestFromAC_AskUserNullHooks, TestFromAC_ApprovalGateEmitsQuestionPending, TestFromAC_NotificationEventsDefault

- Tests per category: happy 9, edge 2, error 4, boundary 6 (TypedDict structure)

- Total: 21 tests, all FAIL (ImportError: QuestionPendingData not exported yet) checked

- ruff: clean

- AC coverage: QuestionPendingData structure (6 tests), AskUser QUESTION_PENDING emit (5 tests), AskUser hooks=None (2 tests), ApprovalGate QUESTION_PENDING emit (4 tests), ApprovalGate no-emit cases (2 tests), OwlBearSettings default (2 tests)

[[2026-03-24]] Tue 02:13

## Builder Notes

- Files changed: src/owlbear/core/hooks.py, src/owlbear/tools/ask_user.py, src/owlbear/safety/gate.py
- Tests: 21 passed on task suite; 91 passed on widened scoped suite for touched modules.
- Coverage: src/owlbear/core/hooks.py 98%, src/owlbear/tools/ask_user.py 100%, src/owlbear/safety/gate.py 100%.
- Lint: ruff clean.
- Evidence: PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/test_question_pending_emit.py -q --tb=short -p pytest_asyncio.plugin -> 21 passed; PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/test_question_pending_emit.py tests/test_ask_user.py tests/test_approval_gate.py tests/test_hooks.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short -p pytest_asyncio.plugin -p pytest_cov -> 91 passed; uv run ruff check src/owlbear/core/hooks.py src/owlbear/tools/ask_user.py src/owlbear/safety/gate.py tests/test_question_pending_emit.py -> All checks passed.
- Fixes applied: Added QuestionPendingData export and QUESTION_PENDING emission in AskUserToolset and ApprovalGateToolset before awaiting channel.receive(); emission remains absent for ungated and pre-granted approval paths.

[[2026-03-24]] Tue 03:22

## Review Evidence

### Test Results

- PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/test_question_pending_emit.py -q --tb=short -p pytest_asyncio.plugin -> 21 passed, 4 optional-dependency warnings.

- uv run ruff check src/owlbear/core/hooks.py src/owlbear/tools/ask_user.py src/owlbear/safety/gate.py tests/test_question_pending_emit.py -> All checks passed.

- PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/test_question_pending_emit.py tests/test_ask_user.py tests/test_approval_gate.py tests/test_hooks.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short -p pytest_asyncio.plugin -p pytest_cov -> 91 passed, 4 warnings; src/owlbear/core/hooks.py 98 percent, src/owlbear/tools/ask_user.py 100 percent, src/owlbear/safety/gate.py 100 percent.

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

| AC line | Mapped test(s) | Would fail if AC were violated? | Verdict |

| --- | --- | --- | --- |

| QuestionPendingData required keys and types | tests/test_question_pending_emit.py:67, 71, 75, 79 | No. These assertions only check required and optional key sets. grep for __annotations__ or get_type_hints in tests/test_question_pending_emit.py returned no matches, so changing the value annotations away from str would still pass. | LAX |

| AskUserToolset.ask_user() emits QUESTION_PENDING with formatted prompt before channel.receive() | tests/test_question_pending_emit.py:106-177 plus prompt-format tests at tests/test_ask_user.py:107 and 117 | No for the options branch. The emitted payload is checked exactly only for the no-options case at tests/test_question_pending_emit.py:161; the options case only checks alpha and beta membership at :176-177, so a non-equal payload would still pass. | LAX |

| ApprovalGateToolset.call_tool() emits QUESTION_PENDING with prompt text and tool name before receive | tests/test_question_pending_emit.py:241-324 plus channel prompt tests at tests/test_approval_gate.py:101-128 and 437-458 | No. The emitted payload question is only checked as a non-empty string at tests/test_question_pending_emit.py:302-303; no test compares it to send_blocks(..., text_fallback) or the exact fallback prompt text. | LAX |

| ApprovalGateToolset does not emit when approval is not required | tests/test_question_pending_emit.py:341 | Yes. emitted == [] would fail immediately on any emit. | COVERED |

| ApprovalGateToolset does not emit when tool is pre-granted | tests/test_question_pending_emit.py:365 | Yes. emitted == [] would fail immediately on any emit. | COVERED |

| OwlBearSettings default notification_events excludes question_pending | tests/test_question_pending_emit.py:380 and 384; implementation at src/owlbear/config.py:314 | Yes. | COVERED |

#### Security Review

- No security issues found in src/owlbear/core/hooks.py, src/owlbear/tools/ask_user.py, or src/owlbear/safety/gate.py.

#### Test Integrity

| Original test | Change made | Assessment |

| --- | --- | --- |

| tests/test_question_pending_emit.py from commit cc7c945 | git diff --name-only cc7c945 HEAD -- tests/test_question_pending_emit.py produced no output. Task history shows cc7c945 for the test-writer and 5fda8ed for the builder. | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |

| --- | --- | --- |

| Assertion specificity | WEAK | tests/test_question_pending_emit.py:302-303 only asserts a non-empty approval question; :176-177 only checks option names are present; :67-79 checks key sets but not the TypedDict value annotations. |

| Negative and error-path coverage | ADEQUATE | tests/test_question_pending_emit.py:341 and 365 cover the two no-emit branches; TestFromAC_AskUserNullHooks covers hooks=None and omitted hooks paths. |

| Manual mutation reasoning | WEAK | Changing QuestionPendingData annotations away from str, or emitting a generic non-empty string instead of the real fallback prompt in src/owlbear/safety/gate.py:109-114, would still leave the scoped suite green. |

| Test independence | STRONG | Each test builds fresh mocks, channels, sessions, and hook registries. |

| Descriptive names | STRONG | The TestFromAC_* classes and methods describe the behavior under test clearly. |

#### Data Safety

- No data safety issues found.

#### Implementation-Aware Test Gaps

- src/owlbear/tools/ask_user.py:112-132 sends prompt and emits QUESTION_PENDING from the same prompt variable, but no test pins payload equality to the exact formatted options prompt.

- src/owlbear/safety/gate.py:107-114 sends send_blocks(..., text_fallback) and emits QUESTION_PENDING from that fallback, but no test asserts the emitted question equals text_fallback.

- src/owlbear/core/hooks.py:131 defines QuestionPendingData, but no test asserts its value annotations are str / NotRequired[str].

### Pass 2 - INFORMATIONAL

- No informational findings beyond the blocking test gaps.

### AC Compliance

| AC line | Evidence | Mapped test | Status |

- Summary: file target PASS; QuestionPendingData type-contract coverage FAIL; AskUser emitted formatted-prompt coverage FAIL; hooks=None PASS; ApprovalGate emitted prompt-text coverage FAIL; approval-not-required PASS; pre-granted PASS; notification_events default PASS; historical RED baseline PASS.

### Verdict

- FAIL. The implementation behaves correctly in the reviewed paths, but the task does not meet the review bar because AC coverage is too weak on QuestionPendingData types and exact emitted question text for both toolsets.

### Action Taken

- kanban\\kanban-md.exe edit 970 --status todo --release

[[2026-03-24]] Tue 04:09

## Test-Writer Notes (retry)

- Retry reason: reviewer FAIL — three AC coverage gaps: (1) QuestionPendingData type annotations only checked key-set membership, not str/NotRequired[str] values; (2) AskUser options branch only checked substrings, not exact formatted prompt; (3) ApprovalGate emitted question only asserted non-empty, not exact text_fallback string.

- Added classes: TestFromAC_970_QuestionPendingDataTypeAnnotations (3 tests), TestFromAC_970_AskUserExactFormattedPrompt (3 tests), TestFromAC_970_ApprovalGateExactFallbackText (3 tests)

- New tests: 9 total. All PASS because implementation is already correct (retry cycle, not new behavior)

- Preserved: 21 original tests — all PASS

- Total in file: 30 tests, 30 passed

- ruff: clean

- Commit: 1185a3c tests/test_question_pending_emit.py

[[2026-03-24]] Tue 04:19

## Builder Notes

- Files changed: none.

- RED check: TestFromAC suite already green before builder changes (`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/test_question_pending_emit.py -q --tb=short -p pytest_asyncio.plugin` -> 30 passed, 4 warnings).

- Tests: 100 passed (`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/test_question_pending_emit.py tests/test_ask_user.py tests/test_approval_gate.py tests/test_hooks.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short -p pytest_asyncio.plugin -p pytest_cov`).

- Coverage (task modules): src/owlbear/core/hooks.py 98%, src/owlbear/tools/ask_user.py 100%, src/owlbear/safety/gate.py 100%.

- Lint: `uv run ruff check src/owlbear/core/hooks.py src/owlbear/tools/ask_user.py src/owlbear/safety/gate.py tests/test_question_pending_emit.py` -> All checks passed.

- Evidence: `git status --short -- src/owlbear/core/hooks.py src/owlbear/tools/ask_user.py src/owlbear/safety/gate.py tests/test_question_pending_emit.py` returned empty.

- Fixes applied: None. Current HEAD already satisfies the strengthened TestFromAC contract from the retry cycle.

[[2026-03-24]] Tue 05:15

## Review Evidence

### Test Results

- PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/test_question_pending_emit.py -q --tb=short -p pytest_asyncio.plugin -> 30 passed, 4 optional-dependency warnings.

- PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/test_question_pending_emit.py tests/test_ask_user.py tests/test_approval_gate.py tests/test_hooks.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short -p pytest_asyncio.plugin -p pytest_cov -> 100 passed, 4 warnings.

### Lint Results

- uv run ruff check src/owlbear/core/hooks.py src/owlbear/tools/ask_user.py src/owlbear/safety/gate.py tests/test_question_pending_emit.py -> All checks passed.

### Coverage

- src/owlbear/core/hooks.py -> 98%

- src/owlbear/tools/ask_user.py -> 100%

- src/owlbear/safety/gate.py -> 100%

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |

| --- | --- | --- | --- |

| QuestionPendingData required keys and types | tests/test_question_pending_emit.py:65,69,73,77,395,402,409 | Yes. Required or optional key assertions and get_type_hints checks fail on key or annotation drift. | COVERED |

| AskUser emits source and formatted prompt before receive | tests/test_question_pending_emit.py:106,134,149,427,442,458 and tests/test_ask_user.py:101,111 | Yes. Order, source, plain prompt equality, and exact options prompt are pinned. | COVERED |

| AskUser with hooks=None does not error | tests/test_question_pending_emit.py:203,211 | Yes. Both explicit None and default-omitted hooks paths execute successfully. | COVERED |

| ApprovalGate emits source, prompt text, and tool_name before receive | tests/test_question_pending_emit.py:228,263,306,484,506,531 and tests/test_approval_gate.py:92,117 | Yes. Order, source, tool_name, and exact text_fallback strings for no-arg and with-arg cases are pinned. | COVERED |

| ApprovalGate does not emit when approval is not required | tests/test_question_pending_emit.py:327 | Yes. Any unexpected emit would fail emitted == []. | COVERED |

| ApprovalGate does not emit when pre-granted | tests/test_question_pending_emit.py:344 | Yes. Any unexpected emit would fail emitted == []. | COVERED |

| OwlBearSettings default excludes question_pending | tests/test_question_pending_emit.py:376,382 and src/owlbear/config.py:313 | Yes. The default set is asserted exactly. | COVERED |

| Historical RED baseline recorded before implementation existed | Task body Test-Writer Notes at 2026-03-24 00:35 | Yes. The original RED run recorded 21 failing tests caused by missing QuestionPendingData export. | COVERED |

#### Security Review

- No security issues found. The reviewed code only exports a TypedDict and emits prompt strings through existing hook and channel APIs; no secrets, eval, shell execution, or path handling were added.

#### Test Integrity

| Original Test | Change Made | Assessment |

| --- | --- | --- |

| tests/test_question_pending_emit.py from cc7c945 | git diff --ignore-all-space cc7c945 HEAD shows the original TestFromAC coverage preserved plus nine strengthening tests added in the retry cycle. No original method was weakened or removed. | PRESERVED |

| Retry-cycle reviewed files from 1185a3c | git diff --name-only 1185a3c HEAD -- tests/test_question_pending_emit.py src/owlbear/core/hooks.py src/owlbear/tools/ask_user.py src/owlbear/safety/gate.py produced no output. | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |

| --- | --- | --- |

| Assertion specificity | STRONG | Exact question strings are asserted for plain and options AskUser prompts and no-arg and with-arg approval prompts; TypedDict annotations are checked via get_type_hints. |

| Negative and error paths | ADEQUATE | hooks=None, approval-not-required, and pre-granted no-emit branches are covered directly. |

| Manual mutation reasoning | STRONG | Moving emit after receive breaks tests/test_question_pending_emit.py:106 and :228; changing prompt text or annotations breaks :395, :402, :409, :442, :484, and :506. |

| Test independence | STRONG | Each test builds fresh mocks, hook registries, approval sessions, and channels. |

| Descriptive names | STRONG | The TestFromAC classes and method names are scenario-specific and behavior-specific. |

#### Data Safety

- No data safety issues found.

#### Implementation-Aware Test Gaps

- No significant untested paths remain in the QUESTION_PENDING behavior. The reviewed code paths in src/owlbear/tools/ask_user.py:113-135 and src/owlbear/safety/gate.py:104-114 are covered for plain and options prompt construction, hooks absent, approval-not-required, pre-granted, and emitted payload equality.

### Pass 2 - INFORMATIONAL

- No informational findings.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |

| --- | --- | --- | --- |

| File target | tests/test_question_pending_emit.py exists and task-specific pytest passed. | tests/test_question_pending_emit.py | PASS |

| QuestionPendingData keys and types | src/owlbear/core/hooks.py:131 defines source, question, and tool_name. | tests/test_question_pending_emit.py:65,69,73,77,395,402,409 | PASS |

| AskUser emits QUESTION_PENDING with source and formatted prompt before receive | src/owlbear/tools/ask_user.py:113,124,135 emits the same prompt it sends. | tests/test_question_pending_emit.py:106,134,149,427,442,458; tests/test_ask_user.py:101,111 | PASS |

| AskUser with hooks=None does not error | hooks guard exists in src/owlbear/tools/ask_user.py:126. | tests/test_question_pending_emit.py:203,211 | PASS |

| ApprovalGate emits QUESTION_PENDING with source, prompt text, and tool_name before receive | src/owlbear/safety/gate.py:104,107,109,114 reuses text_fallback for the hook payload. | tests/test_question_pending_emit.py:228,263,306,484,506,531; tests/test_approval_gate.py:92,117 | PASS |

| ApprovalGate does not emit when approval is not required | Early return path remains before prompt construction. | tests/test_question_pending_emit.py:327 | PASS |

| ApprovalGate does not emit when tool is pre-granted | Pre-granted early return remains before prompt construction. | tests/test_question_pending_emit.py:344 | PASS |

| OwlBearSettings default excludes question_pending | src/owlbear/config.py:313 default remains task_complete and on_error only. | tests/test_question_pending_emit.py:376,382 | PASS |

| All tests FAIL in initial RED phase | Historical RED evidence preserved in the first Test-Writer Notes section. | Task body note from 2026-03-24 00:35 | PASS |

### Verdict: PASS

- Confidence .94.

### Action Taken

- kanban\\kanban-md.exe edit 970 --status docs --release

[[2026-03-24]] Tue 10:01

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| QuestionPendingData keys/types | hooks.py:132-139 TypedDict with source(str), question(str), tool_name(NotRequired[str]) | PASS |
| AskUser emits before receive | ask_user.py:117-118 sends then emits;_emit_question_pending L127-134 | PASS |
| AskUser hooks=None safe | ask_user.py:128-129 guard clause | PASS |
| ApprovalGate emits before receive | gate.py:110-116 emits before receive at L118 | PASS |
| ApprovalGate no-emit when not required | gate.py:91-92 early return before emit | PASS |
| ApprovalGate no-emit when pre-granted | gate.py:95-96 early return before emit | PASS |
| notification_events excludes question_pending | config.py:314 default=['task_complete','on_error'] | PASS |
| All tests FAIL in RED phase | Task body: 21 tests all ImportError at 2026-03-24 00:35 | PASS |

### Test Results

- task suite: 30 passed (tests/test_question_pending_emit.py)
- full suite: 4170 passed, 45 failed (all pre-existing RED-phase or unrelated tasks)
- ruff: clean on task files

### Upstream Commits

- cc7c945 test-writer RED (21 tests)
- 5fda8ed builder GREEN
- 1185a3c test-writer retry (9 strengthening tests)
- 19ab105 writer docs

### Quality Note

- Uncommitted cosmetic diff in hooks.py (parenthesized docstring) not from #970

### AC Quality Score: 4

AC was specific and testable. Retry cycle was needed for assertion strength, not AC vagueness.

### Confidence: .96

### Action: archive
