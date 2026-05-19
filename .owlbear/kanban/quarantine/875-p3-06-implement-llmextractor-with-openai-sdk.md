---
id: 875
title: 'P3-06: Implement LLMExtractor with openai SDK'
status: archived
priority: important
created: '2026-04-14T15:28:36.373364+00:00'
updated: '2026-04-14T22:28:42.252004+00:00'
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

Follow-up from #874 research. Implement a concrete `StructuredExtractor` using the `openai` Python SDK. The previous `LLMExtractor` (pydantic-ai) was removed. See `.owlbear/research/874-structuredextractor-replacement.md`.

## Acceptance Criteria

- [ ] `LLMExtractor` class in `llm_extractor.py` satisfying `StructuredExtractor` protocol
- [ ] Uses `AsyncOpenAI` with `response_format` for structured JSON output
- [ ] Constructor takes `model`, `api_key`, `base_url` — works with any OpenAI-compatible endpoint
- [ ] Graceful degradation: `try/except` → empty `ExtractionResult()` on LLM failure
- [ ] `openai>=1.50` added as optional dep group `llm` in `serve/knowledge/pyproject.toml`
- [ ] `full` extras group includes `llm`
- [ ] Existing `LLM_EXTRACTION_PROMPT` constant reused as system prompt
- [ ] ~25 LOC implementation (no over-engineering)

## Affected Files

- `serve/knowledge/src/owlbear_knowledge/llm_extractor.py` (add class)
- `serve/knowledge/pyproject.toml` (add optional dep)
- Tests: TDD — write tests first
[[2026-04-14]]

## Research

- Research doc: .owlbear/research/875-llmextractor-openai-implementation.md
- Sources: 8 studied, 6 high-relevance
- Recommendation: Use `chat.completions.parse(response_format=ExtractionResult)` — SDK auto-handles schema transformation, strict mode, and response parsing (confidence: .90)
- Follow-up tasks created: none — #875 already has complete implementation AC
- Decision requests: none

## Challenge Results

- Challenger: FALLBACK — challenger subagent not in available roster
- Confidence in original: .90
- Key findings: (1) `parse()` is simpler than manual schema approach from #874 sketch (~18 vs ~20 LOC), (2) `ExtractionResult` is directly compatible with strict structured outputs — `dict[str,Any]` fields produce `{}`, optional fields produce `null`, enums supported, (3) Testing via `AsyncMock` of `AsyncOpenAI` — 6 test cases identified

## Tier Classification

