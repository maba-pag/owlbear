---
id: 876
title: 'P3-07: Wire LLMExtractor into MCP knowledge server'
status: archived
priority: medium
created: '2026-04-14T15:28:36.425659+00:00'
updated: '2026-04-14T23:33:34.629424+00:00'
tags:
- phase-3
- scope:knowledge
parent: 772
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Context

Follow-up from #874 research. After #875 implements `LLMExtractor`, wire it into the MCP knowledge server composition so entity extraction is active when openai is available.

## Acceptance Criteria

- [ ] `server.py` conditionally instantiates `LLMExtractor` when openai is importable
- [ ] Model name, API key, and base URL configurable via environment variables
- [ ] Falls back to no-op `EntityExtractor(extractor=None)` when openai is not installed
- [ ] `IntraDocGraphBuilder` and `InterDocGraphBuilder` receive extractor via DI
- [ ] No import errors when openai is not installed (lazy import or try/except)

## Affected Files

- `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` (composition wiring)
- Tests: integration test with mocked LLMExtractor

## Dependencies

- Depends on P3-06 (LLMExtractor implementation)
[[2026-04-14]]

## Research

- Research doc: .owlbear/research/876-wire-llmextractor-server.md
- Sources: 10 studied, 7 high-relevance (all codebase/internal)
- Recommendation: Hybrid env var fallback (OWLBEAR_LLM_*→ OPENAI_*) with import+key gating, ~20 LOC in app_lifespan(), 3 new AppContext fields (confidence: .88)
- Key findings: InterDocGraphBuilder requires extractor (not optional) — must be None when no extractor; IntraDocGraphBuilder accepts optional extractor; existing try/except ImportError pattern in qdrant.py and intake.py provides precedent
- Follow-up tasks created: none — #876 AC is implementation-ready, dependency #875 already tracked
- Decision requests: none
[[2026-04-14]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: composition wiring of LLMExtractor into server lifespan |
| Interface clarity | REFINE | AC #2 and #4 need specificity (see Refined AC below) |
| Dependency correctness | REFINE | Body says "Depends on P3-06" but `depends_on` field is empty. Should be `[875]`. Soft dependency — try/except ImportError means #876 can build/test before #875 lands, but ordering matters for CI. |
| Module layering | PASS | Changes scoped to `server.py` composition layer. Imports from `owlbear_knowledge` (downward). No cross-package violations. |
| TDD compliance | PASS | Test task will be created by pipeline. Research identifies 6 test cases. |
| KISS/YAGNI | PASS | ~20 LOC. No abstractions beyond what's needed. Follows existing conditional-import precedent. |
| Premise challenge | PASS | Capability does not exist — `EntityExtractor()` is currently no-op with no injected extractor. Graph builders not instantiated in server.py. |
| Pattern consistency | PASS | try/except ImportError pattern matches `qdrant.py:10-16` and `intake.py:9-12`. DI via constructor matches existing `EntityExtractor(extractor=)` pattern. |
| Security surface | PASS | Reads API key from env vars (standard pattern). No new user-facing input surfaces. Key is passed to SDK constructor, not logged or exposed. |
| Single domain | PASS | All changes in `scope:knowledge` domain. |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| `import LLMExtractor` | openai not installed | `ImportError` | Yes — try/except, fallback to no-op | None — silent degradation |
| `os.environ.get("OWLBEAR_LLM_API_KEY")` | No key set | N/A (returns None) | Yes — gating skips LLMExtractor creation | None — no-op extractor used |
| `InterDocGraphBuilder(extractor, vs, gs)` | extractor is None | `TypeError` (required param) | Must guard — only create when extractor exists | N/A if guarded |

### Refined AC (supersedes original AC #2 and #4)

Original AC is mostly sound. The following refinements add precision for the test-writer:

- [ ] `server.py` conditionally instantiates `LLMExtractor` when openai is importable **AND** an API key is present in env
- [ ] Env vars: `OWLBEAR_LLM_API_KEY` (fallback: `OPENAI_API_KEY`), `OWLBEAR_LLM_MODEL` (default: `"gpt-4o-mini"`), `OWLBEAR_LLM_BASE_URL` (fallback: `OPENAI_BASE_URL`)
- [ ] Falls back to no-op `EntityExtractor(extractor=None)` when openai is not installed or no API key set
- [ ] `IntraDocGraphBuilder` always instantiated with `extractor=structured_extractor` (works as no-op when None)
- [ ] `InterDocGraphBuilder` instantiated only when `structured_extractor is not None` (constructor requires extractor); set to `None` otherwise
- [ ] `AppContext` gains 3 optional fields: `structured_extractor`, `intra_doc_builder`, `inter_doc_builder`
- [ ] No import errors when openai is not installed (lazy import via try/except in `app_lifespan()`)

### Dependency Note

`depends_on` should be `[875]`. Soft dependency — the try/except ImportError pattern means #876 can be implemented and tested (all fallback paths) before #875 lands. But logical ordering requires #875 for the happy path.

### Challenge Results

- Challenger: FALLBACK — challenger subagent not in available agent roster
- Architect response: Proceeded without challenge. High confidence (.90) based on codebase verification of all 3 constructor signatures, existing conditional-import patterns, and thorough research doc.

### Verdict: APPROVE (with refinements)

### Action Taken: Refined AC for env var names, default model, InterDocGraphBuilder conditionality, and AppContext fields. Advanced to todo. Flagged missing `depends_on: [875]`

[[2026-04-14]]

## Test-Writer Notes

**Test file:** `serve/mcp-knowledge/tests/test_llmextractor_wiring_876.py`

**Classes:**

- `TestFromAC_LLMExtractorConditionalInstantiation` — 10 tests (AC1, AC2, AC3, AC7)
- `TestFromAC_GraphBuilderWiring` — 5 tests (AC4, AC5)
- `TestFromAC_AppContextFields` — 2 tests (AC6)

**Tests per category:**

- Happy path: 6 (LLMExtractor created with OWLBEAR key, OPENAI fallback, EntityExtractor wired with instance, IntraDocGraphBuilder and InterDocGraphBuilder present when extractor available)
- Edge cases: 5 (custom model, OWLBEAR_LLM_BASE_URL, OPENAI_BASE_URL fallback, module-level loader with sys.modules patching)
- Error paths: 4 (no key → EntityExtractor(extractor=None), ImportError silenced → no-op, extractor=None → InterDocGraphBuilder is None)
- Boundary: 2 (default model gpt-4o-mini, AppContext fields accessible on both paths)

**Total: 17 tests — all FAIL confirmed**

```
17 failed, 0 passed — pytest exit code 1
ruff: All checks passed!
```

**AC coverage table:**

| AC | Tests |
|----|-------|
| AC1 — LLMExtractor when importable + key | 1, 2, 10 |
| AC2 — env var naming + defaults | 3, 4, 5, 6 |
| AC3 — fallback to EntityExtractor(extractor=None) | 7, 8, 9, 10 |
| AC4 — IntraDocGraphBuilder always instantiated | 11, 12, 13 |
| AC5 — InterDocGraphBuilder gated on extractor | 14, 15 |
| AC6 — AppContext fields added | 7, 11, 12, 14, 16, 17 |
| AC7 — no ImportError when openai absent | 7, 8 |

**Failure root causes (two patterns):**

1. `LLMExtractorCls` never called (0 invocations) — wiring code not yet in `server.py`
2. `AttributeError` — `AppContext` missing `structured_extractor`, `intra_doc_builder`, `inter_doc_builder` fields; `server.py` missing `IntraDocGraphBuilder`/`InterDocGraphBuilder` imports

**sys.modules patching approach:** `_make_llm_mod(mock_cls)` helper injects a fake `owlbear_knowledge.llm_extractor` module with `LLMExtractor` attribute; `None` entry forces `ImportError` for "openai not installed" path. Autouse fixture handles all I/O-heavy constructor patches.
[[2026-04-14]]

## Builder Notes

### Files Changed

- `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` — wiring changes only

### Changes Applied

1. Added module-level imports: `IntraDocGraphBuilder` (from `owlbear_knowledge.graph_builder`), `InterDocGraphBuilder` (from `owlbear_knowledge.inter_doc_graph_builder`)
2. Added 3 optional fields to `AppContext` dataclass: `structured_extractor`, `intra_doc_builder`, `inter_doc_builder` (all default `None`)
3. In `app_lifespan()`: lazy `from owlbear_knowledge.llm_extractor import LLMExtractor` inside `try/except ImportError`; gated on `OWLBEAR_LLM_API_KEY` (fallback `OPENAI_API_KEY`); model from `OWLBEAR_LLM_MODEL` (default `gpt-4o-mini`); base_url from `OWLBEAR_LLM_BASE_URL` (fallback `OPENAI_BASE_URL`)
4. `EntityExtractor(extractor=structured_extractor)` — replaces bare `EntityExtractor()`
5. `IntraDocGraphBuilder(extractor=structured_extractor)` — always created (no-op when None)
6. `InterDocGraphBuilder(structured_extractor, vs, gs)` — only when `structured_extractor is not None`, else `None`
7. All three new fields forwarded into `AppContext` constructor

### Test Results

- **17 passed, 0 failed** (`TestFromAC_LLMExtractorConditionalInstantiation`: 9, `TestFromAC_GraphBuilderWiring`: 5, `TestFromAC_AppContextFields`: 3)
- Coverage: 46% on full server.py (pre-existing tool handlers untested by this file; new wiring code is fully exercised)

### Lint

- ruff clean (1 I001 import-sort auto-fixed)

### Evidence

- RED confirmed before implementation (per test-writer notes: 17 failed)
- GREEN: 17 passed after ~20 LOC surgical change to server.py
- No files outside AC scope touched
[[2026-04-14]]

## Review Evidence

**Reviewer:** Copilot reviewer mode | **Date:** 2026-04-14

### Test Results

```
pytest: 17 passed, 0 failed, 0 skipped — exit code 0
ruff: clean — exit code 0
coverage: 46% on owlbear_mcp_knowledge.server
```

Coverage note: 46% overall is expected — pre-existing tool handlers are untested by this file; all new wiring code is fully exercised. Not a deduction.

### AC Compliance Table

| AC | Evidence | Status |
|----|----------|--------|
| AC1 — LLMExtractor when importable + key | `if api_key:` → `try: from owlbear_knowledge.llm_extractor import LLMExtractor` → `structured_extractor = LLMExtractor(...)` (server.py:173-184) | ✅ PASS |
| AC2 — Env var naming + defaults | `os.environ.get("OWLBEAR_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")`, model default `"gpt-4o-mini"`, base_url fallback chain (server.py:173-180) | ✅ PASS |
| AC3 — Fallback to EntityExtractor(extractor=None) | `structured_extractor = None` initial; `except ImportError: structured_extractor = None`; `EntityExtractor(extractor=structured_extractor)` (server.py:173-189) | ✅ PASS |
| AC4 — IntraDocGraphBuilder always instantiated | `IntraDocGraphBuilder(extractor=structured_extractor)` unconditional (server.py:190) | ✅ PASS |
| AC5 — InterDocGraphBuilder gated on extractor | `InterDocGraphBuilder(...) if structured_extractor is not None else None` (server.py:191-195) | ✅ PASS |
| AC6 — AppContext gains 3 optional fields | `structured_extractor`, `intra_doc_builder`, `inter_doc_builder` all `= None` defaults in dataclass (server.py:77-82) | ✅ PASS |
| AC7 — No ImportError when openai absent | Lazy import inside `if api_key:` block with `try/except ImportError` (server.py:177-184) | ✅ PASS |

### TestFromAC Integrity

No `TestFromAC_*` classes weakened. All 20 assertions are failure-sensitive:

- `mock_llm_cls.assert_called_once()` — fails if constructor not invoked
- `mock_entity_cls.assert_called_once_with(extractor=None)` — fails if None not passed
- `assert ctx.structured_extractor is None` — fails if no-op not wired
- `mock_llm_cls.assert_not_called()` — fails if LLMExtractor created without key
- Argument matching for model, api_key, base_url kwargs

### Security

- API key read from env only, never hardcoded or logged — PASS
- Lazy import with `try/except ImportError` — PASS
- Base URL passed without format validation (delegation to LLMExtractor is correct design) — acceptable

### Deductions

None.

### Verdict

**PASS — confidence .96 → advancing to docs**
[[2026-04-14]]

## Docs Gate

| # | Item | Applies? | Status | Evidence |
|---|------|----------|--------|----------|
| 1 | Behavior/API change → copilot-instructions.md | No | N/A | copilot-instructions.md is 12 lines (project identity + branches only); no env vars, server config, or tech stack sections exist to update |
| 2 | Module docstrings | No | N/A | `AppContext` class docstring and `app_lifespan()` docstring are still accurate. 3 new fields follow existing no-per-field-docstring pattern (consistent with all other dataclass fields) |
| 3 | External attribution → sources/overview.md | No | N/A | Research doc sources S1–S10 are all internal codebase files and internal research docs; no external repos or articles used |
| 4 | CLI changes → README.md | No | N/A | Task scoped to server.py composition wiring only; no CLI surface changed |
| 5 | Research doc | Yes | PASS | `.owlbear/research/876-wire-llmextractor-server.md` exists and linked in task body; follow-ups noted as none |

**Files updated:** None — no docs impact identified.
**Scratch files:** No `.owlbear/scratch/876-*` files found — nothing to clean.
**Commit:** Skipped — no documentation files modified.
[[2026-04-14]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 - LLMExtractor when importable + key | server.py:185-192 try/except with api_key gating | PASS |
| AC2 - Env var naming + defaults | server.py:186-190 OWLBEAR_LLM_API_KEY/OPENAI_API_KEY fallback, model default gpt-4o-mini, base_url chain | PASS |
| AC3 - Fallback to EntityExtractor(extractor=None) | server.py:185,193-194,199 structured_extractor=None init + except ImportError | PASS |
| AC4 - IntraDocGraphBuilder always instantiated | server.py:200 unconditional IntraDocGraphBuilder(extractor=structured_extractor) | PASS |
| AC5 - InterDocGraphBuilder gated on extractor | server.py:201-204 conditional on structured_extractor is not None, else None | PASS |
| AC6 - AppContext gains 3 optional fields | server.py:99-101 structured_extractor, intra_doc_builder, inter_doc_builder all default None; forwarded at lines 235-237 | PASS |
| AC7 - No ImportError when openai absent | Lazy import inside try/except at server.py:188-193 | PASS |

### Test Results

- pytest (task-scoped): 17 passed, 0 failed
- pytest (full suite): 4262 passed, 332 failed, 8 skipped — failures span 33 files, none in task scope (kanban, sharepoint, orchestrator, other knowledge tasks)
- ruff: 2 violations, both outside scope (engine.py E501, test_sharepoint_885 F841)

### Architect Quality: 4/5

Original AC was adequate (5 items). Architect self-refined to 7 precise items with env var names, default values, conditionality logic, and InterDocGraphBuilder constraint. Minor gap: original AC needed refinement, but architect caught it proactively.

### Deduction Breakdown

- All 7 AC lines have specific evidence: no deduction
- No lint violations in scope: no deduction
- AC quality 4/5 (above 3): no deduction
- Reviewer evidence section present and detailed (7-row table with line refs): no deduction
- Full-suite failures exist but none in task scope: no deduction
- Upstream agents failed to commit deliverables (server.py + test file both uncommitted): noted but not an AC gap

### Confidence: .98

### Action: archive

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 6b26eed2 | feat | server.py, test_llmextractor_wiring_876.py | #876 |
