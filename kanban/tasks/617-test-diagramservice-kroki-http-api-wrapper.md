---
id: 617
title: Test DiagramService (Kroki HTTP API wrapper)
status: archived
priority: needed
created: 2026-03-07T05:20:46.6462937+01:00
updated: 2026-03-07T18:08:23.0252756+01:00
started: 2026-03-07T05:49:31.7651367+01:00
completed: 2026-03-07T18:08:23.0252756+01:00
tags:
    - phase-research
    - scope:core
    - tooling
    - test
class: standard
---

Test-first task for DiagramService. File: tests/test_diagram_service.py

Interface under test (from #620):
  DiagramService(server_url: str = 'https://kroki.io')
  async generate(diagram_type: str, source: str, output_format: str = 'svg') -> bytes
  DiagramError(status_code: int, body: str) — custom exception

AC:

**TestGenerate (happy path — mocked httpx POST):**
- [ ] generate('graphviz', 'digraph G {...}', 'svg') returns bytes from mocked 200 response
- [ ] generate('mermaid', ..., 'png') returns PNG bytes from mocked 200 response
- [ ] POST URL is {server_url}/{diagram_type}/{output_format} (verify via mock call args)
- [ ] Request body is raw diagram source text (no encoding, no JSON)
- [ ] Content-Type header is 'text/plain'
- [ ] Default output_format is 'svg' when omitted
- [ ] DiagramService(server_url='https://custom.example.com') posts to that base URL
- [ ] Trailing slash on server_url is stripped ('https://kroki.io/' -> 'https://kroki.io')

**TestValidation (input guards, no HTTP call):**
- [ ] Empty source ('') raises ValueError
- [ ] Whitespace-only source ('   ') raises ValueError
- [ ] Unknown diagram_type ('unknown') raises ValueError
- [ ] Unsupported output_format ('pdf') raises ValueError
- [ ] All 5 accepted types pass: mermaid, plantuml, graphviz, d2, c4plantuml
- [ ] Both accepted formats pass: svg, png

**TestErrorHandling (Kroki failure responses):**
- [ ] 400 response raises DiagramError; error has .status_code=400 and .body containing response text
- [ ] 500 response raises DiagramError; error has .status_code=500
- [ ] httpx.ConnectError propagates (not wrapped)
- [ ] httpx.TimeoutException propagates (not wrapped)

**TestHttpxConfig (client construction):**
- [ ] httpx.AsyncClient created with Timeout(30, connect=5) — patch constructor, inspect call

**TDD gate:**
- [ ] All tests fail with ImportError or similar before DiagramService exists (no stub)
- [ ] File: tests/test_diagram_service.py

Total: 19 test cases across 4 test classes.

Patterns to follow:
- test_github_api.py: _make_response() / _make_client() helpers for httpx mocking
- test_knowledge_intake.py: AsyncMock(spec=httpx.AsyncClient) with __aenter__/__aexit__
- test_screenshot.py: class-based grouping with clear docstrings
- @pytest.mark.asyncio on all async tests (strict mode)
- patch('owlbear.tools.diagram.service.httpx.AsyncClient', ...) for mock injection

Ref: docs/research/diagram-service-kroki.md (19 test cases, section 4)
