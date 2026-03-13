---
id: 460
title: Add explicit timeouts to all httpx.AsyncClient calls
status: archived
priority: critical
created: 2026-03-04T07:37:40.338076+01:00
updated: 2026-03-06T19:28:07.1282417+01:00
started: 2026-03-06T00:15:20.9905393+01:00
completed: 2026-03-06T19:28:07.1282417+01:00
tags:
    - audit
    - resilience
    - scope:core
class: standard
---

## Acceptance Criteria
- [ ] `auth/copilot.py`: All 3 `httpx.AsyncClient(verify=_ssl_context())` calls get `timeout=httpx.Timeout(10, connect=5)`
- [ ] `tools/github_api.py`: All 4 `httpx.AsyncClient()` calls get `timeout=httpx.Timeout(15, connect=5)`
- [ ] `memory/knowledge/intake.py`: `read_url` gets `timeout=httpx.Timeout(30, connect=5)`
- [ ] `providers/copilot.py`: `create_copilot_client` gets `timeout=httpx.Timeout(600, connect=5)`
- [ ] `tools/browser/launcher.py`: `is_cdp_available` gets `timeout=httpx.Timeout(3, connect=2)`
- [ ] `tools/browser/url_utils.py`: robots.txt fetch gets `timeout=httpx.Timeout(10, connect=5)`
- [ ] Existing timeout sites (`web_search.py`, `bookmark_pipeline.py`) left unchanged -- already correct
- [ ] Tests: Add grep-based or AST test asserting every `httpx.AsyncClient` in src/ has explicit `timeout` kwarg

See docs/research/httpx-timeout.md for rationale and prior art.
