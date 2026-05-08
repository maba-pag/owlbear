---
id: 1433
title: 'P1-05: Panel Output Phrasing section in h-ideation-panel/SKILL.md'
status: in-progress
priority: important
created: 2026-05-08T01:00:48.510035+00:00
updated: 2026-05-08T15:56:09.430234+00:00
tags:
- phase-1
- scope:shared
- ideation
- ux
parent: 1428
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective

Add a light "Panel Output Phrasing" section to `share/skills/h-ideation-panel/SKILL.md` guiding how panel stance section headers should be phrased for mediator consumption (preventing jargon leakage through panel output that the mediator reads and potentially echoes).

Brief: see parent #1428. Full brief at `.owlbear/briefs/draft-ideation-ux/brief.md`.

## Scope

**In:** One new section in `share/skills/h-ideation-panel/SKILL.md`.

**Out:** All other files. This task is independent of #1429 (no vocabulary dependency — panel phrasing is self-contained guidance).

## Acceptance Criteria

- [ ] New "Panel Output Phrasing" section exists in h-ideation-panel/SKILL.md
- [ ] Guidance instructs panelists to use descriptive section headers (e.g., "Structural Concern: tight coupling between X and Y") rather than protocol-coded headers (e.g., "O15-FAIL: coupling violation")
- [ ] Guidance states that stance files may be quoted by the mediator — headers should be readable to the user without translation
- [ ] Section is brief (5-10 lines max) — light cleanup, not a rewrite
- [ ] No changes to existing panel mechanics or stance file structure beyond header phrasing guidance
[[2026-05-08]]
## Test-Writer Notes

- Test file: `tests/test_panel_output_phrasing_1433.py`
- Class: `TestFromAC_PanelOutputPhrasing`
- Commit: `f97481ea`

| Category | Tests | Count |
|----------|-------|-------|
| Happy / presence | `test_panel_output_phrasing_section_exists` | 1 |
| Content / AC2 | `test_section_instructs_descriptive_headers`, `test_section_discourages_protocol_coded_headers` | 2 |
| Content / AC3 | `test_section_mentions_mediator_quoting`, `test_section_mentions_user_readability` | 2 |
| Boundary / AC4 | `test_section_length_within_bounds` | 1 |
| Regression / AC5 | `test_new_section_does_not_displace_existing_sections` | 1 |
| **Total** | | **7** |

All 7 tests FAIL (RED confirmed). Ruff clean.

**AC coverage table:**

| AC | Test(s) |
|----|---------|
| AC1 — section exists | `test_panel_output_phrasing_section_exists` |
| AC2 — descriptive header guidance | `test_section_instructs_descriptive_headers`, `test_section_discourages_protocol_coded_headers` |
| AC3 — mediator quoting + user readability | `test_section_mentions_mediator_quoting`, `test_section_mentions_user_readability` |
| AC4 — brevity (5-10 lines) | `test_section_length_within_bounds` |
| AC5 — no existing sections removed | `test_new_section_does_not_displace_existing_sections` |

**Implementation note for builder:** The helper `_extract_section_body()` parses the section by scanning for `## Panel Output Phrasing` then collecting lines until the next `## ` heading. The section body line count is measured in non-blank lines — target 5-10.
[[2026-05-08]]
## Builder Notes
- Implementation: added a new `## Panel Output Phrasing` section in `share/skills/h-ideation-panel/SKILL.md`.
- Scope control: one surgical docs edit only; no panel mechanics or stance structure changes.
- Tests: 7/7 `TestFromAC_PanelOutputPhrasing` tests passed (`tests/test_panel_output_phrasing_1433.py`).
- Lint: clean (`ruff` clean in quality-runner scoped run).
- Coverage: not applicable for this docs-only task (quality-runner reported no module coverage data in scoped run).
- Evidence summary: RED verified first (7 failing tests, missing section), then GREEN verified after edit (7 passed, failures cleared).
- Commit: `771c2962` with message `docs: add panel output phrasing guidance (#1433, builder)`.
[[2026-05-08]]
## Review Evidence
### Test Results
- quality-runner scoped run on tests/test_panel_output_phrasing_1433.py: 7 passed, 0 failed.
- Ruff on tests/test_panel_output_phrasing_1433.py: clean.
- Coverage: not applicable; builder changed Markdown guidance only.

