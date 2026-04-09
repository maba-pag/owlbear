---
id: 689
title: Implement LLMExtractor concrete StructuredExtractor using PydanticAI
status: backlog
priority: needed
created: 2026-04-08T21:06:19.8005764+02:00
updated: 2026-04-09T05:08:53.0891749+02:00
tags:
    - scope:knowledge
    - ' type:feature'
    - ' source:research'
depends_on:
    - 676
class: standard
---

## Context

Research for #676 determined that PydanticAI is the right SDK for structured extraction. v1 used `Agent(model, output_type=ExtractionResult, system_prompt=EXTRACTION_PROMPT)` successfully. A concrete `StructuredExtractor` implementation is the missing piece that activates the knowledge graph.

## Acceptance Criteria

- [ ] AC1: `LLMExtractor` class in `serve/knowledge/src/owlbear_knowledge/llm_extractor.py` satisfying `StructuredExtractor` protocol
- [ ] AC2: Uses `pydantic-ai` Agent with `result_type=ExtractionResult` and an extraction system prompt
- [ ] AC3: System prompt covers all `EntityType` and `RelationType` enum values
- [ ] AC4: `pydantic-ai` added as optional dependency in `serve/knowledge/pyproject.toml` (e.g., `llm` extras group)
- [ ] AC5: Graceful degradation — if LLM call fails, returns empty `ExtractionResult()` (no exception propagation)
- [ ] AC6: Unit tests with mocked PydanticAI agent

## Affected Files

- `serve/knowledge/src/owlbear_knowledge/llm_extractor.py` (new)
- `serve/knowledge/pyproject.toml`
- `tests/test_llm_extractor.py` (new)

[[2026-04-09]] Thu 05:08
## Research
- Research doc: .owlbear/research/llmextractor-pydanticai-implementation.md
- Sources: 8 studied, 6 high-relevance (codebase: protocol.py, extractor.py, models.py, pyproject.toml; external: PydanticAI agent docs, testing docs, output docs)
- Recommendation: Thin PydanticAI Agent wrapper (~30 LOC) with complete system prompt (confidence: 0.88)
- Key finding: Existing EXTRACTION_PROMPT missing `governed_by` from RelationType enum — LLMExtractor system prompt must include all 7 relation types for AC3 compliance
- Testing strategy: PydanticAI TestModel + agent.override() pattern with ALLOW_MODEL_REQUESTS=False safety guard
- Dependency chain: #687 (async protocol) + #698 (TDD RED) must complete first; metadata defect (depends_on: [676] → [698, 687]) still unapplied
- Follow-up tasks created: none — ACs are complete and concrete, predecessor tasks exist
- Decision requests: none — T1 autonomous (implements existing AC with proven v1 pattern)

## Challenge Results
- Challenger: FALLBACK — challenger agent not available
- Confidence in original: 0.88
- Key risks: PydanticAI transitive deps (~5) mitigated by optional extras group; protocol must be async first (#687)
- Researcher response: N/A (fallback)
