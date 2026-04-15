# StructuredExtractor Replacement After pydantic-ai Removal

> **Owning task:** #874 — P3-05: Investigate StructuredExtractor replacement after pydantic-ai removal
> **Date:** 2026-04-14 **Status:** Complete

## 1. Context and Question

pydantic-ai and `LLMExtractor` were removed (2026-04-14). The `StructuredExtractor` protocol in `protocol.py` has zero implementations. `EntityExtractor` returns empty results when no extractor is injected. `InterDocGraphBuilder` requires an extractor (non-optional). Both #862 and #864 are blocked.

**Question:** What is the minimal, KISS-aligned replacement for `StructuredExtractor` that avoids reintroducing pydantic-ai and keeps the dependency footprint small?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | `protocol.py` — `StructuredExtractor` protocol (async) | Codebase | 1.0 |
| S2 | `extractor.py` — `EntityExtractor` DI pattern | Codebase | 1.0 |
| S3 | `llm_extractor.py` — `LLM_EXTRACTION_PROMPT` constant (no class) | Codebase | 1.0 |
| S4 | `inter_doc_graph_builder.py` — required extractor usage | Codebase | 0.95 |
| S5 | `graph_builder.py` — optional extractor usage | Codebase | 0.90 |
| S6 | `serve/knowledge/pyproject.toml` — current deps: pydantic, strictyaml only | Codebase | 0.95 |
| S7 | `.owlbear/research/llmextractor-pydanticai-implementation.md` (#689) | Research | 0.90 |
| S8 | `.owlbear/research/864-wire-interdocgraphbuilder-pipeline.md` (#864) | Research | 0.90 |
| S9 | OpenAI Python SDK docs — `AsyncOpenAI`, structured outputs | External | 0.90 |
| S10 | LiteLLM docs — `response_format` with Pydantic models | External | 0.85 |
| S11 | Instructor docs — `response_model` with retry/validation | External | 0.80 |
| S12 | Kuboid — LiteLLM supply chain attack March 2026 advisory | External | 0.95 |

## 3. Analysis

### 3.1 Dependency Impact

| Option | New packages | Version conflicts | Install footprint |
|--------|-------------|-------------------|-------------------|
| A: `openai` SDK | 4 (distro, jiter, openai, sniffio) | 0 | ~5 MB |
| B: `litellm` | 13 | 4 downgrades (click, jsonschema, python-dotenv, typer) | ~40 MB |
| C: `instructor` | 7 (openai + docstring-parser, instructor, tenacity) | 0 | ~8 MB |
| D: Raw `httpx` | 0 (already optional dep) | 0 | 0 |

### 3.2 Trade-off Matrix

| Criterion | A: openai (.88) | B: litellm (.30) | C: instructor (.72) | D: httpx (.55) |
|-----------|-----------------|-------------------|----------------------|----------------|
| KISS (deps) | 4 new — lean | 13 new + downgrades — heavy | 7 new — moderate | 0 — leanest |
| Structured output | Native `response_format` + Pydantic | Native `response_format` | `response_model` abstraction | Manual JSON schema |
| Multi-provider | OpenAI-compat via `base_url` | 100+ native providers | Via underlying client | Any HTTP endpoint |
| Async support | `AsyncOpenAI` — native | `acompletion()` — native | `create_async()` via patch | Native `httpx.AsyncClient` |
| Security | Low risk, OpenAI-maintained | **HIGH: supply chain attack Mar 2026** | Medium (wraps openai) | Low risk |
| Impl LOC | ~25 | ~25 | ~20 | ~40 (manual auth/retry) |
| Testing | Mock `AsyncOpenAI` | Mock `acompletion` | Mock patched client | Mock `httpx.AsyncClient` |
| Maintenance | High (OpenAI official) | **Paused releases post-breach** | Active community | Self-maintained |

### 3.3 Security Concern — litellm

On March 24, 2026, litellm versions 1.82.7–1.82.8 were compromised in a supply chain attack (TeamPCP/LAPSUS$). Malicious packages contained a multi-stage credential stealer targeting AWS keys, K8s tokens, SSH keys, and database passwords. LiteLLM has paused new releases pending a security review with Mandiant (S12). This disqualifies litellm from consideration.

### 3.4 Implementation Shape (~25 LOC with openai SDK)

```
class LLMExtractor:
    def __init__(self, model: str, *, api_key: str | None, base_url: str | None):
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    async def extract(self, prompt: str) -> ExtractionResult:
        resp = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": LLM_EXTRACTION_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_schema", "json_schema": {
                "name": "extraction_result",
                "schema": ExtractionResult.model_json_schema(),
                "strict": True,
            }},
        )
        return ExtractionResult.model_validate_json(resp.choices[0].message.content)
```

Graceful degradation: wrap in `try/except` → `ExtractionResult()` on failure.

### 3.5 Why Not httpx?

Zero new deps is attractive, but httpx requires manually managing: auth headers, retry logic, rate limiting, error classification, streaming, and JSON schema formatting. The openai SDK handles all of these for 4 deps. The boilerplate-to-benefit ratio favors openai.

### 3.6 Optional Dependency Strategy

Add `llm = ["openai>=1.50"]` to `[project.optional-dependencies]` and include in `full`. Users who don't need LLM extraction keep zero LLM deps. Matches the existing `qdrant`/`embedding`/`intake` optional groups pattern (S6).

## 4. Recommendation (confidence: .85)

**Option A: `openai` SDK as optional dependency.** 4 new packages, zero version conflicts, native structured outputs via `response_format` with Pydantic, async-first, works with any OpenAI-compatible endpoint (Ollama, LM Studio, Azure, etc.) via `base_url`. ~25 LOC implementation in `llm_extractor.py`.

Challenge: FALLBACK — challenger subagent not in available roster.

**Tier classification: T1 — Autonomous.** This restores a removed capability using a standard library. No new architecture, no security policy changes, no user-facing behavior changes beyond re-enabling extraction. The protocol interface is unchanged; only the concrete implementation is new.

## 5. Follow-up Tasks

1. Implement `LLMExtractor` class in `llm_extractor.py` satisfying `StructuredExtractor` protocol — openai SDK, optional dep, ~25 LOC
2. Wire `LLMExtractor` into MCP knowledge server composition — conditional instantiation when openai is available
