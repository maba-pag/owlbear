# LLMExtractor Implementation with openai SDK

> **Owning task:** #875 — P3-06: Implement LLMExtractor with openai SDK
> **Date:** 2026-04-14 **Status:** Complete

## 1. Context and Question

Task #874 recommended Option A (`openai` SDK) for `StructuredExtractor` replacement (confidence .85). Task #875 implements that recommendation. The existing `llm_extractor.py` has only the `LLM_EXTRACTION_PROMPT` constant — no class.

**Question:** What is the exact API surface, schema compatibility profile, and testing strategy for implementing `LLMExtractor` against the `StructuredExtractor` protocol using the openai Python SDK?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | `protocol.py` — `StructuredExtractor` protocol definition | Codebase | 1.0 |
| S2 | `extractor.py` — `ExtractionResult` model + `EntityExtractor` DI | Codebase | 1.0 |
| S3 | `models.py` — `Entity`, `Edge`, `EntityType`, `RelationType` | Codebase | 1.0 |
| S4 | `llm_extractor.py` — `LLM_EXTRACTION_PROMPT` constant | Codebase | 1.0 |
| S5 | `.owlbear/research/874-structuredextractor-replacement.md` | Research | 0.95 |
| S6 | OpenAI Structured Outputs guide | External | 0.95 |
| S7 | openai-python SDK helpers.md — `chat.completions.parse()` | External | 0.95 |
| S8 | `serve/knowledge/pyproject.toml` — current optional deps | Codebase | 0.90 |

## 3. Analysis

### 3.1 API Choice: `parse()` vs `create()` with Manual Schema

| Criterion | `chat.completions.parse()` | `chat.completions.create()` + manual schema |
|-----------|---------------------------|---------------------------------------------|
| Schema management | Auto from Pydantic model | Manual `model_json_schema()` + dict wrapping |
| Response parsing | Auto `.parsed` attribute | Manual `model_validate_json()` |
| Strict mode handling | SDK transforms schema automatically | Developer must ensure schema compliance |
| Refusal detection | `message.refusal` built in | Must check `content` manually |
| LOC | ~15 | ~20 |
| Error surface | Smaller — SDK handles edge cases | Larger — schema format errors possible |

**Recommendation:** Use `chat.completions.parse(response_format=ExtractionResult)`. The SDK auto-converts the Pydantic model to a strict-mode-compatible JSON schema, auto-parses the response, and handles refusals. This is ~5 fewer LOC than the manual approach in #874's sketch.

### 3.2 Schema Compatibility with Strict Structured Outputs

The `ExtractionResult` → `Entity` / `Edge` models contain fields that need analysis:

| Field | Type | Strict mode behavior | Impact |
|-------|------|---------------------|--------|
| `Entity.metadata` | `dict[str, Any]` | SDK adds `additionalProperties: false` → LLM produces `{}` | Acceptable — metadata is internal |
| `Entity.document_id` | `str \| None` | Converted to `anyOf` with null — supported | OK — LLM produces `null` |
| `Entity.chunk_id` | `str \| None` | Same as above | OK |
| `Entity.id` | `str` (default_factory) | Becomes required; LLM generates IDs | Good — edges need entity IDs |
| `Entity.scope` | `str` (default "global") | Becomes required; LLM fills it | Harmless — can be ignored |
| `Entity.importance` | `float` (ge=0.0, le=1.0) | Constraints preserved in schema | Works with standard models |
| `Edge.weight` | `float` (ge=0) | Constraint preserved | Works |
| `Edge.metadata` | `dict[str, Any]` | Same as Entity.metadata | Acceptable |
| `EntityType` | `StrEnum` | Converted to string enum — supported | 11 values, well within limits |
| `RelationType` | `StrEnum` | Same | 9 values |

**Verdict:** `ExtractionResult` is directly compatible with strict structured outputs. No slim model needed. The `dict[str, Any]` fields produce `{}` (acceptable), optional fields produce `null`, and enum types are natively supported.

### 3.3 Implementation Shape

```
class LLMExtractor:
    def __init__(self, model, *, api_key=None, base_url=None):
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    async def extract(self, prompt):
        try:
            completion = await self._client.chat.completions.parse(
                model=self._model,
                messages=[
                    {"role": "system", "content": LLM_EXTRACTION_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format=ExtractionResult,
            )
            result = completion.choices[0].message.parsed
            return result if result is not None else ExtractionResult()
        except Exception:
            return ExtractionResult()
```

~18 LOC including class/method declarations. Satisfies `StructuredExtractor` protocol (async `extract(prompt: str) -> ExtractionResult`).

### 3.4 Version Constraint

The `chat.completions.parse()` method (non-beta) is documented in the SDK helpers at top level. The `openai>=1.50` constraint from the AC should cover it — verify during implementation by checking the installed version's API surface.

### 3.5 Testing Strategy

| Test | Method | What it verifies |
|------|--------|-----------------|
| Protocol compliance | `isinstance(extractor, StructuredExtractor)` | Runtime-checkable protocol satisfaction |
| Happy path | Mock `AsyncOpenAI`, return parsed `ExtractionResult` | Correct delegation and response handling |
| Refusal handling | Mock returns `parsed=None` (refusal) | Returns empty `ExtractionResult()` |
| Exception handling | Mock raises `Exception` | Graceful degradation to `ExtractionResult()` |
| Constructor params | Inspect `AsyncOpenAI` call args | `model`, `api_key`, `base_url` passed correctly |
| Prompt wiring | Inspect messages in mock call | `LLM_EXTRACTION_PROMPT` used as system message |

Mock `AsyncOpenAI` via `unittest.mock.AsyncMock` — no real API calls needed.

## 4. Recommendation (confidence: .90)

Use `chat.completions.parse(response_format=ExtractionResult)` — the SDK handles schema transformation, strict mode, and response parsing automatically. The existing `ExtractionResult` model works directly without a slim extraction model. ~18 LOC implementation. All AC items are technically feasible as written.

Challenge: FALLBACK — challenger subagent not in available roster.

**Tier classification: T1 — Autonomous.** Restoring a removed concrete implementation for an existing protocol. No architecture changes, no new capability, no security policy impact. The protocol interface (`StructuredExtractor`) is unchanged.

## 5. Follow-up Tasks

No new follow-up tasks needed — #875 already has complete AC for implementation.
