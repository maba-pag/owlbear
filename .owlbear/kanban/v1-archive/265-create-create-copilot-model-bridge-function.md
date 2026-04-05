---
id: 265
title: Create create_copilot_model() bridge function
status: archived
priority: needed
created: 2026-02-28T14:20:13.7625827+01:00
updated: 2026-02-28T23:54:30.8489933+01:00
started: 2026-02-28T15:04:22.7772975+01:00
completed: 2026-02-28T23:54:30.8489933+01:00
tags:
    - phase-8
    - agent
    - auth
class: standard
---

## Context
Bridges existing create_copilot_client() to PydanticAI OpenAIChatModel.
See docs/research/bootstrap-assembly.md S3.3, step 1.
See docs/research/daemon-bootstrap.md S3.1 for confirmed pattern.

## Acceptance Criteria
- [ ] Add async create_copilot_model(settings: OwlBearSettings | None = None) -> OpenAIChatModel to src/owlbear/providers/copilot.py
- [ ] Calls existing create_copilot_client(settings) to get AsyncOpenAI client
- [ ] Wraps client via OpenAIProvider(openai_client=client) from pydantic_ai.providers.openai
- [ ] Constructs OpenAIChatModel(settings.chat_model, provider=provider) from pydantic_ai.models.openai
- [ ] Returns OpenAIChatModel instance ready to pass to Agent() or OwlBearAgent()
- [ ] Unit test: mock create_copilot_client, verify OpenAIProvider and OpenAIChatModel construction
- [ ] Unit test: verify settings.chat_model is forwarded as the model name
- [ ] Unit test: verify RuntimeError propagates when no token cached
- [ ] ~15 LOC implementation, ~40 LOC tests

## Architecture Notes
- Pattern confirmed in tool.graphicator and daemon-bootstrap.md S3.1
- PydanticAI Agent.__init__ accepts model: Model | KnownModelName | str | None
- This function is pure wiring — no new abstractions
- Follows existing create_copilot_client() conventions (async, settings param, defaults to OwlBearSettings())

## TDD
Test task: included in AC above (tests in same task since implementation is ~15 LOC)