### Scope Reconstruction
- Builder commit 771c2962 and test-writer commit f97481ea were confirmed from .git/logs.
- Direct git diff and git status were unavailable in this session, so builder changed-file ownership, TestFromAC immutability, and dirty-tree cleanliness are only partially verified.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1 section exists | share/skills/h-ideation-panel/SKILL.md:197 | test_panel_output_phrasing_section_exists | PASS |
| AC2 descriptive rather than protocol-coded headers | share/skills/h-ideation-panel/SKILL.md:199-200 | test_section_instructs_descriptive_headers; test_section_discourages_protocol_coded_headers | PASS |
| AC3 mediator quoting and user readability | share/skills/h-ideation-panel/SKILL.md:202-203 | test_section_mentions_mediator_quoting; test_section_mentions_user_readability | PASS |
| AC4 brief 5-10 line section | share/skills/h-ideation-panel/SKILL.md:199-204 and next heading at share/skills/h-ideation-panel/SKILL.md:206 show 6 non-blank bullet lines | test_section_length_within_bounds | PASS |
| AC5 phrasing-only change, no mechanics or structure change | share/skills/h-ideation-panel/SKILL.md:204 | test_new_section_does_not_displace_existing_sections | PASS on current file; proof is lax |

### Test-Writer Audit
| AC Line | Mapped Test | Would fail if AC violated? | Verdict |
|---|---|---|---|
| AC1 | test_panel_output_phrasing_section_exists | Yes. Exact heading check at tests/test_panel_output_phrasing_1433.py:70. | COVERED |
| AC2 | test_section_instructs_descriptive_headers; test_section_discourages_protocol_coded_headers | No. Assertions accept token presence only: tests/test_panel_output_phrasing_1433.py:80 checks for the word descriptive anywhere; tests/test_panel_output_phrasing_1433.py:90 matches a broad alternation including avoid, rather than, or instead of without requiring protocol-coded contrast. A section could omit the required contrast and still pass. | LAX |
| AC3 | test_section_mentions_mediator_quoting; test_section_mentions_user_readability | No. tests/test_panel_output_phrasing_1433.py:104 only requires mediator anywhere; tests/test_panel_output_phrasing_1433.py:112 accepts user or readable or translation anywhere. Removing quoted by the mediator or without translation could still leave the tests green. | LAX |
| AC4 | test_section_length_within_bounds | Yes. Exact numeric bound at tests/test_panel_output_phrasing_1433.py:124. | COVERED |
| AC5 | test_new_section_does_not_displace_existing_sections | No. tests/test_panel_output_phrasing_1433.py:137 proves only that named headings remain. It does not prove that panel mechanics or stance file structure were otherwise unchanged. A mechanical edit inside an existing section would still pass. | LAX |

### Additional Checks
- Security review: no issues for this docs-only change.
- Data safety: not applicable.
- Necessity: aligned with brief scope at .owlbear/briefs/draft-ideation-ux/brief.md:127 and architect stance at .owlbear/briefs/draft-ideation-ux/stances/architect.md:122.
- Builder process quality: CLEAN, one builder cycle only.

### Deductions
- 0.10 AC2 proof-quality gap
- 0.10 AC3 proof-quality gap
- 0.05 AC5 proof-quality gap
- 0.03 commit diff and dirty-tree verification unavailable in this session

