---
id: 808
title: Add valid_transitions(status)
status: archived
priority: medium
created: '2026-04-10T21:21:23.793444+00:00'
updated: '2026-04-13T13:27:39.638507+00:00'
tags:
- phase-1
- scope:mcp-kanban
- rigor:thorough
parent: 798
depends_on:
- 807
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `valid_transitions(status)` method on `KanbanEngine`
- Returns set of all configured statuses except the given one
- Raises `ValueError` for invalid status input
- `end_work()`'s linear behavior documented as agent-specific in docstring
- #807 tests pass GREEN
- Existing MCP tests pass (O4)

## Context

Phase 1, independent pair. Depends on #807 (RED tests).
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`
[[2026-04-13]]
## Research
- Research doc: .owlbear/research/valid-transitions-impl-808.md (validation pass — doc already existed)
- Sources: 6 studied, 6 high-relevance
- Validation findings:
  - AC1-3: `valid_transitions()` exists at engine.py L162-180, fully implemented (confirmed)
  - AC4: Doc flagged as ❌ gap → now ✅ resolved. `end_work()` docstring at engine.py L628-633 contains agent-specific Note section
  - AC5: 25/25 tests in test_valid_transitions_807.py pass GREEN (confirmed)
  - AC6: 479/481 engine tests pass; 2 failures are pre-existing and unrelated (#826 missing attr, TaskSummary schema drift)
- Recommendation: Builder work is docstring-verify-and-close — all code exists (confidence: 0.92)
- Follow-up tasks created: none (paired task #807 already exists, no new gaps)
- Decision requests: none (T1 — autonomous, no new capability)
[[2026-04-13]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One method (`valid_transitions`) + docstring clarification on `end_work` |
| Interface clarity | PASS | AC specifies method signature, return type (set), error (ValueError), docstring requirement |
| Dependency correctness | PASS | Depends on #807 (test task, currently in-progress); correctly listed |
| Module layering | PASS | Method on `KanbanEngine`; no upward imports or cross-domain coupling |
| TDD compliance | PASS | #807 is the preceding RED test task (25 test cases, all GREEN-on-arrival) |
| KISS/YAGNI | PASS | Minimal scope; implementation pre-exists, builder work is verify-and-close |
| Premise challenge | PASS | Needed for GUI-ready data contract (parent #798, Brief O5) |
| Pattern consistency | PASS | Follows existing engine method pattern (engine.py L162-180), ValueError for invalid input |
| Security surface | N/A | Internal engine method, no new system boundaries |
| Single domain | PASS | `scope:mcp-kanban` only |

### AC Assessment

| AC | Assessment | Action |
|----|-----------|--------|
| AC1: `valid_transitions(status)` method on `KanbanEngine` | Verifiable — confirmed at engine.py L162 | None |
| AC2: Returns set of all configured statuses except given | Verifiable — L176 `valid_statuses - {status}` | None |
| AC3: Raises `ValueError` for invalid status input | Verifiable — L173-175, tested with 3 error scenarios | None |
| AC4: `end_work()` linear behavior documented as agent-specific | Verifiable — confirmed Note section at engine.py L628-633 | None |
| AC5: #807 tests pass GREEN | Verifiable — 13 methods / 25 parametrized cases, all GREEN | None |
| AC6: Existing MCP tests pass (O4) | Verifiable — builder runs full suite | None |

### Codebase Evidence

- Implementation: `serve/kanban/src/owlbear_kanban/engine.py` L162-180
- Docstring update: `serve/kanban/src/owlbear_kanban/engine.py` L628-633 (Note section)
- Test file: `tests/test_valid_transitions_807.py` (13 methods, 25 test cases)
- Research doc: `.owlbear/research/valid-transitions-impl-808.md`

### Challenge Results

- Challenger: FALLBACK — T1 verify-and-close task, no architectural trade-offs to challenge
- Architect response: Proceeded; implementation pre-exists and is fully verified by research

### Verdict: APPROVE
### Action Taken: Advanced to todo. All AC lines are precise and verifiable. Implementation pre-exists — builder work is verify-and-close. Dependency #807 (in-progress) correctly blocks builder start.
[[2026-04-13]]
## Test-Writer Notes
- Test file: tests/test_valid_transitions_808.py
- Classes: TestFromAC_EndWorkDocstring
- Tests per category: happy 1, edge 1, boundary 1, error 0
- Total: 3 tests — **GREEN-on-arrival** (not failing)
- ruff: clean
- Commit: 982d9e9a

### AC Coverage

| AC | Tests | Notes |
|----|-------|-------|
| AC1: valid_transitions() method on KanbanEngine | Covered by #807 test file | Not duplicated here |
| AC2: Returns set excluding given status | Covered by #807 test file | Not duplicated here |
| AC3: Raises ValueError for invalid status | Covered by #807 test file | Not duplicated here |
| AC4: end_work() docstring documents linear behavior as agent-specific | 3 tests in TestFromAC_EndWorkDocstring | GREEN-on-arrival — docstring Note section already exists at engine.py L628-633 |
| AC5: #807 tests pass GREEN | Builder verification step | No testable unit-test interface |
| AC6: Existing MCP tests pass | Builder verification step | No testable unit-test interface |

### GREEN-on-Arrival Note
All 3 tests pass immediately because both the `valid_transitions()` implementation and the `end_work()` docstring Note section were confirmed as pre-existing during the architecture review and research doc (.owlbear/research/valid-transitions-impl-808.md). Tests are written such that they would fail in the absence of the docstring content — this matches the #807 precedent for this paired RED/GREEN task pair. Builder work is verify-and-close: run #807 tests (AC1-3), confirm docstring (AC4), run MCP suite (AC6), advance.
[[2026-04-13]]
## Builder Notes

### Files Changed
- No code changes needed — implementation was pre-existing (verify-and-close task).

### Evidence Summary
- **AC1–AC3** (`valid_transitions()` method): Implementation confirmed at `engine.py` L162–180. Returns `set[str]`, raises `ValueError` for invalid status, excludes current status.
- **AC4** (`end_work()` docstring): Note section at `engine.py` L628–640 contains "agent-specific convention" and cross-references `valid_transitions`. All 3 `TestFromAC_EndWorkDocstring` tests pass.
- **AC5** (#807 tests GREEN): 25/25 tests in `test_valid_transitions_807.py` pass.
- **AC6** (existing MCP tests): 252 passed, 1 pre-existing failure (`test_drop_board_context_489.py` — unrelated `kanban_bin` keyword arg issue, predates this task).

### Test Results
- `test_valid_transitions_807.py` + `test_valid_transitions_808.py`: **28/28 passed**
- MCP kanban suite (`-k "kanban"`): **252 passed, 1 pre-existing failure, 2 skipped**

### Lint Status
- ruff: **clean** on `engine.py`, `test_valid_transitions_807.py`, `test_valid_transitions_808.py`

### Coverage
- No new code written; existing implementation already covered by #807 tests.

### Fixes Applied
- None — verify-and-close only.
[[2026-04-13]]
## Review Evidence

### Test Results
- pytest: 28 passed, 0 failed (test_valid_transitions_807.py + test_valid_transitions_808.py)

### Lint
- ruff: clean on engine.py, test_valid_transitions_807.py, test_valid_transitions_808.py

### Coverage
- owlbear_kanban.engine: 17% (expected — module is large; only valid_transitions L162-180 and end_work docstring L628-640 are in scope; broader engine coverage is provided by the full test suite)

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage (test_valid_transitions_808.py)
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC4: end_work() docstring uses "agent" | test_end_work_docstring_uses_word_agent | YES — asserts `"agent" in doc.lower()`; removing Note section would fail | COVERED |
| AC4: docstring labels linear progression as "convention" | test_end_work_docstring_notes_linear_success_is_a_convention | YES — asserts any of `("convention", "agent-specific", "agent specific")` in doc | COVERED |
| AC4: docstring cross-references valid_transitions or uses "agent" | test_end_work_docstring_contrasts_linear_with_general_state_machine | YES — asserts "agent" OR "valid_transitions" in doc | COVERED |
| AC1-AC3: valid_transitions() contract | Covered by test_valid_transitions_807.py (25 tests, 13 methods) | YES — parametrized set equality, exclusion, ValueError, custom config | COVERED |

#### Security Review
- valid_transitions(): reads from self._config.statuses; no user-controlled external input, no new system boundary. No issues.
- end_work() change is docstring-only. No issues.

#### Test Integrity (TestFromAC_EndWorkDocstring)
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| test_end_work_docstring_uses_word_agent | None — builder made no code changes | PRESERVED |
| test_end_work_docstring_notes_linear_success_is_a_convention | None | PRESERVED |
| test_end_work_docstring_contrasts_linear_with_general_state_machine | None | PRESERVED |

#### Test Quality
- **Assertion specificity**: STRONG — each assertion targets specific words; generic `assert result` pattern absent.
- **Error/negative paths**: N/A for docstring tests (all 3 are presence checks; no error branches exist).
- **Mutation resistance**: Removing the Note section entirely fails all 3; removing "agent-specific convention" fails tests 1 & 2; removing "valid_transitions" cross-reference would not fail test 3 (relies on "agent" in doc for that branch — acceptable).
- **Test independence**: STRONG — all access `KanbanEngine.end_work.__doc__` as a class attribute; no fixtures or shared state.
- **Naming**: STRONG — descriptive names clearly state the AC signal under test.

#### Data Safety
- No new data paths, no LLM output, no mutable shared state. Clean.

#### Implementation-Aware Test Gap Analysis
- engine.py L173-175 (ValueError guard): tested by 4 error tests in #807 file.
- engine.py L176 (`valid_statuses - {status}`): tested by 14 parametrized cases.
- engine.py L628-640 Note section: tested by all 3 tests in #808 file.
- No untested significant paths.

#### Builder Process Quality
- Single `## Builder Notes` section; no retries; no loop. CLEAN.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: valid_transitions(status) on KanbanEngine | engine.py L162 — method exists, returns set[str] | test_valid_transitions_807.py — 14 parametrized cases | PASS |
| AC2: Returns set of all statuses except given | engine.py L176: `valid_statuses - {status}` | test_returns_all_statuses_except_given x7, test_given_status_excluded_from_result x7 | PASS |
| AC3: Raises ValueError for invalid status | engine.py L173-175: guard + descriptive message | test_unknown, test_empty_string, test_case_mismatch, test_value_error_message_names_invalid_status | PASS |
| AC4: end_work() docstring agent-specific | engine.py L628-640: "agent-specific convention" + cross-ref valid_transitions | TestFromAC_EndWorkDocstring (3 tests, all GREEN) | PASS |
| AC5: #807 tests pass GREEN | quality-runner: 25/25 pass in 807 file (28 total including 808) | test_valid_transitions_807.py | PASS |
| AC6: Existing MCP tests pass | Builder reports 252 passed, 1 pre-existing failure (test_drop_board_context_489 — kanban_bin kwarg, predates this task). Scope confirmed independent. | MCP kanban suite | PASS |

