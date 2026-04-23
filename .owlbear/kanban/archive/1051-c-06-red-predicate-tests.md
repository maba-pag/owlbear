---
id: 1051
title: 'C-06: RED — predicate tests'
status: in-progress
priority: important
created: 2026-04-21T10:42:50.287239+00:00
updated: 2026-04-22T05:09:55.075271+00:00
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