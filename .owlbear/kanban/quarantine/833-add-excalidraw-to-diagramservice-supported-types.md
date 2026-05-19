---
id: 833
title: Add excalidraw to DiagramService SUPPORTED_TYPES (Kroki passthrough)
status: archived
priority: needed
created: 2026-03-15T20:09:20.4918652+01:00
updated: 2026-03-16T20:58:27.1797634+01:00
started: 2026-03-16T20:58:22.7934901+01:00
completed: 2026-03-16T20:58:22.7934901+01:00
tags:
    - scope:core
    - tooling
depends_on:
    - 836
class: standard
---

AC:

- [ ] 'excalidraw' added to SUPPORTED_TYPES frozenset (service.py L7)
- [ ] _SVG_ONLY_TYPES = frozenset({"excalidraw"}) module-level constant added to service.py (beside SUPPORTED_TYPES/SUPPORTED_FORMATS)
- [ ] generate() raises ValueError when diagram_type in_SVG_ONLY_TYPES and output_format != "svg" -- check placed after existing output_format guard (service.py ~L49)
- [ ] ValueError message matches pattern "supports only svg output"
- [ ] All tests pass (including #836 tests)
- [ ] ruff clean

Pattern: follow existing ValueError validation guards in generate(). New _SVG_ONLY_TYPES constant at module level beside SUPPORTED_TYPES/SUPPORTED_FORMATS.
Ref: docs/research/excalidraw-render-service.md, docs/research/excalidraw-render-update.md

[[2026-03-15]] Sun 20:32

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 'excalidraw' added to SUPPORTED_TYPES | Clear, verifiable, one token in frozenset | Kept |
| _SVG_ONLY_TYPES constant | New pattern -- minimal, justified by Kroki SVG-only limitation | Added (was implicit in original AC) |
| generate() raises ValueError for SVG-only types | Precise guard placement specified (~L49), follows existing ValueError pattern | Refined from vague test AC |
| ValueError message pattern | Verifiable via match string | Added |
| All tests pass (including #836) | Standard regression + TDD pair | Kept |
| ruff clean | Standard | Kept |

### Architecture Notes

- service.py is 63 LOC, single-class module. Change adds ~3 LOC (1 constant + 2 guard lines).
- Follows existing ValueError guards in generate() (L44-L52). New guard fits naturally after L49 (output_format check).
- _SVG_ONLY_TYPES is a frozenset constant (KISS) -- no per-type mapping needed since only excalidraw has format restrictions.
- No new imports, no new classes, no interface changes. generate() signature unchanged.
- Kroki Excalidraw support confirmed by research (docs/research/excalidraw-render-service.md S3.2, excalidraw-render-update.md S3.2).
- Existing test_diagram_service.py has comprehensive coverage of generate() validation. New tests follow same patterns (TestGenerate, TestValidation).
- No security surface change -- same Kroki HTTP passthrough as existing types.
- Single domain: tools/diagram. No cross-module impact.

### Changes Made

- Refined AC: replaced mixed test/impl ACs with precise implementation-only AC
- Refined AC: made SVG-only restriction explicit (_SVG_ONLY_TYPES pattern)
- Created #836: TDD RED test task (tests/test_diagram_service.py)
- Added depends_on: #836

### Dependencies

- Added: #836 (test task, must complete first)
- Verified: no other deps needed -- standalone change to service.py

[[2026-03-15]] Sun 20:32

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 'excalidraw' added to SUPPORTED_TYPES | Clear, verifiable, one token in frozenset | Kept |
| _SVG_ONLY_TYPES constant | New pattern -- minimal, justified by Kroki SVG-only limitation | Added (was implicit in original AC) |
| generate() raises ValueError for SVG-only types | Precise guard placement specified (~L49), follows existing ValueError pattern | Refined from vague test AC |
| ValueError message pattern | Verifiable via match string | Added |
| All tests pass (including #836) | Standard regression + TDD pair | Kept |
| ruff clean | Standard | Kept |

### Architecture Notes

- service.py is 63 LOC, single-class module. Change adds ~3 LOC (1 constant + 2 guard lines).
- Follows existing ValueError guards in generate() (L44-L52). New guard fits naturally after L49 (output_format check).
- _SVG_ONLY_TYPES is a frozenset constant (KISS) -- no per-type mapping needed since only excalidraw has format restrictions.
- No new imports, no new classes, no interface changes. generate() signature unchanged.
- Kroki Excalidraw support confirmed by research (docs/research/excalidraw-render-service.md S3.2, excalidraw-render-update.md S3.2).
- Existing test_diagram_service.py has comprehensive coverage of generate() validation. New tests follow same patterns (TestGenerate, TestValidation).
- No security surface change -- same Kroki HTTP passthrough as existing types.
- Single domain: tools/diagram. No cross-module impact.

### Changes Made

- Refined AC: replaced mixed test/impl ACs with precise implementation-only AC
- Refined AC: made SVG-only restriction explicit (_SVG_ONLY_TYPES pattern)
- Created #836: TDD RED test task (tests/test_diagram_service.py)
- Added depends_on: #836

### Dependencies

- Added: #836 (test task, must complete first)
- Verified: no other deps needed -- standalone change to service.py

[[2026-03-16]] Mon 03:08

## Test-Writer Notes

- Test file: tests/test_diagram_service.py
- Classes: TestFromAC_SvgOnlyTypes (new), TestFromAC_ExcalidrawSupport (from #836)
- New tests per category: contract 3, boundary 1
- Total new: 4 tests (+ 3 from #836 = 7 total)
- Env note: pytest hangs on all owlbear imports (systemic env issue); verified via py_compile + ruff + grep
- ruff: clean
- AC coverage:

| AC Line | Test(s) | Category |
|---------|---------|----------|
| excalidraw in SUPPORTED_TYPES | test_excalidraw_in_supported_types (#836) | membership |
| _SVG_ONLY_TYPES constant exists | test_svg_only_types_constant_exists | contract |
| _SVG_ONLY_TYPES is frozenset | test_svg_only_types_is_frozenset | contract |
| _SVG_ONLY_TYPES contains excalidraw | test_svg_only_types_contains_excalidraw | contract |
| _SVG_ONLY_TYPES subset of SUPPORTED_TYPES | test_svg_only_types_subset_of_supported_types | boundary |
| generate() raises ValueError svg-only+non-svg | test_excalidraw_png_raises_value_error (#836) | error |
| ValueError matches 'supports only svg output' | test_excalidraw_png_raises_value_error (#836) | error |
| excalidraw svg generation works | test_generate_excalidraw_svg (#836) | happy |

[[2026-03-16]] Mon 04:42

## Builder Notes

- Files changed: src/owlbear/tools/diagram/service.py
- Tests: Unable to complete pytest verification in this environment (scoped runs hang before producing results)
- Lint: ruff check passed for src/owlbear/tools/diagram/service.py and tests/test_diagram_service.py
- Evidence: Added _SVG_ONLY_TYPES=frozenset({excalidraw}); moved SVG-only ValueError guard to run after output_format validation; guard now checks diagram_type in_SVG_ONLY_TYPES
- Fixes applied: Implemented AC changes in DiagramService.generate validation flow with minimal diff

[[2026-03-16]] Mon 12:16

## Test-Writer Notes (re-run 2026-03-16)\n- Test file: tests/test_diagram_service.py\n- Classes: TestFromAC_ExcalidrawSupport (3 tests), TestFromAC_SvgOnlyTypes (4 tests)\n- Tests per category: happy 1, error 1, contract 5\n- Total: 7 AC tests (36 total in file), all PASS (impl already complete)\n- ruff: clean\n- AC coverage: AC1->test_excalidraw_in_supported_types; AC2->test_svg_only_types_*; AC3+AC4->test_excalidraw_png_raises_value_error

[[2026-03-16]] Mon 13:00

## Builder Notes

- Files changed: src/owlbear/tools/diagram/service.py
- Tests: 36 passed in tests/test_diagram_service.py; coverage run reports src/owlbear/tools/diagram/service.py at 100%
- Lint: ruff check passed for src/owlbear/tools/diagram/service.py and tests/test_diagram_service.py
- Evidence: uv run pytest tests/test_diagram_service.py -q --tb=short -> 36 passed in 1.41s; uv run pytest tests/test_diagram_service.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short -> 36 passed, service.py 100%; uv run ruff check src/owlbear/tools/diagram/service.py tests/test_diagram_service.py -> All checks passed
- Fixes applied: No additional code changes required in this run; verified existing implementation meets all AC
