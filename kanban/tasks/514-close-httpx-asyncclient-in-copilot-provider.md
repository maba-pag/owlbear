---
id: 514
title: Close httpx.AsyncClient in Copilot provider
status: todo
priority: important
created: 2026-03-04T07:38:25.3834342+01:00
updated: 2026-03-09T22:59:48.6062564+01:00
started: 2026-03-06T23:49:40.5848276+01:00
tags:
    - audit
    - resilience
    - auth
depends_on:
    - 650
class: standard
---

C-4: providers/copilot.py creates httpx.AsyncClient passed to AsyncOpenAI but never closes it. Leaks connection pool for daemon lifetime.

## AC

### Sub-problem 1: Bootstrap registers AsyncOpenAI client for cleanup

- `bootstrap()` in bootstrap.py calls `create_copilot_client(settings)` directly (not `create_copilot_model`) to obtain the `AsyncOpenAI` client
- `bootstrap()` builds the `OpenAIProvider` and `OpenAIChatModel` inline (same 3 lines currently in `create_copilot_model`)
- `cleanup.append(openai_client.close)` is called in `bootstrap()` — follows the `GitHubToolset.aclose` / `infra.conn.close` precedent
- `create_copilot_model()` remains unchanged for external/test callers — no breaking change

### Sub-problem 2: Cleanup loop awaits async callables

- The cleanup loop in cli.py `_run()` (currently `cb()` without await) uses `inspect.isawaitable()` on the return value to await async callables
- Pattern: `result = cb(); if inspect.isawaitable(result): await result`
- `_chat_async()` in cli.py also runs `result.cleanup` in a `finally` block (currently missing — second leak vector)
- `BootstrapResult.cleanup` docstring already says "sync and async callables" — implementation now matches the contract

### Sub-problem 3: Daemon auth refresh closes old client

- `_handle_classified_error` AUTH branch in daemon.py calls `await old_client.close()` (or equivalent) before `agent.update_model(new_model)`
- The old `AsyncOpenAI` client is obtained from the model's provider before replacement (e.g. `agent.inner.model.client` or passed through a closure/attribute)
- If accessing the old client from the model is not feasible via public API, an alternative is to store a reference to the current `AsyncOpenAI` client as an attribute on `OwlBearAgent` (e.g. `agent._openai_client`) set during bootstrap, updated on auth refresh

### General

- All existing tests pass (no regressions)
- `uv run ruff check src/ tests/` clean
- No new module-level mutable state — client reference flows through bootstrap wiring or agent attribute
- Module layering respected: daemon.py (assembly layer) may import from providers/copilot.py

## Architecture notes

