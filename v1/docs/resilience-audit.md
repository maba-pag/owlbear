# OwlBear Resilience Engineering Audit

> **Date:** 2026-03-03  **Status:** Complete

## Executive Summary

OwlBear has a **solid resilience foundation** — error classification (`ErrorCategory`), structured error feedback (`ToolError`), hook-based lifecycle events, escalation to the user, and two retry layers (HTTP transport + tool-level). Browser cleanup is exemplary. However, this audit identifies **3 CRITICAL**, **5 HIGH**, **5 MEDIUM**, and **4 LOW** findings. The most alarming gaps: (1) `ErrorJournal` is defined but never wired into the daemon or any agent flow, (2) most `httpx.AsyncClient()` calls lack timeouts, and (3) SQLite connections opened in `bootstrap.py` are never closed.

---

## Findings

### 1. Retry Patterns

| ID | Sev | Title | Evidence |
|----|-----|-------|----------|
| R-1 | INFO | Two well-placed retry layers | `providers/copilot.py` L57-69 (HTTP transport, 3 attempts, exp backoff, Retry-After), `tools/hooked.py` L127-134 (tool-level, 3 attempts, transient-only) |
| R-2 | HIGH | Copilot transport retries only `HTTPStatusError`, not connection errors | `providers/copilot.py` L58: `retry=retry_if_exception_type(httpx.HTTPStatusError)`. `ConnectError`, `TimeoutException` bypass retry entirely. If the Copilot API is briefly unreachable, the first request fails permanently. |
| R-3 | MEDIUM | Daemon's manual retry duplicates tool-level retry with different parameters | `daemon.py` L190-225 reimplements exp backoff (3 retries, base 1s) while `HookedToolset` already retries transient errors (3 attempts, base 0.5s). The daemon retry wraps `agent.turn()`, which includes tool calls — so transient tool errors get 3×3=9 total attempts. |
| R-4 | HIGH | Auth, GitHub, Slack, intake, web_search — zero retry on external calls | `auth/copilot.py` (3 HTTP calls, no retry), `tools/github_api.py` (4 endpoints, no retry), `channels/slack.py` (`chat_postMessage`, no retry), `memory/knowledge/intake.py:read_url` (no retry), `tools/web_search.py:_web_read` (no retry) |
| R-5 | MEDIUM | Doc says "max 5 attempts" but code uses max 3 | `python.instructions.md` L27: "max 5 attempts". `providers/copilot.py` L59: `stop_after_attempt(3)`. `tools/hooked.py` L129: `stop_after_attempt(3)`. `daemon.py` L168: `_TRANSIENT_MAX_RETRIES = 3`. Inconsistent with documented convention. |

### 2. Exception Hierarchy

| ID | Sev | Title | Evidence |
|----|-----|-------|----------|
| E-1 | LOW | Flat exception hierarchy — only 3 custom exceptions | `BlockedCommandError`, `BlockedURLError`, `AskUserTimeoutError`. No `OwlBearError` base class. Makes blanket catching difficult without `Exception`. |
| E-2 | INFO | `ErrorCategory` enum is well-designed | `core/errors.py` L37-50: 4 clear categories (TRANSIENT, AUTH, PERMANENT, TOOL_SEMANTIC) with pure classifier function — good. |

### 3. Error Propagation

| ID | Sev | Title | Evidence |
|----|-----|-------|----------|
| P-1 | MEDIUM | 30+ broad `except Exception` catches across codebase | `bootstrap.py` (6 occurrences), `ingest.py` (5), `tools/` (multiple). All annotated `# noqa: BLE001` indicating deliberate choice, but many silently return `None` without logging context about *what* failed. |
| P-2 | HIGH | `_recover_from_error` swallows all exceptions in PERMANENT path | `daemon.py` L232-233: `logger.exception("Error processing message")` + `channel.send(f"Error: {exc}")`. If `channel.send` itself fails, the error is silently lost — no journal entry, no re-raise. |
| P-3 | LOW | Hook handlers swallow exceptions by design | `core/hooks.py` L88-93: Intentional — one bad handler won't block others. Acceptable trade-off, but errors in critical hooks (escalation, observability) only appear in logs. |

