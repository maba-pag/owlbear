---
id: 30
title: 'P4-02: Research Copilot OAuth from Graphicator project'
status: archived
priority: high
created: 2026-02-24T15:15:19.0279037+01:00
updated: 2026-02-27T10:00:07.9889007+01:00
started: 2026-02-24T15:17:05.0151219+01:00
completed: 2026-02-27T10:00:07.9889007+01:00
tags:
    - phase-4
    - research
    - auth
class: standard
---

AC: Analyze C:\Users\p362329\OneDrive\Coding\Projects\tool.graphicator for the Copilot OAuth implementation. Study: (1) src/graphicator/auth/copilot.py -- device-flow OAuth (request_device_code, poll_for_access_token, exchange_for_copilot_token, derive_base_url, token caching), (2) src/graphicator/agents/__init__.py -- agent factory routing to Copilot vs GitHub Models, (3) src/graphicator/config.py -- provider settings, (4) editor headers and integration headers, (5) tests/test_auth_copilot.py -- test patterns. Document in docs/research/copilot-auth.md.

**NOTE: Task #44 (Copilot API provider) merged into this scope.** Research confirmed PydanticAI OpenAIProvider works with Copilot base_url directly: OpenAIProvider(base_url='https://api.individual.githubcopilot.com/v1', api_key=token). The real work is OAuth device-flow auth + token refresh. See docs/research/pydantic-ai-integration.md §3.3.
