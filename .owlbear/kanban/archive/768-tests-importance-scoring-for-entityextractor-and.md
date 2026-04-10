---
id: 768
title: 'Tests: importance scoring for EntityExtractor and retrieval'
status: archived
priority: needed
created: 2026-03-13T10:34:42.072241+01:00
updated: 2026-03-13T15:31:03.6709091+01:00
started: 2026-03-13T14:42:33.9324356+01:00
completed: 2026-03-13T15:31:03.0339841+01:00
tags:
    - scope:core
    - memory
    - knowledge
    - type:test
depends_on:
    - 721
class: standard
---

## Goal
RED-phase tests for importance scoring feature (#722).

## AC
- [ ] Test Entity model accepts importance: float with default 0.5, constrained 0.0-1.0
- [ ] Test EntityExtractor.extract() returns entities with importance field populated
- [ ] Test GraphStore.insert_entity() round-trips importance through insert/get/list
- [ ] Test GraphAugmentedRetriever._expand() sorts by importance DESC when weight_by_importance=True
- [ ] Test GraphAugmentedRetriever ignores importance when weight_by_importance=False (default)
- [ ] All tests fail (RED phase) before implementation

## References
- Implementation task: #722
- docs/research/always-on-memory-integration.md

[[2026-03-13]] Fri 11:28
## Test-Writer Notes
- Test file: tests/test_knowledge_importance.py
- Classes: TestFromAC_EntityImportanceField, TestFromAC_ExtractorImportance, TestFromAC_GraphStoreImportanceRoundTrip, TestFromAC_ExpandSortsByImportance, TestFromAC_ImportanceIgnoredByDefault
- Tests per category: happy 7, edge 3, error 2, boundary 4
- Total: 16 tests, all FAIL
- ruff: clean
- AC coverage:

| AC Line | Test(s) | Category |
|---------|---------|----------|
| Entity importance field default 0.5, [0,1] | test_default_importance_is_half, test_custom_importance_accepted, test_importance_zero_allowed, test_importance_one_allowed, test_importance_below_zero_rejected, test_importance_above_one_rejected, test_importance_near_boundaries | happy, edge, error, boundary |
| EntityExtractor.extract() populates importance | test_extracted_entities_have_importance | happy |
| GraphStore round-trips importance | test_round_trip_via_get, test_round_trip_via_list, test_default_importance_round_trips, test_boundary_values_round_trip | happy, boundary |
| _expand() sorts by importance DESC | test_higher_importance_first, test_same_importance_stable_order | happy, edge |
| weight_by_importance=False default | test_default_weight_by_importance_is_false, test_explicit_false_preserves_traversal_order | happy |

[[2026-03-13]] Fri 13:44
## Builder Notes
- Files changed: src/owlbear/memory/knowledge/models.py, graph.py, retrieval.py
- Tests: 16 passed (all TestFromAC), 154 related tests passed (0 regressions)
- Coverage: models.py 100%, retrieval.py 90%, extractor.py 81%
- Lint: ruff clean (S608 pre-existing false positive on graph.py string concat)
- Changes: (1) Added importance field to Entity model [0.0-1.0, default 0.5], (2) Updated GraphStore insert/get/list to persist importance, (3) Added weight_by_importance param to GraphAugmentedRetriever with DESC sort in _expand()

[[2026-03-13]] Fri 14:06
## Review Evidence

### Test Results
- pytest (scoped): 16 passed, 0 failed (tests/test_knowledge_importance.py)
- pytest (related files): 186 passed, 0 failed
- pytest (full suite): 3197 passed, 25 failed (all pre-existing, none related to this task)

### Lint Results
- ruff: S608 on graph.py:172  pre-existing false positive (parameterized SQL with `?` placeholders; `AND`-join from internal clauses, not user input). Verified by running ruff against HEAD (original had 6 errors including E501; builder reformatted to fix those).

### Coverage
- models.py: 100%
- retrieval.py: 90%
- extractor.py: 81% (uncovered lines are unrelated error-handling paths)
- graph.py: 32% (full module; only importance-related paths exercised by this task)

### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | All assertions check exact values (`== 0.5`, `== 0.9`, `pytest.approx(0.85)`), specific exceptions (`ValidationError`), and positional ordering in output lines |
| Negative/error paths | ADEQUATE | Below-zero and above-one validation tested; default fallback exercised via round-trip; extractor test is mock-based with only happy path (AC doesn't require negative extraction tests) |
| Mutation reasoning | STRONG | Flipping `ge` to `gt`, removing `reverse=True`, changing default to `True`, removing importance from INSERT SQL  all caught by specific tests |
| Test independence | STRONG | Each test uses fresh in-memory DB via fixture; mock fixtures are per-test; no shared mutable state |
| Descriptive names | STRONG | All names describe scenario + expected outcome (e.g., `test_importance_below_zero_rejected`, `test_higher_importance_first`) |

### Security Review
- Hardcoded secrets: None found
- Injection: SQL uses parameterized `?` placeholders; S608 false positive (clauses built from internal entity_type/scopes, not user input)
- Path traversal: N/A  no file path operations
- Insecure deserialization: N/A  only `json.loads` (safe)
- Input validation: importance constrained via Pydantic `Field(ge=0.0, le=1.0)`
- Dependency risk: No new dependencies
- Secret leakage: No secrets in logs/errors

### Test Writer vs Builder Comparison
`git diff HEAD -- tests/test_knowledge_importance.py` returned empty  builder made zero changes to the test file.

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_EntityImportanceField (7 methods) | No change | PRESERVED |
| TestFromAC_ExtractorImportance (1 method) | No change | PRESERVED |
| TestFromAC_GraphStoreImportanceRoundTrip (4 methods) | No change | PRESERVED |
| TestFromAC_ExpandSortsByImportance (2 methods) | No change | PRESERVED |
| TestFromAC_ImportanceIgnoredByDefault (2 methods) | No change | PRESERVED |

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Entity importance: float, default 0.5, [0.0-1.0] | models.py:91 `importance: float = Field(default=0.5, ge=0.0, le=1.0)` | test_default_importance_is_half, test_custom_importance_accepted, test_importance_zero_allowed, test_importance_one_allowed, test_importance_below_zero_rejected, test_importance_above_one_rejected, test_importance_near_boundaries | PASS |
| EntityExtractor.extract() returns entities with importance | extractor returns ExtractionResult with importance=0.7 entity | test_extracted_entities_have_importance | PASS |
| GraphStore round-trips importance through insert/get/list | graph.py insert adds importance column, get/list return importance from row[8] | test_round_trip_via_get, test_round_trip_via_list, test_default_importance_round_trips, test_boundary_values_round_trip | PASS |
| _expand() sorts by importance DESC when weight_by_importance=True | retrieval.py:213-217 `sorted(neighbors, key=lambda pair: pair[0].importance, reverse=True)` | test_higher_importance_first, test_same_importance_stable_order | PASS |
| Ignores importance when weight_by_importance=False (default) | retrieval.py:101 `weight_by_importance: bool = False`; sort only applied inside `if self._weight_by_importance` | test_default_weight_by_importance_is_false, test_explicit_false_preserves_traversal_order | PASS |

### Verdict: PASS (confidence .94)
All 5 AC lines met with specific evidence. Tests are high quality (4 STRONG, 1 ADEQUATE). No security issues. No regressions. TestFromAC classes unmodified.

-t

[[2026-03-13]] Fri 14:42
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Internal knowledge-subsystem feature; no tech-stack, convention, or API change at project level |
| 2 | Docstrings complete | Yes | Updated | Added `weight_by_importance` param to `GraphAugmentedRetriever` class docstring in retrieval.py; models.py Entity field self-documented via Pydantic Field constraints; graph.py methods already had accurate docstrings |
| 3 | sources/overview.md | No | N/A | No external patterns adopted; straightforward extension of existing code |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/always-on-memory-integration.md exists and is referenced in task body |

### Files Updated
- src/owlbear/memory/knowledge/retrieval.py (docstring only)

### Scratch Files Cleaned
- None (no docs/scratch/768-* files found)

[[2026-03-13]] Fri 15:30
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Entity importance float default 0.5 [0,1] | models.py:91 Field(default=0.5, ge=0.0, le=1.0); 7 tests | PASS |
| EntityExtractor.extract() populates importance | Mock-based test verifies importance=0.7 on result | PASS |
| GraphStore round-trips importance | graph.py INSERT/get/list include importance col; 4 tests | PASS |
| _expand() sorts DESC when weight_by_importance=True | retrieval.py:217-221 sorted(reverse=True); 2 tests | PASS |
| Ignores importance when False (default) | retrieval.py:103 default=False; 2 tests | PASS |
| All tests fail RED phase | Test-writer: 16 FAIL; builder: 16 PASS; test file unmodified | PASS |

### Test Results
- pytest (scoped): 16 passed, 0 failed
- pytest (related 164 tests): 164 passed, 0 failed
- Full suite collection errors: 5 pre-existing trafilatura/regex (unrelated)
- ruff: S608 pre-existing false positive on graph.py:172 (parameterized SQL)

### Confidence: .96
### Action: archive

[[2026-03-13]] Fri 15:30
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Entity importance float default 0.5 [0,1] | models.py:91 Field(default=0.5, ge=0.0, le=1.0); 7 tests | PASS |
| EntityExtractor.extract() populates importance | Mock-based test verifies importance=0.7 on result | PASS |
| GraphStore round-trips importance | graph.py INSERT/get/list include importance col; 4 tests | PASS |
| _expand() sorts DESC when weight_by_importance=True | retrieval.py:217-221 sorted(reverse=True); 2 tests | PASS |
| Ignores importance when False (default) | retrieval.py:103 default=False; 2 tests | PASS |
| All tests fail RED phase | Test-writer: 16 FAIL; builder: 16 PASS; test file unmodified | PASS |

### Test Results
- pytest (scoped): 16 passed, 0 failed
- pytest (related 164 tests): 164 passed, 0 failed
- Full suite collection errors: 5 pre-existing trafilatura/regex (unrelated)
- ruff: S608 pre-existing false positive on graph.py:172 (parameterized SQL)

### Confidence: .96
### Action: archive
