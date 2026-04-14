---
id: 876
title: 'P3-07: Wire LLMExtractor into MCP knowledge server'
status: backlog
priority: important
created: '2026-04-14T15:28:36.425659+00:00'
updated: '2026-04-14T17:12:17.134942+00:00'
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
- Recommendation: Hybrid env var fallback (OWLBEAR_LLM_* → OPENAI_*) with import+key gating, ~20 LOC in app_lifespan(), 3 new AppContext fields (confidence: .88)
- Key findings: InterDocGraphBuilder requires extractor (not optional) — must be None when no extractor; IntraDocGraphBuilder accepts optional extractor; existing try/except ImportError pattern in qdrant.py and intake.py provides precedent
- Follow-up tasks created: none — #876 AC is implementation-ready, dependency #875 already tracked
- Decision requests: none