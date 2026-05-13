---
id: 1522
title: 'P2-03: Tests for proof_bundle migration script'
status: done
priority: needed
created: 2026-05-13T02:29:59.211402+00:00
updated: 2026-05-13T05:31:47.895962+00:00
tags:
  - phase-2
  - scope:kanban
  - tdd
  - feature
  - migration
parent: 1514
depends_on:
  - 1516
blocked: false
block_reason:
claimed_at: 2026-05-13T05:31:47.895962+00:00
archival_reason:
archival_refs: []
---
Brief: see parent #1514

## Scope
In scope: Unit tests for migration function that extracts proof_bundle from body to frontmatter
Out of scope: Engine changes, MCP tools, skill files

## Acceptance Criteria
- AC1: A callable in `owlbear_kanban.migrate` reads a task file whose body contains a line matching `Proof bundle: smoke`, extracts value `"smoke"` from the first body-line match, and writes it to the frontmatter `proof_bundle` field
- AC2: After extraction, only the first matched `Proof bundle:` line is removed from body text; later occurrences in pipeline-note sections are preserved
- AC3: When frontmatter already contains a non-None `proof_bundle` value, the callable returns without modifying the file

Proof bundle: behavioral
2026-05-13T03:58:40+00:00
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tests only for proof_bundle migration function |
| Interface clarity | PASS (after refine) | Refined AC to name module (`owlbear_kanban.migrate`), specify first-match semantics, and clarify preservation of pipeline-note occurrences |
| Dependency correctness | PASS | #1516 archived/completed; model fields and storage canonical fields in place |
| Module layering | PASS | Tests import from `owlbear_kanban.migrate`, no upward imports |
| TDD compliance | PASS | This IS the RED task; #1523 is the paired GREEN task |
| KISS/YAGNI | PASS | Three focused AC lines, no unnecessary complexity |
| Premise challenge | PASS | Migration of proof_bundle from body to frontmatter is necessary for structured task spec feature |
| Pattern consistency | PASS | Follows existing `_migrate_task_file(path, *, dry_run)` pattern in migrate.py |
| Security surface | PASS | File I/O within kanban directory only, no external boundaries |
| Single domain | PASS | scope:kanban only |

### AC Refinements Applied
| AC | Original Issue | Refined Wording |
|----|---------------|-----------------|
| AC1 | "Migration function" failed B1 (no concrete target) | "A callable in `owlbear_kanban.migrate`" — names the module |
| AC2 | "the matched line" ambiguous with multi-match bodies | "only the first matched `Proof bundle:` line is removed; later occurrences in pipeline-note sections are preserved" |
| AC3 | Minor — "skips tasks" lacked observable outcome | "returns without modifying the file" — clearer testable assertion |

### Challenger Concern Disposition
| Concern | Severity | Disposition |
|---------|----------|-------------|
| Destructive-match ambiguity | critical | ACCEPTED — refined AC2 to specify first-match-only removal, preserve pipeline notes |
| AC quality B1/B2 | moderate | ACCEPTED — refined AC1 to name module, AC3 to specify observable outcome |
| Normalization gap | moderate | DISMISSED — model validator normalizes on `read_task()`; migration writes raw extracted value; normalization at write is an implementation choice, not a test contract |
| Canonical-order gap | moderate | DISMISSED — `migrate._CANONICAL_FIELDS` update is implementation scope for #1523, not test scope for #1522 |

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral (confirmed — TDD RED task for destructive migration function warrants full test coverage)
- Test-writer: PROCEED

### Design Diverge
- Trigger: skipped — single established approach (follows existing `_migrate_task_file` pattern), no alternatives to evaluate

