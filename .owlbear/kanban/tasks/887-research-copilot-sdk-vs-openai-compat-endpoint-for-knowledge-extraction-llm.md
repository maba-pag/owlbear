---
id: 887
title: 'Research: Copilot SDK vs OpenAI-compat endpoint for knowledge extraction LLM'
status: research
priority: important
created: '2026-04-15T13:34:22.037145+00:00'
updated: '2026-04-15T13:34:22.037145+00:00'
tags:
- research
- scope:knowledge
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
Evaluate two approaches for using GitHub Copilot's LLM from the knowledge extraction pipeline (Python MCP server), without requiring an external OpenAI API key.

## Acceptance Criteria
- Compare **Copilot SDK** (`github-copilot-sdk`) vs **OpenAI SDK with Copilot endpoint** (faking VS Code client headers at `api.githubcopilot.com`)
- For each approach, verify:
  1. Can send a system prompt + user content and get structured JSON back
  2. Works from a standalone Python process (MCP server, not inside VS Code)
  3. Supports `ExtractionResult` schema parsing (entities + edges)
  4. Authentication flow — does it use Copilot subscription seamlessly?
  5. Rate limits, model availability, latency
- Document which models support structured output (`response_format`) via each approach
- Recommend one approach with confidence score and trade-off analysis
- Reference v1 experiment where OpenAI-compatible Copilot endpoint was tested (OpenClaw context)

## Context
- Current: `LLMExtractor` in `serve/knowledge/src/owlbear_knowledge/llm_extractor.py` uses `openai.AsyncOpenAI` with `chat.completions.parse(response_format=ExtractionResult)`
- Goal: use Copilot subscription for LLM access without external API keys
- Copilot SDK: `pip install github-copilot-sdk` (v0.2.2) — session-based, event-driven, supports BYOK
- OpenAI-compatible endpoint: `api.githubcopilot.com` — tested in v1, required client ID header faking

## Research sources
- https://pypi.org/project/github-copilot-sdk/
- https://github.com/github/copilot-sdk
- https://github.com/ericc-ch/copilot-api (OpenAI-compat wrapper)
- v1 experiment notes (if findable in archive)