### Verdict
- FAIL. Current implementation appears correct, but the TestFromAC suite is too weak to prove AC2, AC3, and AC5. Confidence 0.72. Route to backlog for AC and test-quality rework.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Tighten the AC-proof contract for AC2 and AC3 so tests require the actual contrast and quoting or readability statements, not single-token presence. | tests/test_panel_output_phrasing_1433.py | tests/test_panel_output_phrasing_1433.py:80, tests/test_panel_output_phrasing_1433.py:90, tests/test_panel_output_phrasing_1433.py:104, tests/test_panel_output_phrasing_1433.py:112 |
| 2 | architect | Redefine AC5 proof so tests detect edits to panel mechanics or stance-file structure, not only missing headings, then hand back through test-writing. | tests/test_panel_output_phrasing_1433.py; share/skills/h-ideation-panel/SKILL.md | tests/test_panel_output_phrasing_1433.py:137; share/skills/h-ideation-panel/SKILL.md:204 |
[[2026-05-08]]

## Architecture Review (cycle 2)
### Context
Reviewer FAIL (0.72) on cycle 1 was correct — tests are too lax for AC2, AC3, AC5.
Implementation is verified correct (section exists, content satisfies all criteria).
This cycle tightens AC wording for testability, then re-routes through test-writer.

### Refined Acceptance Criteria
Replacing original AC lines with tightened versions:

- [ ] AC1: New "## Panel Output Phrasing" section heading exists in h-ideation-panel/SKILL.md (td:1)
- [ ] AC2: Section contains both sides of the contrast — (a) positive guidance to use descriptive/natural-language headers with an inline example, AND (b) explicit guidance to avoid protocol-coded or jargon-first headers with an inline negative example. Both "descriptive" and "protocol-coded" (or "jargon") must appear in the section body. (td:2)
- [ ] AC3: Section contains both: (a) a statement about mediator quoting where "quoted" and "mediator" co-occur in the same line/bullet, AND (b) a statement about user readability where "readable" and "without translation" co-occur in the same line/bullet. (td:2)
- [ ] AC4: Section body is 5–10 non-blank lines (td:1)
- [ ] AC5: All 7 pre-existing top-level ## headings preserved; total ## heading count = original count + 1; the new section includes an explicit scope-boundary statement containing "phrasing only" or equivalent confirming it does not alter panel mechanics or stance file structure. (td:1)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One section addition to one file |
| Interface clarity | PASS | AC now specifies exact co-occurrence patterns for testability |
| Dependency correctness | PASS | No dependencies; independent of #1429 |
| Module layering | N/A | Markdown prose, no code |
| TDD compliance | PASS | Test file exists from cycle 1; will be updated by test-writer |
| KISS/YAGNI | PASS | 6 bullets of guidance, minimal |
| Premise challenge | PASS | Brief justifies preventing jargon leakage through panel output |
| Pattern consistency | PASS | Follows existing section patterns in h-ideation-panel/SKILL.md |
| Security surface | N/A | No system boundary |
| Single domain | PASS | Ideation skill guidance only |

### Challenge Results
- Challenger: reconsider (0.38)
- Concerns: (1) AC not yet written to task, (2) AC5 potentially weakened
- Architect response: ACCEPTED in part — (1) AC is being written now, (2) AC5 STRENGTHENED with section-count invariant (original + 1) and explicit scope-boundary phrase requirement. The challenger's process objection was about sequencing, not substance.

### Test Depth
- Max depth: 2
- Test-writer: PROCEED (update existing tests to match tightened AC)

### Implementation Note
The existing implementation at share/skills/h-ideation-panel/SKILL.md:197-204 already satisfies all tightened AC. Builder should NOT need to change the file — only tests need updating.

### Verdict: APPROVE
### Action Taken: Tightened AC2/AC3/AC5 for testability, routing to todo for test-writer update cycle.

[[2026-05-08]]
Architecture review cycle 2: Tightened AC2 (co-occurrence of descriptive + protocol-coded contrast), AC3 (same-line co-occurrence of quoted/mediator and readable/without-translation), AC5 (section-count invariant + scope-boundary phrase). Implementation already satisfies all tightened criteria. Routing to test-writer to update assertions.
[[2026-05-08]]
## Test-Writer Notes

