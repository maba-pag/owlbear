# SSE Endpoint Implementation: watchfiles + sse-starlette

> **Owning task:** #1234 — Implement SSE endpoint with watchfiles-based file watcher
> **Date:** 2026-05-01 **Status:** Complete

## 1. Context and Question

Task #1233 concluded that SSE with invalidation-only events + watchfiles-based file watcher is the right transport for real-time cockpit updates (confidence: 0.78). This task researches the implementation details: API surface, dependency wiring, error handling, shutdown cleanup, testing strategy.

Scoped to backend only — frontend EventSource integration is #1235.

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | pypi.org/project/sse-starlette (v3.4.1) | Library docs | 0.9 |
| 2 | watchfiles.helpmanual.io (v1.1.1) — awatch API | Library docs | 0.9 |
| 3 | serve/cockpit/src/ (main, routes, deps, cache) | Live codebase | 1.0 |
| 4 | serve/kanban/src/owlbear_kanban/storage_io.py | Atomic write pattern (.tmp-) | 0.8 |
| 5 | serve/cockpit/web/src/hooks/usePolling*.ts | Frontend polling contract | 0.7 |
| 6 | .owlbear/research/1233-realtime-cockpit-updates.md | Parent research | 1.0 |

## 3. Analysis

### 3.1 Implementation Pattern

```python
# routes/events.py (~35 LOC)
@router.get("/events")
async def events(request: Request, engine=Depends(get_engine)):
    async def event_generator():
        tasks_dir = engine.tasks_dir
        if not tasks_dir.exists():
            return  # No dir = no events; client falls back to polling

        async for changes in awatch(
            tasks_dir,
            watch_filter=lambda change, path: path.endswith(".md") and not Path(path).name.startswith(".tmp-"),
            recursive=False,
            stop_event=stop_event,  # set on shutdown
        ):
            if await request.is_disconnected():
                break
            mtime = max(p.stat().st_mtime_ns for _, p in changes if Path(p).exists())
            yield {"event": "tasks-changed", "data": json.dumps({"mtime": mtime})}

    return EventSourceResponse(event_generator())
```

### 3.2 Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Watcher scope | Per-connection | KISS; localhost single-user; 1-3 connections max; no shared state |
| Watch filter | `.md` only, exclude `.tmp-*` | Matches storage.py scan; prevents events from atomic write temps |
| Recursive | False | Tasks are flat .md files, no subdirs |
| Debounce | 1600ms (watchfiles default) | Groups rapid writes; still 2× faster than current 3s poll |
| Event model | Invalidation-only | Preserves existing fetch contract; no new response models |
| Mtime source | Actual file mtime_ns from changed files | Matches existing /api/tasks mtime semantics |
| Missing-dir handling | Return immediately (empty generator) | Client falls back to 3s polling; no crash |
| Shutdown cleanup | sse-starlette CancelledError + stop_event | Library handles SIGTERM gracefully |
| Auth | None (matches existing cockpit: localhost-only, no auth) | Consistent with current API surface |

### 3.3 Dependency Impact

| Package | Version | Size | Transitive deps | Already in lock? |
|---------|---------|------|-----------------|------------------|
| sse-starlette | 3.4.1 | 16.5 KB wheel | 0 (starlette already present) | Yes (via MCP) |
| watchfiles | 1.1.1 | ~2 MB wheel (Rust binary) | anyio (already present) | No — new |

Both must be added to `serve/cockpit/pyproject.toml` explicitly.

### 3.4 Risk Matrix

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| watchfiles Rust wheel unavailable for platform | Low | High | Pre-built wheels for macOS arm64/x64, Linux x64/arm64 |
| Dir-missing at subscribe time | Low | Medium | Guard: empty generator, client polls normally |
| Watcher thread leak on unclean shutdown | Medium | Low | sse-starlette cancels generator; stop_event halts awatch |
| Excessive watchers from many tabs | Low | Low | Social limit; optional Semaphore(10) guard for defense |
| Temp-file events causing spurious refreshes | Medium | Low | watch_filter excludes .tmp-* prefix |

### 3.5 Testing Strategy

| Test type | Approach |
|-----------|----------|
| Unit: event emission | Mock `awatch` to yield synthetic changes; assert SSE events contain correct mtime |
| Unit: disconnect cleanup | Start stream, close client, assert generator terminates cleanly |
| Unit: missing-dir | Engine with nonexistent tasks_dir → endpoint returns 200 with no events |
| Integration: file write triggers event | Write .md to temp dir, verify event arrives within 2s |
| Unit: tmp-file filter | Trigger .tmp- file creation → no event emitted |

Use `httpx.AsyncClient` with `stream("GET", "/api/events")` for SSE testing. Mock `awatch` via dependency injection or module-level patch.

## 4. Recommendation

Proceed with implementation as described. The pattern is ~35 LOC, uses well-maintained libraries, and preserves all existing contracts.

**Confidence: 0.75**

Challenge: reconsider — confidence in original: 0.64. Challenger identified valid gaps in missing-dir handling, shutdown lifecycle, temp-file filtering, and dependency grounding. All addressed in §3.2 design decisions table. Core approach (per-connection watcher + invalidation-only events) was not disputed.

## 5. Follow-up Tasks

1. #1234 itself → advance to backlog (implementation task — backend SSE endpoint)
2. Frontend EventSource integration → #1235 (already exists as sibling)