### 4. Graceful Degradation

| ID | Sev | Title | Evidence |
|----|-----|-------|----------|
| D-1 | INFO | Knowledge, bookmark, web_search toolsets degrade gracefully | `bootstrap.py` L348/436/452: Each returns `None` on failure, logged at WARNING. Agent continues without the capability. Good pattern. |
| D-2 | MEDIUM | Ingest pipeline partial-success model is sound | `ingest.py` L626-636: Returns `"partial"` when embed succeeds but extract fails (or vice versa). Good. |
| D-3 | LOW | `web_search` returns user-friendly error strings instead of raising | `web_search.py` L192-197: `"Timeout fetching {url}"`, `"HTTP {status}: {url}"`. Good for LLM consumption. |

### 5. Resource Cleanup

| ID | Sev | Title | Evidence |
|----|-----|-------|----------|
| C-1 | CRITICAL | SQLite connections opened in `bootstrap.py` are never closed | `bootstrap.py` L298: `conn = sqlite3.connect(...)` — passed to `GraphStore`, `IngestPipeline`, etc. No `conn.close()` in any cleanup path. `BootstrapResult.cleanup` list exists but no SQLite cleanup is registered. Leaked FDs accumulate over daemon lifetime. |
| C-2 | HIGH | `_build_bookmark_toolset` opens a *second* SQLite connection to the same DB | `bootstrap.py` L403: Another `sqlite3.connect(str(db_path))` for bookmark pipeline. Two unmanaged connections to the same file with no coordination. Risk of WAL contention and lock errors under concurrent writes. |
| C-3 | INFO | Browser cleanup is exemplary | `tools/browser/manager.py` L121-157: Nested try/finally chain ensures page→context→browser→Playwright are closed in order regardless of exceptions. |
| C-4 | MEDIUM | `providers/copilot.py` creates an `httpx.AsyncClient` that is never closed | `providers/copilot.py` L85: `http_client = httpx.AsyncClient(transport=transport)` — passed to `AsyncOpenAI`. No `close()` or context manager. Leaks the underlying connection pool for the daemon's lifetime. |

### 6. Timeout Handling

| ID | Sev | Title | Evidence |
|----|-----|-------|----------|
| T-1 | CRITICAL | `auth/copilot.py` HTTP calls have no timeout | `auth/copilot.py` L73-78 (`request_device_code`), L135-142 (`exchange_for_copilot_token`): `httpx.AsyncClient()` default timeout is 5s for connect, but stream reads can hang indefinitely. On a corporate proxy, device-flow calls can block forever. |
| T-2 | CRITICAL | `tools/github_api.py` — all 4 API calls have no timeout | `github_api.py` L176/200/227/248: `httpx.AsyncClient()` with no timeout kwarg. GitHub API slowdowns block agent indefinitely. |
| T-3 | HIGH | `memory/knowledge/intake.py:read_url` has no timeout | `intake.py` L52: `httpx.AsyncClient()` with no timeout. Ingesting a slow URL blocks the pipeline indefinitely. |
| T-4 | LOW | `web_search.py:_web_read` correctly sets `timeout=30` | `web_search.py` L194: Good — one of the few callers that sets an explicit timeout. |
| T-5 | MEDIUM | `Slack.receive` timeout returns `None` but caller loops forever | `channels/slack.py` L224-228: `asyncio.wait_for(..., timeout=self._receive_timeout)` returns `None` on timeout. But `daemon.py` L296-298: `message = await channel.receive()` — `None` triggers shutdown. This is correct for CLI but may cause premature daemon exit on Slack idle periods. |