- **Retry cycle (cycle 2) — test-only, direct-to-review advance**
- Test file: `tests/test_panel_output_phrasing_1433.py`
- Class: `TestFromAC_PanelOutputPhrasing`
- Commit: `279ae988`

### New tests added (7 tightened, addressing reviewer gaps)

| Category | Tests | Count |
|----------|-------|-------|
| AC2 — both-sides contrast | `test_ac2_contrast_both_terms_coexist` | 1 |
| AC2 — inline examples | `test_ac2_positive_side_has_inline_example`, `test_ac2_negative_side_has_inline_example` | 2 |
| AC3 — same-line co-occurrence | `test_ac3_quoted_and_mediator_same_line`, `test_ac3_readable_and_without_translation_same_line` | 2 |
| AC5 — count invariant | `test_ac5_heading_count_equals_original_plus_one` | 1 |
| AC5 — scope boundary phrase | `test_ac5_scope_boundary_phrase_present` | 1 |
| **Total new** | | **7** |

### Result

- 7 existing tests: PASS (unchanged)
- 7 new tightened tests: PASS (implementation already satisfies tightened AC per architect cycle 2)
- Total: 14/14 passed, ruff clean

### Step 1b.1 criteria satisfied

- Reviewer follow-up contained only test-proof gaps (no implementation fixes)
- All new tests pass against current code (implementation satisfies tightened AC)
- No lint issues

Builder skipped. Advancing directly to review.

### AC coverage table

| AC | Test(s) | Tightened? |
|----|---------|-----------|
| AC1 — section exists | `test_panel_output_phrasing_section_exists` | — |
| AC2 — contrast + examples | `test_section_instructs_descriptive_headers`, `test_section_discourages_protocol_coded_headers` (original weak) + `test_ac2_contrast_both_terms_coexist`, `test_ac2_positive_side_has_inline_example`, `test_ac2_negative_side_has_inline_example` | YES |
| AC3 — same-line co-occurrence | `test_section_mentions_mediator_quoting`, `test_section_mentions_user_readability` (original weak) + `test_ac3_quoted_and_mediator_same_line`, `test_ac3_readable_and_without_translation_same_line` | YES |
| AC4 — brevity | `test_section_length_within_bounds` | — |
| AC5 — count invariant + scope boundary | `test_new_section_does_not_displace_existing_sections` (original weak) + `test_ac5_heading_count_equals_original_plus_one`, `test_ac5_scope_boundary_phrase_present` | YES |
[[2026-05-08]]
## Builder Notes
- Implementation: no file changes in this builder cycle.
- Basis: architect cycle-2 note states existing implementation already satisfies tightened AC; test-writer added stronger proofs.
- Tests: 14/14 passed in `tests/test_panel_output_phrasing_1433.py` (scoped quality-runner run).
- Coverage: not requested (docs-only scope; no Python source change this cycle).
- ruff: clean on `tests/test_panel_output_phrasing_1433.py`.
- Evidence summary: verified GREEN on tightened suite, confirmed no additional builder intervention needed, and advanced to review.
[[2026-05-08]]
## Review Evidence
### Test Results
- quality-runner scoped run on tests/test_panel_output_phrasing_1433.py: 14 passed, 0 failed.
- Ruff on tests/test_panel_output_phrasing_1433.py: clean.
- Coverage: not applicable for this docs-only, test-only retry cycle.

