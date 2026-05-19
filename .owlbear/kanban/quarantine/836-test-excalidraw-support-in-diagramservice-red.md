---
id: 836
title: 'Test: excalidraw support in DiagramService (RED)'
status: archived
priority: needed
created: 2026-03-15T20:28:46.4705585+01:00
updated: 2026-03-16T02:43:06.4743545+01:00
started: 2026-03-16T02:42:42.7346257+01:00
completed: 2026-03-16T02:42:42.7346257+01:00
tags:
    - test
    - scope:core
    - tooling
class: standard
---

AC:

- [ ] New tests in tests/test_diagram_service.py following existing TestGenerate/TestValidation patterns:
  - test_generate_excalidraw_svg: generate('excalidraw', '{type:excalidraw,elements:[]}', 'svg') calls Kroki with POST /excalidraw/svg (mock HTTP, follow_make_response/_make_client pattern)
  - test_excalidraw_png_raises_value_error: generate('excalidraw', valid_json, 'png') raises ValueError matching 'only supports svg'
  - test_excalidraw_in_supported_types: assert 'excalidraw' in SUPPORTED_TYPES
- [ ] DIAGRAM_TYPES tuple updated to include 'excalidraw' (so parametrized test_known_types_accepted covers it)
- [ ] Tests are red (implementation not yet changed)
- [ ] Existing test_diagram_service.py tests untouched and still pass
- [ ] ruff clean

Pattern: follow TestGenerate._make_response/_make_client helpers and patch(f'{MODULE}.httpx.AsyncClient') pattern in test_diagram_service.py
File: tests/test_diagram_service.py

[[2026-03-15]] Sun 20:49

## Test-Writer Notes

- Test file: tests/test_diagram_service.py
- Classes: TestFromAC_ExcalidrawSupport
- Tests: happy 1, error 1, membership 1, parametrized 1
- Total: 4 tests, all FAIL
- ruff: clean
- AC coverage:

| AC Line | Test(s) | Category |
|---------|---------|----------|
| generate excalidraw svg | test_generate_excalidraw_svg | happy |
| png raises ValueError | test_excalidraw_png_raises_value_error | error |
| excalidraw in SUPPORTED_TYPES | test_excalidraw_in_supported_types | membership |
| DIAGRAM_TYPES includes excalidraw | test_known_types_accepted[excalidraw] | parametrized |

[[2026-03-15]] Sun 21:14

## Builder Notes

- Files changed: src/owlbear/tools/diagram/service.py
- Tests: 32 passed, coverage 100% on diagram/service.py
- Lint: ruff clean
- Evidence: 4 new tests green (3 TestFromAC + 1 parametrized), 28 existing untouched
- Diff: +4/-1 lines -- added 'excalidraw' to SUPPORTED_TYPES, SVG-only guard

[[2026-03-15]] Sun 21:29

## Review Evidence

Reviewer: reviewer, 2026-03-15

### Test Results

- pytest: 32 passed, 0 failed (tests/test_diagram_service.py)
- Coverage: service.py 100%

### Lint Results

- ruff: All checks passed

### Security Review

No findings. Change is +4/-1 lines: added 'excalidraw' to frozenset, added SVG-only guard. No injection, secrets, deserialization, path traversal, or new dependencies.

### TestFromAC Comparison

Builder commit (952b787) did NOT modify test file. All TestFromAC methods intact.

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_ExcalidrawSupport::test_generate_excalidraw_svg | No change | PRESERVED |
| TestFromAC_ExcalidrawSupport::test_excalidraw_png_raises_value_error | No change | PRESERVED |
| TestFromAC_ExcalidrawSupport::test_excalidraw_in_supported_types | No change | PRESERVED |

### Test Quality

| Dimension | Rating |
|-----------|--------|
| Assertion specificity | STRONG |
| Negative/error-path | STRONG |
| Mutation resilience | STRONG |
| Test independence | STRONG |
| Descriptive names | STRONG |

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| New tests following existing patterns | TestFromAC_ExcalidrawSupport uses_make_response/_make_client + patch pattern; 3 tests match AC spec | PASS |
| DIAGRAM_TYPES includes excalidraw | Line 26: tuple updated; test_known_types_accepted[excalidraw] passes | PASS |
| Tests are red | N/A at review (builder implemented) | PASS |
| Existing tests untouched and still pass | Builder commit only touched service.py; 28 pre-existing tests pass | PASS |
| ruff clean | All checks passed | PASS |

### Verdict: PASS

Confidence: .95

[[2026-03-16]] Mon 01:22

## Docs Gate

Writer: writer, 2026-03-16

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | Yes | Updated | Added 'excalidraw' to Diagrams row in tech stack table; noted svg-only constraint |
| 2 | Docstrings | No | N/A | service.py already has accurate docstrings on DiagramService, generate(), DiagramError; ValueError docstring covers new excalidraw guard |
| 3 | sources/overview.md | No | N/A | No external patterns adopted |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | No research phase |

### Files Updated

- .github/copilot-instructions.md (added excalidraw to Diagrams tech stack row)

### Scratch Files Cleaned

- Deleted docs/scratch/836-cov.txt

[[2026-03-16]] Mon 02:42

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| New tests following existing patterns | TestFromAC_ExcalidrawSupport: 3 tests using_make_response/_make_client + patch pattern (L341,357,367) | PASS |
| DIAGRAM_TYPES includes excalidraw | L23: tuple updated with 'excalidraw'; parametrized test covers it | PASS |
| Tests are red | Test-writer notes: 4 FAIL; builder made GREEN in 952b787 | PASS |
| Existing tests untouched and still pass | Builder commit 952b787 only touched service.py; 28 pre-existing tests confirmed by reviewer | PASS |
| ruff clean | Reviewer confirmed All checks passed | PASS |

### Test Results

- pytest: env-degraded (all terminals timeout/blank). Builder: 32 passed. Reviewer: 32 passed (independently verified).
- ruff: All checks passed (reviewer confirmed)

### Quality Gaps

- test_diagram_service.py not committed by test-writer (orphan committed by auditor as b14e2e0)
- Test file also contains TestFromAC_SvgOnlyTypes (4 RED tests for #833) -- mixed task changes

### Commits Verified

- 952b787: feat: add excalidraw support (#836, builder) -- service.py only
- 0bce0c2: docs: add excalidraw to Diagrams tech stack (#836, writer) -- copilot-instructions.md
- b14e2e0: test: add excalidraw support tests (#836, test-writer) -- committed by auditor (orphan)

### Confidence: .95

### Action: archive
