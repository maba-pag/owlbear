---
id: 1047
title: 'C-02: RED — body_parser round-trip tests'
status: in-progress
priority: needed
created: 2026-04-21T10:42:50.247058+00:00
updated: 2026-04-21T21:46:29.166991+00:00
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
---
## Brief
Brief C (#1043) — paper-c.md §8.2, §8.11
Module: `serve/kanban/tests/test_body_parser.py`

## Acceptance Criteria

- [ ] AC-C5: `parse_body(render_body(sections)) == sections` round-trip identity
- [ ] AC-C6: CRLF in input normalised to LF in `Section.content`
- [ ] AC-C7: `##Heading` (no space) preserved verbatim as content, never promoted to section boundary
- [ ] AC-C8: `## Heading` (with space) creates `Section(heading="Heading", level=2, ...)`
- [ ] AC-C9: Setext headings (`Heading\n===`) create level-1 sections
- [ ] AC-C10: Code-fenced content containing `## Looks-like-heading` does NOT create a section
- [ ] AC-C11: Trailing whitespace within section content preserved
- [ ] AC-C12: Inter-section blank lines preserved on round-trip
- [ ] AC-C53: Setext-heading input round-trips through write as ATX-heading output (same Section model)
- [ ] All tests fail (RED phase — no implementation exists yet)
[[2026-04-21]]
## Test-Writer Notes
- Test file: tests/test_body_parser_1047.py
- Classes: TestFromAC_BodyParserEdgeCases
- Tests per category: happy 0, edge 4, error 0, boundary 4 (all 4 tests are edge/boundary)
- Total: 4 tests, all FAIL
- ruff: clean

### AC Coverage
| AC | Test(s) |
|----|---------|
| C5 (round-trip identity) | test_ac_c5_roundtrip_atx_no_trailing_newline, test_ac_c5_roundtrip_preamble_no_trailing_newline |
| C10 (code-fence heading isolation) | test_ac_c10_five_backtick_fence_not_closed_by_three, test_ac_c10_five_tilde_fence_not_closed_by_three |

### Context
The module-level test_body_parser.py (committed earlier, de06fa41) already covers the happy-path ACs for C5–C12 and C53, but those tests all PASS because body_parser.py was implemented before this task was formally processed. This task-scoped file covers boundary conditions not exercised in the base suite:
1. **AC-C5 boundary**: render_body always appends a trailing `\n` when content lacks one; this breaks round-trip identity for inputs without a trailing newline.
2. **AC-C10 boundary**: The closing-fence regex uses `{3,}` regardless of opening-fence length; a 3-backtick/tilde line incorrectly closes a 5-backtick/tilde fence, leaking interior headings.

Both are confirmed bugs — all 4 tests fail with AssertionError on current implementation.
[[2026-04-21]]
## Builder Notes
- Implementation: updated serve/kanban/src/owlbear_kanban/body_parser.py to (1) preserve section content exactly in `render_body` (no forced trailing LF), and (2) require closing fence length >= opening fence length in `parse_body`.
- Tests: 4/4 `TestFromAC_BodyParserEdgeCases` tests now pass (`tests/test_body_parser_1047.py`).
- Regression check: module-level parser suite passes (21/21 in `serve/kanban/tests/test_body_parser.py`).
- Coverage: `body_parser` at 100% in scoped quality-runner verification.
- Ruff: clean for parser + both parser test files.
- Evidence summary: RED verified first (exact 4 failures matching AC-C5 and AC-C10 boundaries), then GREEN verified with zero failures after patch.

### Post-task Reflection
- Problem faced: parser fence-close regex only enforced `{3,}`, which allowed premature closure of longer fences.
- Workaround applied: tracked opening fence length and matched close with dynamic lower bound.
- Pattern discovered: round-trip identity requires writer neutrality; auto-normalizing trailing newlines in `render_body` breaks `parse(render(x)) == x` for no-trailing-LF inputs.
- Time sink: quality-runner path mapping required one correction to point module-level tests to `serve/kanban/tests/test_body_parser.py`.
- Quality gap: task-scoped coverage alone understated module confidence; adding module-level suite in the same scoped run provided full 100% evidence for the touched module.
[[2026-04-21]]
## Review Evidence
### Scope
- Reviewed implementation: serve/kanban/src/owlbear_kanban/body_parser.py
- Verified tests: tests/test_body_parser_1047.py and serve/kanban/tests/test_body_parser.py
- No public signature changes observed; downstream call sites remain serve/kanban/src/owlbear_kanban/storage.py:38 and serve/kanban/src/owlbear_kanban/predicates.py:31.

### Test Results
- quality-runner scoped verification: 25 passed, 0 failed, 0 skipped

### Lint
- Ruff clean
- Editor diagnostics: none in body_parser.py or the two parser test files

### Coverage
- owlbear_kanban.body_parser: 100%
- Scoped overall percentage reported as 21%; gating used the touched-module percentage above

### Pass 1 — CRITICAL
#### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC-C5 | Round-trip equality is asserted across happy-path and no-trailing-LF cases; render_body neutrality is exercised at body_parser.py:166-168 | serve/kanban/tests/test_body_parser.py:25,30,36,42,209; tests/test_body_parser_1047.py:23,34 | PASS |
| AC-C6 | Current tests only prove carriage returns disappear; they do not prove line breaks are preserved as LF after normalization at body_parser.py:51 | serve/kanban/tests/test_body_parser.py:54-69 | FAIL (LAX) |
| AC-C7 | No-space headings are blocked from promotion and preserved verbatim in content | serve/kanban/tests/test_body_parser.py:73-87 | PASS |
| AC-C8 | Heading text and levels are asserted directly for H2, H1, and H6 | serve/kanban/tests/test_body_parser.py:91-113 | PASS |
| AC-C9 | Setext level-1 and level-2 parsing is asserted directly | serve/kanban/tests/test_body_parser.py:117-131 | PASS |
| AC-C10 | Bare-fence, indented-code, and long-fence boundary cases all prevent interior heading promotion | serve/kanban/tests/test_body_parser.py:135-154; tests/test_body_parser_1047.py:46-83 | PASS |
| AC-C11 | Exact trailing-space preservation is asserted in section content | serve/kanban/tests/test_body_parser.py:158-165 | PASS |
| AC-C12 | The dedicated inter-section test uses a broad disjunction and does not pin the triple blank line to the section boundary implemented in body_parser.py:106-107, 119-120, 128-129 | serve/kanban/tests/test_body_parser.py:169-184 | FAIL (LAX) |
| AC-C53 | The render assertion only checks for substring '# My Heading', so a wrong heading level such as '## My Heading' would still pass; the second test does not exercise render_body | serve/kanban/tests/test_body_parser.py:190-205 | FAIL (LAX) |
| RED-phase fail evidence | Historical task-body evidence records 4 failing tests before the fix | .owlbear/kanban/tasks/1047-c-02-red-body-parser-round-trip-tests.md:37-55 | PASS |

#### Security Review
- PASS: body_parser.py is a pure in-memory regex/string parser with no filesystem, subprocess, network, deserialization, or secret-handling sinks in scope.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---|---|---|
| TestFromAC_BodyParserEdgeCases | Class and 4 AC-named methods remain present at tests/test_body_parser_1047.py:14,23,34,46,67; no skip or xfail found | PRESERVED |
| TestFromAC_BodyParserRoundTrip | Class and AC-named methods remain present at serve/kanban/tests/test_body_parser.py:20-209; no skip or xfail found | PRESERVED |

#### Test Quality
- Assertion specificity: WEAK
- Negative and edge-path coverage: ADEQUATE
- Manual mutation reasoning: WEAK
- Test independence: STRONG
- Descriptive test names: STRONG

#### Data Safety
- PASS: the implementation is local-state only and performs no persistence, shared-state mutation, or resource-amplifying work.

#### Implementation-Aware Test Gap Analysis
- FAIL: the CRLF normalization branch at body_parser.py:51 is not tested for LF preservation.
- FAIL: the ATX render branch at body_parser.py:165-166 is not pinned to the exact heading level for setext-derived sections.
- FAIL: the inter-section blank-line preservation logic at body_parser.py:106-107, 119-120, 128-129 is not anchored by a precise boundary assertion.

#### Necessity Check
- N/A: no new dependency, integration, or speculative capability added in this task.

#### Builder Process Quality
- CLEAN: one Builder Notes section only; no retry loop evidence.

### Verdict
- FAIL
- Reason: passing quality checks are not enough here because AC-C6, AC-C12, and AC-C53 still rely on lax assertions that would allow incorrect behavior to pass.
- Action: return to todo so the test-writer can strengthen those assertions; the current implementation shows no independent defect under the reviewed scope.

### Reviewer Reflection
- quality-runner evidence was clean, but code-reader surfaced false-confidence risk in three AC assertions.
- Historical RED-state failure is documented in the task body, but not independently rerunnable on the post-fix tree.
- The gating issue is insufficient proof, not observed parser misbehavior.
[[2026-04-21]]
## Test-Writer Notes
- Retry: reviewer cited lax assertions for AC-C6, AC-C12, AC-C53 and routed back to test-writer.
- Per `w-tdd-red` Step 1b: "If reviewer cites code quality, weak tests, or security (not missing tests): Pass through — the builder will address the findings."
- Implementation is correct for all three cited ACs; stronger assertions all PASS (traced and verified).
- No failing tests can be constructed: no bugs found in AC-C6 (LF preservation), AC-C12 (blank-line exact count), or AC-C53 (heading-level precision).
- 4 existing TestFromAC_BodyParserEdgeCases tests preserved (all PASS — builder's GREEN implementation intact).
- 0 new tests added.

### Pass-through rationale
The reviewer's directive ("return to todo so the test-writer can strengthen assertions") conflicts with two constraints:
1. Skill rule: weak-test finding = pass-through; builder addresses via `TestBuilderDiscovered` precision tests.
2. RED phase: all new tests must FAIL; with correct implementation, stronger assertions for C6/C12/C53 PASS.
Builder should add `TestBuilderDiscovered` tests with the stronger assertions the reviewer requires.
[[2026-04-21]]
## Builder Notes
- Files changed: tests/test_body_parser_1047.py
- Scope: Added 3 precision assertions under `TestBuilderDiscovered` for reviewer-flagged AC gaps (C6, C12, C53); no implementation code changes.
- Tests: 28 passed, 0 failed, 0 skipped (`tests/test_body_parser_1047.py` + `serve/kanban/tests/test_body_parser.py`).
- Builder-discovered tests added:
  - `test_ac_c6_crlf_normalises_to_exact_lf_content`
  - `test_ac_c12_preserves_exact_triple_blank_between_sections`
  - `test_ac_c53_setext_level_one_renders_exact_atx_h1`
- Coverage: `owlbear_kanban.body_parser` 100% (scoped run).
- Ruff: clean (no violations).
- Evidence summary: new assertions pin exact LF-normalized content for CRLF input, exact triple-blank inter-section boundary preservation, and exact ATX H1 render output for setext level-1 input.

### Post-task Reflection
- Problem faced: existing AC checks were behaviorally correct but too permissive for mutation resistance.
- Workaround applied: introduced task-scoped precision checks in a dedicated `TestBuilderDiscovered` class to preserve immutability of `TestFromAC_*`.
- Pattern discovered: reviewer quality findings can be addressed with assertion-strengthening tests even when no implementation defect exists.
- Time sink: none beyond baseline + post-edit quality verification runs.
- Quality gap: none remaining for the three cited AC assertions in scoped parser coverage.
[[2026-04-21]]
## Review Evidence
### Test Results
- quality-runner scoped verification: 28 passed, 0 failed, 0 skipped

### Lint
- Ruff clean

### Coverage
- owlbear_kanban.body_parser: 100%

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| AC-C5 | serve/kanban/tests/test_body_parser.py:25,30,36,42 and tests/test_body_parser_1047.py:23,34 | Covered for empty, preamble, single/multi-section, and no-trailing-LF cases; not for sections containing fenced or indented code, even though paper-c.md:187-191 applies the round-trip/content guarantee to all sections produced by parse_body | MISSING |
| AC-C6 | serve/kanban/tests/test_body_parser.py:54,64 and tests/test_body_parser_1047.py:89 | Exact LF-normalized content is now asserted | COVERED |
| AC-C7 | serve/kanban/tests/test_body_parser.py:73,81 | No-space headings are checked for both non-promotion and verbatim content preservation | COVERED |
| AC-C8 | serve/kanban/tests/test_body_parser.py:91,99,107 | Heading text and level are asserted directly for H2, H1, and H6 | COVERED |
| AC-C9 | serve/kanban/tests/test_body_parser.py:117,125 | Setext level-1 and level-2 parsing is asserted directly | COVERED |
| AC-C10 | serve/kanban/tests/test_body_parser.py:135,149 and tests/test_body_parser_1047.py:46,67 | Current tests prove non-promotion for standard fenced, indented, and shorter-close cases | COVERED |
| AC-C11 | serve/kanban/tests/test_body_parser.py:158 | Exact trailing-space preservation is asserted in section content | COVERED |
| AC-C12 | serve/kanban/tests/test_body_parser.py:169,180 and tests/test_body_parser_1047.py:98 | Exact triple-blank boundary preservation is now asserted | COVERED |
| AC-C53 | serve/kanban/tests/test_body_parser.py:190,199 and tests/test_body_parser_1047.py:107 | Exact ATX H1 render and Section-model equivalence are both asserted | COVERED |

#### Security Review
- No issues in serve/kanban/src/owlbear_kanban/body_parser.py:32-169; reviewed code is string and regex parsing only.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---|---|---|
| TestFromAC_BodyParserEdgeCases | Unchanged; builder added a separate TestBuilderDiscovered block at tests/test_body_parser_1047.py:86-114 | PRESERVED |
| TestFromAC_BodyParserRoundTrip | Unchanged since the prior review cycle | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | STRONG | C6, C12, and C53 now use exact equality and explicit negative checks at tests/test_body_parser_1047.py:89-114 |
| Negative and edge-path coverage | ADEQUATE | C7 and C10 cover non-promotion cases at serve/kanban/tests/test_body_parser.py:73-154 and tests/test_body_parser_1047.py:46-83 |
| Manual mutation reasoning | ADEQUATE | Prior lax assertions are fixed; remaining blind spots are isolated under implementation-aware gaps below |
| Test independence | STRONG | Each test builds local markdown input and parses it independently |
| Descriptive test names | STRONG | Both suites use AC-named tests throughout |

#### Data Safety
- No issues; no persistence, shared mutable state, or resource-amplifying behavior in serve/kanban/src/owlbear_kanban/body_parser.py:32-169.

#### Implementation-Aware Gaps
- FAIL: Neither serve/kanban/tests/test_body_parser.py:135-154 nor tests/test_body_parser_1047.py:46-83 asserts that fenced or indented code lines are preserved verbatim in Section.content or in rendered output. A regression in the pass-through paths at serve/kanban/src/owlbear_kanban/body_parser.py:81-97 could still satisfy the current heading-list assertions while violating paper-c.md:187-191.
- FAIL: The changed close-fence rule in serve/kanban/src/owlbear_kanban/body_parser.py:87 is intended to match same-length or longer closes, but the suite only proves equal-length closes and shorter-close rejection. Brief C binds parser behavior to markdown-it-py/CommonMark at paper-c.md:171-179, and the task's own boundary tests cite the same-or-greater fence rule at tests/test_body_parser_1047.py:49-51. A mutation from the current same-or-greater regex to exact-length-only would survive the current suite.

#### Necessity Check
- N/A: no new dependency, integration, or speculative capability added.

#### Builder Process Quality
| Metric | Value |
|---|---|
| Builder Notes sections | 2 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- Non-blocking doc mismatch: serve/kanban/src/owlbear_kanban/body_parser.py:18 says empty ATX headings may omit the space, but the regex at line 19 requires a space.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC-C5 | Round-trip is proven for empty, preamble, single/multi-section, and no-trailing-LF cases, but not for parsed sections containing fenced or indented code despite paper-c.md:187-191 requiring byte-exact within-section content | serve/kanban/tests/test_body_parser.py:25,30,36,42 and tests/test_body_parser_1047.py:23,34 | FAIL |
| AC-C6 | Exact LF-normalized content is asserted | serve/kanban/tests/test_body_parser.py:54,64 and tests/test_body_parser_1047.py:89 | PASS |
| AC-C7 | No-space headings are not promoted and are preserved in content | serve/kanban/tests/test_body_parser.py:73,81 | PASS |
| AC-C8 | Exact heading and level checks for H1, H2, and H6 | serve/kanban/tests/test_body_parser.py:91,99,107 | PASS |
| AC-C9 | Setext level-1 and level-2 parsing checks | serve/kanban/tests/test_body_parser.py:117,125 | PASS |
| AC-C10 | Non-promotion is asserted for standard fenced, indented, and shorter-close cases | serve/kanban/tests/test_body_parser.py:135,149 and tests/test_body_parser_1047.py:46,67 | PASS |
| AC-C11 | Trailing whitespace preservation is asserted in content | serve/kanban/tests/test_body_parser.py:158 | PASS |
| AC-C12 | Exact triple-blank inter-section preservation is asserted | serve/kanban/tests/test_body_parser.py:169,180 and tests/test_body_parser_1047.py:98 | PASS |
| AC-C53 | Exact ATX H1 render and Section-model equivalence are both asserted | serve/kanban/tests/test_body_parser.py:190,199 and tests/test_body_parser_1047.py:107 | PASS |

### Deductions
- -0.08: general AC-C5 round-trip proof still missing fenced and indented code content fidelity
- -0.06: touched close-fence logic still lacks a longer-close acceptance test

### Confidence: 0.86
### Verdict: FAIL
### Action
- Reject to todo. The implementation looks correct on the reviewed inputs, but the current suite still leaves two contract-bearing fence paths unproven.
[[2026-04-21]]
## Test-Writer Notes
- Retry #2: reviewer cited missing tests for (a) fenced/indented code verbatim in Section.content and (b) longer-close fence acceptance (AC-C10 same-or-greater rule).
- Per `w-tdd-red` Step 1b: "if reviewer cites missing tests → write NEW failing tests." Attempted to construct four candidate tests covering both gaps; all four PASS with the current implementation (confirmed by inline probe against production code).
- RED-phase hard rule: all new tests must FAIL. Writing tests that pass is prohibited.
- Result: no new tests added. 4 existing `TestFromAC_BodyParserEdgeCases` + 3 `TestBuilderDiscovered` tests preserved (all PASS — builder's GREEN implementation intact).

### Pass-through rationale (second cycle)
The two cited gaps:
1. **AC-C5 fenced/indented content verbatim**: `parse_body(render_body(sections)) == sections` holds for fenced and indented code sections; `Section.content` preserves fence markers and interior lines byte-exact. All assertions PASS.
2. **AC-C10 longer-close acceptance**: a 5-backtick/tilde close correctly terminates a 3-backtick/tilde fence; content after the close is parsed as normal. All assertions PASS.

The reviewer's concern is **mutation resilience** (would a test catch a regression?). Mutation-resilient regression guards that exercise correct behavior are GREEN/builder-discovered tests. The builder should add these under `TestBuilderDiscovered` — the established mechanism from the first cycle.

Recommendation: reviewer should accept a second `TestBuilderDiscovered` batch from the builder covering (a) fenced-section content verbatim assertions and (b) longer-close fence acceptance assertions, rather than routing back to test-writer.