### Scope Reconstruction
- This is the second review cycle. A prior Review Evidence section already exists in .owlbear/kanban/tasks/1433-p1-05-panel-output-phrasing-section-in-h-ideation-panel-skill-md.md:80, so the reviewer loop-breaker applies on any new FAIL.
- Current implementation evidence is the handbook section at share/skills/h-ideation-panel/SKILL.md:197-204, originally added in builder commit 771c2962 and confirmed in .git/logs/HEAD:2262.
- Current retry-cycle proof changes are the tightened tests recorded in test-writer commit 279ae988, confirmed in .git/logs/HEAD:2275.
- Direct git diff and git status were not available in this tool surface, so dirty-tree contamination and commit-level diff ownership are not fully verified. Small confidence deduction applied.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1: section heading exists | share/skills/h-ideation-panel/SKILL.md:197 | test_panel_output_phrasing_section_exists | PASS |
| AC2: positive descriptive guidance plus explicit negative contrast with examples | Current wording is correct at share/skills/h-ideation-panel/SKILL.md:199-200, but the strengthened proof still keys on descriptive/protocol-coded token presence and example presence rather than affirmative vs prohibitive semantics at tests/test_panel_output_phrasing_1433.py:148, tests/test_panel_output_phrasing_1433.py:163, tests/test_panel_output_phrasing_1433.py:168, tests/test_panel_output_phrasing_1433.py:175, tests/test_panel_output_phrasing_1433.py:180 | test_section_instructs_descriptive_headers; test_section_discourages_protocol_coded_headers; test_ac2_contrast_both_terms_coexist; test_ac2_positive_side_has_inline_example; test_ac2_negative_side_has_inline_example | FAIL |
| AC3: mediator quoting and user readability statements | share/skills/h-ideation-panel/SKILL.md:202-203 and same-line co-occurrence assertions at tests/test_panel_output_phrasing_1433.py:189-216 | test_ac3_quoted_and_mediator_same_line; test_ac3_readable_and_without_translation_same_line | PASS |
| AC4: 5-10 non-blank lines | share/skills/h-ideation-panel/SKILL.md:199-204 is 6 non-blank lines; bounded extraction and count check at tests/test_panel_output_phrasing_1433.py:41-59 and 118-124 | test_section_length_within_bounds | PASS |
| AC5: preserve all 7 legacy top-level headings, heading count original plus one, and explicit scope-boundary statement | Current handbook satisfies this at share/skills/h-ideation-panel/SKILL.md:11,23,57,117,152,190,197,204,206, but tests only prove substring presence for legacy headings at tests/test_panel_output_phrasing_1433.py:137, count invariant at tests/test_panel_output_phrasing_1433.py:225-233, and phrasing-only phrase at tests/test_panel_output_phrasing_1433.py:239-248. They do not prove each legacy section remains a top-level ## heading or that the scope-boundary line retains the unchanged mechanics and stance-structure clause. | test_new_section_does_not_displace_existing_sections; test_ac5_heading_count_equals_original_plus_one; test_ac5_scope_boundary_phrase_present | FAIL |

### Test-Writer Audit
| AC Line | Mapped Test | Would fail if AC violated? | Verdict |
|---|---|---|---|
| AC1 | test_panel_output_phrasing_section_exists | Yes. Exact heading presence at tests/test_panel_output_phrasing_1433.py:67. | COVERED |
| AC2 | test_section_instructs_descriptive_headers; test_section_discourages_protocol_coded_headers; test_ac2_contrast_both_terms_coexist; test_ac2_positive_side_has_inline_example; test_ac2_negative_side_has_inline_example | No. The strengthened selectors still match any line containing descriptive or protocol-coded plus an example at tests/test_panel_output_phrasing_1433.py:168 and 180. A reversed-semantics mutation could stay green. | LAX |
| AC3 | test_ac3_quoted_and_mediator_same_line; test_ac3_readable_and_without_translation_same_line | Yes. Same-line co-occurrence would fail if the quoting or readability statements were removed or split. | COVERED |
| AC4 | test_section_length_within_bounds | Yes. Exact 5-10 line bound at tests/test_panel_output_phrasing_1433.py:118-124. | COVERED |
| AC5 | test_new_section_does_not_displace_existing_sections; test_ac5_heading_count_equals_original_plus_one; test_ac5_scope_boundary_phrase_present | No. The suite does not prove each preserved heading remains a top-level ## heading, and the scope-boundary assertion does not require the mechanics and stance-file-structure disclaimer. | LAX |