- **Pattern precedent:** `GitHubToolset.aclose()` registered in `build_toolsets` cleanup list (#507). Same pattern for OpenAI client.
- **Module touch points:** copilot.py (no change), bootstrap.py (inline model build + register cleanup), cli.py (await async cleanup + add chat cleanup), daemon.py (close old client on auth refresh)
- **Cleanup loop fix scope:** The `inspect.isawaitable` guard is the minimal fix. An alternative (asyncio.iscoroutine) is less correct because `.close()` returns a coroutine, not necessarily an awaitable wrapper. `inspect.isawaitable` covers both.
- **Chat cleanup gap:** `_chat_async` never runs cleanup — this is a pre-existing bug exposed by this task. Fixing it here is correct scope because without it, the registered cleanup callable would never execute in chat mode.

## Research findings (2026-03-06)

Preserved below for reference — see original research in task history.

### 1. Theoretical validity

Sound fix. httpx docs require explicit aclose() for long-lived clients. AsyncOpenAI.close() delegates to http_client.aclose(). Without it, the TCP connection pool leaks for the daemon lifetime. Auth refreshes (daemon.py L279) create additional unclosed clients.

### 2. Prior art

- httpx docs: 'Make sure to close the client... await client.aclose()' (<https://www.python-httpx.org/async/#opening-and-closing-clients>)
- openai-python: AsyncOpenAI.close() is async, calls self._client.aclose()
- OwlBear precedent: infra.conn.close registered in BootstrapResult.cleanup (bootstrap.py L654)

### 3. Technical feasibility

Two sub-problems:
(a) Expose the AsyncOpenAI client so bootstrap can register cleanup. Currently create_copilot_model() returns only OpenAIChatModel. Fix: return (model, client) tuple, or call create_copilot_client() directly in bootstrap and build the model there.
(b) Cleanup loop is sync-only (cli.py L1105: cb() without await), but AsyncOpenAI.close() is async. BootstrapResult.cleanup docstring says 'sync and async callables' but the loop never awaits. Fix: inspect.isawaitable(result) guard in cleanup loop; the loop already runs inside async def _run().
(c) Auth refresh (daemon.py L279) creates a new model without closing the old client. Fix: agent.update_model() should close the old OpenAI client, or daemon code should close it explicitly before replacement.

### 4. Architecture fit

Matches existing cleanup pattern exactly. Only 3 touch points: copilot.py (expose client), bootstrap.py (register cleanup), cli.py (await async callbacks). daemon.py auth refresh is a bonus fix.

### 5. Implementation approach

**Recommended (.90 confidence):** Restructure bootstrap to call create_copilot_client() directly:

`
openai_client = await create_copilot_client(settings)
cleanup.append(openai_client.close)
provider = OpenAIProvider(openai_client=openai_client)
model = OpenAIChatModel(settings.chat_model, provider=provider)
`

Fix cleanup loop (cli.py):
`
result = cb()
if inspect.isawaitable(result):
    await result
`

Fix daemon auth refresh to close old client before replacement.

create_copilot_model() can remain for external/test callers (no breaking change).

[[2026-03-09]] Mon 22:00
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| SP1: bootstrap calls create_copilot_client | bootstrap/__init__.py L85: still calls create_copilot_model | FAIL |
| SP1: Inline model build + cleanup.append | No cleanup registration found in bootstrap | FAIL |
| SP1: create_copilot_model unchanged | copilot.py L127-148: unchanged | PASS |
| SP2: Cleanup loop isawaitable | cli.py L975-977, L1085-1088: implemented | PASS |
| SP2: _chat_async finally cleanup | cli.py L972-977: implemented | PASS |
| SP3: AUTH closes old client | daemon.py L373-375: implemented | PASS |
| SP3: _openai_client updated | daemon.py L384: implemented | PASS |
| SP3: _openai_client set at bootstrap | Never set  only on refresh | FAIL |

### Test Results
- pytest: 1334 passed, 1 failed (PermissionError in test_context_hydration, env issue not #514-related), 2 skipped
- ruff: clean on all 4 task files

### Confidence: .65
### Action: reject to backlog

Core issue: Sub-problem 1 (bootstrap cleanup registration) is entirely unimplemented. bootstrap() still calls create_copilot_model() which hides the AsyncOpenAI client. No cleanup.append(openai_client.close). Agent._openai_client never set at bootstrap so first auth refresh also fails to close original client.

[[2026-03-09]] Mon 22:00
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| SP1: bootstrap calls create_copilot_client | bootstrap/__init__.py L85: still calls create_copilot_model | FAIL |
| SP1: Inline model build + cleanup.append | No cleanup registration found in bootstrap | FAIL |
| SP1: create_copilot_model unchanged | copilot.py L127-148: unchanged | PASS |
| SP2: Cleanup loop isawaitable | cli.py L975-977, L1085-1088: implemented | PASS |
| SP2: _chat_async finally cleanup | cli.py L972-977: implemented | PASS |
| SP3: AUTH closes old client | daemon.py L373-375: implemented | PASS |
| SP3: _openai_client updated | daemon.py L384: implemented | PASS |
| SP3: _openai_client set at bootstrap | Never set  only on refresh | FAIL |

### Test Results
- pytest: 1334 passed, 1 failed (PermissionError in test_context_hydration, env issue not #514-related), 2 skipped
- ruff: clean on all 4 task files

### Confidence: .65
### Action: reject to backlog

Core issue: Sub-problem 1 (bootstrap cleanup registration) is entirely unimplemented. bootstrap() still calls create_copilot_model() which hides the AsyncOpenAI client. No cleanup.append(openai_client.close). Agent._openai_client never set at bootstrap so first auth refresh also fails to close original client.

[[2026-03-09]] Mon 22:59
## Architecture Review
**Verdict:** APPROVED (with refinement)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| SP1: bootstrap calls create_copilot_client | Clear, verifiable | Keep |
| SP1: inline model build | Clear, verifiable | Keep |
| SP1: cleanup.append(openai_client.close) | Clear, follows GitHubToolset precedent | Keep |
| SP1: create_copilot_model unchanged | Clear, no-break constraint | Keep |
| **SP1: agent._openai_client set at bootstrap** | **MISSING -- auditor flagged. Without this, daemon SP3 gets None on first auth refresh** | **ADDED** |
| SP2: cleanup loop isawaitable | Already implemented in codebase | Verify only |
| SP2: _chat_async cleanup | Already implemented | Verify only |
| SP3: AUTH closes old client | Already implemented | Verify only |
| SP3: _openai_client updated on refresh | Already implemented | Verify only |
| General: tests pass, ruff clean, no mutable state, layering | Standard gates | Keep |

### Architecture Notes
- SP2 and SP3 are already implemented from prior build cycle. Builder: verify, do not rewrite.
- Remaining work is SP1 only: replace bootstrap/__init__.py L87 create_copilot_model with 4-line inline build + cleanup registration + agent attribute assignment.
- Pattern precedent: GitHubToolset.aclose() registered in build_toolsets cleanup list.
- Module layering: bootstrap (assembly) calls create_copilot_client from providers -- correct direction.
- _openai_client as post-construction attribute is pragmatic. Do not add to OwlBearAgent.__init__ (YAGNI).

### AC Refinement
Added to Sub-problem 1 (4th bullet, before create_copilot_model line):
- After agent construction, bootstrap sets `agent._openai_client = openai_client` so daemon auth refresh (SP3) can close the original client on first rotation

### Dependencies
- Verified: depends_on [650] (test task) -- in review status, needs AC#1 test fixed first
- No new dependencies needed
