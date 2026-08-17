# DiagramService Kroki HTTP API — Test Design Research

> **Owning task:** #617 — Test DiagramService (Kroki HTTP API wrapper)
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

Task #617 is test-first: write tests for a `DiagramService` that wraps Kroki's HTTP API. The implementation lives in #620. This research validates the Kroki API contract, corrects an AC error, and defines concrete test cases.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | Kroki docs — Usage | <https://docs.kroki.io/kroki/setup/usage/> | .95 — POST endpoint formats, encoding rules |
| 2 | Kroki docs — HTTP Clients | <https://docs.kroki.io/kroki/setup/http-clients/> | .90 — cURL/HTTPie examples, request formats |
| 3 | yuzutech/kroki DiagramHandler.java | <https://github.com/yuzutech/kroki/blob/main/server/src/main/java/io/kroki/server/service/DiagramHandler.java> | .95 — Error handling: 400 codes, validation logic |
| 4 | Kroki docs — Install (container list) | <https://docs.kroki.io/kroki/setup/install/> | .85 — Which types need companion containers |
| 5 | antoinebou12/uml-mcp | <https://github.com/antoinebou12/uml-mcp> | .80 — Python Kroki wrapper patterns, fallback strategy |
| 6 | OwlBear test_screenshot.py | `tests/test_screenshot.py` | .90 — Service test pattern (class-based, fixtures) |
| 7 | OwlBear test_github_api.py | `tests/test_github_api.py` | .85 — httpx mock pattern (`_make_response`, `_make_client`) |
| 8 | OwlBear httpx-timeout.md | `docs/research/httpx-timeout.md` | .90 — Timeout conventions per use case |

## 3. Analysis

### 3.1 Kroki API Contract

**POST with plain text** (simplest — recommended):

```
POST /{diagram_type}/{output_format}
Content-Type: text/plain

digraph G { Hello->World }
```

Response: raw image bytes (PNG) or SVG string. Content-Type varies by format.

**POST with JSON** (alternative):

```json
POST /
{ "diagram_source": "...", "diagram_type": "graphviz", "output_format": "svg" }
```

**Key finding:** The GET method uses deflate+base64 URL encoding. POST does **not** — it sends raw text. The #620 AC incorrectly says "deflated+base64 source body" for POST. This must be corrected.

### 3.2 Error Responses (from DiagramHandler.java)

| HTTP Status | Condition | Response Body |
|-------------|-----------|---------------|
| 400 | Empty request body | "Request body must not be empty." |
| 400 | Empty `diagram_source` (JSON) | "Field diagram_source must not be empty." |
| 400 | Unsupported output format | "Unsupported output format: X for Y" |
| 400 | Invalid diagram syntax | Diagram-library-specific error text |
| 400 | Unknown diagram type | "Unknown diagram type: X" (routed to 404) |

All error bodies are **plain text**, not JSON.

### 3.3 Diagram Types Available on Free kroki.io

| Type | Endpoint | Companion Needed | SVG | PNG |
|------|----------|-----------------|-----|-----|
| graphviz | `/graphviz` | No (core) | Yes | Yes |
| plantuml | `/plantuml` | No (core) | Yes | Yes |
| c4plantuml | `/c4plantuml` | No (core) | Yes | Yes |
| d2 | `/d2` | No (core) | Yes | Yes |
| mermaid | `/mermaid` | Yes (kroki-mermaid) | Yes | Yes |

Note: Free kroki.io runs all companions. Self-hosted needs explicit companion containers.

### 3.4 POST Approach Comparison

| Approach | KISS | Encoding | URL Complexity |
|----------|------|----------|----------------|
| Text POST to `/{type}/{format}` (.90) | High | None | Simple path |
| JSON POST to `/` (.75) | Medium | JSON body | Root with body routing |
| GET with deflate+base64 (.60) | Low | deflate+base64 | Encoded URL path |

**Verdict (.90):** Text POST to `/{type}/{format}` — simplest, no encoding needed.

### 3.5 Timeout Selection

Per `docs/research/httpx-timeout.md`, external API calls with small payloads use 15s (GitHub API) or 30s (URL fetch). Kroki typical latency ~200ms, but complex diagrams can take several seconds. **30s with 5s connect** matches existing `read_url`/`bookmark_pipeline` precedent and the current #617 AC.

### 3.6 Test Architecture (from existing patterns)

| Pattern Element | Source | How to Apply |
|----------------|--------|--------------|
| Class-based test groups | `test_screenshot.py` | `TestGenerate`, `TestValidation`, `TestErrorHandling` |
| `_make_response` helper | `test_github_api.py` | Build `httpx.Response` with status, content, headers |
| `_make_client` helper | `test_github_api.py` | `AsyncMock` wrapping response for `async with` context |
| `@pytest.mark.asyncio` | `test_visual_feedback.py` | All `generate()` tests are async |
| `MagicMock(spec=...)` | `test_knowledge_intake.py` | `spec=httpx.Response` for type safety |

## 4. Recommendation (.90 confidence)

### 4.1 AC Correction for #620

