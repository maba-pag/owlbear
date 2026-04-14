---
id: 875
title: 'P3-06: Implement LLMExtractor with openai SDK'
status: backlog
priority: important
created: '2026-04-14T15:28:36.373364+00:00'
updated: '2026-04-14T16:56:14.893246+00:00'
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