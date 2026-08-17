# Copilot OAuth Research — Device-Flow Auth from Graphicator

> **Owning task:** #30 — P4-02: Research Copilot OAuth from Graphicator project
> **Date:** 2026-02-26
> **Status:** Complete

## 1. Context and Question

OwlBear needs GitHub Copilot API authentication via OAuth device-flow (RFC 8628).
Graphicator (`tool.graphicator`) has a working implementation to analyze and port.
PydanticAI's `OpenAIProvider` connects to Copilot with `base_url` + `api_key` —
the real work is the OAuth dance and token management.

## 2. Sources Studied

| Source | Path / URL | Relevance |
|--------|-----------|-----------|
| Graphicator `auth/copilot.py` | `tool.graphicator/src/graphicator/auth/copilot.py` | 1.0 |
| Graphicator `agents/__init__.py` | `tool.graphicator/src/graphicator/agents/__init__.py` | .90 |
| Graphicator `config.py` | `tool.graphicator/src/graphicator/config.py` | .85 |
| Graphicator `test_auth_copilot.py` | `tool.graphicator/tests/test_auth_copilot.py` | .95 |
| GitHub OAuth docs (device flow) | `docs.github.com/.../authorizing-oauth-apps#device-flow` | .80 |
| PydanticAI integration research | `docs/research/pydantic-ai-integration.md` C-3.3 | .90 |

## 3. Device-Flow OAuth Mechanism

**Flow:** `bearclaw auth login` -> (1) POST `github.com/login/device/code` ->
`{device_code, user_code, verification_uri}` -> (2) Display code, open browser ->
(3) Poll POST `github.com/login/oauth/access_token` -> `{access_token}` ->
(4) GET `api.github.com/copilot_internal/v2/token` with Bearer -> `{token, expires_at}`
-> Cache to `~/.owlbear/copilot_token.json`.

### 3.1 Constants

```python
COPILOT_CLIENT_ID = "Iv1.b507a08c87ecfe98"  # VS Code OAuth app (public, not secret)
DEVICE_CODE_URL = "https://github.com/login/device/code"
ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"
COPILOT_TOKEN_URL = "https://api.github.com/copilot_internal/v2/token"
DEFAULT_COPILOT_BASE = "https://api.individual.githubcopilot.com"
```

### 3.2 Editor Headers (REQUIRED — 403 without them)

```python
_EDITOR_HEADERS = {
    "Editor-Version": "vscode/1.97.1",
    "Editor-Plugin-Version": "copilot-chat/0.27.3",
    "User-Agent": "GitHubCopilotChat/0.27.3",
    "X-Github-Api-Version": "2025-04-01",
}
```

### 3.3 Integration Header (for LLM API calls, not OAuth)

```python
_COPILOT_INTEGRATION_HEADER = {"Copilot-Integration-Id": "vscode-chat"}
```

Set as `default_headers` on `AsyncOpenAI` client for chat completions.

## 4. Function Signatures

### 4.1 `auth/copilot.py` — 7 public + 2 private

| Function | Signature | Behavior |
|----------|-----------|----------|
| `_ssl_context` | `() -> ssl.SSLContext` | `truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)` |
| `_http_client` | `() -> httpx.AsyncClient` | Client with `verify=_ssl_context()`, `headers=_EDITOR_HEADERS` |
| `request_device_code` | `async () -> dict[str, Any]` | POST with `client_id`, `scope="read:user"` |
| `poll_for_access_token` | `async (device_code, interval=5, timeout=900.0) -> str` | Handles `authorization_pending` (sleep), `slow_down` (interval+=5), `TimeoutError`, `RuntimeError` |
| `exchange_for_copilot_token` | `async (access_token: str) -> dict[str, Any]` | GET with `Bearer` auth, returns `{token, expires_at}` |
| `derive_base_url` | `(token: str) -> str` | Parses `proxy-ep` from semicolon-delimited token, converts `proxy.*` -> `api.*` |
| `save_token` | `(token_data, path=None) -> None` | JSON write, creates parent dirs |
| `load_token` | `(path=None) -> dict | None` | Returns None if missing, invalid JSON, or expired (60s margin) |
| `get_copilot_token` | `async (token_path=None) -> str` | Cache-first, falls back to full device flow |

### 4.2 Agent Factory (`agents/__init__.py`)

