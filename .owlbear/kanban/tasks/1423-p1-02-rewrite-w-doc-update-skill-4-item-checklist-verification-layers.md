---
id: 1423
title: 'P1-02: Rewrite w-doc-update skill — 4-item checklist + verification layers'
status: todo
priority: needed
created: 2026-05-08T00:32:18.617094+00:00
updated: 2026-05-09T03:27:53.933213+00:00
tags:
- phase-1
- scope:shared
- brief:doc-writer-quality
- type:docs
parent: 1421
depends_on:
- 1422
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

Full rewrite of `share/skills/w-doc-update/SKILL.md` implementing the doc-writer quality redesign:

1. Convention mapping table mapping code path patterns to documentation files (serve/{pkg}/src/** → serve/{pkg}/README.md, etc.)
2. 4-item checklist: README Verification, External Attribution, Research Doc, Deletion Detection — no diagram items
3. Verification layers section: Layer 1 (grep for removed symbols) + Layer 2 (LLM full-file editorial read)
4. TODO marker format and insertion rules: `> **TODO:** {category} — {description} [#{id}]` with categories stale|inaccurate|missing|unverified
5. Gate-blocking rules: unverified on task-introduced content blocks; unverified on pre-existing passes
6. No-impact fast path: if changed files map to no READMEs, advance with evidence
7. Attribution rules for task-caused (fix inline) vs pre-existing (TODO marker)

**In scope:** SKILL.md content only. Must pass test assertions from #1422.
**Out of scope:** Agent file changes (#1424), prompt file changes (#1425).

Brief: see parent #1421
## Research\n- Research doc: .owlbear/research/doc-update-skill-rewrite-1423.md\n- Sources: 4 studied, 3 high-relevance\n- Recommendation: fast-track — implementation already complete, 52/52 tests pass (confidence: 0.95)
[[2026-05-08]]
## Research\nValidation pass — the SKILL.md rewrite was already implemented by the parent #1421 builder (commits 4404082c, eb98fff3, d41dc0b4). All 52 test assertions from #1422 pass. All 7 AC items verified against the brief design spec.\n\nResearch doc: .owlbear/research/doc-update-skill-rewrite-1423.md\nConfidence: 0.95\nNo follow-up tasks needed — siblings #1424 and #1425 already exist.
[[2026-05-08]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single deliverable: SKILL.md rewrite |
| Interface clarity | PASS | 7 AC items are specific and testable (52 assertions from #1422 confirm) |
| Dependency correctness | PASS | Depends on #1422 (test suite) — completed/archived, tests pass |
| Module layering | N/A | Skill file, no code imports |
| TDD compliance | PASS | #1422 provides 52 test assertions; implementation pre-verified |
| KISS/YAGNI | PASS | Exactly the scope from the brief, no extras |
| Premise challenge | PASS | Doc-writer quality redesign is a validated need (brief + parent #1421) |
| Pattern consistency | PASS | Follows standard SKILL.md structure (frontmatter, steps, output template, verification checklist) |
| Security surface | N/A | No system boundaries |
| Single domain | PASS | Shared/skills domain only |

### Failure Mode Map
N/A — no codepaths with failure modes (markdown skill file).

### Design Diverge
Skipped — single clear approach (implementation already complete, no alternatives to evaluate).

### Challenge Results
Challenger: SKIPPED — all td:0 (per Step 2.1)

### Test Depth
AC lines: all td:0 — implementation already exists and is covered by 52 tests from #1422.
Test-writer: SKIP

### Context Note
Research confirms the SKILL.md v3 rewrite was already implemented by the parent #1421 builder (commits 4404082c, eb98fff3, d41dc0b4). All 7 AC items verified against the current file content. Builder should verify existing content satisfies AC and confirm — no new writing needed.

Tagged `type:docs` for test-writer pass-through routing.

### Verdict: APPROVE
### Action Taken: Advanced to todo with type:docs tag added for pipeline routing.
[[2026-05-09]]
## Test-Writer Notes
- Non-implementation task (tagged type:docs) — no tests applicable.
- Architect confirmed: "Test-writer: SKIP" in architecture review.
- Passing through to builder.
[[2026-05-09]]
## Builder Notes
- Non-implementation task pass-through confirmed from task body (`## Test-Writer Notes`).
- Implementation: no files changed.
- Verification: quality-runner scoped run on tests/test_doc_writer_quality_1422.py => 52 passed, 0 failed.
- Lint: ruff scoped to tests/test_doc_writer_quality_1422.py => clean (0 issues).
- Coverage: N/A for docs-only/pass-through verification cycle.
- Evidence summary: acceptance criteria are already satisfied by existing content in share/skills/w-doc-update/SKILL.md; builder required only independent verification and routing to review.
- Fixes applied: none (no implementation delta needed).
[[2026-05-09]]
## Review Evidence
### Test Results
- quality-runner scoped run on `tests/test_doc_writer_quality_1422.py`: 52 passed, 0 failed, 0 skipped.
- Parallel fan-out note: `code-reader` returned no response, so I fell back to sequential manual review of `share/skills/w-doc-update/SKILL.md` and `tests/test_doc_writer_quality_1422.py`.

### Lint
- `ruff` scoped to `tests/test_doc_writer_quality_1422.py`: clean (0 violations).

### Coverage
- N/A for this markdown-only verification task. The independent quality-runner pass was run without coverage modules.

### Loop / Scope
- Prior review failures: none. The task file contains one `## Builder Notes` section at `.owlbear/kanban/tasks/1423-p1-02-rewrite-w-doc-update-skill-4-item-checklist-verification-layers.md:84` and no prior `## Review Evidence` section.
- Dirty-tree / commit-diff audit: not independently executable in the current tool surface, so TestFromAC immutability remains slightly lower-confidence.

### AC Compliance
| AC | Evidence | Mapped Test(s) | Status |
|---|---|---|---|
| 1. Convention mapping table | `share/skills/w-doc-update/SKILL.md:24-37` and explicit src row at `:30`; no-impact fast path at `:37` | `tests/test_doc_writer_quality_1422.py:28`, `:275`, `:433`, `:451` | PASS |
| 2. 4-item checklist, no diagram items | checklist section at `share/skills/w-doc-update/SKILL.md:39-72`; item headings at `:43`, `:52`, `:58`, `:63` | `tests/test_doc_writer_quality_1422.py:28`, `:231`, `:238`, `:244`, `:250` plus diagram-ban assertions in the same suite | PASS |
| 3. Verification layers | Item 1 layers at `share/skills/w-doc-update/SKILL.md:47-48`; dedicated section at `:94-101` | `tests/test_doc_writer_quality_1422.py:284`, `:294` | PASS |
| 4. TODO marker format + categories | template at `share/skills/w-doc-update/SKILL.md:74-87`, exact template at `:76` | `tests/test_doc_writer_quality_1422.py:189-225`, especially `:220` | PASS |
| 5. Gate-blocking rules | `share/skills/w-doc-update/SKILL.md:89-92`, with explicit task/pre-existing lines at `:91-92` | `tests/test_doc_writer_quality_1422.py:405`, `:419` | PASS |
| 6. No-impact fast path | `share/skills/w-doc-update/SKILL.md:37` requires `"no docs impact" with evidence and advance` | `tests/test_doc_writer_quality_1422.py:433` | PASS |
| 7. Attribution rules: task-caused fix inline vs pre-existing TODO marker | live file contains the rule at `share/skills/w-doc-update/SKILL.md:49-50`, but the suite does not contain a discriminating assertion for either clause | no direct AC7 proof; closest checks only prove generic TODO marker presence / gate wording at `tests/test_doc_writer_quality_1422.py:60`, `:78`, `:405`, `:419` | FAIL |

### Test Quality Assessment
- `TestFromAC_*` coverage is strong for AC1-AC6: the suite checks exact headings, exact row coupling, explicit gate lines, and the exact TODO template.
- AC7 remains under-proven. A mutation that removes or weakens `share/skills/w-doc-update/SKILL.md:49-50` while leaving the generic TODO section and gate rules intact would likely keep the current 52-test suite green.

### Deductions
- `-0.18` AC7 lacks mapped discriminating TestFromAC proof.
- `-0.02` `code-reader` returned no response; manual sequential review used instead.
- `-0.02` commit/diff-based immutability check was unavailable in the current tool surface.

### Verdict
- FAIL
- Confidence: `0.78`

### Action
- Reject to `todo`. The live SKILL.md content satisfies the task, but the proof is incomplete for AC7. This is a test-gap / proof-quality failure, not a builder-content failure.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add discriminating `TestFromAC_*` assertions that fail if Item 1 no longer requires `Fix task-caused issues inline` and `For pre-existing unresolved issues, insert a visible TODO marker`; if the strengthened tests pass against current content, advance directly back to review per builder-skip | `tests/test_doc_writer_quality_1422.py` | AC7 gap: `share/skills/w-doc-update/SKILL.md:49-50` is not directly asserted; current closest checks are only `tests/test_doc_writer_quality_1422.py:60`, `:78`, `:405`, `:419` |
[[2026-05-09]]
## Test-Writer Notes
- Retry: AC7 attribution-rule gap filled per reviewer Required Follow-up.
- Test file: `tests/test_doc_writer_quality_1422.py`
- New class: `TestFromAC_AttributionRules` (4 tests added)
- Tests per category: AC-derived/discriminating: 4
- Total: 56 tests (52 preserved + 4 new)

### New tests
| Test | What it proves |
|---|---|
| `test_item1_fix_task_caused_inline` | `Fix task-caused issues inline` present in Item 1 body |
| `test_item1_preexisting_issues_insert_todo_marker` | `pre-existing unresolved issues → insert a visible TODO marker` present in Item 1 body |
| `test_item1_has_both_attribution_rules` | Both attribution rules exist simultaneously in Item 1 |
| `test_item1_attribution_rules_scoped_to_item1_not_only_gate` | Both `task-caused` and `pre-existing` appear in Item 1 itself — not only in the Gate rules section |

### AC7 coverage
| AC clause | Test(s) | Discriminating? |
|---|---|---|
| Task-caused issues: fix inline | `test_item1_fix_task_caused_inline`, `test_item1_has_both_attribution_rules`, `test_item1_attribution_rules_scoped_to_item1_not_only_gate` | YES — fails if line removed from Item 1 |
| Pre-existing issues: TODO marker | `test_item1_preexisting_issues_insert_todo_marker`, `test_item1_has_both_attribution_rules`, `test_item1_attribution_rules_scoped_to_item1_not_only_gate` | YES — fails if line removed from Item 1 |

### Result
All 4 new tests PASS against current SKILL.md — per step 1b.1: reviewer gap was test-proof only, implementation unchanged, advancing directly to review.
- Lint: ruff clean (0 violations)
- Commit: 3332b411
[[2026-05-09]]
## Builder Notes
- Scope: docs-only verification task for `share/skills/w-doc-update/SKILL.md`; no implementation changes required.
- Files changed: none.
- Verification run (quality-runner, scoped): `uv run pytest tests/test_doc_writer_quality_1422.py -q --tb=line --cov --cov-report=term-missing --cov-fail-under=0 -n 0`.
- Test results: 56 passed, 0 failed, 0 skipped.
- Lint run: `uv run ruff check tests/test_doc_writer_quality_1422.py`.
- Lint status: clean (0 violations).
- Coverage: N/A for this pass (coverage collector reported no application module data; suite validates markdown/spec assertions).
- Evidence summary: retry objective (AC7 proof gap) is now satisfied by added `TestFromAC_AttributionRules` tests and independent GREEN verification; task is ready for review.
- Fixes applied: none (verification-only cycle).
[[2026-05-09]]
## Review Evidence
### Test Results
- quality-runner scoped run on `tests/test_doc_writer_quality_1422.py`: 56 passed, 0 failed, 0 skipped.
- Command (quality-runner): `uv run pytest tests/test_doc_writer_quality_1422.py -q --tb=line`

### Lint
- `ruff` scoped to `tests/test_doc_writer_quality_1422.py`: clean (0 violations).
- Command (quality-runner): `uv run ruff check tests/test_doc_writer_quality_1422.py`

### Coverage
- N/A for this markdown-only task and test-only retry. The reviewed artifact is `share/skills/w-doc-update/SKILL.md`; no application module is owned by this retry.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| 1. Convention mapping table | `tests/test_doc_writer_quality_1422.py:357`, `:365`, `:372`, `:379`, `:390`, `:451` | Yes — these tests pin the table shape and the exact `serve/{pkg}/src/**` → `serve/{pkg}/README.md` row at `share/skills/w-doc-update/SKILL.md:30-34` | COVERED |
| 2. 4-item checklist; no diagram items | `tests/test_doc_writer_quality_1422.py:28`, `:36`, `:42`, `:231`, `:238`, `:244`, `:250`, `:265` | Yes — checklist count, exact item names, and diagram exclusions would fail if the structure regressed from `share/skills/w-doc-update/SKILL.md:43-63` | COVERED |
| 3. Verification layers | `tests/test_doc_writer_quality_1422.py:48`, `:54`, `:284`, `:294` | Yes — these tests pin Layer 1 / Layer 2 wording in Item 1 and the dedicated section at `share/skills/w-doc-update/SKILL.md:47-48` and `:98-100` | COVERED |
| 4. TODO marker format and insertion rules | `tests/test_doc_writer_quality_1422.py:192`, `:198`, `:205`, `:212`, `:220` | Yes — exact template and categories would fail if `share/skills/w-doc-update/SKILL.md:74-87` regressed | COVERED |
| 5. Gate-blocking rules | `tests/test_doc_writer_quality_1422.py:405`, `:419` | Yes — these tests pin the two gate lines at `share/skills/w-doc-update/SKILL.md:89-92` | COVERED |
| 6. No-impact fast path | `tests/test_doc_writer_quality_1422.py:433` | Yes — this test would fail if `"no docs impact" with evidence and advance` disappeared from `share/skills/w-doc-update/SKILL.md:37` | COVERED |
| 7. Attribution rules for task-caused vs pre-existing | `tests/test_doc_writer_quality_1422.py:481`, `:489`, `:501`, `:523` | No for the full pre-existing clause — the executable matcher at `tests/test_doc_writer_quality_1422.py:492` and `:508` accepts `pre-existing.*TODO marker`, which is broader than `share/skills/w-doc-update/SKILL.md:50` (`insert a visible TODO marker`). The full clause appears only in docstrings/messages at `tests/test_doc_writer_quality_1422.py:466`, `:470`, `:497`, `:519`, not in a discriminating assertion. | LAX |

#### Security Review
- No issues. Scope is a markdown skill file plus spec tests; no secrets, injection, deserialization, path, or boundary-handling changes were introduced.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| Existing `TestFromAC_*` suite in `tests/test_doc_writer_quality_1422.py` | Retry commit `3332b411` added `TestFromAC_AttributionRules`; no weakening or removal of the prior assertions was detected, and `share/skills/w-doc-update/SKILL.md` was unchanged in the retry | STRENGTHENED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | WEAK | `tests/test_doc_writer_quality_1422.py:492` and `:508` allow any Item 1 wording matching `pre-existing.*TODO marker`; they do not executable-pin the full contract at `share/skills/w-doc-update/SKILL.md:50` (`insert a visible TODO marker`). |
| Negative/error-path coverage | ADEQUATE | For this docs/spec task, the suite checks presence, scoping, and prohibited content rather than runtime exceptions. |
| Manual mutation reasoning | WEAK | A mutation such as `For pre-existing issues, reference the TODO marker policy.` would still satisfy `pre-existing.*TODO marker` and keep AC7 green while weakening the Item 1 instruction. |
| Test independence | STRONG | Each AC7 test reads the file fresh and scopes itself to `_item1_section()`. |
| Descriptive test names | STRONG | The new test names map directly to the claimed AC7 clauses. |

#### Data Safety
- No issues in this markdown/test-only scope.

#### Implementation-Aware Gaps
- The live skill content still satisfies AC1-AC7. The blocking defect is proof quality in the retry tests, not implementation in `share/skills/w-doc-update/SKILL.md`.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 2 |
| Approach variation | Yes — original verification-only pass, then post-review verification after test-writer retry |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- Dirty-tree contamination: no overlap was found in `share/skills/w-doc-update/SKILL.md` or `tests/test_doc_writer_quality_1422.py`; only kanban task files were dirty.
- Commit scope was reconstructed from reflog evidence rather than direct `git diff`, so file-ownership confidence is slightly reduced but still adequate for review.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| 1. Convention mapping table | `share/skills/w-doc-update/SKILL.md:30-34` | `tests/test_doc_writer_quality_1422.py:357`, `:365`, `:372`, `:379`, `:390`, `:451` | PASS |
| 2. 4-item checklist; no diagram items | `share/skills/w-doc-update/SKILL.md:43-63` | `tests/test_doc_writer_quality_1422.py:28`, `:36`, `:42`, `:231`, `:238`, `:244`, `:250`, `:265` | PASS |
| 3. Verification layers | `share/skills/w-doc-update/SKILL.md:47-48`, `:98-100` | `tests/test_doc_writer_quality_1422.py:48`, `:54`, `:284`, `:294` | PASS |
| 4. TODO marker format and insertion rules | `share/skills/w-doc-update/SKILL.md:74-87` | `tests/test_doc_writer_quality_1422.py:192`, `:198`, `:205`, `:212`, `:220` | PASS |
| 5. Gate-blocking rules | `share/skills/w-doc-update/SKILL.md:89-92` | `tests/test_doc_writer_quality_1422.py:405`, `:419` | PASS |
| 6. No-impact fast path | `share/skills/w-doc-update/SKILL.md:37` | `tests/test_doc_writer_quality_1422.py:433` | PASS |
| 7. Attribution rules for task-caused vs pre-existing | `share/skills/w-doc-update/SKILL.md:49-50` | `tests/test_doc_writer_quality_1422.py:481`, `:489`, `:501`, `:523` | FAIL |

### Confidence: 0.84
### Verdict: FAIL
### Action
- Reject to `backlog`. This is the second review cycle on the same proof-quality issue, and the remaining AC7 matcher weakness is still a review-blocking gap.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine the AC7 proof contract and re-issue the retry so the executable assertion must enforce the full Item 1 pre-existing clause (`insert a visible TODO marker`), not merely mention `pre-existing ... TODO marker` inside Item 1 | `tests/test_doc_writer_quality_1422.py`, `.owlbear/kanban/tasks/1423-p1-02-rewrite-w-doc-update-skill-4-item-checklist-verification-layers.md` | `share/skills/w-doc-update/SKILL.md:50` vs executable regex at `tests/test_doc_writer_quality_1422.py:492` and `:508`; the full clause appears only in docstrings/messages at `tests/test_doc_writer_quality_1422.py:466`, `:470`, `:497`, `:519` |
[[2026-05-09]]

## Architecture Review (Retry 2)
### Context
Second review rejection for AC7 proof-quality gap. The live SKILL.md content is correct (`share/skills/w-doc-update/SKILL.md:49-50`). The defect is exclusively in the test assertions.

### AC7 Refinement
**Previous AC7:** "Attribution rules for task-caused (fix inline) vs pre-existing (TODO marker)"
**Refined AC7:** "Attribution rules for task-caused (fix inline) vs pre-existing (insert a visible TODO marker) — test assertions for the pre-existing clause must require the verb 'insert' in the executable match, rejecting any co-occurrence of merely 'pre-existing' and 'TODO marker'"

### Specific Fix Required
In `tests/test_doc_writer_quality_1422.py`, two regex patterns use a lax OR branch:
- Line ~492 (`test_item1_preexisting_issues_insert_todo_marker`): `r"pre.existing.*insert.*TODO\s+marker|pre.existing.*TODO\s+marker"` — remove the second OR branch `|pre.existing.*TODO\s+marker`
- Line ~508 (`test_item1_has_both_attribution_rules`): same pattern — remove the second OR branch

After removal, both tests enforce `pre.existing.*insert.*TODO\s+marker` which requires "insert" in the pre-existing attribution rule. A mutation like "reference the TODO marker policy" would correctly fail.

### Evaluation
No re-evaluation of criteria needed — the SKILL.md content and all other AC lines remain unchanged from the first approved review. Only the test-writer needs to tighten two regex patterns.

### Test Depth
- AC7 fix: td:1 (one-line regex fix per test, smoke verification)
- All other AC lines: td:0 (unchanged)
- Test-writer: PROCEED (AC7 only)

### Challenge Results
Challenger: SKIPPED — mechanical regex fix, no architectural decision.

### Verdict: REFINE → APPROVE
### Action Taken: AC7 refined with specific assertion contract. Advancing to todo for test-writer to apply the two-line regex fix.

[[2026-05-09]]
REFINE → APPROVE: AC7 refined with explicit assertion contract requiring 'insert' verb in pre-existing clause match. Two-line regex fix in tests/test_doc_writer_quality_1422.py (remove second OR branch from lines ~492 and ~508). All other AC lines unchanged. Advancing to todo.