The AC line "POST ... with deflated+base64 source body" is wrong. Kroki POST accepts **plain text body** — encoding is only for GET URLs. Correct to: "POST to `{kroki_server_url}/{diagram_type}/{output_format}` with `Content-Type: text/plain` and raw source body."

### 4.2 Refined Test Cases for #617

**TestGenerate (happy path):**

1. `test_generate_svg_returns_bytes` — mock 200 + SVG body → returns SVG bytes
2. `test_generate_png_returns_bytes` — mock 200 + PNG body → returns PNG bytes
3. `test_generate_uses_correct_url` — verifies POST to `{server}/{type}/{format}`
4. `test_generate_sends_source_as_body` — raw diagram text in request body
5. `test_generate_sends_text_plain_content_type` — Content-Type header check
6. `test_default_output_format_is_svg` — omitting format defaults to svg
7. `test_custom_server_url` — non-default `server_url` used correctly
8. `test_server_url_trailing_slash_stripped` — `"https://kroki.io/"` normalized

**TestValidation (input guards):**

9. `test_empty_source_raises_valueerror` — `""` → `ValueError`
10. `test_whitespace_source_raises_valueerror` — `"  "` → `ValueError`
11. `test_unknown_diagram_type_raises_valueerror` — `"unknown"` → `ValueError`
12. `test_unsupported_output_format_raises_valueerror` — `"pdf"` → `ValueError`
13. `test_accepted_diagram_types` — mermaid, plantuml, graphviz, d2, c4plantuml all pass
14. `test_accepted_output_formats` — svg, png both pass

**TestErrorHandling (Kroki failures):**

15. `test_400_raises_diagram_error` — 400 status → `DiagramError` with body
16. `test_500_raises_diagram_error` — 500 status → `DiagramError` with status code
17. `test_connect_error_propagates` — `httpx.ConnectError` raised transparently
18. `test_timeout_error_propagates` — `httpx.TimeoutException` raised transparently

**TestHttpxConfig (client setup):**

19. `test_uses_explicit_timeout` — `httpx.Timeout(30, connect=5)` on client

**Total: 19 test cases** covering happy path, validation, errors, and httpx config.

### 4.3 DiagramService Interface Contract (for tests to target)

```python
# src/owlbear/tools/diagram/service.py
class DiagramService:
    def __init__(self, server_url: str = "https://kroki.io"): ...
    async def generate(self, diagram_type: str, source: str, output_format: str = "svg") -> bytes: ...


class DiagramError(Exception):
    def __init__(self, status_code: int, body: str): ...
```

## 5. Follow-up Tasks

```powershell
# Move #617 to backlog with refined AC
kanban\kanban-md.exe move 617 backlog

# Fix incorrect AC on #620 (POST uses plain text, not deflate+base64)
kanban\kanban-md.exe edit 620 --body "Implement Tier 1 diagram rendering service. File: src/owlbear/tools/diagram/service.py

AC:
- [ ] DiagramService class in src/owlbear/tools/diagram/service.py
- [ ] async generate(diagram_type: str, source: str, output_format: str = 'svg') -> bytes
- [ ] POST to {kroki_server_url}/{diagram_type}/{output_format} with Content-Type: text/plain and raw source body
- [ ] Accepted diagram_type: mermaid, plantuml, graphviz, d2, c4plantuml (ValueError on unknown)
- [ ] Accepted output_format: svg, png (ValueError on unknown)
- [ ] Raises DiagramError(status_code, body) on non-2xx response
- [ ] httpx.AsyncClient with Timeout(30, connect=5) per project convention
- [ ] kroki_server_url: str field added to OwlBearSettings (default 'https://kroki.io')
- [ ] src/owlbear/tools/diagram/__init__.py exports DiagramService, DiagramError
- [ ] All tests from #617 pass, ruff clean

Pattern: follow ScreenshotService (stateless, injected deps)
Ref: docs/research/visuals-diagrams-mcp.md section 4 Tier 1
CORRECTED: POST uses plain text body, NOT deflate+base64 (that is for GET only). See docs/research/diagram-service-kroki.md."
```

## 6. Attribution Updates

| Source | URL | License | What | Where Used | Date |
|--------|-----|---------|------|------------|------|
| Kroki docs — Usage | <https://docs.kroki.io/kroki/setup/usage/> | MIT | POST API contract: text/JSON formats, no encoding needed for POST | `docs/research/diagram-service-kroki.md` | 2026-03-07 |
| Kroki docs — HTTP Clients | <https://docs.kroki.io/kroki/setup/http-clients/> | MIT | cURL/HTTPie request examples, Content-Type patterns | `docs/research/diagram-service-kroki.md` | 2026-03-07 |
| yuzutech/kroki DiagramHandler.java | <https://github.com/yuzutech/kroki> | MIT | Error handling: BadRequestException codes, empty body/source validation, UnsupportedFormatException | `docs/research/diagram-service-kroki.md` | 2026-03-07 |
| Kroki docs — Install | <https://docs.kroki.io/kroki/setup/install/> | MIT | Core vs companion container diagram type availability | `docs/research/diagram-service-kroki.md` | 2026-03-07 |
