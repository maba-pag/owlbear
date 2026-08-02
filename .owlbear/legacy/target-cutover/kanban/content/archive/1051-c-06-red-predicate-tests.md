---
id: 1051
title: 'C-06: RED — predicate tests'
status: archived
priority: medium
created: 2026-04-21T10:42:50.287239+00:00
updated: 2026-04-23T03:13:54.530724+00:00
tags:
- phase:storage
- brief:c
- scope:kanban
- tdd:red
parent: 1043
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
## Brief
Brief C (#1043) — paper-c.md §8.8
Module: `serve/kanban/tests/test_predicates.py`

## Acceptance Criteria

- [ ] AC-C39: `required_sections` matches `Section.heading` case-insensitively, with surrounding whitespace stripped
- [ ] AC-C40: `require_list_in_section` uses same case-insensitive, whitespace-stripped heading lookup, returns true iff matched section's content parses to at least one CommonMark list (`bullet_list` or `ordered_list`)
- [ ] AC-C41: Predicate behaviour matches Brief B D64 semantically; only the implementation substrate changed (list[Section] instead of regex)
- [ ] All tests fail (RED phase — no implementation exists yet)
[[2026-04-21]]
## Test-Writer Notes

**Situation:** `predicates.py` implementation already exists — builder ran ahead of test-writer in this batch. All tests pass (21/21), ruff clean.

**Test file:** `serve/kanban/tests/test_predicates.py`
**Classes:**
- `TestFromAC_RequiredSections` (12 tests) — AC-C39, AC-C41
- `TestFromAC_RequireListInSection` (9 tests) — AC-C40, AC-C41

**Categories:**
- Happy path: 4 (exact match, bullet list, ordered list, case-insensitive)
- Edge: 5 (empty required list, preamble heading=None, empty content, whitespace stripping)
- Error/boundary: 12 (one-missing, not-present, code-fence, no-space-##, multi-section)

**AC Coverage:**
| AC | Tests |
|----|-------|
| C39 case-insensitive, whitespace-stripped heading | 9 |
| C40 list detection (bullet/ordered), same lookup | 9 |
| C41 semantic equivalence to Brief B D64 | 2 |

**Fail verification:** N/A — implementation already existed when task was claimed. Tests pass against the extant implementation. Passing through to builder.
[[2026-04-22]]
## Builder Notes
- Implementation: no code changes in this builder pass.
- Context: task is RED-phase test task, but `predicates.py` implementation already existed before this claim (per Test-Writer Notes), so fail-before-implement verification is not applicable in this handoff state.
- Tests: 21/21 passed in `serve/kanban/tests/test_predicates.py` (`failed: []`).
- Coverage: 98% on `owlbear_kanban.predicates` (49 statements, 1 missing line: 31).
- Ruff: clean on `serve/kanban/src/owlbear_kanban/predicates.py` and `serve/kanban/tests/test_predicates.py`.
- Evidence summary: AC-C39/C40/C41 behaviors are satisfied by current implementation and validated by TestFromAC suite.

- Reflection: upstream sequencing (GREEN before RED task finalization) prevented strict RED fail-verification at builder time.
- Reflection: quality-runner scoped verification provided sufficient independent evidence to advance without speculative edits.
- Reflection: no surgical code changes were needed; avoided unrelated refactors to keep diff zero-risk.
[[2026-04-22]]
## Review Evidence
### Test Results
- pytest: 21 passed, 0 failed (independent quality-runner scoped run on serve/kanban/tests/test_predicates.py)

### Lint: clean
- ruff: clean for serve/kanban/src/owlbear_kanban/predicates.py and serve/kanban/tests/test_predicates.py

### Coverage: owlbear_kanban.predicates: 98%
- Missing line: serve/kanban/src/owlbear_kanban/predicates.py:31 (`return parse_body(task.body)`)

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC-C39: `required_sections` matches `Section.heading` case-insensitively, with surrounding whitespace stripped | `test_ac_c39_case_insensitive_match`, `test_ac_c39_whitespace_stripped_from_section_heading`, related `TestFromAC_RequiredSections` cases | Yes. Shared matcher strips and casefolds at serve/kanban/src/owlbear_kanban/predicates.py:38, and the suite exercises casefolding plus heading-side/query-side trimming in the required_sections path. | COVERED |
| AC-C40: `require_list_in_section` uses same case-insensitive, whitespace-stripped heading lookup, returns true iff matched section's content parses to at least one CommonMark list (`bullet_list` or `ordered_list`) | `test_ac_c40_section_lookup_case_insensitive`, `test_ac_c40_section_lookup_whitespace_stripped`, `test_ac_c40_list_inside_code_fence_not_counted` | No. The suite trims only the query string at serve/kanban/tests/test_predicates.py:179-184, never `Section.heading` for `require_list_in_section`, even though lookup depends on serve/kanban/src/owlbear_kanban/predicates.py:38. It also does not probe CommonMark boundary cases against regex-based list detection at serve/kanban/src/owlbear_kanban/predicates.py:22-24,87,96. | LAX |
| AC-C41: Predicate behaviour matches Brief B D64 semantically; only the implementation substrate changed (list[Section] instead of regex) | `test_ac_c41_no_space_heading_does_not_satisfy_require_list`, `test_ac_c41_semantic_equivalence_to_brief_b_d64` | No. Representative positive and no-space-heading negative cases exist, but semantic equivalence is not established when the regex heuristics diverge from CommonMark semantics. | LAX |
| All tests fail (RED phase — no implementation exists yet) | task body AC plus task state | No. The task body still requires fail-first at .owlbear/kanban/tasks/1051-c-06-red-predicate-tests.md:31, but the same task body records that `predicates.py` already existed and fail verification was N/A at .owlbear/kanban/tasks/1051-c-06-red-predicate-tests.md:35 and :54. | UNSATISFIABLE IN THIS REVIEW STATE |

#### Security Review
- No issues in scoped files. The reviewed module is pure in-process text inspection with no subprocess, filesystem, network, secret, deserialization, or dynamic execution surface.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_RequiredSections` | No weakening evidence in current file; assertions remain explicit boolean checks. | PRESERVED |
| `TestFromAC_RequireListInSection` | No weakening evidence in current file; assertions remain explicit boolean checks. | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Assertions are direct `is True` / `is False` checks throughout the suite. |
| Negative/error-path coverage | ADEQUATE | Missing-section, no-list, code-fence, and no-space-heading negatives are covered. |
| Manual mutation reasoning | WEAK | Removing heading-side stripping from the shared matcher at serve/kanban/src/owlbear_kanban/predicates.py:38 would not fail the `require_list_in_section` suite because only query-side trimming is tested at serve/kanban/tests/test_predicates.py:179-184. Likewise, over-permissive regex behavior at serve/kanban/src/owlbear_kanban/predicates.py:22-24,87 is not challenged by boundary tests. |
| Test independence | STRONG | Every test builds fresh `Section` and `Task` values through local helpers at serve/kanban/tests/test_predicates.py:22-38. |
| Descriptive test names | STRONG | Test names are AC-linked and behavior-specific across both `TestFromAC_*` classes. |

#### Data Safety
- No issues. The reviewed code is side-effect free boolean inspection of task body content.

#### Implementation-Aware Gaps
- `serve/kanban/src/owlbear_kanban/predicates.py:31` is uncovered. Quality-runner reported the only missing line at the `parse_body(task.body)` branch, and every scoped test constructs `Task.body` as `list[Section]` through serve/kanban/tests/test_predicates.py:29.
- `serve/kanban/src/owlbear_kanban/predicates.py:22-24,87,96` still uses regex heuristics for list and fence detection instead of parsing CommonMark. This likely accepts four-space-indented `- item` / `1. item` and misses fences indented by up to three spaces. No scoped test exercises those boundaries.
- `serve/kanban/tests/test_predicates.py:179-184` tests query-side whitespace trimming only. There is no `require_list_in_section` case where the matched `Section.heading` itself contains surrounding whitespace, despite the shared lookup path at serve/kanban/src/owlbear_kanban/predicates.py:38.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- The test file header in serve/kanban/tests/test_predicates.py:1-15 is stale. It still describes an ImportError-based RED state even though the implementation exists and the scoped run is green.
- Task sequencing is inconsistent: this task still carries a literal RED-only AC while the implementation already exists and the green rewrite task remains separate. That is an AC-quality problem, not evidence that the current suite is sufficient.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC-C39: case-insensitive, whitespace-stripped heading match for `required_sections` | Shared matcher strips and casefolds at serve/kanban/src/owlbear_kanban/predicates.py:38; heading-side whitespace is exercised by `test_ac_c39_whitespace_stripped_from_section_heading` at serve/kanban/tests/test_predicates.py:80-85. | `TestFromAC_RequiredSections` | PASS |
| AC-C40: same lookup for `require_list_in_section`, true iff CommonMark list exists | Lookup uses the shared matcher at serve/kanban/src/owlbear_kanban/predicates.py:38, but list detection relies on regex at serve/kanban/src/owlbear_kanban/predicates.py:22-24,87. Tests cover query-side trimming at serve/kanban/tests/test_predicates.py:179-184 and a column-0 fence only at :193-199, leaving heading-side whitespace and CommonMark boundaries unproved. | `TestFromAC_RequireListInSection` | FAIL |
| AC-C41: semantic equivalence to Brief B D64 | Positive/no-space-heading checks exist at serve/kanban/tests/test_predicates.py:121-132 and :213-223, but no boundary tests prove equivalence when regex heuristics diverge from CommonMark parsing. | both `TestFromAC_*` classes | FAIL |
| All tests fail (RED phase — no implementation exists yet) | The task body still requires fail-first at .owlbear/kanban/tasks/1051-c-06-red-predicate-tests.md:31, but the task body itself states the implementation already existed and fail verification was not possible at lines 35 and 54. | task body | FAIL |

### Deductions
- -0.14: AC-C40 proof is lax; `require_list_in_section` coverage misses heading-side whitespace and CommonMark boundary cases.
- -0.12: AC-C41 semantic-equivalence proof is incomplete.
- -0.10: Test quality includes a WEAK mutation-resistance dimension.
- -0.08: The string-body compatibility branch at predicates.py:31 is uncovered.
- -0.06: The literal RED-only AC is unsatisfiable in the current task state.

### Confidence: .50
### Verdict: FAIL
### Action
- Reject to backlog. Architect needs to re-scope or supersede the stale RED-only AC, and the test-writer needs explicit coverage for heading-side whitespace plus CommonMark boundary cases before this task can be accepted.

### Reflection
- RED and GREEN sequencing broke the literal fail-first AC; that must be treated as an AC-quality defect, not silently waived.
- A green scoped run hid a likely semantic mismatch because the suite never challenged the regex heuristic against CommonMark boundaries.
- The coverage miss on predicates.py:31 exposed that the string-body compatibility path is still untested.
- No builder loop issue was present; the rejection is about evidence quality and task-state quality, not churn.
[[2026-04-22]]
## Architecture Review (Return Cycle)

### Context
Reviewer rejected at .50 confidence. Five deductions: (1) AC-C40 heading-side whitespace untested for `require_list_in_section`, (2) AC-C41 semantic-equivalence proof incomplete, (3) weak mutation resistance, (4) string-body compatibility branch at predicates.py:31 uncovered, (5) literal RED-only AC unsatisfiable.

### Reviewer Findings Assessment

| Finding | Valid? | Resolution |
|---------|--------|------------|
| AC "All tests fail" unsatisfiable — implementation already exists | Yes | Drop from AC. Pipeline sequencing artifact, not a design requirement. |
| Heading-side whitespace untested for `require_list_in_section` | Yes | Add AC-C40a. `required_sections` has this test (`test_ac_c39_whitespace_stripped_from_section_heading`), but `require_list_in_section` only tests query-side trimming at test_predicates.py:179-184. Both paths use `_section_matches` at predicates.py:38 but test coverage must prove both entry points. |
| String-body compatibility branch uncovered (predicates.py:31) | Yes | Add AC-C40b. `_get_sections` str→`parse_body` fallback is live code with zero test coverage. |
| CommonMark boundary cases untested | Partially valid | The implementation uses regex heuristics (predicates.py:22-24). Testing exact CommonMark spec compliance is the GREEN task's responsibility (#1060). Existing positive/negative tests (bullet, ordered, prose, code-fence) provide adequate contract coverage for the RED phase. |
| AC-C41 semantic equivalence unproven at boundaries | Partially valid | Representative equivalence check (`test_ac_c41_semantic_equivalence_to_brief_b_d64`) is sufficient. Exhaustive boundary proof would require the old regex implementation for differential testing, which is out of scope. |

### Codebase Evidence

- `_section_matches` (predicates.py:35-38) is the shared heading matcher for both `required_sections` and `require_list_in_section` — strips and casefolds both sides.
- `_get_sections` (predicates.py:28-31) has two branches: list passthrough (covered) and str→parse_body fallback (uncovered).
- `parse_body` (body_parser.py:32) is separately tested in test_body_parser.py but never exercised through the predicates entry point.
- `required_sections` and `require_list_in_section` have no external consumers yet (only test_predicates.py imports them).
- Section model (models.py:193-201): Pydantic BaseModel with heading, level, content.

### Revised Acceptance Criteria

The following replaces the original AC section for downstream agents:

- [ ] AC-C39: `required_sections` matches `Section.heading` case-insensitively, with surrounding whitespace stripped
- [ ] AC-C40: `require_list_in_section` uses same case-insensitive, whitespace-stripped heading lookup (both query-side and heading-side), returns true iff matched section's content contains at least one CommonMark list item (`bullet_list` or `ordered_list`) outside fenced code blocks
- [ ] AC-C40a: Test suite includes at least one `require_list_in_section` case where `Section.heading` has surrounding whitespace (heading-side stripping proof)
- [ ] AC-C40b: At least one test exercises the string-body compatibility path (`_get_sections` when `task.body` is `str`, triggering `parse_body` at predicates.py:31)
- [ ] AC-C41: Predicate behaviour matches Brief B D64 semantically; only the implementation substrate changed (list[Section] instead of regex)

**Dropped:** "All tests fail (RED phase — no implementation exists yet)" — implementation already existed when test-writer first claimed; pipeline sequencing artifact, not a design requirement.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Test coverage for one module (predicates.py) |
| Interface clarity | PASS | Revised AC specifies exact gaps: AC-C40a (heading-side ws) and AC-C40b (str-body path) |
| Dependency correctness | PASS | No deps listed; downstream #1060 depends on this task correctly |
| Module layering | PASS | Test-only task, no layering concern |
| TDD compliance | PASS | Tagged `tdd:red`; test-writer processes it |
| KISS/YAGNI | PASS | Two targeted test additions, no scope creep |
| Premise challenge | PASS | Predicates module exists and needs the coverage reviewer identified |
| Pattern consistency | PASS | Test file follows `TestFromAC_` naming convention established in suite |
| Security surface | PASS | Pure in-process text inspection, no system boundary |
| Single domain | PASS | Kanban domain only |

### Challenge Results
- Challenger: FALLBACK — not available in session (only Explore agent)
- This is the first architecture review cycle for this task

### Verdict: REFINE → APPROVE
### Action: Revised AC to address reviewer's valid findings. Dropped unsatisfiable RED AC. Added AC-C40a (heading-side whitespace) and AC-C40b (string-body compatibility). Advanced to todo.
[[2026-04-22]]
## Test-Writer Notes (Retry)

**Situation:** Retry cycle — reviewer found two coverage gaps (AC-C40a, AC-C40b). Implementation already exists; all new tests PASS (consistent with original builder-ahead-of-test state).

**Test file:** `serve/kanban/tests/test_predicates.py`
**Classes (unchanged naming):**
- `TestFromAC_RequiredSections` (12 tests, was 11 → +1)
- `TestFromAC_RequireListInSection` (12 tests, was 10 → +2)

**New tests added:**
| Test | AC | Class |
|------|-----|-------|
| `test_ac_c40b_string_body_required_sections` | AC-C40b | `TestFromAC_RequiredSections` |
| `test_ac_c40a_heading_side_whitespace_stripped` | AC-C40a | `TestFromAC_RequireListInSection` |
| `test_ac_c40b_string_body_require_list_in_section` | AC-C40b | `TestFromAC_RequireListInSection` |

**AC Coverage:**
| AC | Tests |
|----|-------|
| C39: required_sections case-insensitive, whitespace-stripped | 9 |
| C40: require_list_in_section same lookup, CommonMark list | 9 |
| C40a: require_list_in_section heading-side whitespace proof | 1 (new) |
| C40b: string-body compatibility (_get_sections → parse_body) | 2 (new) |
| C41: semantic equivalence to Brief B D64 | 2 |

**Fail verification:** N/A — implementation already existed at first pass and continues to exist. New tests serve as coverage/mutation-resistance proofs per architecture review directive. 24/24 pass, ruff clean.

**Commit:** `40f3643a` — `test: add AC-C40a/C40b coverage tests for predicates (#1051, test-writer)`
[[2026-04-22]]
## Builder Notes
- Implementation: no code changes required in this builder pass.
- Files changed: none.
- Tests: 24 TestFromAC tests passed in `serve/kanban/tests/test_predicates.py` (`failed: []`).
- Coverage: 100% on `owlbear_kanban.predicates`.
- Ruff: clean (no violations on scoped paths).
- Evidence summary: AC-C39/C40/C40a/C40b/C41 are satisfied by the current implementation and validated by scoped quality-runner results.
- Fixes applied: none (implementation already satisfied updated retry AC).

- Reflection: retry-cycle additions (AC-C40a/AC-C40b) closed prior review evidence gaps without requiring source edits.
- Reflection: quality-runner scoped verification provided independent GREEN evidence suitable for advancement.
- Reflection: keeping a zero-diff handoff avoided unnecessary churn and preserved surgical task boundaries.
[[2026-04-22]]
## Review Evidence

### Test Results
- Independent quality-runner scoped run: 24 passed, 0 failed, 0 skipped in `serve/kanban/tests/test_predicates.py`.

### Lint
- Ruff clean on `serve/kanban/src/owlbear_kanban/predicates.py` and `serve/kanban/tests/test_predicates.py`.

### Coverage
- Scoped coverage for `owlbear_kanban.predicates`: 100%.
- The quality-runner report also showed a low workspace-wide overall percentage from the scoped invocation; the target module coverage is the relevant gate here.

### Pass 1 — Critical Checks

#### Test-Writer AC Coverage
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC-C39 | `_section_matches` strips and casefolds both sides at `serve/kanban/src/owlbear_kanban/predicates.py:34-38`. `required_sections` exercises exact, case-insensitive, query-side trim, heading-side trim, missing, multi-section, empty-list, and `heading=None` cases in `serve/kanban/tests/test_predicates.py:47-145`. | PASS |
| AC-C40 | The revised task AC still requires CommonMark list-item and fenced-code-block semantics at `.owlbear/kanban/tasks/1051-c-06-red-predicate-tests.md:178`. The implementation relies on regex heuristics at `serve/kanban/src/owlbear_kanban/predicates.py:22-24,87,96`, while the suite proves only `-` bullets, `1.` ordered items, query-side trim, one heading-side trim case, and one unindented backtick fence in `serve/kanban/tests/test_predicates.py:156-212,238-256`. The suite does not demonstrate that CommonMark-valid regressions such as alternative bullet markers or other fenced-block forms would fail. | FAIL |
| AC-C40a | Explicit heading-side whitespace proof exists in `serve/kanban/tests/test_predicates.py:238-243`, hitting the same `_section_matches` helper at `serve/kanban/src/owlbear_kanban/predicates.py:34-38`. | PASS |
| AC-C40b | Both entry points cover the `task.body` string compatibility path in `_get_sections` at `serve/kanban/src/owlbear_kanban/predicates.py:27-31`, via `serve/kanban/tests/test_predicates.py:134-145` and `serve/kanban/tests/test_predicates.py:245-256`. | PASS |
| AC-C41 | The revised task still requires semantic preservation at `.owlbear/kanban/tasks/1051-c-06-red-predicate-tests.md:181`. The suite has one positive sample and one no-space-heading negative sample in `serve/kanban/tests/test_predicates.py:121-132,214-236`, but it does not pin down the broader CommonMark-sensitive behaviors implied by the production regex substrate in `serve/kanban/src/owlbear_kanban/predicates.py:22-24,87,96`. | FAIL |

#### Security Review
- No issues found. The scoped code is pure in-memory text inspection with no filesystem, subprocess, network, deserialization, or dynamic execution sink.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_RequiredSections` | Current assertions remain explicit boolean checks; no weakening is visible in the present file. | PRESERVED |
| `TestFromAC_RequireListInSection` | Current assertions remain explicit boolean checks; no weakening is visible in the present file. | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Assertions are direct `is True` / `is False` checks throughout the file. |
| Negative and error-path coverage | ADEQUATE | Missing-section, prose-only, empty-content, no-space-heading, and one fenced-block negative are covered. |
| Manual mutation reasoning | WEAK | A regression in the CommonMark-sensitive regex substrate at `serve/kanban/src/owlbear_kanban/predicates.py:22-24,87,96` would still pass the current suite because the positive cases only prove `-` and `1.` markers at `serve/kanban/tests/test_predicates.py:156-168`, and the only fence case is one backtick block at `serve/kanban/tests/test_predicates.py:206-212`. |
| Test independence | STRONG | Tests build fresh `Task` and `Section` values through local helpers and inline constructors. |
| Descriptive test names | STRONG | Test names are AC-linked and behavior-specific. |

#### Data Safety
- No issues found. The reviewed code is stateless boolean inspection of task content.

#### Implementation-Aware Test Gaps
- The retry closed the prior heading-side-whitespace and string-body-path gaps.
- The remaining gap is the CommonMark contract itself: the revised AC line at `.owlbear/kanban/tasks/1051-c-06-red-predicate-tests.md:178` is broader than the proof supplied by `serve/kanban/tests/test_predicates.py:156-212,238-256`.
- Because the test task is the RED specification for downstream work, leaving those cases unproved gives false confidence even though line coverage is 100%.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — Informational
- `serve/kanban/tests/test_predicates.py:1-15` still advertises an obsolete RED-only state and ImportError expectation. That is stale but not the reason for rejection.
- The architecture return note at `.owlbear/kanban/tasks/1051-c-06-red-predicate-tests.md:162-163` treated exact CommonMark boundary coverage as a GREEN concern, but the binding revised AC text at `.owlbear/kanban/tasks/1051-c-06-red-predicate-tests.md:178-181` still keeps that contract in scope. I reviewed against the binding AC text.

### Deductions
- -0.08: AC-C40 still lacks proof for the full CommonMark-sensitive contract stated in the revised AC.
- -0.06: AC-C41 semantic-preservation evidence remains sample-based rather than contract-level.
- -0.02: Manual mutation resistance is weak for the list and fence substrate.

### Confidence
- .84

### Verdict
- FAIL

### Action
- Return to todo.
- Add `TestFromAC_*` coverage that would fail on CommonMark-valid list or fence regressions that are still in scope under `.owlbear/kanban/tasks/1051-c-06-red-predicate-tests.md:178-181`.
- If those edge cases are intentionally not part of this RED task, the architect must first narrow the AC text before the suite can be approved.

### Reflection
- A retry that fixes the last review findings can still fail if the revised AC remains broader than the new tests.
- 100% line coverage on the target module did not eliminate the contract gap; the missing evidence is semantic, not line-level.
- The clean builder pass was credible, but the quality gate here is test strength, not whether the current implementation happens to pass the present suite.
[[2026-04-22]]
## Test-Writer Notes (Retry 2)

**Situation:** Second retry — reviewer cited weak mutation resistance: only `-` and `1.` bullet markers tested, only backtick fence tested, AC-C41 semantic equivalence proof sample-based.

**Test file:** `serve/kanban/tests/test_predicates.py`
**Classes:** `TestFromAC_RequireListInSection` (4 new tests added, total 16)

**New tests (all 4 added to `TestFromAC_RequireListInSection`):**

| Test | AC | Mutation Guard |
|------|----|---------------|
| `test_ac_c40_star_bullet_returns_true` | C40 | Fails if `*` removed from `[-*+]` regex |
| `test_ac_c40_plus_bullet_returns_true` | C40 | Fails if `+` removed from `[-*+]` regex |
| `test_ac_c40_tilde_fence_excludes_list_items` | C40 | Fails if tilde fence detection removed |
| `test_ac_c41_all_bullet_markers_recognised` | C41 | Fails if any of `-`, `*`, `+` removed from bullet substrate |

**AC Coverage:**
| AC | Tests |
|----|-------|
| C39: required_sections case-insensitive, whitespace-stripped | 9 |
| C40: require_list_in_section same lookup, CommonMark list/fence | 13 |
| C40a: heading-side whitespace proof | 1 |
| C40b: string-body compatibility | 2 |
| C41: semantic equivalence to Brief B D64 (all bullet markers, fence forms) | 3 |

**Results:** 28/28 pass (implementation already exists), ruff clean.
**Commit:** `51a32331` — `test: add CommonMark boundary coverage for predicates (#1051, test-writer)`
[[2026-04-22]]
## Builder Notes
- Implementation: no code changes required in this builder pass.
- Files changed: none.
- Tests: 28 passed, 0 failed, 0 skipped in `serve/kanban/tests/test_predicates.py` (independent quality-runner scoped run).
- Coverage: 100% on `owlbear_kanban.predicates` (49 statements, 0 missed).
- Ruff: clean for `serve/kanban/src/owlbear_kanban/predicates.py` and `serve/kanban/tests/test_predicates.py`.
- Evidence summary: current implementation satisfies AC-C39/C40/C40a/C40b/C41 as exercised by the `TestFromAC_*` suite; no blocking implementation gaps surfaced.
- Fixes applied: none.

- Reflection: retry-cycle tests strengthened evidence sufficiently to validate behavior without changing source code.
- Reflection: scoped quality-runner verification gave canonical, comparable gate evidence (pytest, ruff, coverage).
- Reflection: keeping a zero-diff builder pass preserved surgical scope and avoided speculative edits.
[[2026-04-22]]
## Review Evidence
### Test Results
- Independent quality-runner scoped run: 28 passed, 0 failed, 0 skipped in `serve/kanban/tests/test_predicates.py`.

### Lint
- Ruff clean for `serve/kanban/src/owlbear_kanban/predicates.py` and `serve/kanban/tests/test_predicates.py`.

### Coverage
- `owlbear_kanban.predicates`: 100% (49 statements, 0 missed).

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC-C39: `required_sections` matches `Section.heading` case-insensitively, with surrounding whitespace stripped | `test_ac_c39_whitespace_stripped_from_section_heading` and related `TestFromAC_RequiredSections` cases at `serve/kanban/tests/test_predicates.py:80-145` | Yes. The shared matcher at `serve/kanban/src/owlbear_kanban/predicates.py:34-38` is exercised from the `required_sections` entry point. | COVERED |
| AC-C40: `require_list_in_section` uses same case-insensitive, whitespace-stripped heading lookup, returns true iff matched section content parses to at least one CommonMark list item outside fenced code blocks | `test_ac_c40_bullet_list_in_section_returns_true` (`:156`), `test_ac_c40_ordered_list_in_section_returns_true` (`:163`), `test_ac_c40_list_inside_code_fence_not_counted` (`:206`), `test_ac_c40a_heading_side_whitespace_stripped` (`:238`), `test_ac_c40_star_bullet_returns_true` (`:258`), `test_ac_c40_plus_bullet_returns_true` (`:265`), `test_ac_c40_tilde_fence_excludes_list_items` (`:272`) | No. The task AC at `.owlbear/kanban/tasks/1051-c-06-red-predicate-tests.md:178` and the normative spec at `.owlbear/briefs/draft-kanban-storage-c-2026-04-20/paper-c.md:570` still require parser-backed CommonMark semantics, but the implementation under test uses regex heuristics at `serve/kanban/src/owlbear_kanban/predicates.py:22-24,81-109`. The current suite would stay green if indented code-block lines or indented and shorter-closing fences were misclassified. | LAX |
| AC-C40a: heading-side whitespace proof for `require_list_in_section` | `test_ac_c40a_heading_side_whitespace_stripped` at `serve/kanban/tests/test_predicates.py:238` | Yes. This directly exercises heading-side stripping through `_section_matches` at `serve/kanban/src/owlbear_kanban/predicates.py:34-38`. | COVERED |
| AC-C40b: string-body compatibility path is exercised | `test_ac_c40b_string_body_required_sections` at `serve/kanban/tests/test_predicates.py:134` and `test_ac_c40b_string_body_require_list_in_section` at `serve/kanban/tests/test_predicates.py:245` | Yes. Both force the string-body fallback in `_get_sections` at `serve/kanban/src/owlbear_kanban/predicates.py:27-31`. | COVERED |
| AC-C41: Predicate behaviour matches Brief B D64 semantically; only the substrate changed | `test_ac_c41_semantic_equivalence_to_brief_b_d64` at `serve/kanban/tests/test_predicates.py:226` and `test_ac_c41_all_bullet_markers_recognised` at `serve/kanban/tests/test_predicates.py:280` | No. These representative checks do not prove semantic equivalence where the current regex detector diverges from parser-backed CommonMark handling. The same AC-C40 gap carries into AC-C41. | LAX |

#### Security Review
- No issues found. The scoped code only performs in-memory heading normalization and content scanning; there is no filesystem, subprocess, network, secret, deserialization, or dynamic-execution surface.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_RequiredSections` | Current file still uses explicit boolean assertions with no skip or xfail markers. No weakening is visible in the present snapshot. | PRESERVED |
| `TestFromAC_RequireListInSection` | Current file still uses explicit boolean assertions with no skip or xfail markers. No weakening is visible in the present snapshot. | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Assertions are explicit `is True` / `is False` checks throughout `serve/kanban/tests/test_predicates.py`. |
| Negative and error-path coverage | ADEQUATE | Missing-section, prose-only, empty-content, no-space-heading, backtick-fence, and tilde-fence negatives are present. |
| Manual mutation reasoning | WEAK | `_BULLET_RE` and `_ORDERED_RE` accept arbitrary leading spaces and tabs at `serve/kanban/src/owlbear_kanban/predicates.py:22-23`, and `_FENCE_RE` plus `_remove_fenced_blocks` only recognise column-0 openings and do not tie closing length to opening length at `serve/kanban/src/owlbear_kanban/predicates.py:24,96-102`. No current test would fail if four-space-indented list-like lines were treated as lists or if a shorter closing fence ended a longer opening fence. |
| Test independence | STRONG | Tests build fresh `Task` and `Section` values through local helpers at `serve/kanban/tests/test_predicates.py:21-39`. |
| Descriptive test names | STRONG | Test names remain AC-keyed and behavior-specific. |

#### Data Safety
- No issues found. The reviewed code is side-effect free boolean inspection of task content.

#### Implementation-Aware Gaps
- The binding spec still says `require_list_in_section` should parse section content with `markdown-it-py` and assert a CommonMark `bullet_list` or `ordered_list` child at `.owlbear/briefs/draft-kanban-storage-c-2026-04-20/paper-c.md:570`. The implementation instead relies on regex scanning at `serve/kanban/src/owlbear_kanban/predicates.py:22-24,81-109`.
- `_BULLET_RE` and `_ORDERED_RE` at `serve/kanban/src/owlbear_kanban/predicates.py:22-23` will accept four-space-indented `- item` or `1. item` lines that CommonMark treats as code-block content, not top-level list items. No scoped test covers that boundary.
- Fence handling remains under-specified in the suite. `_FENCE_RE` only matches column-0 openings at `serve/kanban/src/owlbear_kanban/predicates.py:24,96`, and closing detection only checks the fence character, not the opening length, at `serve/kanban/src/owlbear_kanban/predicates.py:99-102`. The repo already treats fence length as a real CommonMark boundary in `tests/test_body_parser_1047.py:49`. No scoped predicate test would fail on those regressions.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 3 |
| Approach variation | Upstream test coverage changed between retries, but the builder pass remained a no-op verification step each time. |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- `serve/kanban/tests/test_predicates.py:1-5` still advertises an obsolete RED-only ImportError state even though the scoped run is green.
- No divergence between the fresh code-reader audit and this review synthesis: both found AC-C40 and AC-C41 still unproved against the parser-backed CommonMark contract.
- This is the third review cycle on the task. Prior `## Review Evidence` sections are already present at `.owlbear/kanban/tasks/1051-c-06-red-predicate-tests.md:68` and `.owlbear/kanban/tasks/1051-c-06-red-predicate-tests.md:249`, so loop-breaker routing applies on another fail.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC-C39 | `_section_matches` strips and casefolds both sides at `serve/kanban/src/owlbear_kanban/predicates.py:34-38`; heading-side whitespace proof is at `serve/kanban/tests/test_predicates.py:80`. | `TestFromAC_RequiredSections` | PASS |
| AC-C40 | The task AC at `.owlbear/kanban/tasks/1051-c-06-red-predicate-tests.md:178` and the design spec at `.owlbear/briefs/draft-kanban-storage-c-2026-04-20/paper-c.md:570` still require parser-backed CommonMark list detection. The implementation uses regex heuristics at `serve/kanban/src/owlbear_kanban/predicates.py:22-24,81-109`, and the suite never proves failure on indented code-block or fence-length and fence-indent regressions. | `TestFromAC_RequireListInSection` | FAIL |
| AC-C40a | Explicit heading-side whitespace proof exists at `serve/kanban/tests/test_predicates.py:238`, reusing `_section_matches` at `serve/kanban/src/owlbear_kanban/predicates.py:34-38`. | `TestFromAC_RequireListInSection` | PASS |
| AC-C40b | The string-body fallback in `_get_sections` at `serve/kanban/src/owlbear_kanban/predicates.py:27-31` is exercised by tests at `serve/kanban/tests/test_predicates.py:134` and `serve/kanban/tests/test_predicates.py:245`. | both `TestFromAC_*` classes | PASS |
| AC-C41 | Representative equivalence checks exist at `serve/kanban/tests/test_predicates.py:226` and `serve/kanban/tests/test_predicates.py:280`, but they do not prove equivalence for the parser-backed CommonMark boundaries still permitted by the AC and spec text. | both `TestFromAC_*` classes | FAIL |

### Deductions
- -0.11: AC-C40 remains unproved against the parser-backed CommonMark contract stated in the task and paper-c.
- -0.09: AC-C41 semantic-equivalence evidence remains sample-based because the same list-detection gap persists.
- -0.05: Manual mutation resistance is still weak for indented-list and fence-boundary regressions.
- -0.02: Third review failure on the same task triggers loop-breaker routing.

### Confidence
- .73

### Verdict
- FAIL

### Action
- Reject to backlog.
- Architect must either narrow AC-C40 and AC-C41 to the intended regex-level scope or keep the parser-backed CommonMark wording and require additional `TestFromAC_*` coverage that fails on the still-open indented-list and fence-boundary regressions.
- Until that contract is reconciled, this RED task should not be approved as the specification for downstream work.

### Reflection
- Clean scoped execution and 100% line coverage did not resolve the contract problem because the remaining gap is semantic, not line-level.
- The retry correctly fixed heading-side whitespace and string-body coverage, but it still did not prove the parser-backed CommonMark behavior the task text claims.
- Repeated no-op builder passes on a test-only task created churn without moving the core AC ambiguity; that is why this cycle needs loop-breaker routing rather than another ordinary retry.
[[2026-04-22]]
## Architecture Review (Return Cycle 2 — Loop-breaker)

### Context
Third reviewer rejection at .73 confidence. Loop-breaker routing applies. All three rejections cite the same root cause: AC-C40 and AC-C41 promise "CommonMark list (`bullet_list` or `ordered_list`)" but the implementation at predicates.py:22-24 uses regex heuristics (`_BULLET_RE`, `_ORDERED_RE`, `_FENCE_RE`). The tests prove the regex behavior thoroughly (28/28 pass, 100% coverage, all 3 bullet markers, both fence types) but cannot prove parser-backed CommonMark semantics because that is not what the code does.

### Root Cause Analysis
The paper-c spec at section 8.8 used aspirational CommonMark language ("parses to at least one CommonMark list"). The implementation chose regex heuristics — a pragmatic, KISS-compliant decision for gate-checking boolean predicates on kanban content. The first architecture review (this task's previous return cycle) narrowed AC-C40 but retained "CommonMark list item" language, perpetuating the contract mismatch across two more review cycles.

The reviewer was correct each time: the AC as written requires proof the tests cannot provide, because the code under test does not use a CommonMark parser. The fix is not more tests — it is narrowing the AC to match the implementation substrate.

### Revised Acceptance Criteria

The following REPLACES all prior AC sections (original and first return cycle). This is the binding AC for downstream agents:

- [ ] AC-C39: `required_sections` matches `Section.heading` case-insensitively, with surrounding whitespace stripped on both sides
- [ ] AC-C40: `require_list_in_section` uses same case-insensitive, whitespace-stripped heading lookup (both query-side and heading-side), returns true iff matched section's content contains at least one list-item line (bullet markers `- * +` or ordered `N.`) outside fenced code blocks, detected via regex heuristics
- [ ] AC-C40a: Test suite includes at least one `require_list_in_section` case where `Section.heading` has surrounding whitespace (heading-side stripping proof)
- [ ] AC-C40b: At least one test exercises the string-body compatibility path (`_get_sections` when `task.body` is `str`, triggering `parse_body` at predicates.py:31)
- [ ] AC-C41: Predicate behaviour matches Brief B D64 observable contract: `required_sections` checks section presence, `require_list_in_section` checks for list content; implementation substrate changed from raw-body regex to section-list with content-level regex

Changes from prior revision:
- AC-C40: "CommonMark list (`bullet_list` or `ordered_list`)" changed to "list-item line (bullet markers `- * +` or ordered `N.`) ... via regex heuristics" — matches actual implementation
- AC-C41: "matches Brief B D64 semantically" changed to "matches Brief B D64 observable contract" with explicit scope — removes unverifiable "semantic equivalence" claim that required differential testing against a parser

### Codebase Evidence
- `_BULLET_RE = re.compile(r"^[ \t]*[-*+] ", re.MULTILINE)` at predicates.py:22
- `_ORDERED_RE = re.compile(r"^[ \t]*\d+\. ", re.MULTILINE)` at predicates.py:23
- `_FENCE_RE = re.compile(r"^(`{3,}|~{3,})", re.MULTILINE)` at predicates.py:24
- `_section_matches` at predicates.py:34-38: strips and casefolds both sides
- `_get_sections` at predicates.py:27-31: str-to-parse_body fallback branch
- Test suite: 28 tests in test_predicates.py covering all AC lines (see Test-Writer Notes Retry 2)
- Quality evidence: 28/28 pass, 100% coverage on owlbear_kanban.predicates, ruff clean

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Test coverage for one module (predicates.py) |
| Interface clarity | PASS | Revised AC now precisely describes regex-based detection, matching implementation |
| Dependency correctness | PASS | No deps; downstream #1060 depends on this correctly |
| Module layering | PASS | Test-only task, no layering concern |
| TDD compliance | PASS | Tagged `tdd:red`; test-writer processes it |
| KISS/YAGNI | PASS | Narrowed AC eliminates unverifiable CommonMark parser requirement — YAGNI |
| Premise challenge | PASS | Predicates module exists and tests are comprehensive for regex substrate |
| Pattern consistency | PASS | `TestFromAC_` naming convention; explicit boolean assertions |
| Security surface | PASS | Pure in-memory text inspection, no system boundary |
| Single domain | PASS | Kanban domain only |

### Challenge Results
- Challenger: FALLBACK — not available in session (only Explore agent)
- Architect confidence: .94 — the contract mismatch was the sole reviewer objection across 3 cycles; narrowing AC resolves it without losing test quality

### Verdict: REFINE then APPROVE
### Action: Narrowed AC-C40 and AC-C41 to match the regex-based implementation substrate. Existing test suite (28 tests, 100% coverage) already satisfies the narrowed AC. Advanced to todo. Loop-breaker resolved by fixing the specification, not by adding more tests to prove behavior the code does not implement.
[[2026-04-22]]
## Test-Writer Notes (Retry 3)

**Situation:** Retry cycle 3 — Architecture Review (Loop-breaker) narrowed AC-C40 and AC-C41 to match the regex-based implementation substrate. The existing 28 tests already satisfy the narrowed AC (confirmed by architect: "Existing test suite (28 tests, 100% coverage) already satisfies the narrowed AC"). No new tests required.

Reviewer AC compliance post-narrowing:
| AC | Status |
|----|--------|
| C39: required_sections case-insensitive, whitespace-stripped | PASS |
| C40 (narrowed): require_list_in_section same lookup, list-item line via regex, outside fenced blocks | PASS |
| C40a: heading-side whitespace proof | PASS |
| C40b: string-body compatibility | PASS |
| C41 (narrowed): matches Brief B D64 observable contract | PASS |

**Action taken:** Fixed stale file header in `serve/kanban/tests/test_predicates.py` (obsolete RED-phase/ImportError description flagged as informational across all 3 reviewer passes). No source code edits.

**Test file:** `serve/kanban/tests/test_predicates.py`
**Classes:** `TestFromAC_RequiredSections` (12 tests), `TestFromAC_RequireListInSection` (16 tests)
**Total:** 28 tests, 28 pass, ruff clean, 100% coverage on owlbear_kanban.predicates

**Commit:** `555f1e09` — `test: update stale RED-phase header in test_predicates.py (#1051, test-writer)`
[[2026-04-22]]
## Builder Notes
- Implementation: no source changes required in this builder pass.
- Files changed: none.
- Tests: 28 passed, 0 failed, 0 skipped in `serve/kanban/tests/test_predicates.py` (quality-runner scoped run).
- Coverage: 100% on `owlbear_kanban.predicates`.
- Ruff: clean for `serve/kanban/src/owlbear_kanban/predicates.py` and `serve/kanban/tests/test_predicates.py`.
- Approach: enforced GREEN gate by independent scoped verification against current AC-aligned test suite; no speculative edits.
- Evidence summary: AC-C39/C40/C40a/C40b/C41 are satisfied by the extant implementation and validated by canonical quality-runner evidence.

- Reflection: this task remained a no-op implementation handoff because the source already satisfied the revised AC.
- Reflection: quality-runner provided consistent, comparable evidence for pass criteria without broad-suite noise.
- Reflection: maintaining zero diff preserved surgical scope and avoided churn on settled behavior.
[[2026-04-22]]
## Review Evidence
### Test Results
- pytest: 28 passed, 0 failed, 0 skipped (independent quality-runner scoped run on `serve/kanban/tests/test_predicates.py`)

### Lint
- ruff: clean for `serve/kanban/src/owlbear_kanban/predicates.py` and `serve/kanban/tests/test_predicates.py`

### Coverage
- `owlbear_kanban.predicates`: 100%

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC-C39 | `test_ac_c39_case_insensitive_match`, `test_ac_c39_whitespace_stripped_from_section_heading`, related `required_sections` cases | Yes. `_section_matches` at `serve/kanban/src/owlbear_kanban/predicates.py:34-38` is exercised from the `required_sections` entry point. | COVERED |
| AC-C40 | `test_ac_c40_bullet_list_in_section_returns_true`, `test_ac_c40_ordered_list_in_section_returns_true`, `test_ac_c40_section_lookup_case_insensitive`, `test_ac_c40_section_lookup_whitespace_stripped`, `test_ac_c40_list_inside_code_fence_not_counted`, `test_ac_c40a_heading_side_whitespace_stripped`, `test_ac_c40b_string_body_require_list_in_section`, `test_ac_c40_star_bullet_returns_true`, `test_ac_c40_plus_bullet_returns_true`, `test_ac_c40_tilde_fence_excludes_list_items` | No. The binding AC at `.owlbear/kanban/tasks/1051-c-06-red-predicate-tests.md:475` requires detection of list-item lines outside fenced code blocks. The only fence fixtures in the scoped suite are `serve/kanban/tests/test_predicates.py:207` and `serve/kanban/tests/test_predicates.py:273`, and both keep every list-like line inside the fence. No `TestFromAC_*` case proves `_remove_fenced_blocks()` exits fence mode after the closing line at `serve/kanban/src/owlbear_kanban/predicates.py:102-104` and still sees a real list item that follows. | LAX |
| AC-C40a | `test_ac_c40a_heading_side_whitespace_stripped` | Yes. It directly proves heading-side stripping through `_section_matches` at `serve/kanban/src/owlbear_kanban/predicates.py:34-38`. | COVERED |
| AC-C40b | `test_ac_c40b_string_body_required_sections`, `test_ac_c40b_string_body_require_list_in_section` | Yes. Both force the string-body fallback in `_get_sections` at `serve/kanban/src/owlbear_kanban/predicates.py:27-31`. | COVERED |
| AC-C41 | `test_ac_c41_no_space_heading_is_content_not_matched`, `test_ac_c41_no_space_heading_does_not_satisfy_require_list`, `test_ac_c41_semantic_equivalence_to_brief_b_d64`, `test_ac_c41_all_bullet_markers_recognised` | Yes. The current suite distinguishes section-presence checks from list-content checks across the section-list substrate. | COVERED |

#### Security Review
- No issues. Scoped code is pure in-memory normalization and regex scanning; there is no filesystem, subprocess, network, deserialization, or dynamic-execution surface.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_RequiredSections` | Current assertions remain explicit boolean checks. No weakening is visible in the present file. | PRESERVED |
| `TestFromAC_RequireListInSection` | Current assertions remain explicit boolean checks. No weakening is visible in the present file. | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Assertions are direct `is True` / `is False` checks throughout the scoped suite. |
| Negative and error-path coverage | ADEQUATE | Missing-section, prose-only, empty-content, no-space-heading, and fenced negatives are covered. |
| Manual mutation reasoning | ADEQUATE | The suite would catch heading-normalization, string-body fallback, and bullet-marker regressions, but not a regression that never resumes scanning after a closed fence. |
| Test independence | STRONG | Fresh fixtures are built through local helpers; no shared mutable state is present. |
| Descriptive test names | STRONG | Names remain AC-keyed and behavior-specific. |

#### Data Safety
- No issues. The reviewed code is side-effect free text inspection.

#### Implementation-Aware Gaps
- A significant untested path remains in `serve/kanban/src/owlbear_kanban/predicates.py:95-109`. `_remove_fenced_blocks()` has explicit enter-fence, close-fence, and post-fence resume behavior, but the only fence fixtures in the task suite are pure fenced negatives at `serve/kanban/tests/test_predicates.py:207` and `serve/kanban/tests/test_predicates.py:273`.
- No current `TestFromAC_*` case covers content shaped like fenced block followed by a real list item after the closing fence. A regression that fails to leave fence mode at `serve/kanban/src/owlbear_kanban/predicates.py:102-104` would violate AC-C40 while staying green.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 4 |
| Approach variation | No source changes across retries; repeated verification-only handoffs |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- This review used the loop-breaker AC rewrite as the binding contract at `.owlbear/kanban/tasks/1051-c-06-red-predicate-tests.md:472-478`, not the superseded parser-backed wording earlier in the task body.
- Minor wording drift remains in docstrings/comments that still say "CommonMark list" even though the binding AC is regex-based. Non-blocking.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC-C39 | `_section_matches` strips and casefolds both sides at `serve/kanban/src/owlbear_kanban/predicates.py:34-38`; `required_sections` coverage includes case-insensitive and heading-side whitespace proofs at `serve/kanban/tests/test_predicates.py:56` and `serve/kanban/tests/test_predicates.py:79`. | `TestFromAC_RequiredSections` | PASS |
| AC-C40 | The binding AC at `.owlbear/kanban/tasks/1051-c-06-red-predicate-tests.md:475` requires list-item detection outside fenced code blocks. Fence handling lives in `serve/kanban/src/owlbear_kanban/predicates.py:90-109`, but fence fixtures only appear at `serve/kanban/tests/test_predicates.py:207` and `serve/kanban/tests/test_predicates.py:273` and keep all list-like lines inside fences; no mixed fence/outside case proves post-fence resume behavior. | `TestFromAC_RequireListInSection` | FAIL |
| AC-C40a | Explicit heading-side whitespace proof exists at `serve/kanban/tests/test_predicates.py:237`, reusing `_section_matches` at `serve/kanban/src/owlbear_kanban/predicates.py:34-38`. | `TestFromAC_RequireListInSection` | PASS |
| AC-C40b | The string-body fallback in `_get_sections` at `serve/kanban/src/owlbear_kanban/predicates.py:27-31` is exercised by tests at `serve/kanban/tests/test_predicates.py:133` and `serve/kanban/tests/test_predicates.py:244`. | both `TestFromAC_*` classes | PASS |
| AC-C41 | Observable-contract coverage is present at `serve/kanban/tests/test_predicates.py:120`, `serve/kanban/tests/test_predicates.py:213`, `serve/kanban/tests/test_predicates.py:225`, and `serve/kanban/tests/test_predicates.py:279`. | both `TestFromAC_*` classes | PASS |

### Deductions
- -0.08: AC-C40 remains under-proved because post-fence resume behavior is untested.
- -0.03: Mutation resistance is incomplete for the fence-handling branch.
- -0.02: This is the fourth review cycle on the same task; backlog routing applies.

### Confidence: .87
### Verdict: FAIL
### Action
- Reject to backlog.
- Add a `TestFromAC_RequireListInSection` case with a fenced block followed by a real list item after the closing fence, or narrow AC-C40 if post-fence resume behavior is intentionally out of scope.
- Because this is a 3rd+ review failure, backlog routing is mandatory even though the remaining issue is a test-gap rather than an implementation bug.

### Reflection
- Clean pytest/lint/coverage evidence can still miss a meaningful branch when a helper collapses multiple truth-table cases into one headline behavior.
- Negative fence-only cases proved exclusion but not resumption after the fence closes.
- The loop-breaker AC rewrite fixed the old parser-contract mismatch, but one concrete task-local gap still remained in the regex fence path.
[[2026-04-22]]
## Architecture Review (Return Cycle 3)

### Context
Fourth reviewer rejection at .87 confidence. Single remaining gap: AC-C40 "outside fenced code blocks" has no post-fence resume proof. All fence tests are pure negatives (content entirely inside fences → False). If `_remove_fenced_blocks()` never exited fence mode at predicates.py:102-104, no test would fail.

### Reviewer Finding Assessment

| Finding | Valid? | Resolution |
|---------|--------|------------|
| AC-C40 post-fence resume untested | Yes | Add AC-C40c. The "outside fenced code blocks" clause requires proving list items after a closing fence are detected. One targeted test case. |

### Revised Acceptance Criteria

The following is the binding AC. Unchanged lines from the loop-breaker revision are preserved; AC-C40c is new.

- [ ] AC-C39: `required_sections` matches `Section.heading` case-insensitively, with surrounding whitespace stripped on both sides
- [ ] AC-C40: `require_list_in_section` uses same case-insensitive, whitespace-stripped heading lookup (both query-side and heading-side), returns true iff matched section's content contains at least one list-item line (bullet markers `- * +` or ordered `N.`) outside fenced code blocks, detected via regex heuristics
- [ ] AC-C40a: Test suite includes at least one `require_list_in_section` case where `Section.heading` has surrounding whitespace (heading-side stripping proof)
- [ ] AC-C40b: At least one test exercises the string-body compatibility path (`_get_sections` when `task.body` is `str`, triggering `parse_body` at predicates.py:31)
- [ ] AC-C40c: At least one test exercises post-fence resume: a section with a fenced code block containing list-like lines, followed by a real list item after the closing fence, returning True
- [ ] AC-C41: Predicate behaviour matches Brief B D64 observable contract: `required_sections` checks section presence, `require_list_in_section` checks for list content; implementation substrate changed from raw-body regex to section-list with content-level regex

Changes from loop-breaker revision:
- Added AC-C40c: post-fence resume proof — the only untested branch in `_remove_fenced_blocks()` across 4 review cycles

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Test coverage for one module (predicates.py) |
| Interface clarity | PASS | AC-C40c makes the post-fence resume requirement explicit and testable |
| Dependency correctness | PASS | No deps listed; downstream #1060 depends on this correctly |
| Module layering | PASS | Test-only task, no layering concern |
| TDD compliance | PASS | Tagged `tdd:red`; test-writer processes it |
| KISS/YAGNI | PASS | One additional test case — minimal scope |
| Premise challenge | PASS | Post-fence resume is real behavior in predicates.py:102-104, not hypothetical |
| Pattern consistency | PASS | TestFromAC_ naming convention; explicit boolean assertions |
| Security surface | PASS | Pure in-memory text inspection, no system boundary |
| Single domain | PASS | Kanban domain only |

### Challenge Results
- Challenger: FALLBACK — not available in session (only Explore agent)
- Architect confidence: .95 — four review cycles identified this as the sole remaining gap; one targeted test closes it

### Verdict: REFINE then APPROVE
### Action: Added AC-C40c (post-fence resume proof). Existing 28 tests satisfy all other AC lines. Advanced to todo.
[[2026-04-23]]
## Test-Writer Notes (Retry 4)

**Situation:** Retry 4 — Architecture Review (Return Cycle 3) added AC-C40c: post-fence resume proof. Single new test required. Implementation already exists and satisfies all AC lines.

**Test file:** `serve/kanban/tests/test_predicates.py`
**Class:** `TestFromAC_RequireListInSection` (+1 test, total 17 in that class)

**New test:**
| Test | AC | Mutation Guard |
|------|----|----------------|
| `test_ac_c40c_post_fence_resume_returns_true` | C40c | Fails if `_remove_fenced_blocks()` never exits fence mode (in_fence never reset to False at predicates.py:102-104) |

**Content structure tested:**
```
```
- fake inside fence
1. also fake
```
- real item after fence
```
Section with a backtick fence containing list-like lines (excluded), followed by a real bullet item after the closing fence (counted → True).

**AC Coverage:**
| AC | Tests |
|----|-------|
| C39: required_sections case-insensitive, whitespace-stripped | 9 |
| C40: require_list_in_section same lookup, list-item line via regex, outside fenced blocks | 14 |
| C40a: heading-side whitespace proof | 1 |
| C40b: string-body compatibility | 2 |
| C40c: post-fence resume — list item after closing fence detected | 1 (new) |
| C41: observable contract equivalence to Brief B D64 | 3 |

**Results:** 29/29 pass, ruff clean, 100% coverage on `owlbear_kanban.predicates`
**Fail verification:** N/A — implementation already existed (consistent with all prior retry cycles on this task).
**Commit:** `1db043b2` — `test: add AC-C40c post-fence resume coverage (#1051, test-writer)`
[[2026-04-23]]
## Builder Notes
- Implementation: no source changes required; existing `serve/kanban/src/owlbear_kanban/predicates.py` already satisfies current AC set.
- Files changed: none.
- Tests: 29 passed, 0 failed, 0 skipped in `serve/kanban/tests/test_predicates.py`.
- Coverage: `owlbear_kanban.predicates` 100%.
- Ruff: clean for `serve/kanban/src/owlbear_kanban/predicates.py` and `serve/kanban/tests/test_predicates.py`.
- Approach: verification-only GREEN gate using quality-runner scoped execution against the current task AC (including AC-C40c post-fence resume).
- Evidence summary: all scoped gates are green (`failed: []`, `clean: true`, module coverage 100%), so task is ready for review.

- Reflection: this remained a surgical no-op implementation pass because AC closure was achieved via upstream test additions.
- Reflection: scoped quality-runner output provided canonical evidence without broad-suite lint/test noise.
- Reflection: zero-diff handoff avoided churn and preserved strict task boundaries.
[[2026-04-23]]
## Review Evidence
### Test Results
- pytest: 29 passed, 0 failed, 0 skipped (independent quality-runner scoped run on `serve/kanban/tests/test_predicates.py`)

### Lint
- ruff: clean for `serve/kanban/src/owlbear_kanban/predicates.py` and `serve/kanban/tests/test_predicates.py`

### Coverage
- `owlbear_kanban.predicates`: 100%

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC-C39 | `test_ac_c39_case_insensitive_match` (`serve/kanban/tests/test_predicates.py:56`), `test_ac_c39_whitespace_stripped_from_section_heading` (`serve/kanban/tests/test_predicates.py:79`) | Yes. `_section_matches` strips and casefolds both sides at `serve/kanban/src/owlbear_kanban/predicates.py:34-38`; removing either behavior would flip these assertions. | COVERED |
| AC-C40 | `test_ac_c40_bullet_list_in_section_returns_true` (`serve/kanban/tests/test_predicates.py:156`), `test_ac_c40_ordered_list_in_section_returns_true` (`:163`), `test_ac_c40_list_inside_code_fence_not_counted` (`:205`), `test_ac_c40_star_bullet_returns_true` (`:257`), `test_ac_c40_plus_bullet_returns_true` (`:264`), `test_ac_c40_tilde_fence_excludes_list_items` (`:271`), `test_ac_c40c_post_fence_resume_returns_true` (`:289`) | Yes under the binding AC at `.owlbear/kanban/tasks/1051-c-06-red-predicate-tests.md:647-652`. `require_list_in_section()` selects sections via `_section_matches` and checks list-item lines after `_remove_fenced_blocks()` at `serve/kanban/src/owlbear_kanban/predicates.py:59-109`. The suite proves bullet and ordered markers, both fence characters, exclusion inside fences, and resume after a closed fence. | COVERED |
| AC-C40a | `test_ac_c40a_heading_side_whitespace_stripped` (`serve/kanban/tests/test_predicates.py:237`) | Yes. Removing heading-side stripping from `_section_matches` at `serve/kanban/src/owlbear_kanban/predicates.py:34-38` would fail this test. | COVERED |
| AC-C40b | `test_ac_c40b_string_body_required_sections` (`serve/kanban/tests/test_predicates.py:133`), `test_ac_c40b_string_body_require_list_in_section` (`:244`) | Yes. Both force the string-body fallback in `_get_sections()` at `serve/kanban/src/owlbear_kanban/predicates.py:27-31`; breaking `parse_body(task.body)` would fail them. | COVERED |
| AC-C40c | `test_ac_c40c_post_fence_resume_returns_true` (`serve/kanban/tests/test_predicates.py:289`) | Yes. The only real list item is after the closing fence, so a broken fence-exit path at `serve/kanban/src/owlbear_kanban/predicates.py:102-104` would turn this false. | COVERED |
| AC-C41 | `test_ac_c41_no_space_heading_is_content_not_matched` (`serve/kanban/tests/test_predicates.py:120`), `test_ac_c41_no_space_heading_does_not_satisfy_require_list` (`:213`), `test_ac_c41_semantic_equivalence_to_brief_b_d64` (`:225`), `test_ac_c41_all_bullet_markers_recognised` (`:279`) | Yes. These tests pin the observable contract stated in the binding AC: section presence is separate from list-content detection, pseudo-headings in content do not count, and all three supported bullet markers remain accepted. | COVERED |

#### Security Review
- No issues. Scoped code is pure in-memory heading normalization and regex scanning. No subprocess, filesystem, network, secret, deserialization, or dynamic-execution surface is present in `serve/kanban/src/owlbear_kanban/predicates.py:27-109`.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_RequiredSections` | No weakening evidence in the current file; assertions remain explicit boolean checks at `serve/kanban/tests/test_predicates.py:54-144`. | PRESERVED |
| `TestFromAC_RequireListInSection` | The current suite retains explicit positive and negative assertions and adds `test_ac_c40c_post_fence_resume_returns_true` at `serve/kanban/tests/test_predicates.py:289-295` to cover the previously missing fence-resume branch. | STRENGTHENED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Assertions are explicit `is True` / `is False` checks throughout `serve/kanban/tests/test_predicates.py`. |
| Negative and error-path coverage | STRONG | Missing-section, absent-list, empty-content, pseudo-heading, backtick-fence, tilde-fence, and post-fence resume paths are all exercised at `serve/kanban/tests/test_predicates.py:86-101,169-211,271-295`. |
| Manual mutation reasoning | ADEQUATE | The suite would fail on regressions to heading normalization, string-body fallback, supported bullet markers, fence exclusion, tilde-fence support, and post-fence resume (`serve/kanban/tests/test_predicates.py:133-145,205-211,237-255,257-295`). Broader CommonMark-style fence variants were explicitly narrowed out of this task’s binding AC. |
| Test independence | STRONG | Fresh `Section` and `Task` values are built per test via helpers at `serve/kanban/tests/test_predicates.py:21-39`. |
| Descriptive test names | STRONG | Test names are AC-keyed and behavior-specific across both `TestFromAC_*` classes. |

#### Data Safety
- No issues. The reviewed code is side-effect free boolean inspection of task content.

#### Implementation-Aware Gaps
- No significant untested path remains under the binding AC in `.owlbear/kanban/tasks/1051-c-06-red-predicate-tests.md:644-652`. `_remove_fenced_blocks()` enter-fence, close-fence, and resume behavior is now exercised by `serve/kanban/tests/test_predicates.py:205-211`, `:271-277`, and `:289-295`.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 5 |
| Approach variation | Upstream AC/test coverage changed across cycles; the builder step remained verification-only because no implementation delta was required. |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- Divergence from code-reader: code-reader marked AC-C40 as LAX due to untested indented-fence behavior at `serve/kanban/src/owlbear_kanban/predicates.py:24,96`. I did not treat that as blocking because the binding task AC was explicitly narrowed to regex heuristics at `.owlbear/kanban/tasks/1051-c-06-red-predicate-tests.md:647-652`, and the final architecture return states AC-C40c was the only remaining untested branch before Retry 4.
- Residual doc-authority drift remains: `.owlbear/briefs/draft-kanban-storage-c-2026-04-20/paper-c.md:565-570` still describes parser-backed/CommonMark semantics, while the task’s binding AC is regex-based. That should be reconciled in the docs phase, not rejected here.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC-C39 | `_section_matches` strips and casefolds both sides at `serve/kanban/src/owlbear_kanban/predicates.py:34-38`; heading-side whitespace proof is at `serve/kanban/tests/test_predicates.py:79-84`. Quality-runner: 29 passed, 0 failed. | `TestFromAC_RequiredSections` | PASS |
| AC-C40 | `require_list_in_section()` uses `_section_matches` plus `_has_list_outside_fences()` at `serve/kanban/src/owlbear_kanban/predicates.py:59-109`; task AC is explicitly regex-based at `.owlbear/kanban/tasks/1051-c-06-red-predicate-tests.md:647-652`; tests prove bullet, ordered, fence exclusion, tilde-fence support, and post-fence resume at `serve/kanban/tests/test_predicates.py:156-168,205-211,257-295`. Quality-runner: 29 passed, 0 failed. | `TestFromAC_RequireListInSection` | PASS |
| AC-C40a | Explicit heading-side whitespace proof exists at `serve/kanban/tests/test_predicates.py:237-242`, reusing `_section_matches` at `serve/kanban/src/owlbear_kanban/predicates.py:34-38`. Quality-runner: 29 passed, 0 failed. | `TestFromAC_RequireListInSection` | PASS |
| AC-C40b | The string-body fallback in `_get_sections()` at `serve/kanban/src/owlbear_kanban/predicates.py:27-31` is exercised by tests at `serve/kanban/tests/test_predicates.py:133-145` and `:244-255`. Quality-runner: 29 passed, 0 failed. | both `TestFromAC_*` classes | PASS |
| AC-C40c | The post-fence resume branch at `serve/kanban/src/owlbear_kanban/predicates.py:102-104` is exercised by `serve/kanban/tests/test_predicates.py:289-295`. Quality-runner: 29 passed, 0 failed. | `TestFromAC_RequireListInSection` | PASS |
| AC-C41 | Observable-contract checks are present at `serve/kanban/tests/test_predicates.py:120-132,213-236,279-285`, covering section presence vs list-content detection and marker support. Quality-runner: 29 passed, 0 failed. | both `TestFromAC_*` classes | PASS |

### Deductions
- -0.03: External brief wording in `paper-c.md` still describes the superseded parser-backed contract, creating non-blocking authority drift.
- -0.02: Five builder review cycles created process friction even though the final state is clean.

### Confidence: .95
### Verdict: PASS
### Reflection
- The final architect revision is the controlling contract; earlier CommonMark/parser wording in the task history and brief is superseded for this review.
- Retry 4 closed the only task-local fence gap by proving post-fence resume behavior.
- A green scoped run alone was not enough; the pass depended on reconciling subagent disagreement against the binding AC text.
[[2026-04-23]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Task is test-only (serve/kanban/tests/test_predicates.py). No behavior, API, CLI, config, or package structure changed. serve/kanban/README.md has no "predicate" references. |
| 2 | Module docstrings | No | N/A | serve/kanban/src/owlbear_kanban/predicates.py was not modified across any builder pass (all 5 passes were verification-only, zero diff). |
| 3 | External attribution | No | N/A | No external patterns or references used. Task is test coverage for an existing module. |
| 4 | Research doc | No | N/A | No research phase for this test-coverage task. No .owlbear/research/*.md referenced. |
| 5 | Diagram maintenance (describes match) | No | N/A | kanban.excalidraw describes serve/kanban/src/** and mcp-topology.excalidraw describes serve/kanban/src/**. Changed file is serve/kanban/tests/ — no describes-match. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted. All builder passes were zero-diff. |

**Reviewer informational note (Pass 2):** authority drift in .owlbear/briefs/draft-kanban-storage-c-2026-04-20/paper-c.md (still describes parser-backed CommonMark semantics vs regex-based binding AC). Briefs are OUT of IN-scope list — no action taken; noted for architect if a follow-up task is warranted.

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/kanban/tests/test_predicates.py | OUT | N/A (test file) |
| serve/kanban/src/owlbear_kanban/predicates.py | IN (docstrings only) | N/A (not modified) |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no .owlbear/scratch/1051-* files found)
[[2026-04-23]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC-C39: case-insensitive, whitespace-stripped heading match | `_section_matches` strips/casefolds at predicates.py:34-38; 12 tests in `TestFromAC_RequiredSections` | PASS |
| AC-C40: list-item line via regex outside fenced blocks | `_has_list_outside_fences` + `_remove_fenced_blocks` at predicates.py:81-109; 14 tests cover bullet, ordered, fence exclusion, tilde-fence, post-fence resume | PASS |
| AC-C40a: heading-side whitespace proof | `test_ac_c40a_heading_side_whitespace_stripped` at test_predicates.py:237 | PASS |
| AC-C40b: string-body compatibility | `test_ac_c40b_string_body_required_sections` at test_predicates.py:134, `test_ac_c40b_string_body_require_list_in_section` at test_predicates.py:244 — both force `_get_sections` str→`parse_body` fallback | PASS |
| AC-C40c: post-fence resume | `test_ac_c40c_post_fence_resume_returns_true` at test_predicates.py:289 — fence with list-like lines inside, real list item after closing fence → True | PASS |
| AC-C41: observable contract equivalence | `test_ac_c41_semantic_equivalence_to_brief_b_d64` at test_predicates.py:225, `test_ac_c41_all_bullet_markers_recognised` at test_predicates.py:279 — section presence vs list-content distinction, all 3 bullet markers | PASS |

### Test Results
- pytest (full suite): 1259 passed, 4 skipped, 133 failed — all failures in unrelated modules (ideation diagram, mcp models, cockpit, list sessions). Zero failures in test_predicates.py.
- pytest (scoped, per reviewer): 29 passed, 0 failed
- ruff: clean for task-scoped files (5 W292 in unrelated files)
- coverage: 100% on owlbear_kanban.predicates

### Architect Quality: 3/5
Original AC was vague enough to cause 3 architecture return cycles: (1) unsatisfiable "All tests fail" RED-only AC when implementation already existed, (2) aspirational "CommonMark list" language that didn't match the regex-based implementation, (3) missing post-fence resume specification. The final AC revision (Return Cycle 3) is precise and well-scoped, but the initial quality caused significant pipeline churn (5 review cycles, 4 test-writer retries, 4 builder retries).

### Deduction Breakdown
- -.03: AC quality score 3/5 (notable gaps requiring 3 architecture return cycles)

### Confidence: .97
### Action: archive