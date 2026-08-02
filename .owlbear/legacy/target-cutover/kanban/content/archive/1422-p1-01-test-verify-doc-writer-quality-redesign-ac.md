---
id: 1422
title: 'P1-01: Test — verify doc-writer quality redesign AC'
status: archived
priority: medium
created: 2026-05-08T00:32:15.467895+00:00
updated: 2026-05-08T22:26:59.893590+00:00
tags:
- phase-1
- scope:shared
- brief:doc-writer-quality
parent: 1421
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

Write `tests/test_doc_writer_quality_1422.py` — a pytest suite that verifies all 5 AC items from the brief:

1. `w-doc-update/SKILL.md` contains: convention mapping table (serve/{pkg} → README pattern), 4-item checklist with NO diagram items, verification procedure section with grep + LLM editorial layers, TODO marker insertion rules with visible blockquote format, gate-blocking rule distinguishing task-content vs pre-existing
2. `doc-writer.agent.md` contains NO references to diagrams, Excalidraw, or `.excalidraw` files
3. `doc-audit.prompt.md` includes: TODO marker batch resolution dimension, diagram ownership section, `describes`-based diagram verification
4. No references to old "item 5" or "item 6" (diagram maintenance/creation) remain in w-doc-update
5. TODO marker format grep pattern works: `> **TODO:** {category} — {description} [#{id}]`