### 7. Error Recovery (ErrorJournal)

| ID | Sev | Title | Evidence |
|----|-----|-------|----------|
| J-1 | HIGH | `ErrorJournal` is never instantiated or wired | `memory/error_journal.py` defines class. `grep ErrorJournal src/` returns only the definition file — zero imports, zero usage in `bootstrap.py`, `daemon.py`, or any agent. The entire error learning system is dead code. |
| J-2 | MEDIUM | `ErrorJournal` is synchronous file I/O in an async daemon | `error_journal.py` L67-73: `self._path.open("a")` is blocking I/O. In the daemon's async event loop, journal writes will block the loop during rotation of 10K entries. |

### 8. Circuit Breaker Patterns

| ID | Sev | Title | Evidence |
|----|-----|-------|----------|
| CB-1 | MEDIUM | No circuit breakers anywhere | `grep circuit.?breaker src/` returns zero matches. If the Copilot API returns 503 for 10 minutes, every agent turn burns 3 retries × backoff before failing. No "open circuit" to fast-fail. For an always-on daemon, this means cascading delays. |

### 9. Idempotency

| ID | Sev | Title | Evidence |
|----|-----|-------|----------|
| I-1 | INFO | Ingest pipeline has content-hash dedup | `ingest.py` L197-219: `check_content_changed()` + `compute_content_hash()` — safe to re-ingest same document. Good. |
| I-2 | INFO | Qdrant upsert is idempotent | `qdrant.py` uses deterministic `uuid5` point IDs and `upsert`. Safe to retry. |
| I-3 | LOW | `ErrorJournal.log()` is append-only — duplicate entries on retry | `error_journal.py` L62-75: No dedup key. If daemon retry writes a log entry, then retries the same operation and writes again, duplicates accumulate. Minor since journal is never wired (J-1). |

### 10. Cascading Failures

| ID | Sev | Title | Evidence |
|----|-----|-------|----------|
| CF-1 | MEDIUM | Background tasks in ingest can accumulate silently | `ingest.py` L512-514: `asyncio.create_task(...)` stored in `_background_tasks` set. Task failures are caught (`BLE001`) but many concurrent ingests could spawn unlimited background tasks. No semaphore or concurrency limit. |
| CF-2 | LOW | Daemon `_recover_from_error` can itself fail if channel is dead | `daemon.py` L231-233: Recovery sends error to channel. If Slack WebSocket is disconnected, `channel.send()` raises. The outer `try/except BLE001` in the daemon loop catches it, but the chain `turn fails → recovery fails → loop continues silently` means errors disappear. |

---

## Risk Matrix

| ID | Finding | Probability | Impact | Risk |
|----|---------|-------------|--------|------|
| C-1 | SQLite connections never closed | **Certain** | High (FD leak, eventual crash) | **CRITICAL** |
| T-1 | Auth HTTP calls no timeout | High (corporate proxies) | High (daemon hangs) | **CRITICAL** |
| T-2 | GitHub API no timeout | High (API degradation) | High (agent blocks) | **CRITICAL** |
| J-1 | ErrorJournal dead code | Certain | High (no error learning) | **HIGH** |
| R-2 | Transport retries skip ConnectError | Medium | High (single-failure kill) | **HIGH** |
| R-4 | Multiple external calls unretried | High | Medium (transient failures pass through) | **HIGH** |
| P-2 | Daemon swallows PERMANENT errors | Medium | Medium (silent failures) | **HIGH** |
| C-2 | Duplicate SQLite connections | Medium | Medium (lock contention) | **HIGH** |
| C-4 | httpx client never closed | Certain | Low (slow leak) | **MEDIUM** |
| CB-1 | No circuit breakers | Medium | Medium (cascading delays) | **MEDIUM** |

---

## Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Fix: Add explicit timeouts to all httpx.AsyncClient calls" --status backlog --priority critical --tags "resilience,config,phase-13" --body "Add timeout=httpx.Timeout(10, connect=5) to: auth/copilot.py (3 calls), tools/github_api.py (4 calls), memory/knowledge/intake.py:read_url, tools/browser/launcher.py, tools/browser/url_utils.py. Evidence: audit findings T-1, T-2, T-3."

kanban\kanban-md.exe create "Fix: Close SQLite connections in bootstrap cleanup" --status backlog --priority critical --tags "resilience,config,phase-13" --body "Register conn.close() in BootstrapResult.cleanup for knowledge and bookmark connections. Consider a shared connection factory. Evidence: audit findings C-1, C-2."

kanban\kanban-md.exe create "Fix: Add ConnectError/TimeoutException to Copilot transport retry" --status backlog --priority needed --tags "resilience,auth,phase-13" --body "In providers/copilot.py, _validate_transient_response only raises for status codes. Add retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)) alongside HTTPStatusError. Evidence: audit finding R-2."

kanban\kanban-md.exe create "Wire ErrorJournal into daemon loop and agent error paths" --status backlog --priority needed --tags "resilience,agent,phase-13" --body "ErrorJournal exists but is never instantiated. Wire it: (1) create in bootstrap, (2) log from daemon._recover_from_error, (3) expose query via agent toolset. Evidence: audit finding J-1."

kanban\kanban-md.exe create "Add retry decorators to GitHub API, Slack send, and intake.read_url" --status backlog --priority needed --tags "resilience,tooling,phase-13" --body "Wrap external calls with tenacity retry (transient errors only, 3 attempts, exp backoff). Specifically: github_api.py (4 methods), channels/slack.py (chat_postMessage), memory/knowledge/intake.py (read_url). Evidence: audit finding R-4."

kanban\kanban-md.exe create "Implement circuit breaker for Copilot API" --status backlog --priority important --tags "resilience,agent,phase-13" --body "Add a lightweight circuit breaker (half-open after 60s, trip after 5 consecutive failures) around Copilot API calls. Consider tenacity + custom state or a simple class. Evidence: audit finding CB-1."

kanban\kanban-md.exe create "Establish OwlBearError base exception hierarchy" --status backlog --priority nice-to-have --tags "resilience,config,phase-13" --body "Create OwlBearError base class. Subclass BlockedCommandError, BlockedURLError, AskUserTimeoutError from it. Enables except OwlBearError instead of broad except Exception. Evidence: audit finding E-1."

kanban\kanban-md.exe create "Close httpx.AsyncClient in providers/copilot.py" --status backlog --priority important --tags "resilience,auth,phase-13" --body "The AsyncClient created for OpenAI is never closed. Either register close() in bootstrap cleanup or restructure as async context manager. Evidence: audit finding C-4."

kanban\kanban-md.exe create "Make ErrorJournal async-safe with aiofiles or run_in_executor" --status backlog --priority nice-to-have --tags "resilience,config,phase-13" --body "ErrorJournal uses blocking file I/O. In the async daemon loop, rotation of 10K entries blocks the event loop. Use aiofiles or asyncio.to_thread for log/rotate. Evidence: audit finding J-2."

kanban\kanban-md.exe create "Align retry max attempts: docs say 5, code uses 3" --status backlog --priority nice-to-have --tags "resilience,docs,phase-13" --body "python.instructions.md says 'max 5 attempts' but all retry code uses 3. Either update docs to 3 or code to 5. Evidence: audit finding R-5."
```

## Attribution

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| OwlBear codebase | (local) | Direct code audit of 14 source files | This audit document | 2026-03-03 |
| httpx docs — Timeouts | <https://www.python-httpx.org/advanced/timeouts/> | Default timeout behavior reference | Findings T-1 through T-3 | 2026-03-03 |
| tenacity docs | <https://tenacity.readthedocs.io/en/latest/> | Retry pattern best practices | Findings R-1 through R-5 | 2026-03-03 |