```python
# Copilot path: AsyncOpenAI(api_key=token, base_url=derived_url,
#   default_headers={"Copilot-Integration-Id": "vscode-chat"})
# -> OpenAIProvider(openai_client=client)
# -> Agent(model=OpenAIChatModel(chat_model, provider=provider))
```

**Key:** Uses `OpenAIProvider(openai_client=client)` (not `base_url=` param)
because the `Copilot-Integration-Id` header must be on the OpenAI client.

### 4.3 Config (`config.py`)

`COPILOT_FREE_MODELS`: `frozenset({"gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano", "gpt-5-mini", "o4-mini", "text-embedding-3-small"})`.
Provider: `Literal["github_models", "copilot"]`. Token path: `~/.graphicator/copilot_token.json`.
OwlBear already has `OwlBearSettings` with `copilot_token_path: Path` and `copilot_base_url: str`.

## 5. Token Structure and Caching

**Token format:** Semicolon-delimited `key=value` pairs: `tid=<id>;proxy-ep=<host>;...`
**Response:** `{"token": "tid=...;proxy-ep=proxy.individual.githubcopilot.com;...", "expires_at": 1740000000}`
**Expiry check:** `expires_at <= time.time() + 60` (60s safety margin).
**Cache location:** `~/.owlbear/copilot_token.json` (raw JSON dump).
**Refresh:** `load_token()` returns None -> full device flow -> `save_token()`.

## 6. Test Patterns from Graphicator (13 tests)

**Mock strategy:** Patch `httpx.AsyncClient.post`/`.get` with `AsyncMock`. Lightweight `MockResponse` class with `.json()` and `.raise_for_status()`.

**Key techniques:** `asyncio.sleep` mocked to prevent delays. `time.monotonic` mocked with `side_effect=[0, 1000]` for timeout tests. `builtins.print` mocked to suppress output. `tmp_path` for all file tests.

**Tests cover:** device code request, poll (immediate/pending/slow_down/timeout/unexpected error), token exchange, save/load round-trip, expired token, missing file, cache hit, cache miss + full refresh.

**Gap:** `derive_base_url()` has NO tests in Graphicator. Task #34 must add: (1) token with proxy-ep, (2) without proxy-ep, (3) proxy-ep with scheme, (4) malformed token.

## 7. Adaptation Notes for OwlBear

| Area | Change from Graphicator |
|------|------------------------|
| Token path | `~/.graphicator/` -> `~/.owlbear/` (already in `OwlBearSettings`) |
| Config | `BaseModel + from_env()` -> `pydantic-settings BaseSettings` (already done) |
| Token path type | `str` -> `Path` (already done in `OwlBearSettings`) |
| Provider routing | Remove `github_models` branch — OwlBear is Copilot-only |
| Free models | Port `COPILOT_FREE_MODELS` as module constant or settings field |
| Entry point rename | `get_copilot_token()` -> `load_or_refresh_token()` per task #31 AC |
| Error types | Consider `CopilotAuthError(Exception)` over bare `RuntimeError` |
| Async bridge | `asyncio.run()` only in CLI (task #33), never in library code |
| `/v1` suffix | `AsyncOpenAI` appends `/v1` automatically — don't double-add |

### PydanticAI Provider Pattern (task #32)

```python
from openai import AsyncOpenAI
from pydantic_ai.providers.openai import OpenAIProvider


def create_copilot_provider(token: str, base_url: str) -> OpenAIProvider:
    client = AsyncOpenAI(
        api_key=token, base_url=f"{base_url}/v1", default_headers={"Copilot-Integration-Id": "vscode-chat"}
    )
    return OpenAIProvider(openai_client=client)
```

## 8. Recommendation (.95 confidence)

**Direct port with minimal adaptation.** Graphicator's implementation is clean,
well-tested, and already uses OwlBear's target stack (httpx + truststore + async).
Porting effort is low — primarily path/name changes and config integration.

| Risk | Mitigation |
|------|------------|
| Editor header versions go stale | Make configurable or document update process |
| `asyncio.run()` conflicts with event loop | Only use in CLI commands |

## 9. Follow-up Tasks

Tasks #31–36 already exist and cover all work. No new tasks needed.

- **#31:** See C-3, C-4 for constants, signatures, behavior
- **#32:** See C-4.2, C-7 for AsyncOpenAI + integration header
- **#33:** See C-7 for CLI structure
- **#34:** See C-6 for test patterns + derive_base_url gap
- **#35:** See C-4.2 for provider factory tests
- **#36:** See C-7 for integration verification
