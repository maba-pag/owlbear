# Cockpit Launch Command — uv run cockpit + Browser Auto-Open

> **Owning task:** #937 — P3-01: Launch command (uv run cockpit) + browser auto-open
> **Date:** 2026-04-19 **Status:** Complete

## 1. Context and Question

How to wire `uv run cockpit` to start the FastAPI server, serve the built SPA, and auto-open the browser? Key sub-questions: static file serving pattern, SPA catch-all routing, browser open timing, dist directory resolution.

## 2. Sources Studied

| Source | URL | Relevance | What Taken |
|--------|-----|-----------|------------|
| FastAPI StaticFiles docs | https://fastapi.tiangolo.com/tutorial/static-files/ | 0.9 | Mount pattern, StaticFiles constructor |
| Starlette StaticFiles source | https://github.com/encode/starlette/blob/master/starlette/staticfiles.py | 1.0 | html=True only serves index.html for directories, NOT deep routes — confirmed catch-all needed |
| Starlette StaticFiles docs | https://starlette.dev/staticfiles/ | 0.9 | `html=True` parameter, `check_dir` parameter |
| FastAPI Lifespan Events | https://fastapi.tiangolo.com/advanced/events/ | 0.7 | asynccontextmanager lifespan pattern (NOT used — browser open belongs in CLI `run()`) |
| Existing codebase: orchestrator entry point | serve/orchestrator/pyproject.toml | 0.8 | `[project.scripts]` pattern: `owlbear = "owlbear.cli:app"` |
| Existing codebase: cockpit main.py | serve/cockpit/src/owlbear_cockpit/main.py | 1.0 | Current app structure, route registration order |
| Vite build config | serve/cockpit/web/vite.config.ts | 0.8 | `outDir: '../dist'`, output structure: `dist/index.html` + `dist/assets/` |

## 3. Analysis

### Static Serving + SPA Routing

| Approach | Handles Deep Routes | Test Isolation | Complexity | KISS |
|----------|-------------------|----------------|------------|------|
| `StaticFiles(html=True)` at `/` | NO — 404s on `/tasks/123` (confirmed from source) | Poor (crashes if dist/ missing at import) | Low | ✓ |
| `StaticFiles` at `/assets/` + catch-all `/{path:path}` | YES | Good (if conditional in `run()`) | Medium | ✓ |
| Custom middleware | YES | Good | High | ✗ |

**Winner:** Option 2 — StaticFiles for known asset paths + catch-all route for SPA.

### Browser Auto-Open Timing

| Approach | Reliability | Test Safety | Complexity |
|----------|-------------|-------------|------------|
| `threading.Timer(1.0)` in `run()` | Good (server starts in <500ms) | Safe (only called from CLI) | Low |
| Health-poll loop in thread | Excellent | Safe | Medium |
| Lifespan event | Poor (fires before accept) | Unsafe (triggers in TestClient) | Low |

**Winner:** `threading.Timer(1.0)` — pragmatic for a local-only dev tool. Timer is a daemon thread that won't block shutdown.

### dist_dir Resolution

| Approach | Works in uv workspace | Works if published | Complexity |
|----------|----------------------|-------------------|------------|
| `Path(__file__).resolve().parents[2] / "dist"` | YES (editable install) | NO | Low |
| `importlib.resources` | YES | YES | Medium |
| Environment variable | YES | YES | Low but manual |

**Winner:** `__file__`-relative — package is workspace-only, never published. The `sys.exit(1)` guard catches misconfiguration immediately.

### Route Ordering (verified from Starlette Router source)

FastAPI/Starlette checks routes in registration order. Specific routes match before parameterized ones:
1. `/api/*` (include_router) — matches API calls
2. `/health` (app.get) — matches health checks
3. `/assets/` (app.mount StaticFiles) — matches static assets
4. `/{path:path}` (app.get catch-all) — everything else → index.html

No shadowing when catch-all is registered LAST.

## 4. Recommendation

**Confidence: 0.85**

Implementation pattern:
1. Add `[project.scripts]` entry: `cockpit = "owlbear_cockpit.main:run"`
2. Add `run()` function that dynamically mounts static serving + catch-all BEFORE starting uvicorn
3. Static routes are CLI-time concern, not module-import concern → test isolation preserved
4. `threading.Timer(1.0, webbrowser.open, [url]).start()` as daemon thread before `uvicorn.run()`
5. `COCKPIT_PORT` env var (default: 8420), `COCKPIT_NO_OPEN` env var to suppress browser

Challenge: reconsider (challenger confidence 0.55) — key challenges:
- `__file__` fragility for dist_dir → Rebutted: workspace-only + sys.exit guard
- `StaticFiles(html=True)` as alternative → Rebutted: confirmed from source that it 404s deep routes
- Route shadowing concerns → Rebutted: registration order is deterministic, catch-all last
- Accepted: static routes conditional in `run()` (not at module level) for test isolation

## 5. Follow-up Tasks

- Task at `todo` status for implementation (this task itself advances to backlog for arch review)
