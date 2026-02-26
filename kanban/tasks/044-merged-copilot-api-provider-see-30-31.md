---
id: 44
title: 'MERGED: Copilot API provider (see #30-31)'
status: done
priority: high
created: 2026-02-26T15:57:14.0162051+01:00
updated: 2026-02-26T19:42:42.2428665+01:00
tags:
    - phase-2
    - agent
    - auth
class: standard
---

## MERGED into tasks #30-31

Research confirmed: PydanticAI OpenAIProvider(base_url='https://api.individual.githubcopilot.com/v1', api_key=token) works directly. No custom provider needed. The real work is OAuth device-flow (task #30-31).

See docs/pydantic-ai-integration-research.md §3.3
