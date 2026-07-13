---
id: 1283
title: 'P1-03: Update cross-references in README, WIRING, h-agent-structure, h-memory-structure'
status: archived
priority: medium
created: 2026-05-02T16:01:10.613477+00:00
updated: 2026-05-03T15:05:39.462988+00:00
tags:
- phase-1
- scope:docs
- shared-layer
- docs
parent: 1280
depends_on:
- 1282
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1280 and `.owlbear/briefs/draft-neutral-shared/brief.md`

## Acceptance Criteria

- [ ] share/README.md has no dangling references to content removed from owlbear-system.instructions.md
- [ ] share/WIRING.md has no dangling references to removed content
- [ ] h-agent-structure SKILL.md "Current stubs" table updated if it referenced moved content
- [ ] h-memory-structure SKILL.md updated if it referenced owlbear-system.instructions.md by OwlBear-specific content
- [ ] No broken internal links introduced by the split
- [ ] Tests from #1281 pass for the cross-reference assertions

## Scope

- IN: share/README.md, share/WIRING.md, h-agent-structure/SKILL.md, h-memory-structure/SKILL.md
- OUT: owlbear-system.instructions.md itself (#1282), init.py (#1284)


**Additional scope (from research File 20):** Extend `agent-ecosystem.instructions.md` applyTo to also cover `.owlbear/agents/**,.owlbear/skills/**,.owlbear/instructions/**,.owlbear/prompts/**` so consumers writing to local `.owlbear/` paths get the structural conventions.

[[2026-05-02]]
## Research
- Research doc: .owlbear/research/p1-03-cross-reference-update.md
- Sources: 9 studied, 7 high-relevance
- Recommendation: T1 autonomous — 5 files, ~7 line changes (confidence: 0.92)
- Follow-up tasks created: none (this task IS the implementation task)
- Decision requests: none
- Dependency added: depends_on #1282 (must complete first to know new description text)

### Key findings
- 2 description references need updating after #1282 (README.md:97, h-agent-structure:344)
- agent-ecosystem.instructions.md applyTo extension requires 4 mirror updates (README.md, h-agent-structure, WIRING.md ×2)
- h-memory-structure § Memory Governance reference is SAFE (§3 stays in file)
- WIRING.md filename references are SAFE (filename unchanged)
- Challenge: skipped (trivial cross-reference inventory)
[[2026-05-03]]


## Refined Acceptance Criteria

*Supersedes original AC and research key-findings above. Test-writer: use ONLY this section.*

**Primary changes (applyTo extension + mirror updates):**

- [ ] `share/instructions/agent-ecosystem.instructions.md` YAML `applyTo` field extended to: `"share/agents/**,share/skills/**,share/instructions/**,share/prompts/**,.owlbear/agents/**,.owlbear/skills/**,.owlbear/instructions/**,.owlbear/prompts/**"` (td:1)
- [ ] `share/README.md` instruction stubs table: `agent-ecosystem.instructions.md` row applyTo column updated to mirror value from AC1 (td:1)
- [ ] `share/skills/h-agent-structure/SKILL.md` "Current stubs" table: `agent-ecosystem.instructions.md` row applyTo column updated to mirror value from AC1 (td:1)
- [ ] `share/WIRING.md` Table 2 instructions row for `agent-ecosystem.instructions`: "Seldom" column scope description and abbreviated applyTo updated to include `.owlbear/` ecosystem files (td:1)
- [ ] `share/WIRING.md` Gap Analysis row for `agent-ecosystem.instructions`: notes updated to reflect `.owlbear/` scope (td:1)

**Cosmetic fix (while editing h-agent-structure):**

- [ ] `share/skills/h-agent-structure/SKILL.md` authority-files table: `owlbear-system.instructions.md` role column updated from "Decision heuristics, system awareness, memory governance (universal)" to "System instructions — decision heuristics, system awareness, memory governance, and operational fundamentals (universal)" for consistency with current YAML description (td:0)

**Verification (no code changes — confirmed safe by codebase analysis):**

- [ ] `share/README.md` line 97 substantive-docs table description for `owlbear-system.instructions.md` already matches current YAML content — no change needed (td:0)
- [ ] `share/WIRING.md` filename references to `owlbear-system.instructions.md` remain valid (filename unchanged) — no change needed (td:0)
- [ ] `share/skills/h-memory-structure/SKILL.md` line 43 `§ Memory Governance` reference resolves to `owlbear-system.instructions.md` §3 (still present) — no change needed (td:0)

**Scope:** IN: `agent-ecosystem.instructions.md`, `share/README.md`, `share/WIRING.md`, `share/skills/h-agent-structure/SKILL.md`. OUT: `owlbear-system.instructions.md` (#1282, done), `h-memory-structure/SKILL.md` (verified safe, no changes), `setup/init.py` (#1284).

## Architecture Review

### Research Correction

The research doc claims "2 description references need updating after #1282 (README.md:97, h-agent-structure:344)." Codebase analysis shows this is stale:

- **README.md:97** uses the content portion after the em-dash: "Decision heuristics, system awareness, memory governance, and operational fundamentals." #1282 only changed the prefix from "OwlBear system instructions" to "System instructions" — the content portion is unchanged. **No update needed.**
- **h-agent-structure:344** uses a condensed role summary: "Decision heuristics, system awareness, memory governance (universal)." This pre-existing truncation omits "and operational fundamentals" and was present BEFORE #1282. It is not a regression, but is worth correcting while editing the file (cosmetic fix, td:0).

The real work is the applyTo extension (5 file changes) plus the cosmetic fix (1 change).

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | All changes are mirror-consistency edits for the agent-ecosystem.instructions.md applyTo extension |
| Interface clarity | PASS (after refinement) | AC lines specify exact file, table, column, and expected value |
| Dependency correctness | PASS | #1282 is archived/done; no other blocking deps |
| Module layering | N/A | Docs-only task, no code modules |
| TDD compliance | PASS | td:1 lines will be processed by test-writer |
| KISS/YAGNI | PASS | applyTo extension is minimal (one YAML field + 4 mirrors); `.owlbear/` paths don't exist yet but pattern is harmless when unmatched and prevents a separate mirror-update task in Phase 2 |
| Premise challenge | PASS | applyTo extension comes from brief research-notes File 20; ensures consumers writing `.owlbear/` ecosystem files get structural conventions |
| Pattern consistency | PASS | Follows existing mirror-update pattern (each applyTo change is reflected in README stubs table, h-agent-structure stubs table, and WIRING.md) |
| Security surface | N/A | No system boundaries; docs-only changes |
| Single domain | PASS | Documentation domain only |

### Design Diverge

Skipped — single approach (mirror-update pattern), no competing designs.

### Challenge Results

- Challenger: reconsider (0.67)
- Concerns addressed:
  1. **Verification gap (td:1 without tests):** Valid. Existing #1281 tests don't cover applyTo changes. Refined AC has td:1 lines — test-writer will create tests. No existing test gate replaced without a successor.
  2. **Scope drift (applyTo extension as new functionality):** Accepted as valid minor scope expansion. The applyTo pattern is harmless when unmatched (no `.owlbear/` dirs exist yet), prevents a separate mirror-update task later, and the brief's research notes explicitly recommend it. Cost: one YAML field change + 4 mirror edits in already-scoped files.
  3. **h-agent-structure:344 ambiguity:** Resolved. Added AC6 as cosmetic fix (td:0). Convention: authority-files table uses condensed role summaries with scope annotation, not verbatim YAML descriptions. The existing truncation is pre-existing, not a #1282 regression, but worth correcting for accuracy.
  4. **Stale task record:** Resolved. Refined AC section supersedes original AC and research key-findings. Explicit note added that research description-reference claims are stale.
  5. **Dependency framing (AC6 deletion):** Original AC6 ("Tests from #1281 pass") referenced a task that depends on this one. Replaced with concrete td:1 AC lines that the test-writer will process independently. #1281's `test_section_refs_exist_in_owlbear_system` regression guard remains as passive coverage.
- Architect response: all 5 concerns addressed, proceeding with APPROVE.

### Test Depth

- Max depth: 1
- Test-writer: PROCEED (5 lines td:1, 4 lines td:0)

### Verdict: APPROVE
### Action Taken: Refined AC to replace vague cross-reference checks with specific applyTo-extension AC lines (td:1) plus verified-safe items (td:0). Added `docs` pass-through tag. Corrected stale research findings re: description references. Advancing to todo.

[[2026-05-03]]
Architecture review complete. Refined AC: replaced 6 vague cross-reference checks with 5 specific applyTo-extension td:1 lines + 1 cosmetic fix (td:0) + 3 verified-safe no-ops (td:0). Research claimed 2 description references need updating — codebase analysis shows both are already correct (README.md:97 matches content portion after em-dash; h-agent-structure:344 is a pre-existing condensed form). Real work: extend agent-ecosystem.instructions.md applyTo to include .owlbear/ paths + 4 mirror updates. Challenger reconsider (0.67) → 5 concerns addressed. Added `docs` pass-through tag.
[[2026-05-03]]
## Test-Writer Notes
- Test file: tests/test_cross_references_1283.py
- Classes: TestFromAC_ApplyToExtension
- Tests per category: happy 5, edge 0, error 0, boundary 0
- Total: 5 tests, all FAIL
- ruff: clean

AC coverage:
| AC line | Test |
|---------|------|
| AC1: agent-ecosystem.instructions.md applyTo includes .owlbear/ paths (td:1) | test_agent_ecosystem_instructions_apply_to_includes_owlbear_paths |
| AC2: share/README.md stubs table mirrors .owlbear/ paths (td:1) | test_readme_instruction_stubs_table_mirrors_owlbear_paths |
| AC3: h-agent-structure SKILL.md stubs table mirrors .owlbear/ paths (td:1) | test_h_agent_structure_stubs_table_mirrors_owlbear_paths |
| AC4: WIRING.md Table 2 row includes .owlbear/ scope (td:1) | test_wiring_table2_agent_ecosystem_row_includes_owlbear_scope |
| AC5: WIRING.md Gap Analysis notes reflect .owlbear/ scope (td:1) | test_wiring_gap_analysis_agent_ecosystem_notes_mention_owlbear |
| AC6 cosmetic fix (td:0) | skipped (depth-zero) |
| Verification ACs (td:0 ×3) | skipped (depth-zero) |
[[2026-05-03]]
## Builder Notes
- Implementation: updated cross-reference mirrors for the `agent-ecosystem.instructions.md` `applyTo` extension across:
  - `share/instructions/agent-ecosystem.instructions.md`
  - `share/README.md`
  - `share/WIRING.md`
  - `share/skills/h-agent-structure/SKILL.md`
- Fixes applied:
  - Extended `agent-ecosystem.instructions.md` `applyTo` to include `.owlbear/agents/**,.owlbear/skills/**,.owlbear/instructions/**,.owlbear/prompts/**`.
  - Mirrored that full scope string in `share/README.md` and `h-agent-structure` Current stubs table.
  - Updated `share/WIRING.md` Table 2 and Gap Analysis `agent-ecosystem.instructions` rows to mention `.owlbear/` ecosystem scope.
  - Applied cosmetic wording fix in `h-agent-structure` authority-files table for `owlbear-system.instructions.md` role text.
- Tests: 5/5 `TestFromAC_ApplyToExtension` passed (`tests/test_cross_references_1283.py`).
- Lint: `ruff` clean for scoped paths.
- Coverage: non-applicable for this docs-only validation task (`pytest-cov` reported no-data-collected warning because tests assert file content, not runtime module execution).
- Commit: `e66cbe42` (`docs: update cross-reference mirrors for applyTo extension (#1283, builder)`).

### Reflection
- The failing assertions mapped 1:1 to missing mirror rows, enabling a purely surgical doc patch.
- Keeping the `applyTo` value identical in all mirror tables avoided drift and made the fix deterministic.
- Coverage tooling is noisy for structural/docs assertions; explicit note in evidence prevents false gate failures.
[[2026-05-03]]
## Review Evidence
### Test Results
- quality-runner pytest: 5 passed, 0 failed on [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py)

### Lint
- quality-runner ruff: clean on [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py)

### Coverage
- Not applicable for this docs-only artifact-validation task. The task asserts markdown/instruction content, not runtime module behavior.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: exact applyTo extension in [share/instructions/agent-ecosystem.instructions.md](share/instructions/agent-ecosystem.instructions.md#L3) | [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L30) with assertion at [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L42) | No. It only checks that the four new .owlbear paths appear somewhere in the file content, not that the YAML applyTo field itself carries the required exact value. A prose/comment listing those paths would still pass. | LAX |
| AC2: README stubs row mirrors full AC1 value at [share/README.md](share/README.md#L106) | [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L47) with assertion at [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L62) | No. It only requires .owlbear/agents/** in the row. Missing .owlbear/skills/**, .owlbear/instructions/**, or .owlbear/prompts/** would still pass. | LAX |
| AC3: h-agent-structure stubs row mirrors full AC1 value at [share/skills/h-agent-structure/SKILL.md](share/skills/h-agent-structure/SKILL.md#L328) | [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L68) with assertion at [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L88) | No. Same weakness as AC2: only .owlbear/agents/** is asserted, not the full mirrored value. | LAX |
| AC4: WIRING Table 2 row reflects .owlbear ecosystem scope at [share/WIRING.md](share/WIRING.md#L226) | [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L94) with assertion at [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L111) | No. It only checks for generic .owlbear/ presence in the row, not the intended ecosystem scope or abbreviated applyTo content. | LAX |
| AC5: WIRING Gap Analysis notes reflect .owlbear ecosystem scope at [share/WIRING.md](share/WIRING.md#L257) | [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L117) with assertion at [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L133) | No. Any generic .owlbear/ mention satisfies the test, even if the required scope wording regresses. | LAX |

#### Security Review
- No issues in the doc-only changes at [share/instructions/agent-ecosystem.instructions.md](share/instructions/agent-ecosystem.instructions.md#L3), [share/README.md](share/README.md#L106), [share/WIRING.md](share/WIRING.md#L226), [share/WIRING.md](share/WIRING.md#L257), and [share/skills/h-agent-structure/SKILL.md](share/skills/h-agent-structure/SKILL.md#L328).

#### Test Integrity
- PRESERVED. Builder commit e66cbe42 changed only [share/README.md](share/README.md), [share/WIRING.md](share/WIRING.md), [share/instructions/agent-ecosystem.instructions.md](share/instructions/agent-ecosystem.instructions.md), and [share/skills/h-agent-structure/SKILL.md](share/skills/h-agent-structure/SKILL.md). [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py) was not touched.

#### Test Quality
- WEAK assertion specificity. The key assertions at [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L42), [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L62), [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L88), [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L111), and [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L133) are substring checks that allow materially wrong mirror content to pass.
- WEAK manual mutation resistance. Removing three of the four new .owlbear globs from the README or h-agent-structure rows, or reducing the WIRING rows to generic .owlbear wording, would leave the suite green.
- ADEQUATE independence and naming. Tests are isolated and descriptively named.

#### Data Safety
- No issues. This task only changes static documentation/instruction artifacts.

#### Implementation-Aware Test Gaps
- Missing proof that AC1 targets the YAML applyTo field at [share/instructions/agent-ecosystem.instructions.md](share/instructions/agent-ecosystem.instructions.md#L3), rather than arbitrary file content.
- Missing proof that AC2 and AC3 mirror the full AC1 value at [share/README.md](share/README.md#L106) and [share/skills/h-agent-structure/SKILL.md](share/skills/h-agent-structure/SKILL.md#L328).
- Missing proof that AC4 and AC5 preserve the intended .owlbear ecosystem scope at [share/WIRING.md](share/WIRING.md#L226) and [share/WIRING.md](share/WIRING.md#L257).

#### Builder Process Quality
- CLEAN. One builder section, no retry loop detected.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | [share/instructions/agent-ecosystem.instructions.md](share/instructions/agent-ecosystem.instructions.md#L3) has the full extended applyTo value. | [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L30) | PASS |
| AC2 | [share/README.md](share/README.md#L106) mirrors the full extended applyTo value. | [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L47) | PASS |
| AC3 | [share/skills/h-agent-structure/SKILL.md](share/skills/h-agent-structure/SKILL.md#L328) mirrors the full extended applyTo value. | [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L68) | PASS |
| AC4 | [share/WIRING.md](share/WIRING.md#L226) updates the Table 2 row to include share/ and .owlbear/ ecosystem scope plus abbreviated applyTo. | [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L94) | PASS |
| AC5 | [share/WIRING.md](share/WIRING.md#L257) updates Gap Analysis notes to mention share/ and .owlbear/ ecosystem files. | [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L117) | PASS |
| AC6 | [share/skills/h-agent-structure/SKILL.md](share/skills/h-agent-structure/SKILL.md#L344) updates the authority-files role text to the current wording. | td:0 - no test required | PASS |
| Verification: README substantive-docs row already correct | [share/README.md](share/README.md#L97) already matches the current system-instructions description. | td:0 - no test required | PASS |
| Verification: WIRING filename references remain valid | [share/WIRING.md](share/WIRING.md#L42) still references owlbear-system.instructions.md by unchanged filename. | td:0 - no test required | PASS |
| Verification: h-memory-structure reference remains valid | [share/skills/h-memory-structure/SKILL.md](share/skills/h-memory-structure/SKILL.md#L43) still resolves to the Memory Governance section. | td:0 - no test required | PASS |

### Deductions
- -0.18: all five td:1 AC lines are only weakly proven by substring assertions, creating a false-green risk despite correct live content.

### Verdict
- FAIL with confidence 0.82. The implementation satisfies the refined AC, but the review gate fails because the TestFromAC assertions are lax and would stay green across materially wrong mirror regressions.

### Action
- Move to todo for test-writer retry only. No builder changes are required on the current snapshot.
- Required follow-up:
  1. AC1 must assert the YAML applyTo field value itself, not just .owlbear substrings anywhere in the file.
  2. AC2 and AC3 must assert the full mirrored applyTo value, not only .owlbear/agents/**.
  3. AC4 and AC5 must assert the intended .owlbear ecosystem scope/abbreviated applyTo text, not generic .owlbear presence.

### Reflection
- Green scoped pytest was insufficient here; direct artifact inspection exposed false-green proof quality.
- Mirror-value tasks need exact-value assertions, not substring presence checks.
- Builder diff verification gave high-confidence TestFromAC immutability evidence because the commit touched only doc files.
[[2026-05-03]]
## Test-Writer Notes
- Retry: added 5 stronger tests for reviewer gaps. All pass against current impl.
- Builder skip: test-only retry, all tests green.
- Test file: tests/test_cross_references_1283.py
- Class: TestFromAC_ApplyToExtension (10 tests total: 5 original preserved + 5 new stricter assertions)
- ruff: clean

### Retry changes (reviewer required follow-up)
| Reviewer gap | New test |
|---|---|
| AC1: must assert YAML `applyTo:` field itself, not arbitrary file content | `test_agent_ecosystem_instructions_apply_to_yaml_field_contains_owlbear_paths` — parses frontmatter, extracts applyTo value, asserts all 4 paths |
| AC2: must mirror all four .owlbear/** patterns, not just agents/** | `test_readme_stubs_row_mirrors_all_owlbear_paths` — asserts all 4 _EXPECTED_OWLBEAR_PATHS in row |
| AC3: must mirror all four .owlbear/** patterns, not just agents/** | `test_h_agent_structure_stubs_row_mirrors_all_owlbear_paths` — asserts all 4 paths in row |
| AC4: must assert abbreviated .owlbear/agents/** in applyTo, not generic .owlbear/ | `test_wiring_table2_row_abbreviates_owlbear_agents_glob` — checks `.owlbear/agents/**` specifically |
| AC5: must assert 'ecosystem' scope language, not generic .owlbear/ | `test_wiring_gap_analysis_row_mentions_owlbear_ecosystem_scope` — requires both `.owlbear/` and 'ecosystem' in row |

All 5 existing tests preserved and still green. All 5 new tests also green (implementation was already correct).
pytest: 10 passed, 0 failed. ruff: clean.
[[2026-05-03]]
## Builder Notes
- Non-implementation pass-through on retry cycle: implementation files were already correct; test-writer strengthened proofs only.
- Verification: quality-runner scoped check on `tests/test_cross_references_1283.py` is green.
- Tests: 10 passed, 0 failed, 0 skipped.
- Ruff: clean (no violations).
- Coverage: not applicable for this docs/assertion-only test file (no source modules imported).
- Files changed by builder in this cycle: none.
- Routing: advancing to review per builder-skip/test-only retry convention.
[[2026-05-03]]
## Review Evidence
### Test Results
- quality-runner pytest: 10 passed, 0 failed on [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py)

### Lint
- quality-runner ruff: clean on [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py)

### Coverage
- Not applicable for this docs-only artifact-validation task. The tests validate markdown/instruction content, not runtime modules.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: exact YAML `applyTo` value at [share/instructions/agent-ecosystem.instructions.md](share/instructions/agent-ecosystem.instructions.md#L3) | [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L145) with assertion at [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L174) | No. The retry now checks the YAML field itself, but it only asserts presence of the four new `.owlbear/...` globs. The canonical full value is defined at [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L26) and never asserted, so the test would stay green if any `share/...` prefix globs were removed or if extra wrong content were added while the four new suffixes remained. | LAX |
| AC2: README row mirrors the full AC1 value at [share/README.md](share/README.md#L106) | [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L179) with assertion at [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L194) | No. It proves all four `.owlbear/...` globs are present in the row, but it still does not prove the row mirrors the full AC1 value. A row missing one or more `share/...` globs would still pass. | LAX |
| AC3: h-agent-structure row mirrors the full AC1 value at [share/skills/h-agent-structure/SKILL.md](share/skills/h-agent-structure/SKILL.md#L328) | [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L199) with assertion at [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L220) | No. Same issue as AC2: the retry proves the four new `.owlbear/...` globs, not the full mirrored value from AC1. | LAX |
| AC4: WIRING Table 2 row updated in both scope description and abbreviated applyTo at [share/WIRING.md](share/WIRING.md#L226) | [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L225) with assertion at [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L241) | No. The retry only proves `.owlbear/agents/**` appears in the row. The AC names two pieces of proof: the scope description and the abbreviated applyTo update. A description regression with that single glob preserved would still pass. | LAX |
| AC5: WIRING Gap Analysis notes reflect `.owlbear/` ecosystem scope at [share/WIRING.md](share/WIRING.md#L257) | [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L247) with assertion at [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L262) | Yes. Requiring both `.owlbear/` and `ecosystem` in the row would fail if the notes no longer reflected `.owlbear/` ecosystem scope. | COVERED |

#### Security Review
- No security issues in the doc-only artifacts at [share/instructions/agent-ecosystem.instructions.md](share/instructions/agent-ecosystem.instructions.md#L3), [share/README.md](share/README.md#L106), [share/WIRING.md](share/WIRING.md#L226), [share/WIRING.md](share/WIRING.md#L257), and [share/skills/h-agent-structure/SKILL.md](share/skills/h-agent-structure/SKILL.md#L344).

#### Test Integrity
- Current task history shows a test-writer retry at [.owlbear/kanban/tasks/1283-p1-03-update-cross-references-in-readme-wiring-h-agent-structure-h-memory-struct.md](.owlbear/kanban/tasks/1283-p1-03-update-cross-references-in-readme-wiring-h-agent-structure-h-memory-struct.md#L249) and a builder pass-through note stating no files changed in this cycle at [.owlbear/kanban/tasks/1283-p1-03-update-cross-references-in-readme-wiring-h-agent-structure-h-memory-struct.md](.owlbear/kanban/tasks/1283-p1-03-update-cross-references-in-readme-wiring-h-agent-structure-h-memory-struct.md#L273).
- Direct git diff recovery from the current shell was unreliable, so I am not using immutability as pass evidence. The verdict does not depend on it; the fail rests on the live proof gaps in the current tests.

#### Test Quality
- WEAK assertion specificity for AC1-AC4. The retry assertions at [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L174), [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L194), [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L220), and [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L241) remain membership checks rather than exact-value proof for the refined contract.
- WEAK manual mutation resistance. `_FULL_APPLY_TO` is defined at [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L26), but no test asserts it, so partial mirror regressions remain false-green for AC1-AC3. AC4 still permits a scope-description regression if `.owlbear/agents/**` stays present.
- ADEQUATE independence and naming. The tests are isolated and descriptively named.

#### Data Safety
- No issues. This task only changes static documentation and instruction artifacts.

#### Implementation-Aware Test Gaps
- Missing exact-value proof that the YAML `applyTo:` field at [share/instructions/agent-ecosystem.instructions.md](share/instructions/agent-ecosystem.instructions.md#L3) equals the refined AC1 value.
- Missing exact-value proof that the mirror rows at [share/README.md](share/README.md#L106) and [share/skills/h-agent-structure/SKILL.md](share/skills/h-agent-structure/SKILL.md#L328) preserve the full AC1 string, including the `share/...` prefixes.
- Missing proof that the Table 2 scope description at [share/WIRING.md](share/WIRING.md#L226) was updated alongside the abbreviated applyTo text.

#### Builder Process Quality
- CLEAN builder behavior in this cycle: the implementation snapshot remains correct and the retry was test-focused.
- Reviewer loop-breaker applies. This task already contains a prior `## Review Evidence` section at [.owlbear/kanban/tasks/1283-p1-03-update-cross-references-in-readme-wiring-h-agent-structure-h-memory-struct.md](.owlbear/kanban/tasks/1283-p1-03-update-cross-references-in-readme-wiring-h-agent-structure-h-memory-struct.md#L175), so a second review failure routes to `backlog`.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | Live artifact at [share/instructions/agent-ecosystem.instructions.md](share/instructions/agent-ecosystem.instructions.md#L3) is correct, but the mapped proof at [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L145) / [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L174) does not assert the full required value. | [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L145) | FAIL |
| AC2 | Live artifact at [share/README.md](share/README.md#L106) is correct, but the mapped proof at [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L179) / [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L194) does not cover the full mirrored value. | [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L179) | FAIL |
| AC3 | Live artifact at [share/skills/h-agent-structure/SKILL.md](share/skills/h-agent-structure/SKILL.md#L328) is correct, but the mapped proof at [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L199) / [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L220) does not cover the full mirrored value. | [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L199) | FAIL |
| AC4 | Live artifact at [share/WIRING.md](share/WIRING.md#L226) is correct, but the mapped proof at [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L225) / [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L241) does not prove the scope-description part of the AC. | [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L225) | FAIL |
| AC5 | [share/WIRING.md](share/WIRING.md#L257) and [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L247) / [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L262) provide adequate proof of `.owlbear/` ecosystem scope. | [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L247) | PASS |
| AC6 | [share/skills/h-agent-structure/SKILL.md](share/skills/h-agent-structure/SKILL.md#L344) matches the refined cosmetic wording. | td:0 - no test required | PASS |
| Verification: README substantive-docs row already correct | [share/README.md](share/README.md#L97) remains correct. | td:0 - no test required | PASS |
| Verification: WIRING filename references remain valid | [share/WIRING.md](share/WIRING.md#L42) remains valid. | td:0 - no test required | PASS |
| Verification: h-memory-structure reference remains valid | [share/skills/h-memory-structure/SKILL.md](share/skills/h-memory-structure/SKILL.md#L43) remains valid. | td:0 - no test required | PASS |

### Deductions
- -0.08: AC1 still lacks exact full-value proof for the YAML `applyTo:` field.
- -0.08: AC2 and AC3 still lack exact full-mirror proof for the README and h-agent-structure rows.
- -0.04: AC4 still lacks proof for the scope-description half of the contract.
- -0.02: direct git diff recovery was unavailable, so test-integrity evidence is task-body-based rather than repository-diff-based.

### Verdict
- FAIL with confidence 0.78. The artifacts are correct, but the second-cycle retry still leaves AC1-AC4 only partially proven, which is below the reviewer gate.

### Action
- Move to `backlog`. This is a second review-cycle failure with remaining proof-quality gaps, so the reviewer loop-breaker applies.
- Required follow-up:
  1. AC1 must assert exact equality against the canonical full `applyTo` value, not only membership of the four new `.owlbear/...` globs.
  2. AC2 and AC3 must assert the full mirrored value, including the `share/...` prefixes, not only the four `.owlbear/...` suffixes.
  3. AC4 must prove both elements named by the AC: the Table 2 scope description and the abbreviated applyTo update.
  4. No implementation edits are currently indicated by this review; the issue remains AC/test-contract proof quality.

### Reflection
- Defining the exact expected string without asserting it is a recurrent false-green pattern in mirror-value tests.
- The retry improved coverage, but it did not cross the line from subset membership to exact-value proof on the refined contract.
- Because this is the second review failure, another narrow test-only retry would just repeat the loop unless the AC/test contract is tightened first.
[[2026-05-03]]

## Architecture Review (Return Cycle)

### Context
Task returned to backlog via reviewer loop-breaker after two review FAIL cycles. Both reviews confirmed the **implementation artifacts are correct** — the sole issue is test proof quality (assertions are substring-membership checks instead of exact-value assertions).

### Refined AC — Test-Writer Retry Guidance

The Refined Acceptance Criteria section above remains authoritative. This addendum clarifies the **assertion contract** for the test-writer's next retry. No AC lines change; only assertion expectations are tightened.

| AC | Current test weakness | Required assertion fix |
|----|----------------------|----------------------|
| AC1 | Checks 4 `.owlbear/...` substrings in YAML field | Assert `applyTo_value == _FULL_APPLY_TO` (exact equality). The canonical value includes BOTH `share/...` and `.owlbear/...` halves. |
| AC2 | Checks 4 `.owlbear/...` substrings in README row | Assert `_FULL_APPLY_TO in row` (full canonical value appears as substring in the table row). |
| AC3 | Checks 4 `.owlbear/...` substrings in h-agent-structure row | Assert `_FULL_APPLY_TO in row` (full canonical value appears as substring in the table row). |
| AC4 | Checks only `.owlbear/agents/**` in WIRING Table 2 row | Assert BOTH `share/agents/**` AND `.owlbear/agents/**` appear in the row (the abbreviated form includes both halves of the split). |
| AC5 | Already adequate (reviewer: PASS) | No change needed. |

**Key instruction:** `_FULL_APPLY_TO` is already defined in the test file at line 26. USE IT in assertions. The retry failed because the constant was defined but never asserted against.

**Scope of retry:** Test-only. No implementation files need changes. The 5 existing "stronger" tests (lines 145–270) should be rewritten to use exact-value assertions. The 5 original weaker tests (lines 35–140) may be removed or kept as supplementary.

### Evaluation (unchanged from first review)

| Criterion | Assessment |
|-----------|-----------|
| Single responsibility | PASS |
| Interface clarity | PASS (after assertion guidance above) |
| Dependency correctness | PASS (#1282 done) |
| Module layering | N/A (docs-only) |
| TDD compliance | PASS |
| KISS/YAGNI | PASS |
| Premise challenge | PASS |
| Pattern consistency | PASS |
| Security surface | N/A |
| Single domain | PASS |

### Design Diverge
Skipped — single approach (exact-value assertions).

### Challenge Results
Skipped — all td:0 exempt, and the only change is tightening assertion specificity on an already-correct implementation. The architectural decision (applyTo extension + mirrors) was challenged and approved in the first cycle.

### Test Depth
- Max depth: 1
- Test-writer: PROCEED (5 lines td:1, assertions need exact-value rewrite)

### Verdict: APPROVE
### Action Taken: Added assertion-contract guidance table clarifying exact-value vs. substring expectations for each AC line. No AC changes. Test-writer retry is test-only (implementation correct). Advancing to todo.

[[2026-05-03]]
Architecture review (return cycle). Implementation is correct — sole issue is test proof quality. Added assertion-contract guidance table: AC1 needs exact equality against _FULL_APPLY_TO; AC2/AC3 need full canonical value as substring in row; AC4 needs both share/agents/** and .owlbear/agents/** in abbreviated row. Test-writer retry is test-only. Advancing to todo.
[[2026-05-03]]
## Test-Writer Notes
- Retry (3rd cycle): rewrote 5 exact-value assertions per Architecture Review return-cycle guidance. All 10 tests pass against current (correct) impl.
- Builder skip: test-only retry, all tests green.
- Test file: tests/test_cross_references_1283.py
- Class: TestFromAC_ApplyToExtension (10 tests total: 5 original weaker preserved + 5 rewritten with exact-value assertions)
- ruff: clean
- Commit: c4c10dd0

### Retry changes (AR return-cycle required follow-up)
| Reviewer gap | Fix applied |
|---|---|
| AC1: `applyTo_value == _FULL_APPLY_TO` (exact equality, not membership) | `assert apply_to_value == _FULL_APPLY_TO` |
| AC2: full canonical value in README row (not just 4 .owlbear paths) | `assert _FULL_APPLY_TO in row` |
| AC3: full canonical value in h-agent-structure row (not just 4 .owlbear paths) | `assert _FULL_APPLY_TO in row` |
| AC4: BOTH `share/agents/**` AND `.owlbear/agents/**` in Table 2 row | two separate `assert ... in row` |
| AC5: already adequate — no change | unchanged |

All 10 tests green. pytest: 10 passed, 0 failed. ruff: clean.
[[2026-05-03]]
## Builder Notes
- Non-implementation retry cycle: implementation artifacts were already correct; this pass validates current snapshot and advances routing.
- Files changed: none.
- Tests: 10 passed, 0 failed, 0 skipped on `tests/test_cross_references_1283.py` (quality-runner scoped run).
- Ruff: clean on `tests/test_cross_references_1283.py`.
- Coverage: not applicable for this docs/assertion-only task; quality-runner reported no instrumented modules (expected).
- Evidence summary: AC-proof assertions are now exact-value checks in the test snapshot; scoped quality gate is green.

### Reflection
- Test-only retry cycles benefit from explicit builder pass-through notes to avoid unnecessary implementation churn.
- For docs/instruction assertion tasks, coverage output can be zero while still being a valid GREEN gate; recording this prevents false alarms.
- Keeping verification scoped to the task test file avoids unrelated-suite noise and gives a deterministic handoff to review.
[[2026-05-03]]
## Review Evidence
### Test Results
- quality-runner pytest: 10 passed, 0 failed on [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L145)

### Lint
- quality-runner ruff: clean on [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L1)

### Coverage
- Not applicable for this docs-only artifact-validation task. The tests validate markdown/instruction content rather than instrumented runtime modules.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: YAML `applyTo` field equals the full canonical value at [share/instructions/agent-ecosystem.instructions.md](share/instructions/agent-ecosystem.instructions.md#L3) | [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L145) with exact equality at [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L173) | Yes. The test extracts the YAML field and asserts `apply_to_value == _FULL_APPLY_TO`, so any missing `share/...` or `.owlbear/...` segment fails. | COVERED |
| AC2: README stubs row mirrors the full AC1 value at [share/README.md](share/README.md#L106) | [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L179) with full canonical-row assertion at [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L193) | Yes. The row must contain the full canonical `applyTo` string, so partial mirror regressions fail. | COVERED |
| AC3: h-agent-structure stubs row mirrors the full AC1 value at [share/skills/h-agent-structure/SKILL.md](share/skills/h-agent-structure/SKILL.md#L328) | [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L200) with full canonical-row assertion at [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L220) | Yes. The row must contain the full canonical `applyTo` string, so partial mirror regressions fail. | COVERED |
| AC4: WIRING Table 2 row reflects the split scope at [share/WIRING.md](share/WIRING.md#L226) | [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L227) with row assertions at [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L243) and [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L248) | Yes for the current Architecture Review retry contract. The row must contain both `share/agents/**` and `.owlbear/agents/**`, which catches the named abbreviated-scope regression. | COVERED |
| AC5: WIRING Gap Analysis notes reflect `.owlbear/` ecosystem scope at [share/WIRING.md](share/WIRING.md#L257) | [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L254) with scope-language assertion at [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L269) | Yes. The test requires both `.owlbear/` and `ecosystem`, so the intended scope wording is discriminating. | COVERED |

#### Security Review
- No issues in the doc-only artifacts at [share/instructions/agent-ecosystem.instructions.md](share/instructions/agent-ecosystem.instructions.md#L3), [share/README.md](share/README.md#L106), [share/WIRING.md](share/WIRING.md#L226), [share/WIRING.md](share/WIRING.md#L257), and [share/skills/h-agent-structure/SKILL.md](share/skills/h-agent-structure/SKILL.md#L344).

#### Test Integrity
- PRESERVED. Builder implementation commit `e66cbe42` changed only [share/README.md](share/README.md), [share/WIRING.md](share/WIRING.md), [share/instructions/agent-ecosystem.instructions.md](share/instructions/agent-ecosystem.instructions.md), and [share/skills/h-agent-structure/SKILL.md](share/skills/h-agent-structure/SKILL.md).
- Test-writer commit `c4c10dd0` changed only [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py).
- Latest builder cycle is a pass-through with no file changes, per [.owlbear/kanban/tasks/1283-p1-03-update-cross-references-in-readme-wiring-h-agent-structure-h-memory-struct.md](.owlbear/kanban/tasks/1283-p1-03-update-cross-references-in-readme-wiring-h-agent-structure-h-memory-struct.md#L427). No builder modification to `TestFromAC_*` assertions was detected.

#### Test Quality
- Assertion specificity: ADEQUATE. AC1 now uses exact equality at [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L173). AC2 and AC3 assert the full canonical value at [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L193) and [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L220). AC4 asserts both abbreviated halves at [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L243) and [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L248). AC5 asserts `.owlbear/` plus `ecosystem` at [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L269).
- Manual mutation resistance: ADEQUATE. Removing required `share/...` or `.owlbear/...` segments from AC1-AC4, or dropping ecosystem wording from AC5, would now fail the strengthened tests.
- Independence and naming: STRONG. The tests are isolated file-content reads with clear, AC-scoped names.
- Informational only: the original weaker tests remain as supplementary coverage, but the review verdict is anchored to the strengthened assertions added in the latest retry.

#### Data Safety
- No issues. This task only changes static documentation and instruction artifacts.

#### Implementation-Aware Test Gaps
- No significant gaps. The task-owned behavior is static artifact content, and each td:1 AC line now has direct executable proof plus direct artifact inspection.

#### Builder Process Quality
- CLEAN. Task history shows one implementation pass at [.owlbear/kanban/tasks/1283-p1-03-update-cross-references-in-readme-wiring-h-agent-structure-h-memory-struct.md](.owlbear/kanban/tasks/1283-p1-03-update-cross-references-in-readme-wiring-h-agent-structure-h-memory-struct.md#L154), then builder-skip/pass-through notes at [.owlbear/kanban/tasks/1283-p1-03-update-cross-references-in-readme-wiring-h-agent-structure-h-memory-struct.md](.owlbear/kanban/tasks/1283-p1-03-update-cross-references-in-readme-wiring-h-agent-structure-h-memory-struct.md#L267) and [.owlbear/kanban/tasks/1283-p1-03-update-cross-references-in-readme-wiring-h-agent-structure-h-memory-struct.md](.owlbear/kanban/tasks/1283-p1-03-update-cross-references-in-readme-wiring-h-agent-structure-h-memory-struct.md#L427). No repeated implementation churn remains in the passing cycle.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | [share/instructions/agent-ecosystem.instructions.md](share/instructions/agent-ecosystem.instructions.md#L3) and exact field assertion at [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L173) | [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L145) | PASS |
| AC2 | [share/README.md](share/README.md#L106) and full canonical-row assertion at [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L193) | [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L179) | PASS |
| AC3 | [share/skills/h-agent-structure/SKILL.md](share/skills/h-agent-structure/SKILL.md#L328) and full canonical-row assertion at [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L220) | [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L200) | PASS |
| AC4 | [share/WIRING.md](share/WIRING.md#L226) and dual abbreviated-scope assertions at [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L243) and [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L248) | [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L227) | PASS |
| AC5 | [share/WIRING.md](share/WIRING.md#L257) and `.owlbear/` + `ecosystem` assertion at [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L269) | [tests/test_cross_references_1283.py](tests/test_cross_references_1283.py#L254) | PASS |
| AC6 | [share/skills/h-agent-structure/SKILL.md](share/skills/h-agent-structure/SKILL.md#L344) matches the refined cosmetic wording. | td:0 - no test required | PASS |
| Verification: README substantive-docs row already correct | [share/README.md](share/README.md#L97) remains correct. | td:0 - no test required | PASS |
| Verification: WIRING filename references remain valid | [share/WIRING.md](share/WIRING.md#L42) remains valid. | td:0 - no test required | PASS |
| Verification: h-memory-structure reference remains valid | [share/skills/h-memory-structure/SKILL.md](share/skills/h-memory-structure/SKILL.md#L43) remains valid. | td:0 - no test required | PASS |

### Deductions
- -0.04: AC2-AC4 use row-level assertions rather than parsing markdown cells exactly, so there is minor residual proof risk even though the latest Architecture Review retry contract explicitly accepted this row-level form and the live artifacts match.

### Verdict
- PASS with confidence 0.94. The current strengthened tests and direct artifact inspection satisfy the refined acceptance criteria; the earlier FAIL sections in the task history are stale against the current repo state.

### Action
- Advance to `docs`.
- No builder or test-writer follow-up is required from this review.

### Reflection
- Earlier review sections in the task body lagged behind the live test file; the final verdict needed to anchor to the current repo state, not stale notes.
- Exact-value assertions resolved the earlier false-green pattern without any further implementation churn.
- Builder-skip notes were useful evidence here because they made the final cycle's ownership boundaries explicit.
[[2026-05-03]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | N/A (already updated by builder) | `share/README.md` and `share/WIRING.md` were updated by builder commit `e66cbe42`; reviewer PASS at 0.94 confirmed correctness |
| 2 | Module docstrings | No | N/A | No Python modules created or modified |
| 3 | External attribution | No | N/A | No external patterns cited in task |
| 4 | Research doc | Yes | Verified | `.owlbear/research/p1-03-cross-reference-update.md` exists and is linked from task body |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/project-overview.excalidraw` has `describes: serve/*/pyproject.toml, share/**, setup/**, .owlbear/**` — matches changed `share/README.md`, `share/WIRING.md`, `share/instructions/agent-ecosystem.instructions.md`, `share/skills/h-agent-structure/SKILL.md`; footer updated from `f82de323` to `8c413efa` (current HEAD) |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No files deleted; no orphaned IN-scope docs detected |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| share/README.md | IN | Already updated by builder; verified correct by reviewer |
| share/WIRING.md | IN (adjacent doc) | Already updated by builder; verified correct by reviewer |
| share/instructions/agent-ecosystem.instructions.md | OUT (agent-executable) | No edit; builder changes verified correct |
| share/skills/h-agent-structure/SKILL.md | OUT (agent-executable SKILL.md) | No edit; builder changes verified correct |
| tests/test_cross_references_1283.py | OUT (test file) | No edit |
| share/diagrams/project-overview.excalidraw | IN | Footer updated: commit `2210970c` |

### Files Updated
- `share/diagrams/project-overview.excalidraw` — footer updated to `Last verified: 2026-05-03 (8c413efa)`

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `1283-*` scratch files found)
[[2026-05-03]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: agent-ecosystem.instructions.md YAML applyTo extended | Live file confirmed — exact match. Test exact equality at test_cross_references_1283.py:173 | PASS |
| AC2: share/README.md mirrors full value | Reviewer verified at README.md:106, test at test_cross_references_1283.py:193 | PASS |
| AC3: h-agent-structure stubs row mirrors full value | Reviewer verified at SKILL.md:328, test at test_cross_references_1283.py:220 | PASS |
| AC4: WIRING Table 2 row includes both halves | Reviewer verified, dual assertion at test_cross_references_1283.py:243,248 | PASS |
| AC5: WIRING Gap Analysis notes reflect ecosystem scope | Reviewer verified, test at test_cross_references_1283.py:269 | PASS |
| AC6: h-agent-structure cosmetic fix | Live file confirmed (lines 340-348) — matches refined wording | PASS |
| Verification: README substantive-docs already correct | Reviewer verified at README.md:97 | PASS |
| Verification: WIRING filename refs valid | Reviewer verified at WIRING.md:42 | PASS |
| Verification: h-memory-structure ref valid | Reviewer verified at h-memory-structure:43 | PASS |

### Test Results
- pytest: 3797 passed, 130 failed (0 in task scope), 4 skipped
- Task-scoped: 10/10 passed (test_cross_references_1283.py)
- ruff: 1 violation in copilot_auth.py (unrelated)
- vitest: 769 failed (all pre-existing, unrelated to docs-only task)

### Architect Quality: 3/5
Initial AC was 6 vague cross-reference checks requiring full replacement. Refined AC was specific but lacked assertion-contract guidance, causing 2 review cycles before the return-cycle AR added it.

### Deduction Breakdown
- 9/9 AC lines verified with specific evidence: no deduction
- Lint in task scope: clean → no deduction
- AC quality score ≤ 3: -0.03
- Reviewer evidence: present, detailed, PASS at 0.94 → no deduction
- Full-suite failures in task scope: 0 → no deduction
- Commits verified: e66cbe42 (builder), c4c10dd0 (test-writer), c095374d (initial test-writer) → no deduction

### Confidence: .97
### Action: archive