T1 — Autonomous. Restoring removed concrete implementation for existing protocol. No architecture or security changes.
[[2026-04-14]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One class + one optional dep entry — inherently coupled, single logical change. |
| Interface clarity | PASS | Protocol: `async extract(prompt: str) -> ExtractionResult`. Constructor: `model`, `api_key`, `base_url`. All inputs/outputs/side effects explicit in AC. |
| Dependency correctness | PASS | `depends_on: []` — #874 research is the logical predecessor but already completed its deliverable (research doc + follow-up). No blocking dependency. |
| Module layering | PASS | `llm_extractor.py` imports from same package (`models`, `extractor`). No upward or cross-package imports. `openai` is external, added as optional dep. |
| TDD compliance | PASS | AC specifies "Tests: TDD — write tests first." Pipeline test-writer handles. |
| KISS/YAGNI | PASS | ~18 LOC implementation per research. No speculative features. Optional dep preserves zero-LLM-dep default for non-extraction users. |
| Premise challenge | PASS | Verified: `StructuredExtractor` protocol exists with zero implementations. `EntityExtractor` returns empty result when `self._extractor is None` (line 91). Gap is real and blocks production-level extraction. |
| Pattern consistency | PASS | Follows existing DI pattern: `EntityExtractor.__init__(extractor: StructuredExtractor | None)`. Optional dep group follows existing`qdrant`/`embedding`/`intake` pattern in pyproject.toml. `full` group aggregation matches existing convention. |
| Security surface | PASS | `api_key` passed by caller (not hardcoded). `AsyncOpenAI` falls back to `OPENAI_API_KEY` env var when `None`. Prompt already includes `<untrusted_web_content>` data-only instruction (line 57). No new user-facing input surfaces. |
| Single domain | PASS | All changes scoped to `scope:knowledge` — `owlbear_knowledge` package only. |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| `chat.completions.parse()` | Network/auth/rate-limit error | Various openai exceptions | Yes — `except Exception` → `ExtractionResult()` | Falls back to rule-based extraction |
| `chat.completions.parse()` | LLM refusal | `parsed=None` | Yes — None check → `ExtractionResult()` | Same fallback |
| `chat.completions.parse()` | Schema validation error | `ValidationError` | Yes — `except Exception` → `ExtractionResult()` | Same fallback |

### Schema Compatibility Verification

Verified `ExtractionResult` → `Entity` / `Edge` model fields against strict structured output requirements:

- `dict[str, Any]` fields (`metadata`): SDK adds `additionalProperties: false` → LLM produces `{}` — acceptable
- `str | None` fields (`document_id`, `chunk_id`): Converted to `anyOf` with null — supported
- `StrEnum` fields (`EntityType`, `RelationType`): Native enum support — 11 and 9 values respectively
- `float` with constraints (`importance`, `weight`): Constraints preserved in schema
- `ConfigDict(frozen=True)`: Affects mutability only, not JSON schema generation

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| `LLMExtractor` class satisfying `StructuredExtractor` protocol | Verifiable — `isinstance` check + method signature | None |
| Uses `AsyncOpenAI` with `response_format` | Verifiable — mock call args inspection | None |
| Constructor takes `model`, `api_key`, `base_url` | Verifiable — constructor signature + mock verification | None |
| Graceful degradation `try/except` → `ExtractionResult()` | Verifiable — raise in mock → assert empty result | None |
| `openai>=1.50` optional dep group `llm` | Verifiable — pyproject.toml inspection | None |
| `full` extras includes `llm` | Verifiable — pyproject.toml inspection | None |
| `LLM_EXTRACTION_PROMPT` reused as system prompt | Verifiable — mock message inspection | None |
| `~25 LOC` (no over-engineering) | Builder guidance, not testable AC — acceptable as KISS constraint | None |

### Challenge Results

- Challenger: FALLBACK — challenger subagent not in available agent roster
- Architect response: Proceeded without challenge. High confidence based on codebase evidence: protocol is well-defined, DI pattern established, schema compatibility verified field-by-field, all AC lines are testable. Confidence: .93.

### Verdict: APPROVE

### Action Taken: Advanced #875 to todo. All AC verifiable, architecture sound, follows established patterns

[[2026-04-14]]

## Test-Writer Notes

- Test file: tests/test_llm_extractor_875.py
- Classes: `TestFromAC_LLMExtractor`
- Tests per category: happy 3, edge 4, error 3, boundary 3
- Total: 13 tests, all FAIL (ImportError — `LLMExtractor` not implemented)
- ruff: clean

### AC Coverage

| AC Line | Test(s) |
|---------|---------|
| `LLMExtractor` class satisfying `StructuredExtractor` protocol | `test_satisfies_structured_extractor_protocol` |
| Uses `AsyncOpenAI` with `response_format` for structured JSON | `test_response_format_is_extraction_result_class` |
| Constructor takes `model`, `api_key`, `base_url` | `test_constructor_accepts_model_api_key_base_url`, `test_base_url_forwarded_to_async_openai_constructor` |
| Graceful degradation → empty `ExtractionResult()` | `test_llm_runtime_exception_returns_empty_extraction_result`, `test_parsed_none_returns_empty_extraction_result`, `test_connection_error_returns_empty_extraction_result` |
| `openai>=1.50` in optional dep group `llm` | `test_pyproject_toml_has_llm_optional_dep_group`, `test_pyproject_toml_llm_group_requires_openai_gte_1_50` |
| `full` extras group includes `llm` | `test_pyproject_toml_full_group_includes_openai` |
| `LLM_EXTRACTION_PROMPT` reused as system prompt | `test_llm_extraction_prompt_used_as_system_message` |
| Returns `ExtractionResult` on success | `test_extract_returns_extraction_result_type`, `test_extract_returns_entities_from_llm_response` |

### Failure type: `ImportError` — `LLMExtractor` does not exist in `llm_extractor.py`

### Commit: e20f4d6b

[[2026-04-14]]

## Builder Notes

### Files Changed

- `serve/knowledge/src/owlbear_knowledge/llm_extractor.py` — added `LLMExtractor` class (~30 LOC); updated module docstring; added `from openai import AsyncOpenAI` and `from owlbear_knowledge.extractor import ExtractionResult` imports
- `serve/knowledge/pyproject.toml` — added `llm = ["openai>=1.50"]` optional dep group; added `openai>=1.50` to `full` group

### Test Results

- __13/13 passed__ (`TestFromAC_LLMExtractor`)
- No `TestBuilderDiscovered` edge cases needed — all AC paths covered by test-writer

### Lint

- ruff: __clean__ (fixed TRY300 — moved `return` to `else` block)

### Evidence Summary

- `LLMExtractor` satisfies `StructuredExtractor` protocol (runtime `isinstance` check passes)
- Uses `AsyncOpenAI.chat.completions.parse(response_format=ExtractionResult)` — verified via mock call args
- Constructor forwards `api_key` and `base_url` to `AsyncOpenAI` constructor
- Graceful degradation: `except Exception` → `ExtractionResult()`; `parsed=None` → `ExtractionResult()`
- pyproject.toml `llm` group: `openai>=1.50` ✓; `full` group includes `openai>=1.50` ✓
- `LLM_EXTRACTION_PROMPT` sent as system message — verified via mock messages inspection
[[2026-04-14]]

## Review Evidence

### Test Results

- pytest: 13 passed, 0 failed

### Lint: clean

### Coverage: owlbear_knowledge.llm_extractor: 100%

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| `LLMExtractor` satisfying `StructuredExtractor` protocol | `test_satisfies_structured_extractor_protocol` | Yes — `isinstance` against `@runtime_checkable` Protocol; removing `extract` method breaks it | COVERED |
| Uses `AsyncOpenAI` with `response_format` | `test_response_format_is_extraction_result_class` | Yes — asserts `response_format` kwarg is exactly `ExtractionResult` class | COVERED |
| Constructor takes `model`, `api_key`, `base_url` | `test_constructor_accepts_model_api_key_base_url`, `test_base_url_forwarded_to_async_openai_constructor` | Yes — checks signature and `base_url` kwarg forwarding | COVERED |
| Graceful degradation → `ExtractionResult()` | `test_llm_runtime_exception_returns_empty_extraction_result`, `test_parsed_none_returns_empty_extraction_result`, `test_connection_error_returns_empty_extraction_result` | Yes — all three raise in mock and assert `== ExtractionResult()` | COVERED |
| `openai>=1.50` in optional dep group `llm` | `test_pyproject_toml_has_llm_optional_dep_group`, `test_pyproject_toml_llm_group_requires_openai_gte_1_50` | Yes — parses actual pyproject.toml; wrong version or missing key fails | COVERED |
| `full` extras includes `llm` | `test_pyproject_toml_full_group_includes_openai` | Yes — checks actual pyproject.toml for openai in full group | COVERED |
| `LLM_EXTRACTION_PROMPT` reused as system prompt | `test_llm_extraction_prompt_used_as_system_message` | Yes — inspects `messages` kwarg from mock call | COVERED |
| Returns `ExtractionResult` on success | `test_extract_returns_extraction_result_type`, `test_extract_returns_entities_from_llm_response` | Yes — `isinstance` and `len > 0` checks | COVERED |

#### Security Review

- `api_key` defaults to `None` (SDK falls back to `OPENAI_API_KEY` env var) — not hardcoded ✓
- No prompt injection surface beyond the existing `<untrusted_web_content>` tag protection in `LLM_EXTRACTION_PROMPT` (`llm_extractor.py:57`) ✓
- Response deserialized as typed Pydantic model (`ExtractionResult`) by openai SDK — no raw `json.loads`/`yaml.load`/`eval` ✓
- `except Exception` silently swallows errors per AC design (graceful degradation) — no credential/PII leakage in error paths ✓
- `openai>=1.50` well-maintained; no known-vulnerable version pinned ✓
- No issues found

#### Test Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| All 13 `TestFromAC_*` tests | No `TestFromAC_*` changes detected — builder added no `TestBuilderDiscovered` tests and did not modify any test-writer tests | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | `== ExtractionResult()`, `is ExtractionResult`, specific kwarg assertions — no lazy `assert result` |
| Negative/error-path coverage | STRONG | 3 distinct error-path tests (RuntimeError, None-parsed, ConnectionError) |
| Mutation resistance | STRONG | Removing `except Exception` block fails 3 tests; removing `parsed is not None` check fails 1 |
| Test independence | STRONG | Each test uses its own `patch()` context or fixture; no shared mutable state |
| Naming | STRONG | All names describe the behavior under test precisely |

#### Data Safety

- LLM response parsed as `ExtractionResult` Pydantic model by SDK — strongly typed, not raw dict ✓
- No shared mutable state in implementation ✓
- Single atomic operation; no multi-step state issues ✓
- No issues found

#### Implementation-Aware Gaps

- 100% coverage confirmed by quality-runner — all branches (happy path, `except Exception`, `parsed is None`) exercised ✓
- Both `client.chat.completions.parse` and `client.beta.chat.completions.parse` mocked in fixture; implementation uses `chat` (not `beta`) — both mock bindings are harmless defensive setup ✓
- No untested paths

#### Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL

- `test_pyproject_toml_full_group_includes_openai` checks for `"openai" in dep` rather than `"openai>=1.50" in dep`. Practically equivalent given the actual pyproject.toml content but slightly looser than the paired `test_pyproject_toml_llm_group_requires_openai_gte_1_50`. No action required.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| `LLMExtractor` class satisfying `StructuredExtractor` protocol | `llm_extractor.py:67` defines class; `protocol.py:86` `@runtime_checkable`; `isinstance` passes | `test_satisfies_structured_extractor_protocol` | PASS |
| Uses `AsyncOpenAI` with `response_format` | `llm_extractor.py:79` `chat.completions.parse(response_format=ExtractionResult)` | `test_response_format_is_extraction_result_class` | PASS |
| Constructor takes `model`, `api_key`, `base_url` | `llm_extractor.py:73` `def __init__(self, model, api_key=None, base_url=None)` | `test_constructor_accepts_model_api_key_base_url`, `test_base_url_forwarded_to_async_openai_constructor` | PASS |
| Graceful degradation → `ExtractionResult()` | `llm_extractor.py:86–91` `except Exception / else` | 3 error tests | PASS |
| `openai>=1.50` in `llm` group | `pyproject.toml:14` `llm = ["openai>=1.50"]` | `test_pyproject_toml_has_llm_optional_dep_group`, `test_pyproject_toml_llm_group_requires_openai_gte_1_50` | PASS |
| `full` group includes `llm` deps | `pyproject.toml:19` `full` contains `openai>=1.50` | `test_pyproject_toml_full_group_includes_openai` | PASS |
| `LLM_EXTRACTION_PROMPT` as system prompt | `llm_extractor.py:81` `{"role": "system", "content": LLM_EXTRACTION_PROMPT}` | `test_llm_extraction_prompt_used_as_system_message` | PASS |
| ~25 LOC implementation | `llm_extractor.py:67–92` — ~26 LOC including docstring; core logic ~18 LOC | N/A (builder guidance) | PASS |

### Confidence: .97

### Verdict: PASS

[[2026-04-14]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `copilot-instructions.md` is 17 lines (project identity + branches only); no tech stack section. `LLMExtractor` is an internal package class, not a system-wide convention. |
| 2 | Module docstrings | Yes | Verified | Module docstring accurate: "contains system prompt + LLMExtractor concrete implementation using openai SDK." Class docstring accurate: protocol compliance, base_url flexibility, graceful degradation. No updates needed. |
| 3 | External attribution | Yes | Verified | `sources/overview.md` already has rows for S6 (OpenAI Structured Outputs guide) and S7 (openai-python SDK helpers.md) both linked to `875-llmextractor-openai-implementation.md`. Done by research agent. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/875-llmextractor-openai-implementation.md` exists; task body references it in Context and Research sections; no follow-up tasks required (confirmed in research notes). |

### Files Updated

- None

### Scratch Files Cleaned

- None (no `.owlbear/scratch/875-*` files found)
[[2026-04-14]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| `LLMExtractor` class satisfying `StructuredExtractor` protocol | `llm_extractor.py:67`; `test_satisfies_structured_extractor_protocol` passes isinstance check | PASS |
| Uses `AsyncOpenAI` with `response_format` | `llm_extractor.py:79`; `test_response_format_is_extraction_result_class` | PASS |
| Constructor takes `model`, `api_key`, `base_url` | `llm_extractor.py:73`; 2 constructor tests | PASS |
| Graceful degradation → `ExtractionResult()` | `llm_extractor.py:86-91`; 3 error-path tests | PASS |
| `openai>=1.50` in `llm` group | `pyproject.toml:15`; 2 toml tests | PASS |
| `full` extras includes `llm` | `pyproject.toml:19`; `test_pyproject_toml_full_group_includes_openai` | PASS |
| `LLM_EXTRACTION_PROMPT` as system prompt | `llm_extractor.py:81`; `test_llm_extraction_prompt_used_as_system_message` | PASS |
| ~25 LOC implementation | `llm_extractor.py:67-92` ~26 LOC — builder guidance, acceptable | PASS |

### Test Results

- pytest (scoped): 13 passed, 0 failed
- pytest (full): 4,260 passed, 349 failed, 8 skipped — failures are pre-existing, none in task scope
- ruff: 1 E501 in `engine.py:472` — not in task scope

### Architect Quality: 4/5

AC lines were specific and testable. Minor "~25 LOC" is untestable builder guidance but acceptable as KISS constraint. All substantive AC lines are verifiable with clear pass/fail conditions.

### Deduction Breakdown

- Uncommitted builder deliverables (committed by auditor as leftovers): -.02

### Confidence: .98

### Action: archive

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| e20f4d6b | test | tests/test_llm_extractor_875.py | #875 |
| 3b7748ad | feat | llm_extractor.py, pyproject.toml | #875 |
