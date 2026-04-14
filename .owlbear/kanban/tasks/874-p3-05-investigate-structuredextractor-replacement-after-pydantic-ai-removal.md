---
id: 874
title: 'P3-05: Investigate StructuredExtractor replacement after pydantic-ai removal'
status: todo
priority: important
created: '2026-04-14T14:25:52.404434+00:00'
updated: '2026-04-14T16:50:55.894247+00:00'
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

pydantic-ai and LLMExtractor were removed (2026-04-14). The `StructuredExtractor` protocol in `protocol.py` has zero implementations. Both `InterDocGraphBuilder` (requires extractor) and `EntityExtractor` (no-op without injected extractor) are non-functional at production level. This blocks #862 (inter-doc prompt integration) and limits #864 (pipeline wiring) to mock-only testing.

## Acceptance Criteria

- [ ] Research replacement options for StructuredExtractor (lightweight LLM callable, litellm-based, raw API, etc.)
- [ ] Evaluate against KISS principle — minimal deps, no pydantic-ai reintroduction
- [ ] Recommend an approach with trade-off matrix
- [ ] Implementation follow-up task(s) created at research status

## Affected Files

- `serve/knowledge/src/owlbear_knowledge/protocol.py` (StructuredExtractor protocol)
- `serve/knowledge/src/owlbear_knowledge/extractor.py` (EntityExtractor — no-op without impl)
- `serve/knowledge/src/owlbear_knowledge/llm_extractor.py` (prompt templates only — no class)

## Context from #864 research

See: .owlbear/research/864-wire-interdocgraphbuilder-pipeline.md (Section 3.1)

[[2026-04-14]]
## Research
- Research doc: .owlbear/research/874-structuredextractor-replacement.md
- Sources: 12 studied, 8 high-relevance
- Recommendation: `openai` Python SDK as optional dependency (confidence: .85)
- Follow-up tasks created: #875 (implement LLMExtractor), #876 (wire into MCP server)
- Decision requests: none (T1 — Autonomous)

## Key Findings
- 4 options evaluated: openai SDK (.88), litellm (.30), instructor (.72), raw httpx (.55)
- litellm disqualified: supply chain attack March 2026 (TeamPCP/LAPSUS$), 13 deps + 4 version downgrades, releases paused
- openai SDK wins on KISS: 4 new deps, zero conflicts, native structured outputs, async-first, ~25 LOC implementation
- Optional dep group `llm = ["openai>=1.50"]` preserves zero-LLM-dep default for non-extraction users

## Challenge Results
- Challenger: FALLBACK — challenger subagent not in available roster
- Confidence in original: .85
[[2026-04-14]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Pure research task — one question: what replaces StructuredExtractor? |
| Interface clarity | PASS | Research outputs clear: doc, recommendation, follow-up tasks with concrete AC |
| Dependency correctness | PASS | No `depends_on` needed for standalone research |
| Module layering | PASS | Research only — no code changes |
| TDD compliance | N/A | Research task, no code |
| KISS/YAGNI | PASS | Minimal scope, deferred implementation to follow-ups |
| Premise challenge | PASS | Verified: `StructuredExtractor` has zero implementations after pydantic-ai removal; `EntityExtractor` returns empty results without injected extractor; `InterDocGraphBuilder` requires extractor. Gap is real. |
| Pattern consistency | PASS | Research follows standard pattern (doc, findings, follow-ups). Optional dep strategy matches existing `qdrant`/`embedding`/`intake` groups in `serve/knowledge/pyproject.toml` |
| Security surface | PASS | Research correctly identified litellm supply chain risk (TeamPCP/LAPSUS$ Mar 2026). Recommendation (openai SDK) has low security surface. |
| Single domain | PASS | Scoped to `scope:knowledge` |

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| Research replacement options | MET — 4 options evaluated: openai SDK, litellm, instructor, raw httpx | None |
| Evaluate against KISS | MET — trade-off matrix with dep counts, version conflicts, install footprint | None |
| Recommend with trade-off matrix | MET — Section 3.2 trade-off matrix, Section 4 recommendation (confidence .85) | None |
| Follow-up tasks at research | MET — #875 (LLMExtractor impl), #876 (MCP wiring) both at `research` status | None |

### Codebase Evidence

- `protocol.py:91-99`: `StructuredExtractor` protocol — `async extract(prompt) -> ExtractionResult`. Zero implementations confirmed.
- `extractor.py:82-84`: `EntityExtractor` returns empty `ExtractionResult()` when `self._extractor is None`.
- `llm_extractor.py`: Contains `LLM_EXTRACTION_PROMPT` constant only — no class. Confirms removed state.
- `serve/knowledge/pyproject.toml`: Currently has `qdrant`, `embedding`, `intake` optional groups — openai `llm` group follows existing pattern.

### Dependency Flags

- **#876 missing `depends_on: [875]`**: Body says "Depends on P3-06" but `depends_on` field is empty. Must be set before #876 leaves research.

### Challenge Results

- Challenger: FALLBACK — challenger subagent not in available agent roster
- Architect response: Proceeded without challenge. Research quality is high (12 sources, 4 options with scoring, security disqualification well-documented, implementation shape concrete). Confidence in APPROVE: .92.

### Non-Implementation Tag

- Added `research` pass-through tag — task produces no testable Python code.

### Verdict: APPROVE
### Action Taken: Advanced #874 to todo. Flagged #876 dependency gap (needs `depends_on: [875]`).