---
id: 266
title: 'OwlBearAgent: accept model instances and add update_model()'
status: archived
priority: needed
created: 2026-02-28T14:20:23.0188563+01:00
updated: 2026-02-28T23:54:31.5405378+01:00
started: 2026-02-28T15:04:44.2632521+01:00
completed: 2026-02-28T23:54:31.5405378+01:00
tags:
    - phase-8
    - agent
    - core
depends_on:
    - 265
class: standard
---

## Context
OwlBearAgent.__init__ currently takes model: str. Must accept str | Model for Copilot integration.
PydanticAI Agent already has a model.setter property that allows changing the model without rebuilding.
See docs/research/bootstrap-assembly.md S3.3 and S3.6.

## Acceptance Criteria
- [ ] Change OwlBearAgent.__init__ model parameter type from str to str | Model (import from pydantic_ai.models)
- [ ] Store the raw model value (not just str name) so inner Agent gets the Model instance
- [ ] Add update_model(new_model: str | Model) method that sets self.inner.model = new_model
- [ ] update_model also updates self._model_name for usage tracking (extract str name from Model if needed)
- [ ] Do NOT rebuild the inner Agent — PydanticAI Agent.model has a setter that replaces the model in-place
- [ ] Existing tests unchanged: model='test' string usage continues to work
- [ ] Unit test: construct with OpenAIChatModel mock, verify inner.model is the instance
- [ ] Unit test: call update_model(), verify inner.model changed
- [ ] Unit test: verify _model_name updated after update_model for usage tracking
- [ ] ~10 LOC diff

## Architecture Notes
- PydanticAI Agent has: @model.setter def model(self, value) that directly sets self._model
- No need to rebuild Agent — just agent.model = new_model. This preserves toolsets, instructions, etc.
- update_model is needed for token refresh in daemon loop (catch auth error -> refresh -> update_model)
- _model_name tracking: if model is a Model instance, extract model_name attribute or str(model)

## TDD
Test task: included in AC above (tests in same task since diff is ~10 LOC)

## Dependencies
depends_on: [265]