### Challenge Results
- Challenger: reconsider (confidence 0.41)
- Architect response: accepted 2 of 4 concerns, refined AC accordingly; dismissed normalization (model handles on read) and canonical-order (implementation scope for #1523)

### Verdict: APPROVE
### Action Taken: Refined AC1 (module location), AC2 (first-match semantics), AC3 (observable outcome). Advanced #1522 → todo.
2026-05-13T04:05:05+00:00
## Test-Writer Notes
- Test file: tests/test_migrate_1522.py
- Classes: TestFromAC_ProofBundleMigration
- Tests per category: happy 6, edge 6, error 3, boundary 3
- Total: 18 tests, all FAIL (ImportError: `_migrate_proof_bundle_field` not yet in `owlbear_kanban.migrate`)
- ruff: clean

### AC Coverage
| AC | Tests |
|----|-------|
| AC1 — extracts value from first body-line match, writes to frontmatter | test_returns_migrated_status_on_success, test_extracts_smoke_value_to_frontmatter, test_extracts_behavioral_value_to_frontmatter, test_extracts_critical_value_to_frontmatter, test_value_with_surrounding_whitespace_trimmed, test_proof_bundle_line_at_start_of_body, test_dry_run_does_not_write_file |
| AC2 — only first matched line removed; later occurrences preserved | test_first_occurrence_removed_from_body, test_second_occurrence_preserved_in_body, test_only_first_of_multiple_occurrences_removed, test_pipeline_note_occurrence_preserved |
| AC3 — non-None proof_bundle already in frontmatter → no modification | test_returns_already_when_proof_bundle_set, test_file_not_modified_when_proof_bundle_already_set, test_proof_bundle_null_in_frontmatter_proceeds, test_missing_proof_bundle_key_proceeds |

### Notes for Builder (#1523)
- Function signature expected: `_migrate_proof_bundle_field(path: Path, *, dry_run: bool = False) -> tuple[str, str | None]`
- Returns: `('migrated', None)`, `('already', None)`, or `('failed', reason)`
- Pattern: follows existing `_migrate_task_file` in `owlbear_kanban.migrate`
- `proof_bundle: null` in frontmatter is treated as None → proceed with migration
- Empty `Proof bundle:` value (no text after colon) → treat as no-op (`already` or `failed`)
2026-05-13T04:13:40+00:00
## Builder Notes
- Files changed: serve/kanban/src/owlbear_kanban/migrate.py
- Implemented: added `_migrate_proof_bundle_field(path, *, dry_run=False) -> tuple[str, str | None]` to extract first `Proof bundle:` body line into frontmatter `proof_bundle`, remove only first matched line, preserve later occurrences, and short-circuit when frontmatter already has non-None `proof_bundle`.
- Error handling: missing delimiters, YAML parse errors, and file I/O failures return `('failed', reason)`.
- Dry-run behavior: returns `('migrated', None)` without writing.

- RED verification (quality-runner): tests/test_migrate_1522.py failed at import with missing callable (expected RED).
- Module durable baseline (quality-runner): serve/kanban/tests/test_migrate.py passed (71/71), lint clean.
- GREEN verification (quality-runner):
  - Tests: 91 passed, 0 failed (tests/test_migrate_1522.py + serve/kanban/tests/test_migrate.py)
  - Lint: clean (ruff)
  - Coverage: owlbear_kanban.migrate reported 24% in scoped run

- Commit: `6aa8b807` with message `feat: migrate proof_bundle body field (#1522, builder)`.
2026-05-13T04:27:09+00:00
## Review Evidence
- Verdict: FAIL
- Routing: FAIL #1522 -> todo | AC1 and AC2 first-match semantics are not independently pinned by the test suite.
- Builder evidence reviewed first: the builder-provided scoped test, lint, and coverage packet was internally consistent, so no independent rerun was required.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | [serve/kanban/src/owlbear_kanban/migrate.py](serve/kanban/src/owlbear_kanban/migrate.py#L289), [serve/kanban/src/owlbear_kanban/migrate.py](serve/kanban/src/owlbear_kanban/migrate.py#L297), [serve/kanban/src/owlbear_kanban/migrate.py](serve/kanban/src/owlbear_kanban/migrate.py#L303) show the current first-match scan and extracted-value write. | The multi-match fixtures at [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L137) and [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L153) reuse the same value for every occurrence and assert only remaining presence or count. | FAIL — the suite does not independently prove that the first exact-match body line, rather than a later exact-match line, supplies the frontmatter proof_bundle value. |
| AC2 | [serve/kanban/src/owlbear_kanban/migrate.py](serve/kanban/src/owlbear_kanban/migrate.py#L289), [serve/kanban/src/owlbear_kanban/migrate.py](serve/kanban/src/owlbear_kanban/migrate.py#L298), [serve/kanban/src/owlbear_kanban/migrate.py](serve/kanban/src/owlbear_kanban/migrate.py#L304) show the current implementation removes the matched index from the first scan hit. | [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L128) proves removal in the single-match case, but [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L137), [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L153), and [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L169) do not distinguish which exact-match line was removed when multiple exact-match lines exist. | FAIL — a regression that removes a later exact-match line would still satisfy the current multi-match assertions. |
| AC3 | [serve/kanban/src/owlbear_kanban/migrate.py](serve/kanban/src/owlbear_kanban/migrate.py#L284) shows the non-None short-circuit. | [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L189), [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L197), [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L208), [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L216) cover return-without-modification, null, and missing-key behavior. | PASS |

- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---|---|---|---|
| 1 | AC1 | Multi-match fixtures do not falsify later-match extraction. | [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L137), [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L153) | todo |
| 2 | AC2 | Multi-match fixtures do not falsify later-match removal. | [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L128), [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L137), [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L153), [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L169) | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add a differentiated multi-match fixture with different proof_bundle values across the first and later exact-match body lines, then assert both that the frontmatter value comes from the first exact-match line and that only that first exact-match line is removed. | [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L137) | AC1 and AC2 proof gap shown by [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L137), [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L153), [serve/kanban/src/owlbear_kanban/migrate.py](serve/kanban/src/owlbear_kanban/migrate.py#L289), [serve/kanban/src/owlbear_kanban/migrate.py](serve/kanban/src/owlbear_kanban/migrate.py#L304) |

## Observations
- Current source behavior appears correct: the helper stops on the first exact body-line match and removes that same index at [serve/kanban/src/owlbear_kanban/migrate.py](serve/kanban/src/owlbear_kanban/migrate.py#L289), [serve/kanban/src/owlbear_kanban/migrate.py](serve/kanban/src/owlbear_kanban/migrate.py#L298), and [serve/kanban/src/owlbear_kanban/migrate.py](serve/kanban/src/owlbear_kanban/migrate.py#L304). That is why this routes to todo rather than in-progress.
- The rejection is about proof strength, not missing execution evidence.
2026-05-13T04:37:28+00:00
## Test-Writer Notes
- Retry: added 2 differentiated-value multi-match tests to close AC1/AC2 proof gaps flagged by reviewer.
- `test_frontmatter_value_comes_from_first_match_not_later`: body has `smoke` first, `behavioral` later — asserts frontmatter gets `smoke` (proves first-match extraction, not any-match).
- `test_first_match_line_removed_not_later_match_line`: same fixture — asserts `smoke` line removed from body, `behavioral` line preserved (proves first-line removal, not any-line removal).
- Builder skip: test-only retry; all 22 tests pass against current impl.
- Commit: `90fa7379`
2026-05-13T04:52:48+00:00
## Review Evidence
- Verdict: FAIL
- Routing: FAIL #1522 -> backlog | retry still relies on substring assertions, so AC1 exact extracted value and AC2 exact later-line preservation can false-pass on a second review cycle.
- Builder evidence reviewed first: the prior builder packet was internally consistent. Because the retry note omitted fresh lint evidence for the changed test file, I independently verified the retry via quality-runner: `uv run pytest tests/test_migrate_1522.py -v` -> 22 passed, 0 failed; `uv run ruff check tests/test_migrate_1522.py` -> clean; coverage intentionally skipped because this was a test-only retry with no source changes.
- Challenger cross-check: `reconsider` (confidence 0.64), accepted on proof-sufficiency grounds.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | [serve/kanban/src/owlbear_kanban/migrate.py](serve/kanban/src/owlbear_kanban/migrate.py#L284), [serve/kanban/src/owlbear_kanban/migrate.py](serve/kanban/src/owlbear_kanban/migrate.py#L287), [serve/kanban/src/owlbear_kanban/migrate.py](serve/kanban/src/owlbear_kanban/migrate.py#L290), [serve/kanban/src/owlbear_kanban/migrate.py](serve/kanban/src/owlbear_kanban/migrate.py#L297), [serve/kanban/src/owlbear_kanban/migrate.py](serve/kanban/src/owlbear_kanban/migrate.py#L298) show first-match scan/write behavior. | The retry adds differentiated-value coverage at [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L282), but the key assertions at [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L300) and [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L301) are substring membership checks, not exact parsed-value checks. | FAIL — a wrong write that still contains the expected substring would not be falsified. |
| AC2 | [serve/kanban/src/owlbear_kanban/migrate.py](serve/kanban/src/owlbear_kanban/migrate.py#L287), [serve/kanban/src/owlbear_kanban/migrate.py](serve/kanban/src/owlbear_kanban/migrate.py#L298), [serve/kanban/src/owlbear_kanban/migrate.py](serve/kanban/src/owlbear_kanban/migrate.py#L304) remove the first matched index only. | The retry adds differentiated removal coverage at [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L303), but the key assertions at [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L322) and [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L323) are substring membership checks rather than exact preserved-line checks. Exact-count coverage still exists for identical later lines at [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L153) and [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L167), but not for the differentiated fixture that closed the first-vs-later gap. | FAIL — the differentiated fixture still allows a false green if the preserved later line changes while retaining the expected substring. |
| AC3 | [serve/kanban/src/owlbear_kanban/migrate.py](serve/kanban/src/owlbear_kanban/migrate.py#L284) short-circuits when `proof_bundle` already exists. | [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L189), [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L197), [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L208), [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L216) still cover already/no-modification/null/missing-key behavior. | PASS |

- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---|---|---|---|
| 1 | AC1 | Differentiated retry assertions do not prove the exact frontmatter value, only presence/absence of substrings. | [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L282), [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L300), [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L301) | backlog |
| 2 | AC2 | Differentiated retry assertions do not prove exact preservation of the later matched line, only substring presence/absence. | [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L303), [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L322), [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L323) | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Tighten the proof contract for AC1 so the retry must assert the exact parsed `proof_bundle` value in frontmatter, not substring membership, and re-dispatch RED from backlog. | [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L282) | False-green risk at [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L300) and [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L301) |
| 2 | architect | Tighten the proof contract for AC2 so the differentiated multi-match fixture asserts exact preserved later-line content, not substring membership, and re-dispatch RED from backlog. | [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L303) | False-green risk at [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L322) and [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L323) |

## Observations
- The source helper still appears behaviorally correct for the current implementation at [serve/kanban/src/owlbear_kanban/migrate.py](serve/kanban/src/owlbear_kanban/migrate.py#L287), [serve/kanban/src/owlbear_kanban/migrate.py](serve/kanban/src/owlbear_kanban/migrate.py#L297), [serve/kanban/src/owlbear_kanban/migrate.py](serve/kanban/src/owlbear_kanban/migrate.py#L298), and [serve/kanban/src/owlbear_kanban/migrate.py](serve/kanban/src/owlbear_kanban/migrate.py#L304); this remains a proof-quality rejection, not an implementation defect.
- Independent retry verification succeeded: `tests/test_migrate_1522.py` passed 22/22 and ruff was clean.
- Because this is the second review cycle on the same task, the remaining proof-quality blockers escalate to backlog per pipeline policy.
2026-05-13T05:06:29+00:00

## AC Refinement (supersedes original AC1, AC2, AC3)
- AC1: `_migrate_proof_bundle_field` in `owlbear_kanban.migrate` reads a task file whose body contains a line matching `Proof bundle: smoke`, extracts value `"smoke"` from the first body-line match, and writes it to the frontmatter `proof_bundle` field. Differentiated multi-match tests must YAML-parse the written frontmatter and assert `parsed["proof_bundle"] == expected_first_match_value`; substring membership of raw frontmatter text is insufficient proof.
- AC2: After extraction, only the first matched `Proof bundle:` line is removed from body text; later occurrences in pipeline-note sections are preserved. Differentiated multi-match tests must assert exact line-level presence/absence (e.g., splitting body into lines and checking list membership) rather than substring search of the full body string.
- AC3: When frontmatter already contains a non-None `proof_bundle` value, `_migrate_proof_bundle_field` returns without modifying the file.
2026-05-13T05:06:48+00:00
## Architecture Re-Review (proof-quality refinement)

### Context
Second review cycle rejected #1522 → backlog because differentiated multi-match test assertions used substring membership (`"proof_bundle: smoke" in fm_text`) rather than exact parsed-value assertions. Reviewer requested architect tighten proof contracts for AC1 and AC2.

### AC Refinements Applied
| AC | Original Issue | Refined Wording |
|----|---------------|-----------------|
| AC1 | Substring membership of raw YAML text allows false-green (e.g., `proof_bundle: smokey` matches `"proof_bundle: smoke"`) | Must YAML-parse frontmatter and assert `parsed["proof_bundle"] == expected_first_match_value` |
| AC2 | Substring search of full body string doesn't prove which exact line was removed/preserved | Must assert exact line-level presence/absence (line-list membership, not substring) |
| AC3 | No change | Named `_migrate_proof_bundle_field` explicitly per challenger feedback |

### Challenge Results
- Challenger: reconsider (confidence 0.34)
- Disposition: ACCEPTED #1 (named function in AC), ACCEPTED #2 (persisted refinement before advancing). DISMISSED #3 (canonical-order is #1523 scope, not #1522). DISMISSED #4 (single-match substring risk is negligible; reviewer scoped concern to multi-match only).
- Architect response: accepted 2, dismissed 2 with justification

### Proof-Bundle Validation
- Final bundle: behavioral (unchanged)
- Test-writer: PROCEED (fix differentiated multi-match assertions only)

### Design Diverge
- Trigger: skipped — refinement-only cycle, no alternative approaches

### Verdict: APPROVE (REFINE path — AC tightened, then advanced)
### Action Taken: Refined AC1/AC2 proof contracts to mandate YAML-parsed exact-value and line-level assertions for differentiated multi-match tests. Named `_migrate_proof_bundle_field` in all AC lines. Advanced #1522 → todo.
2026-05-13T05:09:57+00:00
## Test-Writer Notes
- Retry: added 2 exact-assertion tests to close AC1/AC2 proof gaps flagged by second reviewer cycle.
- `test_frontmatter_proof_bundle_exact_yaml_value_first_match`: body has `smoke` first, `behavioral` later — YAML-parses written frontmatter and asserts `parsed["proof_bundle"] == "smoke"` (exact value, falsifies substring false-green).
- `test_first_match_line_absent_later_line_present_exact_lines`: same fixture — splits body into lines and checks list membership (`"Proof bundle: smoke" not in body_lines`, `"Proof bundle: behavioral" in body_lines`) instead of substring search of full body string.
- Builder skip: test-only retry; all 24 tests pass against current impl (22 preserved + 2 new). Implementation is correct — proof contract was weak, not the code.
- Lint: clean (ruff). Commit: `87cad468`.
2026-05-13T05:19:08+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1522 -> docs | AC mapped to code and evidence sufficient.
- Upstream evidence reviewed first: the prior builder packet for the source helper remained internally consistent, and the latest test-only retry supplied scoped test and lint status for the changed test file. Because the current cycle changed tests only and the evidence was not contradictory, no independent quality-runner rerun was cost-justified.
- Challenger cross-check: proceed (confidence 0.83).
- Blocking findings: none.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | [serve/kanban/src/owlbear_kanban/migrate.py](serve/kanban/src/owlbear_kanban/migrate.py#L289), [serve/kanban/src/owlbear_kanban/migrate.py](serve/kanban/src/owlbear_kanban/migrate.py#L293), [serve/kanban/src/owlbear_kanban/migrate.py](serve/kanban/src/owlbear_kanban/migrate.py#L298), [serve/kanban/src/owlbear_kanban/migrate.py](serve/kanban/src/owlbear_kanban/migrate.py#L303) iterate body lines in order, extract the first exact match value, break on that first match, and write it to frontmatter. | [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L332), [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L350), [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L351) YAML-parse the written frontmatter and assert `parsed["proof_bundle"] == "smoke"`, closing the prior substring false-green. | PASS |
| AC2 | [serve/kanban/src/owlbear_kanban/migrate.py](serve/kanban/src/owlbear_kanban/migrate.py#L289), [serve/kanban/src/owlbear_kanban/migrate.py](serve/kanban/src/owlbear_kanban/migrate.py#L298), [serve/kanban/src/owlbear_kanban/migrate.py](serve/kanban/src/owlbear_kanban/migrate.py#L304) stop at the first matched body line and remove that exact indexed line only. | [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L353), [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L371), [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L372), [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L373) split the migrated body into lines and assert exact line-level absence of `Proof bundle: smoke` with exact preservation of the later `Proof bundle: behavioral` line inside the pipeline-note section. | PASS |
| AC3 | [serve/kanban/src/owlbear_kanban/migrate.py](serve/kanban/src/owlbear_kanban/migrate.py#L284) short-circuits when `proof_bundle` is already non-None. | [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L191), [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L197), [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L199), [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L208), [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L210), [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L216), [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L218), [tests/test_migrate_1522.py](tests/test_migrate_1522.py#L224) cover already/no-modification/null/missing-key behavior. | PASS |

## Observations
- The two prior false-green vectors are now closed by exact parsed-value proof for AC1 and exact line-membership proof for AC2.
- Editor diagnostics reported no errors in [tests/test_migrate_1522.py](tests/test_migrate_1522.py) or [serve/kanban/src/owlbear_kanban/migrate.py](serve/kanban/src/owlbear_kanban/migrate.py).
2026-05-13T05:30:49+00:00
## Docs Gate

### Checklist

| Item | Result | Evidence |
|------|--------|----------|
| README Verification | N/A — no update needed | `serve/kanban/README.md` migration section documents CLI interface only; `_migrate_proof_bundle_field` is a private helper (underscore-prefixed), not a public API change. No drift introduced. |
| External Attribution | N/A | Internal implementation; no external sources cited. |
| Research Doc | N/A | No research artifact referenced in task body. |
| Deletion Detection | N/A | No files deleted; only `serve/kanban/src/owlbear_kanban/migrate.py` (function addition) and `tests/test_migrate_1522.py` changed. |

### Files Updated
None — no documentation impact.

### Scratch Cleanup
No `.owlbear/scratch/1522-*` files found.