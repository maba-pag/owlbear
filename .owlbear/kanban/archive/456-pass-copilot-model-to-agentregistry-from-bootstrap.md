---
id: 456
title: Pass Copilot model to AgentRegistry from bootstrap
status: archived
priority: critical
created: 2026-03-03T21:12:29.6395952+01:00
updated: 2026-03-04T07:58:30.0069424+01:00
started: 2026-03-03T21:12:37.3480381+01:00
completed: 2026-03-04T07:58:30.0069424+01:00
tags:
    - agent
    - daemon
    - phase-refactor
class: standard
---

## Problem
AgentRegistry defaults to 'gpt-4o' as default_model. bootstrap() creates the Copilot model but never passes it to build_agent_registry(). When delegated agents are instantiated via registry.get(), they try to use OpenAI's API directly instead of the Copilot provider, failing with 'OPENAI_API_KEY not set'.

## Fix
1. Change AgentRegistry.__init__ default_model type: str -> str | Model
2. Update build_agent_registry() to accept and forward the model
3. Update bootstrap() to pass the Copilot model to build_agent_registry()

## AC
- [ ] AgentRegistry accepts str | Model for default_model
- [ ] build_agent_registry() accepts a model parameter and passes to AgentRegistry
- [ ] bootstrap() passes the Copilot model to build_agent_registry()
- [ ] Delegated agents use the Copilot provider (not OpenAI)
- [ ] All tests pass
- [ ] Ruff clean
