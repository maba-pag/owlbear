---
id: 37
title: Validate PydanticAI message types for OwlBear
status: archived
priority: high
created: 2026-02-26T15:56:34.890276+01:00
updated: 2026-02-27T10:00:11.5679091+01:00
started: 2026-02-26T19:41:06.5120847+01:00
completed: 2026-02-27T10:00:11.5679091+01:00
tags:
    - phase-2
    - agent
    - model
class: standard
---

## Research findings (See docs/pydantic-ai-integration-research.md §3.1)

PydanticAI provides a complete message system (2121 LOC): ModelRequest, ModelResponse, UserPromptPart, TextPart, ToolCallPart, ToolReturn, streaming deltas. Building our own would fight the framework.

**Decision:** DO NOT build a custom Message model. Use PydanticAI's types directly.

**Remaining work:**
- Write integration tests proving PydanticAI messages serialize to/from JSONL (for session persistence #41)
- Document the PydanticAI message types in copilot-instructions.md as the canonical format
- If needed, define a thin OwlBear metadata envelope (channel source, session_id) as a wrapper — but only if PydanticAI's metadata field is insufficient

## AC (revised)
Tests proving PydanticAI ModelMessage types round-trip through JSONL serialization. Documentation of canonical message format.