**In scope:** Test file only. File-content assertions using `pathlib.Path.read_text()` and regex/string matching.
**Out of scope:** Implementing the actual skill/agent/prompt changes (that is #1423–#1425).

Brief: see parent #1421
[[2026-05-08]]
## Research
- Research doc: .owlbear/research/doc-writer-quality-test-tightening-1422.md
- Sources: 4 studied, 4 high-relevance (all codebase — brief, skill, tests, review evidence)
- Recommendation: Tighten AC1 test assertions to pin checklist item identity, not just count (confidence: 0.92)

Key findings:
- Builder implemented wrong 4-item checklist (Prose Accuracy / Docstrings / Attribution+Research / TODO Marker) vs brief's binding spec (README Verification / External Attribution / Research Doc / Deletion Detection)
- Docstrings item directly contradicts brief's out-of-scope declaration
- Deletion Detection dropped entirely from implementation
- Root cause: `test_checklist_has_exactly_four_items` asserts count only → any 4 items pass green
- Fix: 6 additional/modified assertions pinning item identity + negative assertion for docstrings
- No new follow-up tasks needed — existing #1422–#1425 chain covers the work
[[2026-05-08]]

## Refined AC (Architecture Review)

This section supersedes the original AC1 above. AC2–AC5 remain unchanged.

### AC1 (refined, td:2)

`w-doc-update/SKILL.md` must contain ALL of the following. Tests must assert both heading identity AND behavior-discriminating content per item (not just count).

1. Convention mapping table with `serve/{pkg}/src/**` → `serve/{pkg}/README.md` pattern
2. Exactly 4 checklist items under `### Item N:` headings with these exact names and behaviors:
   - `### Item 1: README Verification` — section must mention Layer 1 (grep for removed symbols) AND Layer 2 (LLM editorial full-file comparison). Discriminator: assert both "grep" and "editorial" (or "Layer 1"/"Layer 2") appear within this item's section.
   - `### Item 2: External Attribution` — section must reference `.owlbear/sources/overview.md` or external source tracking. Discriminator: assert "sources" or "overview.md" within this item's section.
   - `### Item 3: Research Doc` — section must reference verifying the research file linked from task body. Discriminator: assert "research" file verification language within this item's section.
   - `### Item 4: Deletion Detection` — section must specify child-task + DR protocol for deleted files. Discriminator: assert "child-task" or "DR" or "decision request" within this item's section.
3. No checklist item heading contains "Docstring" (case-insensitive) — module docstrings are explicitly out of scope per brief §Out of scope
4. No checklist item heading contains "Diagram" — diagrams moved to doc-audit
5. Verification procedure: Layer 1 (grep structural) + Layer 2 (LLM editorial)
6. TODO marker insertion rules with blockquote format `> **TODO:** {category} — {description} [#{id}]`
7. Gate rule: task-caused unverified content blocks; pre-existing passes
8. No-impact fast path: if changed files map to no READMEs → "no docs impact" with evidence

### AC2 (td:1)
Unchanged: `doc-writer.agent.md` no diagrams/Excalidraw references.

### AC3 (td:1)
Unchanged: `doc-audit.prompt.md` includes TODO batch resolution, diagram ownership, `describes`-based verification.

### AC4 (td:1)
Unchanged: No old items 5/6 in w-doc-update.

### AC5 (td:1)
Unchanged: TODO marker format matches `> **TODO:** {category} — {description} [#{id}]`.

### Test-writer guidance

- **Amend the existing file** `tests/test_doc_writer_quality_1422.py` — do not replace.
- AC2–AC5 tests (22 of 25) are already COVERED per reviewer. Preserve them.
- AC1 tests need updates: replace the count-only `test_checklist_has_exactly_four_items` with identity-pinning assertions per the behavior discriminators above. Add negative assertions for docstrings and no-impact fast path.
- Expected net: ~6 new/modified tests in the AC1 class, existing tests untouched.

## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One scope: test file assertions only |
| Interface clarity | PASS (after refinement) | AC1 now names items with behavior discriminators |
| Dependency correctness | PASS | No dependencies |
| Module layering | N/A | Test file with pathlib.Path.read_text(), no module imports |
| TDD compliance | PASS | This IS the test task |
| KISS/YAGNI | PASS | Minimal: ~6 new/modified assertions in existing file |
| Premise challenge | PASS | Research confirms false-green from count-only assertion |
| Pattern consistency | PASS | File-content assertions via regex/string — matches existing tests |
| Security surface | PASS | No system boundaries |
| Single domain | PASS | Agent ecosystem only |

### Challenge Results
- Challenger: block (confidence 0.37)
- Key challenges: (1) refined AC not yet written into #1422 body — addressed by this append, (2) names-only insufficient, need behavior discriminators — addressed with per-item discriminator phrases in refined AC, (3) regex-based tests can false-green on hollow prose or false-red on harmless rewording — addressed with specific discriminator phrases that balance precision vs brittleness, (4) parent says subtasks should be archived — superseded by reviewer rejection that returned chain to pipeline processing
- Architect response: accepted challenges 1-3, revised AC to include behavior-level discriminators. Challenge 4 rebutted: archival note was written before rejection, subtasks are now the active path.

### Test Depth
- Max depth: 2 (AC1)
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: AC1 refined with behavior-level discriminators per brief binding spec. AC2–AC5 unchanged (reviewer COVERED). Task advanced to todo.

[[2026-05-08]]
Architecture review complete. AC1 refined with behavior-level discriminators from binding brief — each of 4 checklist items (README Verification, External Attribution, Research Doc, Deletion Detection) now has specific discriminator phrases for regex-based assertions, plus negative assertions for docstrings (out-of-scope) and no-impact fast path. AC2–AC5 unchanged (reviewer COVERED). Challenger addressed: all 3 accepted challenges resolved in refined AC. Test-writer: amend existing file, ~6 new/modified AC1 tests.
[[2026-05-08]]
## Test-Writer Notes
- Test file: tests/test_doc_writer_quality_1422.py
- Classes: TestFromAC_DocUpdateSkillContent, TestFromAC_DocWriterAgentNoDiagrams, TestFromAC_DocAuditPromptContent, TestFromAC_NoOldDiagramItems, TestFromAC_TodoMarkerFormat, TestFromAC_ChecklistItemNames
- Amendments per arch review AC1 refinement:
  1. Removed `test_checklist_has_exactly_four_items` (count-only, superseded by identity-pinning tests in TestFromAC_ChecklistItemNames)
  2. Added `test_item3_research_doc_mentions_verification_language` — missing behavior discriminator for Item 3 (all 4 items now have per-item discriminator coverage)
- Total: 37 tests, all PASS
- ruff: clean
- Builder skip: implementation already complete (builder implemented correct checklist in eb98fff3 as part of #1421 parent task). All AC requirements satisfied. Advance directly to review.
- AC coverage: AC1 (identity-pinning ×13, negative assertions ×2), AC2 (×3), AC3 (×3), AC4 (×4), AC5 (×4). Full coverage across all 5 AC items with behavior discriminators for all 4 checklist items.
- Commit: db7f17e7
[[2026-05-08]]
## Builder Notes
- Implementation: no files changed (pass-through build cycle; task scope is test-only and implementation was already completed upstream)
- Tests: 37 passed from tests/test_doc_writer_quality_1422.py, 0 failed
- Coverage: N/A for this pass-through verification (no module instrumentation requested)
- ruff: clean
- Evidence summary: quality-runner scoped gate confirmed AC test suite is green and lint-clean; task body indicates builder skip with existing implementation commit db7f17e7
- Fixes applied: none
[[2026-05-08]]
## Review Evidence
### Test Results
- pytest: 37 passed, 0 failed (`tests/test_doc_writer_quality_1422.py`) via `quality-runner`

### Lint
- ruff: 0 violations on `tests/test_doc_writer_quality_1422.py`

### Coverage
- N/A. This task validates markdown artifacts only; `quality-runner` reported no instrumentable source module.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1 refined (`.owlbear/kanban/tasks/1422-p1-01-test-verify-doc-writer-quality-redesign-ac.md:54-68`) | Refined AC requires a convention mapping table and exactly 4 `### Item N:` headings with no Diagram/Docstring heading drift. Current tests prove only `serve/{pkg}` presence (`tests/test_doc_writer_quality_1422.py:15`), loose `serve/{pkg}.*README` text (`:21`), Item 1-4 name presence (`:202`, `:209`, `:215`, `:221`), and docstring filtering on extracted headings (`:227-233`). There is no exact-cardinality assertion, and the live skill still expresses mapping as bullets at `share/skills/w-doc-update/SKILL.md:26-29`, so the suite stays green against a refined-AC miss. | `test_convention_mapping_serve_pkg_pattern`, `test_convention_mapping_serve_pkg_to_readme`, `TestFromAC_ChecklistItemNames` | FAIL |
| AC2 | `grep_search` found 0 `diagram|excalidraw` matches in `share/agents/doc-writer.agent.md`; direct absence tests at `tests/test_doc_writer_quality_1422.py:77-98` are discriminating. | `TestFromAC_DocWriterAgentNoDiagrams` | PASS |
| AC3 | Canonical target is `.owlbear/prompts/doc-audit.prompt.md` per brief/parent deliverables; required sections are present at `.owlbear/prompts/doc-audit.prompt.md:46-78`, and the test constant points there at `tests/test_doc_writer_quality_1422.py:7-9`. | `TestFromAC_DocAuditPromptContent` | PASS |
| AC4 | AC says no old item 5/6 references remain. Current tests only ban `### Item 5`, `### Item 6`, and diagram rows (`tests/test_doc_writer_quality_1422.py:140-162`). They do not do a whole-file old-item reference search, so prose reintroductions could false-green. | `TestFromAC_NoOldDiagramItems` | FAIL |
| AC5 | Exact format line exists at `share/skills/w-doc-update/SKILL.md:73`, but proof is fragmented across separate prefix/task-ref/example assertions (`tests/test_doc_writer_quality_1422.py:170-194`). No single assertion proves the full one-line contract `> **TODO:** {category} — {description} [#{id}]`. | `TestFromAC_TodoMarkerFormat` | FAIL |

### Pass 1 — Critical
- Test quality: WEAK. The suite still false-greens on AC1's table/cardinality contract and under-proves AC4/AC5 exactness.
- Security review: no issues in current task scope.
- Data safety: no issues in current task scope.
- Test integrity: no weakening by builder is evident in this builder-skip cycle, but commit-diff proof was unavailable; small confidence deduction only.

### Informational
- No prior `## Review Evidence` section exists in `.owlbear/kanban/tasks/1422-p1-01-test-verify-doc-writer-quality-redesign-ac.md`; this is the first review cycle for this child task.
- Code-reader flagged an AC3 path concern, but the brief, parent task, and `tests/test_path_neutrality_1285.py` establish `.owlbear/prompts/doc-audit.prompt.md` as the canonical prompt location. This was verified directly and is not a blocker.

### Deductions
- `-0.08` AC1 false-green: table/cardinality contract not enforced.
- `-0.03` AC4 whole-file old-item reference proof missing.
- `-0.02` AC5 exact syntax proof fragmented.
- `-0.01` Dirty-tree and commit-diff checks unavailable in this tool surface.

### Confidence: 0.86
### Verdict: FAIL
### Action
- Reject to `todo`. The immediate defect in task `#1422` is test-proof quality: the suite does not yet force the current refined AC to go red when violated. Tightening the tests should intentionally RED against the live table/bullet mismatch and hand off the implementation fix to the downstream build task.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add an exact-cardinality assertion for `### Item N:` headings and a table-shape assertion that fails on bullet-based mapping prose. | `tests/test_doc_writer_quality_1422.py` | Refined AC1 at `.owlbear/kanban/tasks/1422-p1-01-test-verify-doc-writer-quality-redesign-ac.md:54-68`; current loose checks at `tests/test_doc_writer_quality_1422.py:15`, `:21`, `:202-233`; live bullets at `share/skills/w-doc-update/SKILL.md:26-29` |
| 2 | test-writer | Expand negative coverage so AC1/AC4 fail on any Diagram/Docstring/old item 5/6 reference in the relevant surface, not just legacy item names or Item 5/6 headings. | `tests/test_doc_writer_quality_1422.py` | Current negative checks only at `tests/test_doc_writer_quality_1422.py:28`, `:34`, `:140-162`, `:227-233` |
| 3 | test-writer | Replace the split TODO marker checks with one exact-line assertion or regex for `> **TODO:** {category} — {description} [#{id}]`. | `tests/test_doc_writer_quality_1422.py` | Current proof fragmented at `tests/test_doc_writer_quality_1422.py:170-194`; exact live contract line at `share/skills/w-doc-update/SKILL.md:73` |
[[2026-05-08]]
## Test-Writer Notes
- Retry cycle (Step 1b.1): reviewer-cited gaps addressed, all new tests pass against current correct implementation.
- Test file: tests/test_doc_writer_quality_1422.py
- Prior state: 42 tests (all passing) — 5 tests were already added since the review cycle (test_checklist_exactly_four_items, TestFromAC_ConventionMappingTable ×3, test_no_impact_fast_path_present)
- New tests added (3): 
  - `test_no_diagram_in_any_checklist_heading` (TestFromAC_ChecklistItemNames) — Follow-up 2: bans "Diagram" in any `### Item N:` heading, not just legacy strings
  - `test_no_item5_prose_reference` (TestFromAC_NoOldDiagramItems) — Follow-up 2: bans `\bItem 5\b` anywhere in prose/headings (beyond just heading format)
  - `test_no_item6_prose_reference` (TestFromAC_NoOldDiagramItems) — Follow-up 2: bans `\bItem 6\b` anywhere in prose/headings
- Total: 45 tests, all PASS
- Follow-up 1 (cardinality + table-shape): already addressed by test_checklist_exactly_four_items and TestFromAC_ConventionMappingTable ×3 (added before this retry)
- Follow-up 2 (expanded negatives): addressed by 3 new tests above
- Follow-up 3 (exact TODO format): test_todo_marker_complete_template already provides the exact-line assertion; split tests remain as complementary coverage
- ruff: 0 violations
- Builder skip: test-only retry, implementation already correct; advance directly to review
- Commit: 5cb92faf
[[2026-05-08]]
## Builder Notes
- Implementation: no files changed (non-implementation pass-through; task scope is test-only)
- Tests: 45 passed from tests/test_doc_writer_quality_1422.py, 0 failed, 0 skipped
- Coverage: N/A for markdown/test-content validation task (no instrumented source module)
- ruff: clean (0 violations)
- Approach: Confirmed test-writer retry notes and executed fresh scoped quality-runner gate before handoff.
- Evidence summary: quality-runner reported `failed: []`, `clean: true`, `pytest: 0`, `ruff: 0` for task-scoped suite.
- Fixes applied: none
[[2026-05-08]]
## Review Evidence
### Test Results
- pytest: 45 passed, 0 failed (`tests/test_doc_writer_quality_1422.py`) via `quality-runner`

### Lint
- ruff: 0 violations on `tests/test_doc_writer_quality_1422.py` via `quality-runner`

### Coverage
- N/A. `quality-runner` reported `coverage_modules=[]` and no instrumentable source-module scope for this markdown-artifact task.

### Pass 1 — Critical
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| AC1 refined mapping row (`.owlbear/kanban/tasks/1422-p1-01-test-verify-doc-writer-quality-redesign-ac.md:58`) | `test_convention_mapping_serve_pkg_pattern`, `test_convention_mapping_serve_pkg_to_readme`, `test_convention_mapping_is_table` | No. The live skill contains the required `serve/{pkg}/src/**` row at `share/skills/w-doc-update/SKILL.md:30`, but the suite only asserts generic `serve/{pkg}` presence at `tests/test_doc_writer_quality_1422.py:17`, loose `serve/{pkg}.*README` at `tests/test_doc_writer_quality_1422.py:24`, and generic table presence at `tests/test_doc_writer_quality_1422.py:357`. `grep_search` found no `src/**` match anywhere in `tests/test_doc_writer_quality_1422.py`, so removing the `src/**` selector while leaving another `serve/{pkg}`→README row would stay green. | MISSING |
| AC1 gate + no-impact semantics (`.owlbear/kanban/tasks/1422-p1-01-test-verify-doc-writer-quality-redesign-ac.md:68-69`) | `test_gate_rule_task_caused_content_blocks`, `test_gate_rule_preexisting_content_passes`, `test_no_impact_fast_path_present` | No. The live skill states `"no docs impact" with evidence` at `share/skills/w-doc-update/SKILL.md:37` and explicit block/pass semantics at `share/skills/w-doc-update/SKILL.md:91-92`, but the suite only token-checks `task.caused|task.introduced|task.content` at `tests/test_doc_writer_quality_1422.py:74`, `pre.existing` at `tests/test_doc_writer_quality_1422.py:80`, and bare `"no docs impact"` presence at `tests/test_doc_writer_quality_1422.py:342`. `grep_search` found no `with evidence and advance` match in the test file. | LAX |
| AC2 | `TestFromAC_DocWriterAgentNoDiagrams` | Yes. `grep_search` found 0 `diagram|excalidraw` matches in `share/agents/doc-writer.agent.md`, and the scoped suite stayed green. | COVERED |
| AC3 | `TestFromAC_DocAuditPromptContent` | Yes. Required prompt sections are present at `.owlbear/prompts/doc-audit.prompt.md:46`, `:61`, `:69`, and `:77`, and the scoped suite stayed green. | COVERED |
| AC4 | `TestFromAC_NoOldDiagramItems` | Yes. `grep_search` found 0 `Item 5|Item 6` matches in `share/skills/w-doc-update/SKILL.md`, and the scoped suite stayed green. | COVERED |
| AC5 | `test_todo_marker_complete_template` + `TestFromAC_TodoMarkerFormat` | Yes. The exact template is present at `share/skills/w-doc-update/SKILL.md:76`, and the suite now pins it with `test_todo_marker_complete_template` at `tests/test_doc_writer_quality_1422.py:220-222`. | COVERED |

#### Security Review
- No issues. Scope is markdown artifacts plus file-content assertions only.

#### Test Integrity
- No live evidence of builder-weakened or builder-removed `TestFromAC_*` assertions in this builder-skip cycle.
- Commit presence for the reported test-writer hashes was confirmed in `.git/logs/HEAD:2268` (`db7f17e7`) and `.git/logs/HEAD:2286` (`5cb92faf`), but I could not reconstruct a full additive diff or run a dirty-tree overlap check in this tool surface. Small confidence deduction only.

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | WEAK | The suite does not directly assert the required `src/**` selector (`tests/test_doc_writer_quality_1422.py:17`, `:24`, `:357`) and only token-checks the gate / no-impact semantics (`:74`, `:80`, `:342`). |
| Negative / exclusion coverage | ADEQUATE | AC2 and AC4 exclusions are enforced by direct whole-file absence checks and remained green. |
| Manual mutation reasoning | WEAK | Removing the `src/**` token from `share/skills/w-doc-update/SKILL.md:30` while leaving another `serve/{pkg}`→README row would keep the suite green. Likewise, weakening `share/skills/w-doc-update/SKILL.md:37` to drop `with evidence` or preserving the words `task-caused` / `pre-existing` while changing the actual pass/block semantics would not trip the current assertions. |
| Test independence | STRONG | Tests are isolated `Path.read_text()` assertions with no shared mutable state. |
| Descriptive names | STRONG | Test names remain AC-shaped and readable. |

#### Data Safety
- No issues.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1 refined (`.owlbear/kanban/tasks/1422-p1-01-test-verify-doc-writer-quality-redesign-ac.md:58`, `:68-69`) | Live skill satisfies the child contract at `share/skills/w-doc-update/SKILL.md:30`, `:37`, and `:91-92`, but current proof is incomplete: no `src/**` matches in `tests/test_doc_writer_quality_1422.py`, and semantic clauses are only token-checked at `:74`, `:80`, and `:342`. | `TestFromAC_DocUpdateSkillContent`, `TestFromAC_ConventionMappingTable`, `test_no_impact_fast_path_present` | FAIL |
| AC2 | `grep_search` found 0 `diagram|excalidraw` matches in `share/agents/doc-writer.agent.md`; scoped suite green. | `TestFromAC_DocWriterAgentNoDiagrams` | PASS |
| AC3 | Required sections present at `.owlbear/prompts/doc-audit.prompt.md:46`, `:61`, `:69`, `:77`; scoped suite green. | `TestFromAC_DocAuditPromptContent` | PASS |
| AC4 | `grep_search` found 0 `Item 5|Item 6` matches in `share/skills/w-doc-update/SKILL.md`; scoped suite green. | `TestFromAC_NoOldDiagramItems` | PASS |
| AC5 | Exact TODO template present at `share/skills/w-doc-update/SKILL.md:76` and directly asserted at `tests/test_doc_writer_quality_1422.py:220-222`. | `TestFromAC_TodoMarkerFormat` | PASS |

### Informational
- This is the second review cycle on child task `#1422`: an existing `## Review Evidence` section is already present at `.owlbear/kanban/tasks/1422-p1-01-test-verify-doc-writer-quality-redesign-ac.md:141`.
- Parent task `#1421` later tightened AC1 further to a five-row mapping table at `.owlbear/kanban/tasks/1421-doc-writer-quality-redesign-honest-verification-doc-audit-revision.md:384-392`. I did not need that broader parent contract to fail this child task: the child task’s own refined AC already requires the missing `src/**` proof and the under-proved gate / fast-path semantics.

### Deductions
- `-0.07` AC1 required `serve/{pkg}/src/**` mapping row is not directly asserted.
- `-0.05` AC1 gate / no-impact semantics are only token-checked.
- `-0.02` Dirty-tree overlap and full commit-diff reconstruction were unavailable in this reviewer tool surface.

### Confidence: 0.86
### Verdict: FAIL
### Action
- Reject to `backlog` under the loop-breaker rule. This is the second review failure on child task `#1422`, and the remaining blocker is AC1 proof quality / contract clarity rather than implementation correctness.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|---|---|---|---|
| 1 | architect | Re-open child task `#1422` AC1 so the next retry contract requires a discriminating assertion for the `serve/{pkg}/src/**` mapping row, not generic `serve/{pkg}` / `README` presence checks. | `.owlbear/kanban/tasks/1422-p1-01-test-verify-doc-writer-quality-redesign-ac.md`, `tests/test_doc_writer_quality_1422.py`, `share/skills/w-doc-update/SKILL.md` | Child AC at task line `58`; live row at skill line `30`; current assertions at test lines `17`, `24`, and `357`; no `src/**` matches in the test file. |
| 2 | architect | Rewrite the AC1 proof contract for gate and fast-path behavior so the next test-writer retry asserts `blocks`, `passes`, and `with evidence` semantics directly instead of token-presence regexes / substrings. | `.owlbear/kanban/tasks/1422-p1-01-test-verify-doc-writer-quality-redesign-ac.md`, `tests/test_doc_writer_quality_1422.py`, `share/skills/w-doc-update/SKILL.md` | Child AC at task lines `68-69`; live semantics at skill lines `37`, `91-92`; current checks at test lines `74`, `80`, and `342`; no `with evidence and advance` matches in the test file. |
[[2026-05-08]]

## AC1 Supplement (R3 — reviewer follow-up)

The following 2 assertions are MISSING from the current test suite per reviewer cycles 1 and 2. The test-writer must add them. All other tests (currently 50) remain unchanged.

### Gap 1: `src/**` mapping row (td:1)
`TestFromAC_ConventionMappingTable` must include a test asserting that the Step 1 convention mapping table contains the literal string `src/**`. This discriminates the first table row (`serve/{pkg}/src/**` → `serve/{pkg}/README.md`) from the generic `serve/{pkg}` presence checks already in the suite.

**Discriminator:** `assert "src/**" in step1` where `step1` is the Step 1 section text.

### Gap 2: `with evidence` in fast-path (td:1)
`TestFromAC_ConventionMappingTable.test_no_impact_fast_path_advances` (or a new test) must assert that `with evidence` appears in the Step 1 section alongside `no docs impact`. Currently `with evidence` only appears in an assertion message string (line 344), not in an executable predicate.

**Discriminator:** `assert "with evidence" in step1` within the same Step 1 section extraction used by the fast-path test.

### Test-writer guidance (R3)
- Amend `tests/test_doc_writer_quality_1422.py` — add 1 new test + 1 modified assertion.
- Expected net: +1 new test in `TestFromAC_ConventionMappingTable`, 1 assertion added to existing fast-path test.
- DO NOT modify or remove any existing tests.

## Architecture Review (R3)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Scoped to 2 missing test assertions |
| Interface clarity | PASS | Each gap names exact discriminator string |
| Dependency correctness | PASS | No dependencies |
| Module layering | N/A | Test file only |
| TDD compliance | PASS | This IS the test task |
| KISS/YAGNI | PASS | 2 assertions, no new abstractions |
| Premise challenge | PASS | Reviewer documented exact false-green mutations |
| Pattern consistency | PASS | Same `step1` section extraction pattern as existing tests |
| Security surface | PASS | No system boundaries |
| Single domain | PASS | Agent ecosystem only |

### Challenge Results
- Challenger: block (confidence 0.21)
- Root cause: challenger interpreted APPROVE as claiming tests already pass the new AC. Rebuttal: this approves the AC contract for test-writer implementation. The 2 gaps are precisely what the refined AC supplement defines. The test-writer will add them.
- Challenge 3 (stale count 45 vs 50): accepted — count corrected to 50 in R3 guidance.
- Challenges 1-2 (missing assertions): these ARE the gaps being defined. Not a blocker — they're the work item.

### Test Depth
- Max depth: 1 (both gaps are single-assertion additions)
- Test-writer: PROCEED

### Verdict: APPROVE
### Action: AC1 supplemented with 2 specific discriminator assertions per reviewer follow-up. Task advanced to todo.

[[2026-05-08]]
Architecture review R3 complete. AC1 supplemented with 2 specific discriminator assertions addressing reviewer follow-up: (1) `src/**` literal in convention mapping table test, (2) `with evidence` in fast-path test predicate. Both gaps confirmed via grep — 0 executable matches in current test file. Existing 50 tests unchanged. Challenger rebutted: approval is for AC contract, not test completion.
[[2026-05-08]]
## Test-Writer Notes (R3)
- Test file: tests/test_doc_writer_quality_1422.py
- Prior state: 50 tests (all passing per R3 guidance)
- New tests/assertions added (2):
  1. `test_convention_mapping_has_src_selector` (TestFromAC_ConventionMappingTable) — asserts `"src/**"` in Step 1 section; discriminates the specific `serve/{pkg}/src/**` → `serve/{pkg}/README.md` row from generic `serve/{pkg}` presence checks
  2. Added `assert "with evidence" in step1` to `test_no_impact_fast_path_advances` — asserts fast-path output is `"no docs impact" with evidence`, not bare phrase
- Total: 51 tests, all PASS
- ruff: clean (0 violations)
- Both assertions pass against current correct implementation (src/** at SKILL.md:30; with evidence at fast-path sentence)
- Pattern: implementation preceded tests (builder completed in #1421); these tests strengthen the suite against future regressions per reviewer R3 required follow-up
- AC coverage: AC1 (all gaps addressed — src/** Gap 1, with evidence Gap 2), AC2–AC5 unchanged
- Commit: 5de383ce
[[2026-05-08]]
## Builder Notes
- Implementation: no files changed (task scope is test-only verification)
- Tests: 51 passed, 0 failed, 0 skipped (`tests/test_doc_writer_quality_1422.py`)
- Coverage: N/A (no instrumentable source module in scope)
- ruff: clean (0 violations)
- Approach: verified latest test-writer retry state with a fresh scoped quality-runner gate before advancing
- Evidence summary: quality-runner reported pytest exit 0 and ruff exit 0 with `failed: []` and `clean: true`
- Fixes applied: none
[[2026-05-08]]
## Review Evidence
### Test Results
- pytest: 51 passed, 0 failed (`tests/test_doc_writer_quality_1422.py`) via `quality-runner`

### Lint
- ruff: 0 violations on `tests/test_doc_writer_quality_1422.py` via `quality-runner`
- Initial `quality-runner` lint attempt hit an environment error; retry with an explicit workspace-root hint succeeded cleanly.

### Coverage
- N/A. This task reviews markdown-artifact assertions only; `coverage_modules=[]` for the scoped run.

### Pass 1 — Critical
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| AC1 gate rule (`.owlbear/kanban/tasks/1422-p1-01-test-verify-doc-writer-quality-redesign-ac.md:68`) | `test_gate_rule_task_caused_blocks`, `test_gate_rule_preexisting_passes` | No. The current tests assert `task-caused` and `blocks` separately (`tests/test_doc_writer_quality_1422.py:407`, `:411`) and `pre-existing` and `passes` separately (`:418`, `:422`). If the live gate rules at `share/skills/w-doc-update/SKILL.md:91-92` were swapped to `task-caused ... passes` and `pre-existing ... blocks`, all four assertions would still pass. | LAX |
| AC1 no-impact fast path (`.owlbear/kanban/tasks/1422-p1-01-test-verify-doc-writer-quality-redesign-ac.md:69`) | `test_no_impact_fast_path_advances` | Yes. The test now pins `no docs impact`, `with evidence`, and `advance` inside the Step 1 section (`tests/test_doc_writer_quality_1422.py:427-437`). | COVERED |
| AC2 | `TestFromAC_DocWriterAgentNoDiagrams` | Yes. Direct absence tests exist at `tests/test_doc_writer_quality_1422.py:88`, `:98`, `:104`, and `grep_search` found 0 `diagram|excalidraw` matches in `share/agents/doc-writer.agent.md`. | COVERED |
| AC3 | `TestFromAC_DocAuditPromptContent` | Yes. Section-presence tests exist at `tests/test_doc_writer_quality_1422.py:114`, `:124`, `:133`; the prompt contains the required sections at `.owlbear/prompts/doc-audit.prompt.md:46`, `:61`, `:69`, `:71-78`. | COVERED |
| AC4 | `TestFromAC_NoOldDiagramItems` | Yes. Whole-file old-item bans exist at `tests/test_doc_writer_quality_1422.py:174`, `:181`, and `grep_search` found 0 `Item 5|Item 6` matches in `share/skills/w-doc-update/SKILL.md`. | COVERED |
| AC5 | `test_todo_marker_complete_template` | Yes. The exact template is asserted at `tests/test_doc_writer_quality_1422.py:220` and exists at `share/skills/w-doc-update/SKILL.md:76`. | COVERED |

#### Security Review
- No issues. Scope is markdown artifacts plus file-content assertions only.

#### Test Integrity
- No live evidence of builder-weakened or builder-removed `TestFromAC_*` assertions in this builder-skip cycle.
- Commit presence for the test-writer hashes was confirmed in `.git/logs/HEAD:2268` (`db7f17e7`), `.git/logs/HEAD:2286` (`5cb92faf`), and `.git/logs/HEAD:2314` (`5de383ce`).
- Full additive diff reconstruction and dirty-tree overlap checks were not available in this reviewer tool surface. Small confidence deduction only.

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | WEAK | AC1 gate semantics are still under-proved: the suite uses separate whole-file token checks at `tests/test_doc_writer_quality_1422.py:407`, `:411`, `:418`, `:422` rather than binding each subject to its verb. |
| Negative / exclusion coverage | ADEQUATE | AC2 and AC4 use direct absence assertions and remained green against the live files. |
| Manual mutation reasoning | WEAK | Swapping the verbs in the live gate rules at `share/skills/w-doc-update/SKILL.md:91-92` would preserve all four gate-rule assertions. |
| Test independence | STRONG | Tests are isolated `Path.read_text()` assertions with no shared mutable state. |
| Descriptive names | STRONG | Test names remain AC-shaped and readable. |

#### Data Safety
- No issues.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1 refined (`.owlbear/kanban/tasks/1422-p1-01-test-verify-doc-writer-quality-redesign-ac.md:54-69`) | The suite now covers the previously missing R3 gaps: `src/**` at `tests/test_doc_writer_quality_1422.py:397` and fast-path `with evidence` / `advance` at `:427-437`. The remaining blocker is item 7 gate semantics: current token checks at `:407`, `:411`, `:418`, `:422` would not fail on a swapped-semantics regression against `share/skills/w-doc-update/SKILL.md:91-92`. | `TestFromAC_DocUpdateSkillContent`, `TestFromAC_ChecklistItemNames`, `TestFromAC_ConventionMappingTable` | FAIL |
| AC2 | Agent file stayed clean under direct absence tests and grep scan. | `TestFromAC_DocWriterAgentNoDiagrams` | PASS |
| AC3 | Prompt file contains TODO batch resolution, diagram ownership, and describes-based verification sections. | `TestFromAC_DocAuditPromptContent` | PASS |
| AC4 | No old `Item 5` / `Item 6` references remain in the live skill; whole-file tests cover the condition. | `TestFromAC_NoOldDiagramItems` | PASS |
| AC5 | Exact TODO template is present in the skill and asserted exactly in the suite. | `TestFromAC_TodoMarkerFormat` | PASS |

### Informational
- There are already two `## Review Evidence` sections in the task file at `.owlbear/kanban/tasks/1422-p1-01-test-verify-doc-writer-quality-redesign-ac.md:141` and `:213`; this is the third review cycle.
- The R3 `src/**` and fast-path `with evidence` gaps are no longer blockers; those additions landed and are behaving as intended.
- The current implementation in `share/skills/w-doc-update/SKILL.md` is correct. The remaining issue is proof quality / AC carry-through, not implementation behavior.

### Deductions
- `-0.08` AC1 gate-rule assertions still false-green on swapped semantics.
- `-0.02` Full additive diff / dirty-tree overlap checks unavailable in this tool surface.

### Confidence: 0.88
### Verdict: FAIL
### Action
- Reject to `backlog` under the loop-breaker rule. This is the third review cycle, and the remaining blocker is AC/test-quality alignment rather than implementation correctness.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine AC1 item 7 so the next retry requires executable subject-verb coupling for both gate rules, for example exact line assertions or section-scoped sentence matches for `task-caused ... blocks` and `pre-existing ... passes`, then return the task to the test-writer. | `.owlbear/kanban/tasks/1422-p1-01-test-verify-doc-writer-quality-redesign-ac.md`, `tests/test_doc_writer_quality_1422.py`, `share/skills/w-doc-update/SKILL.md` | Prior reviewer requirement at `.owlbear/kanban/tasks/1422-p1-01-test-verify-doc-writer-quality-redesign-ac.md:280`; current split-token checks at `tests/test_doc_writer_quality_1422.py:407`, `:411`, `:418`, `:422`; live gate semantics at `share/skills/w-doc-update/SKILL.md:91-92` |
[[2026-05-08]]

## AC1 Supplement (R4 — gate-rule coupling)

The 2 existing gate-rule tests (`test_gate_rule_task_caused_blocks`, `test_gate_rule_preexisting_passes`) use whole-file token checks that false-green on swapped semantics. Replace them with line-scoped coupling assertions.

### Gap: Gate-rule subject-verb coupling (td:1)

Replace the 4 separate whole-file `assert "token" in content` calls across the 2 gate-rule tests with line-scoped assertions that bind subject to verb on the same line:

- `test_gate_rule_task_caused_blocks`: assert that at least one line in the Gate rules section contains BOTH `task-caused` AND `blocks`. (Example: `any("task-caused" in line and "blocks" in line for line in gate_lines)`)
- `test_gate_rule_preexisting_passes`: assert that at least one line in the Gate rules section contains BOTH `pre-existing` AND `passes`. (Same pattern.)

This ensures swapping the verbs would fail the test.

### Test-writer guidance (R4)
- Amend `tests/test_doc_writer_quality_1422.py` — modify the 2 existing gate-rule tests only.
- Extract the "Gate rules:" section (2 bullet lines following the `Gate rules:` heading in Step 1) and use line-level iteration.
- Total test count stays at 51 — no new tests, just tighter assertions in 2 existing tests.
- DO NOT modify or remove any other tests.

[[2026-05-08]]

### R4 Correction (challenger feedback)

The R4 supplement above incorrectly says "Gate rules: heading in Step 1" — the gate rules are in **Step 2** at `share/skills/w-doc-update/SKILL.md:91-92`. The test-writer should iterate lines of the **full file content** (as the current tests already do with `SKILL_DOC_UPDATE.read_text()`) and apply line-scoped coupling. No section extraction helper is needed — just check `any("task-caused" in line and "blocks" in line for line in content.splitlines())` and the equivalent for `pre-existing`/`passes`.

[[2026-05-08]]
## Architecture Review (R4)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Scoped to tightening 2 existing assertion bodies |
| Interface clarity | PASS | Exact discriminator pattern specified with code example |
| Dependency correctness | PASS | No dependencies |
| Module layering | N/A | Test file only |
| TDD compliance | PASS | This IS the test task |
| KISS/YAGNI | PASS | Modify 2 assertions, no new tests or abstractions |
| Premise challenge | PASS | Reviewer documented exact false-green mutation (swap verbs → still green) |
| Pattern consistency | PASS | Uses same `content.splitlines()` pattern available in test file |
| Security surface | PASS | No system boundaries |
| Single domain | PASS | Agent ecosystem only |

### Challenge Results
- Challenger: reconsider (confidence 0.74)
- Challenge 1 (Step 1 vs Step 2 locator): ACCEPTED — corrected in R4 supplement addendum. Gate rules are in Step 2, not Step 1. Test-writer guidance updated to use full-file line iteration.
- Challenge 2 (change-surface understatement): noted but not a blocker. Modifying assertion bodies within 2 existing test functions is minimal.
- Challenge 3 (contradictory authority — research vs review): the research doc predates the reviewer's gate-rule analysis. Review evidence supersedes research per normal lifecycle progression. No reconciliation needed — downstream agents follow the latest AC supplement.
- Challenge 4 (duplicate surface): the same tokens appearing elsewhere in the skill file actually reinforces the need for line-scoped coupling rather than whole-file checks.

### Test Depth
- Max depth: 1 (single-assertion modifications)
- Test-writer: PROCEED

### Verdict: APPROVE
### Action: AC1 supplemented with gate-rule subject-verb coupling requirement per reviewer R3 follow-up. Section locator corrected per challenger feedback. Task advanced to todo.
[[2026-05-08]]
## Test-Writer Notes (R4)
- Test file: tests/test_doc_writer_quality_1422.py
- Prior state: 51 tests (all passing — correct implementation already in place)
- Changes: tightened 2 existing gate-rule tests — replaced 4 whole-file `assert "token" in content` calls with line-scoped `any("subject" in line and "verb" in line for line in content.splitlines())` checks
  - `test_gate_rule_task_caused_blocks`: now asserts a single line has BOTH `task-caused` AND `blocks`
  - `test_gate_rule_preexisting_passes`: now asserts a single line has BOTH `pre-existing` AND `passes`
- Total: 51 tests, all PASS
- ruff: clean (0 violations)
- Mutation resistance: swapping the verbs in `share/skills/w-doc-update/SKILL.md:91-92` now fails both tests (was false-green under old whole-file token checks)
- Builder skip: test-only, implementation already correct — advance to review
- AC coverage: AC1 gate-rule coupling (R4 Gap: addressed), all prior AC2–AC5 unchanged
- Commit: c3972833
[[2026-05-08]]
## Builder Notes
- Implementation: no files changed (test-only task; verification pass-through)
- Tests: 51 passed, 0 failed, 0 skipped (`tests/test_doc_writer_quality_1422.py`)
- Coverage: N/A for markdown-artifact assertions (`coverage_modules=[]` in scoped gate)
- ruff: clean (0 violations)
- Approach: validated current AC test suite state and executed a fresh scoped quality-runner gate prior to review handoff.
- Evidence summary: quality-runner reported `failed: []`, `clean: true`, pytest exit 0, ruff exit 0.
- Fixes applied: none
[[2026-05-08]]
## Review Evidence
### Test Results
- pytest: 51 passed, 0 failed (`tests/test_doc_writer_quality_1422.py`) via `quality-runner`

### Lint: clean
- ruff: 0 violations on `tests/test_doc_writer_quality_1422.py` via `quality-runner`

### Coverage: N/A
- `coverage_modules=[]`; this is a markdown-artifact test task with no instrumentable source module in scope.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 mapping row (`.owlbear/kanban/tasks/1422-p1-01-test-verify-doc-writer-quality-redesign-ac.md:58`) | `test_convention_mapping_serve_pkg_to_readme`, `test_convention_mapping_has_src_selector` | No. `test_convention_mapping_serve_pkg_to_readme` at `tests/test_doc_writer_quality_1422.py:21` accepts any `serve/{pkg}.*README` match anywhere in the file, and `test_convention_mapping_has_src_selector` at `tests/test_doc_writer_quality_1422.py:397` only requires `src/**` somewhere in Step 1. If the Step 1 src row at `share/skills/w-doc-update/SKILL.md:30` were changed to point somewhere other than `serve/{pkg}/README.md` while the pyproject/tests row still mapped to `serve/{pkg}/README.md`, both tests would stay green. | MISSING |
| AC1 gate + no-impact semantics (`.owlbear/kanban/tasks/1422-p1-01-test-verify-doc-writer-quality-redesign-ac.md:68-69`) | `test_gate_rule_task_caused_blocks`, `test_gate_rule_preexisting_passes`, `test_no_impact_fast_path_advances` | Yes. The latest retry now pins subject+verb coupling at `tests/test_doc_writer_quality_1422.py:405` and `:415`, and it pins `no docs impact` + `with evidence` + `advance` at `tests/test_doc_writer_quality_1422.py:425` against `share/skills/w-doc-update/SKILL.md:37`, `:91`, and `:92`. | COVERED |
| AC2 | `TestFromAC_DocWriterAgentNoDiagrams` | Yes. Any `diagram`, `Excalidraw`, or `.excalidraw` reference would trip the direct absence tests at `tests/test_doc_writer_quality_1422.py:88`, `:98`, and `:104`. | COVERED |
| AC3 | `TestFromAC_DocAuditPromptContent` | Yes for the stated presence contract. The prompt contains the required sections at `.owlbear/prompts/doc-audit.prompt.md:46`, `:61`, `:69`, and `:77`, and the suite asserts them at `tests/test_doc_writer_quality_1422.py:114`, `:124`, and `:133`. | COVERED |
| AC4 | `TestFromAC_NoOldDiagramItems` | Yes. Whole-file bans at `tests/test_doc_writer_quality_1422.py:174` and `:181` would fail on any `Item 5` / `Item 6` reintroduction; live skill is clean. | COVERED |
| AC5 | `test_todo_marker_complete_template` | Yes. The exact template is asserted at `tests/test_doc_writer_quality_1422.py:220` and exists at `share/skills/w-doc-update/SKILL.md:76`. | COVERED |

#### Security Review
- No issues. Scope is a stdlib-only file-content suite plus markdown artifacts.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---|---|---|
| `TestFromAC_*` suite in `tests/test_doc_writer_quality_1422.py` | No weakening, skip, or xfail markers are visible in the current snapshot. Commit presence for task hashes was confirmed in `.git/logs/HEAD:2268` (`db7f17e7`), `.git/logs/HEAD:2286` (`5cb92faf`), `.git/logs/HEAD:2314` (`5de383ce`), and `.git/logs/HEAD:2323` (`c3972833`), but full additive diff reconstruction was unavailable in this tool surface. | PRESERVED (low-confidence) |

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | WEAK | AC1's exact mapping-row contract is still split across `tests/test_doc_writer_quality_1422.py:21` and `:397` instead of proving the single row at `share/skills/w-doc-update/SKILL.md:30`. |
| Negative / exclusion coverage | ADEQUATE | AC2 and AC4 use direct absence assertions and remained green against the live files. |
| Manual mutation reasoning | WEAK | Repointing the src row away from `serve/{pkg}/README.md` while leaving the pyproject/tests row intact at `share/skills/w-doc-update/SKILL.md:31` would keep the current AC1 mapping tests green. |
| Test independence | STRONG | Tests are isolated `Path.read_text()` checks over fixed files with no shared mutable state. |
| Descriptive names | STRONG | Names remain AC-shaped and readable. |

#### Data Safety
- No issues.

#### Implementation-Aware Gaps
- `tests/test_doc_writer_quality_1422.py` still lacks a discriminating assertion that couples `serve/{pkg}/src/**` to `serve/{pkg}/README.md` on the same Step 1 mapping row. That leaves a significant untested branch in AC1's mapping contract.

#### Builder Process Quality
| Metric | Value |
|---|---|
| Builder Notes sections | 4 |
| Approach variation | Yes — prior failures produced substantive AC supplements (R3 and R4) before the latest retry |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- There are already three `## Review Evidence` sections in the task file at `.owlbear/kanban/tasks/1422-p1-01-test-verify-doc-writer-quality-redesign-ac.md:141`, `:213`, and `:356`; this is the fourth review cycle, so the loop-breaker rule applies on any further FAIL.
- `quality-runner` independently reported `51 passed / 0 failed` and `ruff: clean`; the blocker is proof quality, not runtime behavior.
- `code-reader` also flagged broader `w-doc-update` workflow semantics such as the full-file-read sentence at `share/skills/w-doc-update/SKILL.md:46`, but the child task's refined AC at `.owlbear/kanban/tasks/1422-p1-01-test-verify-doc-writer-quality-redesign-ac.md:54-69` does not explicitly carry that clause, so I did not use it as a blocking defect.
- Dirty-tree overlap and full additive diff reconstruction were unavailable in this tool surface.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1 refined (`.owlbear/kanban/tasks/1422-p1-01-test-verify-doc-writer-quality-redesign-ac.md:54-69`) | The live skill satisfies the current child contract at `share/skills/w-doc-update/SKILL.md:30`, `:37`, `:91`, and `:92`. The latest retry closes the prior gate/no-impact gap, but it still does not prove the exact row `serve/{pkg}/src/**` → `serve/{pkg}/README.md`: `tests/test_doc_writer_quality_1422.py:21` matches any `serve/{pkg}.*README` row, and `:397` checks only for `src/**`. | `test_convention_mapping_serve_pkg_to_readme`, `test_convention_mapping_has_src_selector`, `test_gate_rule_task_caused_blocks`, `test_gate_rule_preexisting_passes`, `test_no_impact_fast_path_advances` | FAIL |
| AC2 | Agent file is clean under direct absence checks and direct file read. | `TestFromAC_DocWriterAgentNoDiagrams` | PASS |
| AC3 | Prompt file contains TODO batch resolution, diagram ownership, and describes-based verification sections. | `TestFromAC_DocAuditPromptContent` | PASS |
| AC4 | No old `Item 5` / `Item 6` references remain in the live skill; whole-file tests cover the condition. | `TestFromAC_NoOldDiagramItems` | PASS |
| AC5 | Exact TODO template is present in the skill and asserted exactly in the suite. | `TestFromAC_TodoMarkerFormat` | PASS |

### Confidence: 0.89
### Verdict: FAIL
### Action
- Reject to `backlog`. Only one AC1 proof defect remains, but this task already has three prior review sections, so the pipeline loop-breaker rule applies on a fourth review failure.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Reconcile AC1's retry contract with its still-binding exact-row requirement, then return the task to the test-writer with a proof obligation that couples `serve/{pkg}/src/**` and `serve/{pkg}/README.md` on the same mapping row. | `.owlbear/kanban/tasks/1422-p1-01-test-verify-doc-writer-quality-redesign-ac.md`, `tests/test_doc_writer_quality_1422.py`, `share/skills/w-doc-update/SKILL.md` | Child AC line `58` requires the exact pattern; live row is at `share/skills/w-doc-update/SKILL.md:30`; current proof remains split across `tests/test_doc_writer_quality_1422.py:21` and `:397`, which still false-greens on a wrong src-row destination. |
[[2026-05-08]]

## AC1 Supplement (R5 — exact-row coupling)

The 1 remaining reviewer gap is that `test_convention_mapping_has_src_selector` checks for `src/**` alone and `test_convention_mapping_serve_pkg_to_readme` checks `serve/{pkg}.*README` alone — they are not coupled to the same table row. The test-writer must add one coupling assertion.

### Gap: exact-row coupling for `serve/{pkg}/src/**` → `serve/{pkg}/README.md` (td:1)

Add a new test in `TestFromAC_ConventionMappingTable` that asserts at least one line in the Step 1 section contains BOTH `serve/{pkg}/src/**` AND `serve/{pkg}/README.md`:

```python
assert any(
    "serve/{pkg}/src/**" in line and "serve/{pkg}/README.md" in line
    for line in step1.splitlines()
), "Convention mapping must have a single row coupling serve/{pkg}/src/** to serve/{pkg}/README.md"
```

This proves the exact first table row at `share/skills/w-doc-update/SKILL.md:30` as a coupled pair, not two independent tokens. Same line-coupling pattern as R4 gate-rule fix.

### Test-writer guidance (R5)
- Amend `tests/test_doc_writer_quality_1422.py` — add 1 new test in `TestFromAC_ConventionMappingTable`.
- Use `self._step1_section()` helper (already exists at line 351).
- Expected: +1 test → 52 total. DO NOT modify or remove any existing tests.


[[2026-05-08]]

## Architecture Review (R5)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single coupling assertion in existing test class |
| Interface clarity | PASS | Exact discriminator strings specified with code example |
| Dependency correctness | PASS | No dependencies |
| Module layering | N/A | Test file only |
| TDD compliance | PASS | This IS the test task |
| KISS/YAGNI | PASS | 1 new test, no abstractions |
| Premise challenge | PASS | Reviewer documented exact false-green mutation across 4 cycles |
| Pattern consistency | PASS | Same line-coupling pattern as R4 gate-rule fix, same `_step1_section()` helper |
| Security surface | PASS | No system boundaries |
| Single domain | PASS | Agent ecosystem only |

### Challenge Results
- Challenger: block (confidence 0.24)
- Key challenges: (1) initial proposal used `src/**` + `README.md` — too loose, wouldn't prove `serve/{pkg}` on both sides. ACCEPTED — revised to use full literals `serve/{pkg}/src/**` and `serve/{pkg}/README.md`. (2) Step 1 has two `serve/{pkg}` → README rows at SKILL.md:30-31, so decomposed proofs can false-green. ACCEPTED — the line-coupling assertion with full column literals resolves this by binding source+destination on the same row. (3) Contract narrowing from td:2 to td:1 — noted; the R5 supplement only covers this one remaining gap (td:1), the overall AC1 remains td:2 from prior supplements.
- Architect response: accepted challenges 1-2, revised supplement to use full literal tokens. Challenge 3 noted — the original AC1 td:2 designation covers the full AC1 scope; the R5 gap is a single-assertion addition within that scope.

### Test Depth
- Max depth: 1 (single coupling assertion)
- Test-writer: PROCEED

### Verdict: APPROVE
### Action: AC1 supplemented with exact-row coupling assertion using full `serve/{pkg}/src/**` and `serve/{pkg}/README.md` literals per reviewer R4 follow-up. Challenger feedback integrated — strengthened from generic `src/**`+`README.md` to full column literals. Task advanced to todo.


[[2026-05-08]]
Architecture review R5 complete. AC1 supplemented with exact-row coupling assertion: test must assert that a single line in the Step 1 convention mapping table contains BOTH `serve/{pkg}/src/**` AND `serve/{pkg}/README.md`, proving the first mapping row as a coupled pair. Challenger feedback integrated — initial generic `src/**`+`README.md` proposal strengthened to full column literals after challenger correctly identified false-green path via second `serve/{pkg}` row at SKILL.md:31. Test-writer: add 1 new test using existing `_step1_section()` helper → 52 total.
[[2026-05-08]]
## Test-Writer Notes (R5)
- Test file: tests/test_doc_writer_quality_1422.py
- Prior state: 51 tests (all passing — correct implementation already in place)
- New test added (1): `test_convention_mapping_exact_src_row_coupled` (TestFromAC_ConventionMappingTable)
  - Asserts at least one line in Step 1 contains BOTH `serve/{pkg}/src/**` AND `serve/{pkg}/README.md`
  - Proves the exact first table row at `share/skills/w-doc-update/SKILL.md:30` as a coupled pair
  - Closes R5 Gap: split checks on each token independently were false-green when the src row pointed to a wrong destination
- Total: 52 tests, all PASS
- ruff: clean (0 violations)
- Pattern: `any("serve/{pkg}/src/**" in line and "serve/{pkg}/README.md" in line for line in step1.splitlines())` — same line-coupling pattern as R4 gate-rule fix
- Builder skip: test-only, implementation already correct — advance directly to review
- AC coverage: AC1 R5 gap addressed (exact row coupling), all prior AC2–AC5 unchanged
- Commit: 1a455215
[[2026-05-08]]
## Builder Notes
- Implementation: no files changed (test-only task; non-implementation pass-through)
- Tests: 52 passed, 0 failed, 0 skipped (`tests/test_doc_writer_quality_1422.py`)
- Coverage: N/A for markdown-artifact assertion scope (`coverage_modules=[]`)
- ruff: clean (0 violations)
- Approach: honored test-writer builder-skip guidance and executed a fresh scoped quality-runner gate before handoff
- Evidence summary: quality-runner reported `failed: []`, `clean: true`, pytest exit 0, ruff exit 0
- Fixes applied: none
[[2026-05-08]]
## Review Evidence
### Test Results
- pytest: 52 passed, 0 failed (`tests/test_doc_writer_quality_1422.py`) via `quality-runner`

### Lint
- ruff: 0 violations on `tests/test_doc_writer_quality_1422.py` via `quality-runner`

### Coverage
- N/A. This is a markdown-artifact assertion task with no instrumentable source module in scope; `quality-runner` reported coverage as not applicable.

### Pass 1 — Critical
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| AC1 item 7 gate rule (`.owlbear/kanban/tasks/1422-p1-01-test-verify-doc-writer-quality-redesign-ac.md:68`) | `test_gate_rule_task_caused_blocks`, `test_gate_rule_preexisting_passes` | No. The executable predicates at `tests/test_doc_writer_quality_1422.py:408` and `:418` only bind subject to verb. The required `unverified` token from the AC and live skill text at `share/skills/w-doc-update/SKILL.md:91-92` appears only in assertion-message strings at `tests/test_doc_writer_quality_1422.py:75` and `:81`, so mutating the live rule to `verified content` would stay green. | MISSING |
| AC1 item 8 no-impact fast path (`.owlbear/kanban/tasks/1422-p1-01-test-verify-doc-writer-quality-redesign-ac.md:69`) | `test_no_impact_fast_path_present`, `test_no_impact_fast_path_advances` | No. The executable predicates at `tests/test_doc_writer_quality_1422.py:342`, `:427`, `:430`, and `:434` prove the output phrase, evidence wording, and advance action, but the trigger `if changed files map to no READMEs` from the AC and live skill text at `share/skills/w-doc-update/SKILL.md:36-37` appears only in an assertion-message string at `tests/test_doc_writer_quality_1422.py:344`. Changing the trigger while preserving the output sentence would stay green. | MISSING |
| AC2 | `TestFromAC_DocWriterAgentNoDiagrams` | Yes. `grep_search` found 0 `diagram|excalidraw` matches in `share/agents/doc-writer.agent.md`, and the direct absence tests remain green. | COVERED |
| AC3 | `TestFromAC_DocAuditPromptContent` | Yes. Required sections are present at `.owlbear/prompts/doc-audit.prompt.md:46`, `:61`, `:69`, and `:77`, and the scoped suite remains green. | COVERED |
| AC4 | `TestFromAC_NoOldDiagramItems` | Yes. `grep_search` found 0 `Item 5|Item 6` matches in `share/skills/w-doc-update/SKILL.md`, and the whole-file bans remain green. | COVERED |
| AC5 | `test_todo_marker_complete_template` | Yes. The exact template exists at `share/skills/w-doc-update/SKILL.md:76` and is asserted exactly at `tests/test_doc_writer_quality_1422.py:220`. | COVERED |

#### Security Review
- No issues. Scope is markdown artifacts plus local `Path.read_text()` assertions only.

#### Test Integrity
- Commit presence for task-related test-writer hashes was confirmed in `.git/logs/HEAD:2268` (`db7f17e7`), `.git/logs/HEAD:2286` (`5cb92faf`), `.git/logs/HEAD:2314` (`5de383ce`), `.git/logs/HEAD:2323` (`c3972833`), and `.git/logs/HEAD:2331` (`1a455215`).
- The latest builder cycle is pass-through / builder-skip with no implementation changes (`.owlbear/kanban/tasks/1422-p1-01-test-verify-doc-writer-quality-redesign-ac.md:654`).
- Full additive diff reconstruction and dirty-tree overlap checks were not available in this reviewer tool surface. Small confidence deduction only.

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | WEAK | AC1 still under-proves `unverified` and `no READMEs`: those tokens appear only in assertion messages at `tests/test_doc_writer_quality_1422.py:75`, `:81`, and `:344`, while executable predicates at `:408`, `:418`, `:427`, `:430`, and `:434` do not bind them. |
| Negative / exclusion coverage | ADEQUATE | AC2 and AC4 use direct absence checks and the live files are clean. |
| Manual mutation reasoning | WEAK | Replacing `unverified` with `verified` in `share/skills/w-doc-update/SKILL.md:91-92` or changing the fast-path trigger at `share/skills/w-doc-update/SKILL.md:36-37` while keeping the output sentence intact would preserve a green suite. |
| Test independence | STRONG | The suite uses isolated file reads with no shared mutable state. |
| Descriptive names | STRONG | Test names are AC-shaped and readable. |

#### Data Safety
- No issues.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1 refined (`.owlbear/kanban/tasks/1422-p1-01-test-verify-doc-writer-quality-redesign-ac.md:68-69`) | The live skill currently satisfies the contract at `share/skills/w-doc-update/SKILL.md:36-37` and `:91-92`, but the suite does not executable-prove the `unverified` and `no READMEs` parts of those clauses. | `test_gate_rule_task_caused_blocks`, `test_gate_rule_preexisting_passes`, `test_no_impact_fast_path_present`, `test_no_impact_fast_path_advances` | FAIL |
| AC2 | Agent file is clean under direct absence checks and grep scan. | `TestFromAC_DocWriterAgentNoDiagrams` | PASS |
| AC3 | Prompt file contains TODO marker batch resolution, diagram ownership, and describes-based verification sections. | `TestFromAC_DocAuditPromptContent` | PASS |
| AC4 | No old `Item 5` / `Item 6` references remain in the live skill; whole-file tests cover the condition. | `TestFromAC_NoOldDiagramItems` | PASS |
| AC5 | Exact TODO template is present in the skill and asserted exactly in the suite. | `test_todo_marker_complete_template` | PASS |

### Informational
- `quality-runner` independently reported `52 passed / 0 failed` and `ruff: clean`; the blocker is proof quality, not runtime behavior.
- There are already four prior `## Review Evidence` sections in `.owlbear/kanban/tasks/1422-p1-01-test-verify-doc-writer-quality-redesign-ac.md` at lines `141`, `213`, `356`, and `505`; this is a fifth review cycle.
- A broader section-locality concern exists around the verification-procedure clause, but this verdict does not need it. AC1 already fails on items 7 and 8.

### Deductions
- `-0.06` AC1 item 7 `unverified` is not asserted by an executable predicate.
- `-0.05` AC1 item 8 `no READMEs` trigger is not asserted by an executable predicate.
- `-0.01` Full additive diff / dirty-tree overlap could not be reconstructed in this tool surface.

### Confidence: 0.88
### Verdict: FAIL
### Action
- Reject to `backlog`. This task already has four prior review sections, so the loop-breaker rule applies on any further FAIL. The remaining defects are AC1 proof-quality gaps, not implementation regressions.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine AC1 item 7 so the retry contract requires an executable assertion that couples `task-caused` / `pre-existing`, `unverified`, and `blocks` / `passes` in the same live rule text, then return the task to the test-writer. | `.owlbear/kanban/tasks/1422-p1-01-test-verify-doc-writer-quality-redesign-ac.md`, `tests/test_doc_writer_quality_1422.py`, `share/skills/w-doc-update/SKILL.md` | Child AC line `68`; live skill lines `91-92`; current executable predicates at test lines `408` and `418`; `unverified` exists only in assertion messages at test lines `75` and `81`. |
| 2 | architect | Refine AC1 item 8 so the retry contract requires an executable assertion for the fast-path trigger `if changed files map to no READMEs`, not just the output phrase, then return the task to the test-writer. | `.owlbear/kanban/tasks/1422-p1-01-test-verify-doc-writer-quality-redesign-ac.md`, `tests/test_doc_writer_quality_1422.py`, `share/skills/w-doc-update/SKILL.md` | Child AC line `69`; live skill lines `36-37`; current executable predicates at test lines `342`, `427`, `430`, and `434`; `no READMEs` exists only in an assertion message at test line `344`. |
[[2026-05-08]]

## AC1 Supplement (R6 — final token coupling)

Two remaining false-green gaps from reviewer R5. Both are tightenings of existing assertions.

### Gap 1: `unverified` in gate-rule coupling (td:1)

Tighten the 2 existing gate-rule tests to include `unverified` in the same-line binding:

- `test_gate_rule_task_caused_blocks`: change the `any(...)` to require ALL THREE tokens on one line: `task-caused`, `unverified`, AND `blocks`
- `test_gate_rule_preexisting_passes`: change the `any(...)` to require ALL THREE tokens on one line: `pre-existing`, `unverified`, AND `passes`

Live text at `share/skills/w-doc-update/SKILL.md:91-92`:
```
- task-caused unverified content blocks the gate.
- pre-existing unverified content passes the gate.
```

**Discriminator:** `any("task-caused" in line and "unverified" in line and "blocks" in line for line in content.splitlines())` — adding `"unverified" in line` to existing predicates.

### Gap 2: `no READMEs` trigger in fast-path (td:1)

Add one assertion to the existing `test_no_impact_fast_path_advances` test to prove the trigger condition, not just the output:

```python
assert re.search(r"no README", step1, re.IGNORECASE), (
    "Step 1 fast-path trigger must reference 'no READMEs' — "
    "proving the trigger condition, not just the output phrase"
)
```

Live text at `share/skills/w-doc-update/SKILL.md:36-37`:
```
If all changed files map to no READMEs, use the no-impact fast path: write
"no docs impact" with evidence and advance.
```

### Test-writer guidance (R6)
- Amend `tests/test_doc_writer_quality_1422.py` — modify 3 existing tests only.
- `test_gate_rule_task_caused_blocks`: add `and "unverified" in line` to the `any(...)` predicate.
- `test_gate_rule_preexisting_passes`: add `and "unverified" in line` to the `any(...)` predicate.
- `test_no_impact_fast_path_advances`: add 1 assertion for `no README` in Step 1.
- Total test count stays at 52. No new tests — tighten 3 existing assertions.
- DO NOT modify or remove any other tests.


[[2026-05-08]]

### R6 Correction (challenger feedback)

The R6 Gap 1 supplement above uses whole-file `content.splitlines()` for gate-rule assertions. The challenger correctly identified that the same token triplets (`task-caused` + `unverified` + `blocks` and `pre-existing` + `unverified` + `passes`) appear at BOTH:
- Lines 91–92 (authoritative Gate rules section)
- Lines 148–149 (Verification Checklist summary)

Whole-file iteration would false-green if the gate rules were deleted but the checklist duplicates remained.

**Revised Gap 1:** Extract the Gate rules section using `re.search(r"Gate rules:.*?(?=## )", content, re.DOTALL)` and iterate its lines only. This scopes the assertion to the authoritative gate-rule text, not its checklist echo.

Revised discriminator:
```python
gate_match = re.search(r"Gate rules:.*?(?=## )", content, re.DOTALL)
assert gate_match, "SKILL.md must have a 'Gate rules:' section"
gate_lines = gate_match.group(0).splitlines()
assert any("task-caused" in line and "unverified" in line and "blocks" in line for line in gate_lines)
assert any("pre-existing" in line and "unverified" in line and "passes" in line for line in gate_lines)
```

Gap 2 is unchanged — `_step1_section()` already provides section-scoped extraction.

**Revised test-writer guidance (R6):**
- Modify `test_gate_rule_task_caused_blocks`: replace whole-file `content.splitlines()` with section-scoped `gate_lines` from the `Gate rules:` section. Add `"unverified" in line` to the predicate.
- Modify `test_gate_rule_preexisting_passes`: same section-scoped replacement. Add `"unverified" in line`.
- Modify `test_no_impact_fast_path_advances`: add `assert re.search(r"no README", step1, re.IGNORECASE)`.
- Total test count stays at 52. 3 existing tests tightened, no new tests.

[[2026-05-08]]

## Architecture Review (R6)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | 3 assertion tightenings in existing test functions |
| Interface clarity | PASS | Each gap specifies exact discriminator with code examples and section-scoping |
| Dependency correctness | PASS | No dependencies |
| Module layering | N/A | Test file only |
| TDD compliance | PASS | This IS the test task |
| KISS/YAGNI | PASS | Modify 3 existing predicates, no new tests or abstractions |
| Premise challenge | PASS | Reviewer documented exact false-green mutations across 5 cycles; both gaps are directly evidenced |
| Pattern consistency | PASS | Section extraction via `re.search(...)` matches existing `_step1_section()` pattern in the test file |
| Security surface | PASS | No system boundaries |
| Single domain | PASS | Agent ecosystem only |

### Challenge Results
- Challenger: block (confidence 0.38)
- Challenge 1 (whole-file false-green via checklist duplicates at SKILL.md:148-149): ACCEPTED — revised supplement to use section-scoped `Gate rules:` extraction instead of whole-file iteration. Lines 148-149 echo the same tokens, confirming the false-green path.
- Challenge 2 (Gap 2 regex looseness): NOTED — `re.search(r"no README", step1, re.IGNORECASE)` within `_step1_section()` is already section-scoped to Step 1. The trigger phrase "no READMEs" is semantically specific and does not appear elsewhere in Step 1. The assertion proves the trigger exists alongside the output. Acceptable specificity.
- Challenge 3 (pass count as evidence): ACCEPTED — removed reliance on "52 tests" as corroborating evidence. The approval is based on AC contract precision, not test count.
- Challenge 4 (append-only supplement ambiguity): NOTED — the R6 Correction subsection explicitly supersedes the initial R6 supplement. Downstream agents follow the latest guidance per normal lifecycle.

### Test Depth
- Max depth: 1 (all 3 modifications are single-assertion tightenings)
- Test-writer: PROCEED

### Verdict: APPROVE
### Action: AC1 supplemented with section-scoped gate-rule coupling (`unverified` added to both predicates, scoped to `Gate rules:` section) and fast-path trigger assertion (`no READMEs`). Challenger feedback integrated — initial whole-file approach revised to section-scoped after confirming checklist duplicate false-green path. Task advanced to todo.

[[2026-05-08]]
Architecture review R6 complete. AC1 supplemented with 2 final proof-quality gaps from reviewer R5: (1) gate-rule tests tightened to bind `task-caused`+`unverified`+`blocks` and `pre-existing`+`unverified`+`passes` on same line, section-scoped to `Gate rules:` section (challenger correctly identified whole-file false-green via checklist duplicates at SKILL.md:148-149), (2) fast-path trigger `no READMEs` assertion added to existing test using Step 1 section scope. Test-writer: modify 3 existing tests, 0 new tests, total stays at 52.
[[2026-05-08]]
## Test-Writer Notes (R6)
- Test file: tests/test_doc_writer_quality_1422.py
- Prior state: 52 tests (all passing — correct implementation already in place)
- Changes: tightened 3 existing tests per reviewer R6 required follow-up
  1. `test_gate_rule_task_caused_blocks` (TestFromAC_ConventionMappingTable) — replaced whole-file `content.splitlines()` with section-scoped `Gate rules:` extraction via `re.search(r"Gate rules:.*?(?=## )", content, re.DOTALL)`; added `"unverified" in line` to predicate. Scoping prevents false-green via checklist duplicate lines at SKILL.md:148-149 (challenger-confirmed gap).
  2. `test_gate_rule_preexisting_passes` (TestFromAC_ConventionMappingTable) — same section-scoped replacement + `"unverified" in line` added.
  3. `test_no_impact_fast_path_advances` (TestFromAC_ConventionMappingTable) — added `assert re.search(r"no README", step1, re.IGNORECASE)` to prove the trigger condition, not just the output phrase.
- Total: 52 tests, all PASS
- ruff: clean (0 violations)
- Mutation resistance: swapping unverified→verified in gate rules now fails; deleting gate-rules section now fails; removing no-READMEs trigger while keeping output sentence now fails
- Builder skip: test-only retry, implementation already correct — advance directly to review
- AC coverage: AC1 R6 gaps addressed (gate-rule triple coupling + fast-path trigger), all prior AC2–AC5 unchanged
- Commit: 4693139e
[[2026-05-08]]
## Builder Notes
- Implementation: no files changed (test-only task; non-implementation pass-through)
- Tests: 52 passed, 0 failed, 0 skipped (tests/test_doc_writer_quality_1422.py)
- Coverage: N/A for markdown-artifact assertion scope (coverage_modules=[])
- ruff: clean (0 violations)
- Approach: executed a fresh scoped quality-runner gate before handoff.
- Evidence summary: quality-runner reported failed: [] and clean: true with pytest exit 0 and ruff exit 0.
- Fixes applied: none
[[2026-05-08]]
## Review Evidence
### Test Results
- pytest: 52 passed, 0 failed (`tests/test_doc_writer_quality_1422.py`) via `quality-runner`

### Lint
- ruff: 0 violations on `tests/test_doc_writer_quality_1422.py` via `quality-runner`

### Coverage
- N/A. `coverage_modules=[]`; this is a markdown-artifact assertion task with no instrumentable source module in scope.

### Pass 1 — Critical
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| AC1.1 exact mapping row | `test_convention_mapping_exact_src_row_coupled` | Yes. The test requires one Step 1 line to contain BOTH `serve/{pkg}/src/**` and `serve/{pkg}/README.md`, matching the live row at `share/skills/w-doc-update/SKILL.md:30`. | COVERED |
| AC1.2 exact 4-item checklist with names and discriminators | `test_checklist_exactly_four_items`, `test_item1_name_is_readme_verification`, `test_item2_name_is_external_attribution`, `test_item3_name_is_research_doc`, `test_item4_name_is_deletion_detection`, `test_item1_has_layer1_grep_structural_check`, `test_item1_has_layer2_editorial`, `test_item2_external_attribution_mentions_sources_overview`, `test_item3_research_doc_mentions_verification_language`, `test_item4_deletion_detection_mentions_child_task`, `test_item4_deletion_detection_mentions_dr_protocol` | Yes. Count is pinned, each exact heading is pinned, and each item's required discriminator is asserted against its extracted section. | COVERED |
| AC1.3-AC1.4 no `Docstring` / no `Diagram` headings | `test_no_docstring_checklist_item`, `test_no_diagram_in_any_checklist_heading` | Yes. Both operate on extracted checklist headings and fail on any forbidden heading drift. | COVERED |
| AC1.5 verification layers | `test_verification_procedure_layer1_grep_present`, `test_verification_procedure_layer2_editorial_present` | Yes for the refined child AC as written. The live skill contains Layer 1 grep structural and Layer 2 editorial verification at `share/skills/w-doc-update/SKILL.md:94-100`, and the suite proves those layer concepts are present in the skill. | COVERED |
| AC1.6 TODO marker template | `test_todo_marker_complete_template`, `TestFromAC_TodoMarkerFormat` | Yes. The exact template is present at `share/skills/w-doc-update/SKILL.md:76` and is directly asserted at `tests/test_doc_writer_quality_1422.py:220`. | COVERED |
| AC1.7 gate rules | `test_gate_rule_task_caused_blocks`, `test_gate_rule_preexisting_passes` | Yes. Both tests scope to the authoritative `Gate rules:` section and require subject + `unverified` + verb coupling on a single line; the live rules at `share/skills/w-doc-update/SKILL.md:91-92` satisfy this. | COVERED |
| AC1.8 no-impact fast path | `test_no_impact_fast_path_advances` | Yes. The test proves Step 1 contains the `no README` trigger plus `no docs impact`, `with evidence`, and `advance`, matching `share/skills/w-doc-update/SKILL.md:36-37`. | COVERED |
| AC2 no diagram / Excalidraw refs in `doc-writer.agent.md` | `TestFromAC_DocWriterAgentNoDiagrams` | Yes. Direct absence assertions would fail on any `diagram`, `excalidraw`, or `.excalidraw` reintroduction, and the live file is clean. | COVERED |
| AC3 prompt includes TODO batch resolution, diagram ownership, describes-based verification | `TestFromAC_DocAuditPromptContent` | Yes for the AC as written. The suite asserts the required TODO batch-resolution, diagram-ownership, and describes-based verification dimensions, and the live prompt contains the corresponding sections at `.owlbear/prompts/doc-audit.prompt.md:46`, `:61`, and `:69`. | COVERED |
| AC4 no old `Item 5` / `Item 6` refs remain in `w-doc-update` | `TestFromAC_NoOldDiagramItems` | Yes. Whole-file `Item 5` / `Item 6` bans at `tests/test_doc_writer_quality_1422.py:174` and `:181` fail on any reintroduction, and the live skill is clean. | COVERED |
| AC5 exact TODO marker format | `test_todo_marker_complete_template` | Yes. The exact template is present in the live skill and asserted exactly in the suite. | COVERED |

#### Security Review
- No issues. Scope is fixed-path local file reads plus string / regex assertions only.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---|---|---|
| `TestFromAC_*` suite in `tests/test_doc_writer_quality_1422.py` | No weakened, removed, skipped, or xfailed assertions are visible in the current snapshot. Commit presence for task-related test-writer hashes was confirmed in `.git/logs/HEAD` at lines `2268`, `2286`, `2314`, `2323`, `2331`, and `2340`, but full additive diff reconstruction and dirty-tree overlap checks were unavailable in this tool surface. | PRESERVED (moderate-confidence) |

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | ADEQUATE | The suite now pins the exact src-row coupling, exact TODO template, gate-rule triple-token coupling, and no-README fast-path trigger. Item 3 could be tightened further around exact `task body` wording, but the current section-scoped verification / linkage check remains within the refined discriminator. |
| Negative / exclusion coverage | STRONG | AC2 and AC4 use direct absence assertions, and AC1 also bans Docstring / Diagram checklist headings explicitly. |
| Manual mutation reasoning | ADEQUATE | Repointing the src row, swapping / weakening gate-rule verbs or removing `unverified`, dropping the no-README trigger, or reintroducing old Item 5 / Item 6 references would now fail the suite. |
| Test independence | STRONG | Tests are isolated `Path.read_text()` assertions with no shared mutable state. |
| Descriptive names | STRONG | Test names are AC-shaped and readable. |

#### Data Safety
- No issues.

#### Implementation-Aware Gaps
- No AC-grounded untested paths remain after the R6 tightenings. Residual robustness concern: Item 3 could assert `task body` more directly, but the refined discriminator requires section-scoped research verification / linkage language rather than exact phrase matching.

#### Builder Process Quality
| Metric | Value |
|---|---|
| Builder Notes sections | 6 |
| Approach variation | Yes — prior failures produced substantive AC supplements (R3-R6) before the latest retry state |
| Assessment | FRICTION |

### Pass 2 — Informational
- There are already five prior `## Review Evidence` sections in `.owlbear/kanban/tasks/1422-p1-01-test-verify-doc-writer-quality-redesign-ac.md` at lines `141`, `213`, `356`, `505`, and `662`; this is the sixth review cycle.
- `quality-runner` independently reported `52 passed / 0 failed` and `ruff: clean`; the scoped quality gate is green.
- Broader Step 3-locality and exact-heading concerns were reviewed but not used as blockers because the refined child AC does not require Step 3-scoped assertions or exact prompt heading assertions. Treating those as blocking would invent requirements beyond the task body.
- Commit presence for task-related test-writer hashes was confirmed via `.git/logs/**`, but the lack of terminal access prevented full diff-scoped immutability and dirty-tree reconstruction.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1 refined (`.owlbear/kanban/tasks/1422-p1-01-test-verify-doc-writer-quality-redesign-ac.md:54-69`) | The live skill satisfies the child contract at `share/skills/w-doc-update/SKILL.md:30`, `:36-37`, `:43-76`, and `:89-100`. The latest suite now directly proves the prior reviewer gap areas: exact src-row coupling, gate-rule triple-token coupling in the authoritative section, and the no-README fast-path trigger plus output. | `TestFromAC_DocUpdateSkillContent`, `TestFromAC_ChecklistItemNames`, `TestFromAC_ConventionMappingTable`, `TestFromAC_TodoMarkerFormat` | PASS |
| AC2 | Direct absence tests remain green and the live agent file contains no `diagram`, `excalidraw`, or `.excalidraw` references. | `TestFromAC_DocWriterAgentNoDiagrams` | PASS |
| AC3 | The prompt contains TODO marker batch resolution, diagram ownership, and describes-based verification sections at `.owlbear/prompts/doc-audit.prompt.md:46`, `:61`, and `:69`, and the task suite proves those dimensions are present. | `TestFromAC_DocAuditPromptContent` | PASS |
| AC4 | No old `Item 5` / `Item 6` references remain in the live skill, and the suite enforces whole-file bans for both. | `TestFromAC_NoOldDiagramItems` | PASS |
| AC5 | The exact TODO marker template is present in the live skill and asserted exactly in the suite. | `TestFromAC_TodoMarkerFormat` | PASS |

### Confidence: 0.94
### Verdict: PASS
### Action
- Advance to `docs`. The latest retry closes the prior AC1 proof gaps, and the remaining broader robustness concerns are not binding defects under the refined child AC.
[[2026-05-08]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Changed file is `tests/test_doc_writer_quality_1422.py` — test file; no IN-scope prose docs reference test internals |
| 2 | Module docstrings | No | N/A | Test file; no public module API |
| 3 | External attribution | No | N/A | Only stdlib used (`pathlib`, `re`) |
| 4 | Research doc | Yes | Verified | `.owlbear/research/doc-writer-quality-test-tightening-1422.md` exists and is linked from task body |
| 5 | Diagram maintenance (describes match) | No | N/A | No `describes` glob matches `tests/**` (checked doc-index) |
| 6 | Explicit diagram creation | No | N/A | No request in task body |
| 7 | Deletion detection | No | N/A | No deleted files in task scope |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `tests/test_doc_writer_quality_1422.py` | OUT | N/A — test file |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/1422-*` files found)
[[2026-05-08]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 refined (mapping table, 4-item checklist, discriminators, gate rules, fast-path, TODO, no-impact) | 52/52 tests pass; spot-checked gate-rule section-scoped triple-token coupling at test:405-430, exact src-row coupling at test:451-462, all reviewer R6 COVERED verdicts | PASS |
| AC2 (no diagrams in doc-writer.agent.md) | Reviewer COVERED; absence tests at test:88-104 | PASS |
| AC3 (doc-audit.prompt.md content) | Reviewer COVERED; section-presence tests at test:114-133 | PASS |
| AC4 (no old Item 5/6) | Reviewer COVERED; whole-file bans at test:174-181 | PASS |
| AC5 (TODO marker format) | Reviewer COVERED; exact template at test:220 | PASS |

### Test Results
- pytest (task-scoped): 52 passed, 0 failed
- pytest (full suite): 399 pre-existing failures in unrelated modules (kanban MCP pydantic validation, decision resolution, engine accessor migration, shell timeouts) — none in task scope
- ruff (task-scoped): 0 violations
- ruff (full suite): 12 pre-existing violations in unrelated files — none in task scope

### Architect Quality: 3/5
Original AC specified count-only assertions (any 4 items pass green). Required 6 review cycles with supplements R3-R6 to reach identity-pinning + behavior discriminators + section-scoped coupling. Final AC is well-specified but initial gaps were notable.

### Deduction Breakdown
- -0.03: AC quality score ≤ 3 (6 review cycles to converge)

### Confidence: 0.97
### Action: archive