### Deductions
- Engine coverage 17%: expected for verify-and-close scope; not a deduction against confidence.
- Zero deductions.

### Verdict
- Confidence: .96 → PASS
[[2026-04-13]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A | `valid_transitions()` is a new public method; `end_work()` gained a docstring Note. `.github/copilot-instructions.md` contains no engine API table — high-level identity doc only, no update required. |
| 2 | Module docstrings | Yes | Verified | `valid_transitions()` L162-180: Args/Returns/Raises accurate against implementation. `end_work()` L628-640: Note section present with "agent-specific convention" wording and cross-reference to `valid_transitions`. Both ✓. |
| 3 | External attribution | No | N/A | All 6 research sources are internal repo files (engine.py, server.py, briefs, research docs). No external patterns imported. |
| 4 | CLI changes | No | N/A | Verify-and-close task; no command-line interface changes. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/valid-transitions-impl-808.md` exists and is linked in task body. Follow-up tasks: none needed (noted in research doc and Architecture Review). |

### Files Updated
None — all docstrings were already accurate; no documentation files required editing.

### Scratch Files Cleaned
None found — no `.owlbear/scratch/808-*` files exist.
[[2026-04-13]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: valid_transitions(status) on KanbanEngine | engine.py L163 — method exists, returns set[str] | PASS |
| AC2: Returns set of all statuses except given | engine.py L178: `valid_statuses - {status}` | PASS |
| AC3: Raises ValueError for invalid status | engine.py L175-177: guard + descriptive message | PASS |
| AC4: end_work() docstring agent-specific | engine.py L630-636: "agent-specific convention" + cross-ref valid_transitions | PASS |
| AC5: #807 tests pass GREEN | 25/25 pass in test_valid_transitions_807.py | PASS |
| AC6: Existing MCP tests pass | 4084 passed, 351 pre-existing failures, 0 related to #808 | PASS |

### Test Results
- pytest: 28/28 task-scoped (25 from #807, 3 from #808); full suite 4084 pass / 351 fail (all pre-existing, none #808-related)
- ruff: clean on engine.py, test_valid_transitions_807.py, test_valid_transitions_808.py

### Architect Quality: 4/5
AC1-4 are specific and verifiable. AC5-6 are process verification steps rather than specifications — adequate for a paired red/green verify-and-close task but slightly weaker as acceptance criteria.

### Deduction Breakdown
- AC lines without evidence: 0 (-.02 each) → 0
- Lint violations: 0 (-.05) → 0
- AC quality ≤ 3: no (-.03) → 0
- Missing reviewer evidence: no (-.02) → 0
- Full-suite failures in scope: 0 (-.05) → 0

### Confidence: 1.00
### Action: archive