### Additional Checks
- Security review: no issues in scope.
- Data safety: no issues in scope.
- Test integrity: no weakened or removed TestFromAC assertions visible in the current snapshot; retry-cycle additions are additive.
- Builder process quality: CLEAN. No implementation loop; this retry was test-only after architect AC tightening.

### Deductions
- 0.08 AC2 proof remains vulnerable to reversed-semantics mutations.
- 0.10 AC5 proof does not guarantee preserved top-level headings or the full scope-boundary disclaimer.
- 0.03 git diff and dirty-tree contamination checks unavailable in current tool surface.

### Verdict
- FAIL. The implementation text in share/skills/h-ideation-panel/SKILL.md is correct, but the retry-cycle tests still do not prove AC2 and AC5 strongly enough for review sign-off.
- Confidence: 0.79.
- Action: reject to backlog under the reviewer loop-breaker rule because this task already had one prior review failure.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine AC2 into line-level semantic proof so tests must distinguish affirmative guidance to use descriptive headers from prohibitive guidance to avoid protocol-coded or jargon-first headers. | tests/test_panel_output_phrasing_1433.py | tests/test_panel_output_phrasing_1433.py:148, 163, 168, 175, 180 |
| 2 | architect | Refine AC5 proof so tests verify each of the seven legacy sections remains a top-level ## heading and the scope-boundary line explicitly preserves unchanged panel mechanics and stance file structure. | tests/test_panel_output_phrasing_1433.py; share/skills/h-ideation-panel/SKILL.md | tests/test_panel_output_phrasing_1433.py:137, 225, 239, 248; share/skills/h-ideation-panel/SKILL.md:204 |
[[2026-05-08]]

## Architecture Review (cycle 3)

### Context
Reviewer FAIL (0.79) on cycle 2: AC2 tests still vulnerable to reversed-semantics mutations (token presence without verb-direction check); AC5 tests use substring match instead of line-level heading verification. Implementation remains correct and unchanged since cycle 1 commit `771c2962`.

### Refined Acceptance Criteria (replacing cycle 2 AC)

- [ ] AC1: New `## Panel Output Phrasing` section heading exists in h-ideation-panel/SKILL.md (td:1)
- [ ] AC2: Section contains both semantic directions for header guidance: (a) a bullet with affirmative intent (starting with "Use" or "Prefer") that co-occurs with "descriptive" and "header(s)" and includes an inline example (`for example` or `e.g.`), AND (b) a bullet with prohibitive intent (starting with "Avoid") that co-occurs with "protocol-coded" or "jargon" and "header(s)" and includes an inline example. (td:2)
- [ ] AC3: Section contains both: (a) a line where "quoted" and "mediator" co-occur, AND (b) a line where "readable" and "without translation" co-occur. (td:2) — unchanged from cycle 2, reviewer PASS
- [ ] AC4: Section body is 5–10 non-blank lines (td:1) — unchanged, reviewer PASS
- [ ] AC5: All 7 pre-existing top-level headings preserved as exact `## ` lines (verified by line-start regex `^## {name}`, not substring). Total `## ` heading count = 8 (7 + 1). Scope-boundary line contains "phrasing only" AND at least one of "panel mechanics" or "stance file structure". (td:1)

### What changed from cycle 2
- AC2: Added verb-direction requirement (affirmative/prohibitive bullet prefix) and "header(s)" co-occurrence. Closes reversed-semantics and target-surface-drift gaps.
- AC5: Changed heading preservation from substring to line-start regex. Added scope-boundary co-occurrence (was single-token). Closes heading-level and scope-boundary proof gaps.
- AC1/AC3/AC4: No changes needed.

### Evaluation
| Criterion | Assessment |
|-----------|-----------|
| Single responsibility | PASS — one section addition to one file |
| Interface clarity | PASS — AC now specifies verb-direction + term co-occurrence patterns |
| Dependency correctness | PASS — no dependencies |
| TDD compliance | PASS — test file exists, test-writer will update assertions |
| KISS/YAGNI | PASS — 6 bullets of guidance, minimal |
| Pattern consistency | PASS — follows existing section patterns |

