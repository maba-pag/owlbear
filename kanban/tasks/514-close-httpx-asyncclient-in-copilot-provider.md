---
id: 514
title: Close httpx.AsyncClient in Copilot provider
status: backlog
priority: important
created: 2026-03-04T07:38:25.3834342+01:00
updated: 2026-03-06T23:54:11.8002498+01:00
started: 2026-03-06T23:49:40.5848276+01:00
tags:
    - audit
    - resilience
    - auth
class: standard
---

C-4: providers/copilot.py creates httpx.AsyncClient passed to AsyncOpenAI but never closes it. Leaks connection pool for daemon lifetime.

## AC
- httpx.AsyncClient created in create_copilot_client is closed on daemon shutdown
- Auth refresh in daemon.py closes the old client before replacing it
- All existing tests pass

## Research findings (2026-03-06)

### 1. Theoretical validity
Sound fix. httpx docs require explicit aclose() for long-lived clients. AsyncOpenAI.close() delegates to http_client.aclose(). Without it, the TCP connection pool leaks for the daemon lifetime. Auth refreshes (daemon.py L279) create additional unclosed clients.

### 2. Prior art
- httpx docs: 'Make sure to close the client... await client.aclose()' (https://www.python-httpx.org/async/#opening-and-closing-clients)
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
