# httpx Timeout Configuration Research

> **Owning task:** #460 — Add explicit timeouts to all httpx.AsyncClient calls
> **Date:** 2026-03-06  **Status:** Complete

## 1. Context and Question

The resilience audit (docs/resilience-audit.md, findings T-1/T-2/T-3) identified that most `httpx.AsyncClient` instantiations lack explicit timeouts. On corporate proxies or slow APIs, this blocks the daemon indefinitely. The question: what timeout strategy and values should we apply?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | httpx official docs — Timeouts | <https://www.python-httpx.org/advanced/timeouts/> | 1.0 |
| 2 | PydanticAI `cached_async_http_client` | pydantic-ai `models/__init__.py` (`DEFAULT_HTTP_TIMEOUT=600`, `connect=5`) | .95 |
| 3 | OwlBear codebase — existing patterns | `web_search.py` L194, `bookmark_pipeline.py` L186 | .90 |
| 4 | httpx default behavior | httpx source — default 5s timeout for all phases | .85 |

### Key facts from sources

- **httpx default:** 5s timeout for connect, read, write, and pool — raises `TimeoutException` (Source 1, 4).
- **PydanticAI pattern:** `httpx.Timeout(timeout=600, connect=5)` — 600s overall (matches OpenAI default), 5s connect. Per-client, not per-request (Source 2).
- **OwlBear precedent:** `web_search.py` uses `timeout=30` per-request; `bookmark_pipeline.py` uses `timeout=30` on client constructor (Source 3).

## 3. Analysis

### 3.1 Per-client vs per-request timeouts

| Approach | Pros | Cons |
|----------|------|------|
| Per-client (`AsyncClient(timeout=...)`) | Single point of config; all requests inherit | Can't differentiate fast/slow endpoints |
| Per-request (`client.get(url, timeout=...)`) | Fine-grained control | Easy to miss one; more noise |
| Hybrid (client default + per-request override) | Best of both | Slightly more complex |

**Verdict (.90):** Per-client is sufficient for OwlBear. Each `AsyncClient` is short-lived (`async with`) and scoped to one call type. No need for per-request overrides.

### 3.2 Timeout values by use case

| Module | Call type | Recommended timeout | Rationale |
|--------|-----------|-------------------|-----------|
| `auth/copilot.py` — `request_device_code` | GitHub OAuth (POST) | `Timeout(10, connect=5)` | Small JSON payload; GitHub responds fast |
| `auth/copilot.py` — `poll_for_access_token` | GitHub OAuth poll (POST) | `Timeout(10, connect=5)` | Same; polling loop already has `expires_in` guard |
| `auth/copilot.py` — `exchange_for_copilot_token` | Copilot token (GET) | `Timeout(10, connect=5)` | Small JSON response |
| `tools/github_api.py` — all 4 methods | GitHub REST API (GET/POST) | `Timeout(15, connect=5)` | API can be slower with large issue bodies; 15s generous |
| `memory/knowledge/intake.py` — `read_url` | Arbitrary URL fetch | `Timeout(30, connect=5)` | Unknown content size; matches existing web_search pattern |
| `providers/copilot.py` — `create_copilot_client` | LLM streaming client | `Timeout(600, connect=5)` | Long LLM responses; matches PydanticAI default |
| `tools/browser/launcher.py` — `is_cdp_available` | localhost probe | `Timeout(3, connect=2)` | Local only; should be instant |
| `tools/browser/url_utils.py` — robots.txt fetch | robots.txt | `Timeout(10, connect=5)` | Small file; failure is acceptable |

### 3.3 Should timeouts be configurable via OwlBearSettings?

| Option | Confidence | Rationale |
|--------|------------|-----------|
| Hardcoded per module | **.85** | KISS/YAGNI — timeouts are implementation detail, not user-tunable. PydanticAI hardcodes theirs. Only expose if users report problems. |
| Single `http_timeout` setting | .50 | One size doesn't fit (auth ≠ LLM streaming ≠ URL fetch). Would need multiple settings — over-engineered. |
| Per-module setting | .20 | 6+ new settings for edge cases. Violates YAGNI. |

**Verdict (.85):** Hardcode per module. Add settings later only if user demand requires it.

### 3.4 `httpx.Timeout` vs plain int

| Approach | Confidence | Notes |
|----------|------------|-------|
| `httpx.Timeout(total, connect=N)` | **.90** | Explicit connect timeout matters most for proxy detection. Source 1/2 both use this. |
| `timeout=N` (int shorthand) | .70 | Simpler but applies same value to all phases. OwlBear already uses this in web_search. |

**Verdict (.90):** Use `httpx.Timeout(total, connect=5)` for the 3 critical modules (auth, GitHub, intake). The explicit connect timeout catches proxy/DNS issues fast. For already-correct files (web_search, bookmark_pipeline), leave as-is.

## 4. Recommendation (.90 confidence)

Add `timeout=httpx.Timeout(T, connect=5)` to every `httpx.AsyncClient()` constructor where `T` varies by use case (see §3.2). Hardcode values — no new settings. This is 8 call sites across 5 files. The `providers/copilot.py` client needs `timeout=httpx.Timeout(600, connect=5)` to match PydanticAI convention for LLM streaming.

**Risk:** Timeout too aggressive for edge cases (very slow corporate proxy). **Mitigation:** 10s connect is already generous; `connect=5` matches PydanticAI default. If issues arise, promote to a setting later.

## 5. Follow-up Tasks

All 8 call sites can be fixed in a single task — the scope is small and mechanical.

```
kanban\kanban-md.exe edit 460 --body "## Acceptance Criteria\n- [ ] `auth/copilot.py`: All 3 `httpx.AsyncClient(verify=_ssl_context())` calls get `timeout=httpx.Timeout(10, connect=5)`\n- [ ] `tools/github_api.py`: All 4 `httpx.AsyncClient()` calls get `timeout=httpx.Timeout(15, connect=5)`\n- [ ] `memory/knowledge/intake.py`: `read_url` gets `timeout=httpx.Timeout(30, connect=5)`\n- [ ] `providers/copilot.py`: `create_copilot_client` gets `timeout=httpx.Timeout(600, connect=5)`\n- [ ] `tools/browser/launcher.py`: `is_cdp_available` gets `timeout=httpx.Timeout(3, connect=2)`\n- [ ] `tools/browser/url_utils.py`: robots.txt fetch gets `timeout=httpx.Timeout(10, connect=5)`\n- [ ] Existing timeout sites (`web_search.py`, `bookmark_pipeline.py`) left unchanged — already correct\n- [ ] Tests: Add unit test asserting every `httpx.AsyncClient` in src/ has an explicit `timeout` kwarg (grep-based or AST)\n\nSee docs/research/httpx-timeout.md for rationale and prior art."
```

```
kanban\kanban-md.exe move 460 backlog
```