### Challenge Results
- Challenger: reconsider (0.67)
- Accepted: contract drift (writing AC now), negated-verb (bullet prefix pattern), target-surface drift ("headers" co-occurrence)
- Dismissed: example-polarity (prose-example semantics untestable by regex; natural ceiling for documentation tests)
- Override justified: all accepted concerns addressed in refined AC

### Test Depth
- Max depth: 2
- Test-writer: PROCEED — replace cycle 2 tightened assertions with verb-direction + heading-level checks

### Implementation Note
Implementation at share/skills/h-ideation-panel/SKILL.md:197-204 already satisfies all refined AC. Builder should NOT change the file — only test assertions need updating.

### Verdict: APPROVE → todo

[[2026-05-08]]
Architecture review cycle 3: Refined AC2 (verb-direction bullet prefix + "headers" co-occurrence + inline example) and AC5 (line-start regex heading verification + scope-boundary co-occurrence). Closes reversed-semantics and heading-level proof gaps flagged by reviewer. Implementation unchanged — test-writer to update assertions only.
[[2026-05-08]]
## Test-Writer Notes

- **Retry cycle (cycle 3) — test-only, direct-to-review advance**
- Test file: `tests/test_panel_output_phrasing_1433.py`
- Class: `TestFromAC_PanelOutputPhrasing`
- Commit: `030d12b0`

### New tests added (4 cycle-3 tightened, closing reviewer AC2/AC5 gaps)

| Category | Tests | Count |
|----------|-------|-------|
| AC2 — affirmative verb-direction | `test_ac2_affirmative_bullet_starts_with_use_or_prefer` | 1 |
| AC2 — prohibitive verb-direction | `test_ac2_prohibitive_bullet_starts_with_avoid` | 1 |
| AC5 — line-start heading check | `test_ac5_existing_headings_are_top_level_lines` | 1 |
| AC5 — scope-boundary co-occurrence | `test_ac5_scope_boundary_mentions_mechanics_or_structure` | 1 |
| **Total new** | | **4** |

### Result

- 14 existing tests (cycles 1+2): PASS (unchanged)
- 4 new cycle-3 tests: PASS (implementation already satisfies refined AC)
- Total: **18/18 passed**, ruff clean

### Step 1b.1 criteria satisfied

- Reviewer follow-up cited only test-proof gaps (AC2 reversed-semantics, AC5 heading-level and scope-boundary)
- All new tests pass against current implementation (section at SKILL.md:197-204 satisfies all criteria)
- No lint issues

Builder skipped. Advancing directly to review.

### AC coverage table

| AC | Test(s) | Cycle |
|----|---------|-------|
| AC1 — section exists | `test_panel_output_phrasing_section_exists` | 1 |
| AC2 — contrast + examples (token) | `test_section_instructs_descriptive_headers`, `test_section_discourages_protocol_coded_headers`, `test_ac2_contrast_both_terms_coexist`, `test_ac2_positive_side_has_inline_example`, `test_ac2_negative_side_has_inline_example` | 1/2 |
| AC2 — verb-direction | `test_ac2_affirmative_bullet_starts_with_use_or_prefer`, `test_ac2_prohibitive_bullet_starts_with_avoid` | 3 |
| AC3 — mediator + readability | `test_section_mentions_mediator_quoting`, `test_section_mentions_user_readability`, `test_ac3_quoted_and_mediator_same_line`, `test_ac3_readable_and_without_translation_same_line` | 1/2 |
| AC4 — brevity | `test_section_length_within_bounds` | 1 |
| AC5 — heading count + scope phrase (substring) | `test_new_section_does_not_displace_existing_sections`, `test_ac5_heading_count_equals_original_plus_one`, `test_ac5_scope_boundary_phrase_present` | 1/2 |
| AC5 — top-level heading + co-occurrence | `test_ac5_existing_headings_are_top_level_lines`, `test_ac5_scope_boundary_mentions_mechanics_or_structure` | 3 |