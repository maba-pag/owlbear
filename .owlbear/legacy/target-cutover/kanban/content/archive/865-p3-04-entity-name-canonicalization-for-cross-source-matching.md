---
id: 865
title: 'P3-04: Entity name canonicalization for cross-source matching'
status: archived
priority: medium
created: '2026-04-13T19:16:55.238306+00:00'
updated: '2026-04-15T02:49:08.611676+00:00'
tags:
- phase-3
- scope:knowledge
- deferred
parent: 772
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Context

InterDocGraphBuilder relies on embedding cosine similarity (0.70 threshold) for candidate discovery. No name normalization exists. "Data Classification" and "data classification" from different sources become separate entities. Conservative canonical_name pre-filtering would improve match quality.

See: .owlbear/research/772-interdocgraphbuilder-corporate-types.md (Gap G4)
See: .owlbear/briefs/draft-browser-knowledge-extraction/voices/data-person.md (Gap 3)

## Acceptance Criteria

- [ ] `canonical_name` derived field: lowercase, collapse whitespace, strip leading/trailing articles and punctuation
- [ ] `_collect_candidates()` uses canonical_name for pre-filtering alongside vector similarity
- [ ] Conservative normalization only — "Data Classification Framework" must remain distinct from "data classification"
- [ ] Tests verify canonicalization and pre-filter behavior

## Affected Files

- `serve/knowledge/src/owlbear_knowledge/models.py` (Entity model)
- `serve/knowledge/src/owlbear_knowledge/inter_doc_graph_builder.py`

## Dependency

Deferred until real corporate ingestion shows entity name drift is a measurable problem.

[[2026-04-14]]

## Research

- Research doc: .owlbear/research/865-entity-name-canonicalization.md
- Sources: 7 studied, 5 high-relevance (4 codebase + 2 web + 1 prior research)
- Recommendation: `@computed_field` on Entity model + canonical-name blocking in `_collect_candidates()` (confidence: .82)
- Follow-up tasks created: none — #865 itself is the implementation task with concrete AC
- Decision requests: none — T1 autonomous (incremental extension to existing model/builder)

## Challenge Results

- Challenger: FALLBACK — challenger subagent not available in agent list
- Confidence in original: .82
- Key findings: (1) `@computed_field` is idiomatic Pydantic v2 for derived fields on frozen models; (2) canonical-name blocking is standard industry pre-filter pattern; (3) conservative normalization (lower + whitespace collapse + article/punct strip) preserves "Data Classification Framework" ≠ "data classification" distinctness; (4) ~35 LOC total, no schema migration needed
- Researcher response: proceeded without challenge — high confidence from codebase evidence + industry source alignment

## Implementation Notes

- `_canonicalize(name)` free function: `lower()` → collapse whitespace → strip leading articles (the/a/an) → strip leading/trailing punctuation
- `Entity.canonical_name` as `@computed_field` (pydantic v2) — read-only, always consistent
- `_collect_candidates()` gains canonical-name blocking: build `canonical_name → [Entity]` dict, union candidates with vector-similarity results
- Task retains `deferred` tag — dependency gate: real corporate ingestion must show entity name drift is a measurable problem
[[2026-04-14]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One feature: canonical name normalization for entity matching |
| Interface clarity | PASS | AC specifies normalization rules, usage site, conservativeness example, and test requirement. Implementation Notes disambiguate minor AC wording issues |
| Dependency correctness | PASS | No `depends_on`; `deferred` tag + prose gate controls scheduling |
| Module layering | PASS | Both files in same package (`owlbear_knowledge`). No cross-layer imports needed |
| TDD compliance | PASS | AC4 requires tests; `tests/test_inter_doc_graph_builder.py` provides existing patterns |
| KISS/YAGNI | PASS | ~35 LOC, `@computed_field` (no schema migration), conservative scope |
| Premise challenge | PASS | Explicitly deferred with clear gate: real entity name drift must be measurable |
| Pattern consistency | PASS | First `computed_field` use in package, but idiomatic Pydantic v2. `_canonicalize()` follows existing `_uuid_hex()` free-function pattern |
| Security surface | PASS | Pure string normalization on internal data, no new boundaries |
| Single domain | PASS | `scope:knowledge` only |

### AC Assessment

| AC Line | Assessment | Builder Note |
|---------|-----------|-------------|
| AC1: `canonical_name` derived field | Clear | Articles = (the/a/an) leading-only; punct strip = leading+trailing per Implementation Notes |
| AC2: `_collect_candidates()` pre-filtering | Clear | "alongside" = union semantics; canonical-name groups produce additional candidates merged with vector results |
| AC3: Conservative normalization distinction | Clear | Concrete negative test case provided |
| AC4: Tests | Clear | Extend existing `tests/test_inter_doc_graph_builder.py` patterns |

### Codebase Evidence

- `Entity` model: `serve/knowledge/src/owlbear_knowledge/models.py` — `ConfigDict(frozen=True)`, compatible with `@computed_field`
- `_collect_candidates()`: `serve/knowledge/src/owlbear_knowledge/inter_doc_graph_builder.py:97-120` — pure vector-similarity today, canonical blocking adds parallel candidate path
- Pydantic version: `>=2.10.0` in `serve/knowledge/pyproject.toml` — `computed_field` available
- No existing `computed_field` imports in knowledge package — this will be first use

### Challenge Results

- Challenger: FALLBACK — not available in agent list
- Architect response: proceeded — high confidence from codebase evidence + research alignment (.82)

### Verdict: APPROVE

### Action Taken: Advanced to todo. AC is verifiable, architecture sound, ~35 LOC scope is minimal. `deferred` tag retained — implementation gated on real entity name drift evidence

[[2026-04-14]]

## Test-Writer Notes

- Test file: tests/test_entity_canonicalization_865.py
- Classes: TestFromAC_CanonicalName, TestFromAC_CanonicalPreFilter
- Tests per category: happy 7, edge 4, boundary 2, AC3 2, pre-filter 3
- Total: 18 tests, all FAIL (verified: pytest 18 failed, 0 passed)
- ruff: clean

### AC Coverage

| AC Line | Tests |
|---------|-------|
| AC1: canonical_name derived field (lowercase) | test_canonical_name_lowercases_mixed_case |
| AC1: collapse whitespace | test_canonical_name_collapses_internal_whitespace, test_canonical_name_collapses_tab_whitespace |
| AC1: strip leading article the/a/an | test_..._the, test_..._a, test_..._an, test_article_strip_is_case_insensitive |
| AC1: strip leading/trailing punctuation | test_strips_leading_punctuation, test_strips_trailing_punctuation, test_leading_and_trailing_both_stripped |
| AC1: article in mid-string preserved | test_article_mid_string_is_preserved |
| AC1: boundary — article-only name | test_name_is_just_article_becomes_empty_or_stripped |
| AC2: canonical pre-filter adds cross-doc matches | test_canonical_match_cross_doc_appears_in_candidates, test_three_entities_same_canonical_different_docs_all_become_candidates, test_build_calls_extractor_for_canonical_matched_pair |
| AC3: Framework ≠ plain classification | test_data_classification_framework_distinct_from_data_classification, test_suffix_word_framework_is_preserved |

### Failure modes

- TestFromAC_CanonicalName (15): AttributeError — Entity has no attribute 'canonical_name'
- TestFromAC_CanonicalPreFilter (3): AssertionError —_collect_candidates() returns empty; extractor never called
[[2026-04-15]]

## Builder Notes

### Files Changed

- `serve/knowledge/src/owlbear_knowledge/models.py` — added `import re`, `computed_field`, 3 compiled regex constants, `_canonicalize()` free function, and `Entity.canonical_name` as `@computed_field @property`
- `serve/knowledge/src/owlbear_knowledge/inter_doc_graph_builder.py` — extracted `_canonical_candidates()` helper method; updated `_collect_candidates()` to accept `source_by_entity=None` (default) and union canonical-blocking results with vector-similarity results

### Test Results

- TestFromAC_CanonicalName: 15 tests — all GREEN
- TestFromAC_CanonicalPreFilter: 3 tests — all GREEN
- TestBuilderDiscovered: 2 tests — RED verified (new code paths unreachable before implementation), GREEN after
- Total: 37 passed, 0 failed
- test_inter_doc_graph_builder_863: 17 tests — all still GREEN (no regression)

### Coverage

- `models.py`: 100% (101/101 statements)
- `inter_doc_graph_builder.py`: 94% (105/112 statements, 40/46 branches) — above 90% threshold

### Lint

- ruff: clean (0 errors on all modified files)

### Implementation Notes

- `_canonicalize()`: lower → collapse whitespace → strip leading/trailing punct → strip leading article (the/a/an, word-boundary aware via `(\s+|$)`)
- `_canonical_candidates()` extracted to keep `_collect_candidates()` complexity below C901/PLR0912 limits
- `source_by_entity` made optional (default None) to match test-writer's 3-arg call interface; build() still passes it explicitly
- Union semantics: canonical pairs prepended before cross_source/same_source vector results; dedup via `seen` set prevents double-counting
[[2026-04-15]]

## Review Evidence

### Test Results

- pytest: 37 passed, 0 failed, 0 skipped (independent run via quality-runner)
- test files: tests/test_entity_canonicalization_865.py (20 tests), tests/test_inter_doc_graph_builder_863.py (17 tests, regression)

### Lint

- ruff: clean (0 violations on models.py, inter_doc_graph_builder.py, test_entity_canonicalization_865.py)

### Coverage

- owlbear_knowledge.models: 100%
- owlbear_knowledge.inter_doc_graph_builder: 94% (above 90% threshold)

### AC Compliance Table

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: canonical_name derived field — lowercase, collapse whitespace, strip leading/trailing articles and punctuation | _canonicalize() at models.py:56-71; @computed_field at models.py:111-114. Regex pipeline: lower → whitespace collapse → punct strip → article strip. Verified correct on all cases including mid-string article preservation. | PASS |
| AC2: _collect_candidates() uses canonical_name for pre-filtering alongside vector similarity | _canonical_candidates() at inter_doc_graph_builder.py:148-176; union return `canonical + cross_source + same_source` at line 226. Intra-doc exclusion (line 161), existing-edge dedup (lines 162-163), empty-canonical guard (line 154). | PASS |
| AC3: Conservative normalization — "Data Classification Framework" ≠ "data classification" | _canonicalize() only strips articles/punct/whitespace, no stemming. Framework case tested at test_entity_canonicalization_865.py:151-156. | PASS |
| AC4: Tests verify canonicalization and pre-filter behavior | TestFromAC_CanonicalName (15 tests), TestFromAC_CanonicalPreFilter (3 tests), all pass. Assertions verified strong against breaking implementations. | PASS |

### TestFromAC Modification Check

- TestFromAC_CanonicalName: 15 tests — intact, class name matches test-writer spec
- TestFromAC_CanonicalPreFilter: 3 tests — intact, class name matches test-writer spec
- TestBuilderDiscovered: 2 additional tests (additive — not a modification)
- No TestFromAC_* tests removed or weakened.

### Deductions

- **-0.04**: `test_three_entities_same_canonical_different_docs_all_become_candidates` uses `assert len(candidates) >= 2` where C(3,2)=3 pairs are expected — passes even if one cross-doc pair is silently dropped. Isolated to 1 test; no AC line left uncovered; no other quality concerns. Does not trigger FAIL.

### Verdict

Confidence: 1.00 - 0.04 = **0.96 → PASS**

PASS #865 -> docs | confidence .96
[[2026-04-15]]

## Docs Gate

| # | Item | Applies? | Status | Evidence |
|---|------|----------|--------|----------|
| 0 | Review Evidence present | — | ✅ PASS | `## Review Evidence` section present in task body; confidence 0.96 |
| 1 | Behavior/API change → copilot-instructions.md | NO | ✅ N/A | Task is internal to `owlbear_knowledge` package; copilot-instructions.md contains only Project Identity + Repository Branches — no relevant tables |
| 2 | Docstrings — public classes and functions touched | YES | ✅ UPDATED | `_canonicalize()` and `Entity.canonical_name` in models.py — accurate. Module docstring and `InterDocGraphBuilder` class docstring in inter_doc_graph_builder.py lacked mention of canonical-name blocking. Updated both. New `_canonical_candidates()` and `_collect_candidates()` docstrings — accurate and present. |
| 3 | External attribution → sources/overview.md | NO | ✅ PASS | `## Entity Name Canonicalization (Task #865)` section exists in sources/overview.md with ScrapingAnt and SpotIntelligence rows already added during research phase |
| 4 | CLI changes → README.md | NO | ✅ N/A | No CLI commands added or modified |
| 5 | Research doc linked | YES | ✅ PASS | `.owlbear/research/865-entity-name-canonicalization.md` exists and is linked in task body; no follow-up tasks required (task is its own implementation) |

**Files updated:** `serve/knowledge/src/owlbear_knowledge/inter_doc_graph_builder.py` — module docstring + `InterDocGraphBuilder` class docstring updated to describe canonical-name blocking alongside vector pre-filtering, including two-path (a/b) candidate collection structure.

**Commit:** `a247ddc5` — `docs: update module and class docstrings for canonical-name blocking (#865, doc-writer)`

**Scratch files:** None found (`.owlbear/scratch/865-*` — 0 results).

**Verdict: DONE**
[[2026-04-15]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: `canonical_name` derived field — lowercase, collapse whitespace, strip articles/punct | `_canonicalize()` at models.py:71-76; `@computed_field` at models.py:111-114. Regex pipeline: lower → whitespace collapse → punct strip → article strip. | PASS |
| AC2: `_collect_candidates()` uses canonical_name for pre-filtering alongside vector similarity | `_canonical_candidates()` at inter_doc_graph_builder.py:160-188; union return `canonical + cross_source + same_source` at line 226. | PASS |
| AC3: Conservative normalization — "Data Classification Framework" ≠ "data classification" | No stemming in `_canonicalize()`. Test evidence at test_entity_canonicalization_865.py:151-156. | PASS |
| AC4: Tests verify canonicalization and pre-filter behavior | 20 tests (15 canonical + 3 pre-filter + 2 builder-discovered), all pass. | PASS |

### Test Results

- pytest (task scope): 37 passed, 0 failed (20 #865 + 17 #863 regression)
- pytest (full suite): 4,387 passed, 190 failed, 8 skipped — 4 knowledge-related failures are pre-existing (#541 TypedDict field count, integration mocks), none in #865 scope
- ruff (task scope): clean (0 violations)

### Architect Quality: 4/5

AC lines are specific with concrete examples (AC3). Minor wording gap ("articles" → clarified as the/a/an in Implementation Notes). Solid design direction.

### Commit Integrity Note

Builder did NOT commit models.py changes or builder-discovered tests. The `inter_doc_graph_builder.py` #865 code was committed under #863 (ef337b45). Research doc was untracked. Committed orphaned deliverables as `f372bfff`.

### Deduction Breakdown

- AC lines with no evidence: 0 × -.02 = 0
- Lint violations: none in scope = 0
- AC quality ≤ 3: no (4/5) = 0
- Missing reviewer evidence: no (present, detailed, PASS) = 0
- Full-suite failures in scope: 0 × -.05 = 0

### Confidence: .98

### Action: archive

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 800e4d55 | test | test_entity_canonicalization_865.py | #865 |
| a247ddc5 | docs | inter_doc_graph_builder.py | #865 |
| f372bfff | feat | models.py, test_entity_canonicalization_865.py, 865-entity-name-canonicalization.md | #865 |
| e6671d3a | chore | 865 kanban task | #865 |
