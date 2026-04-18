---
id: 937
title: 'P3-01: Launch command (uv run cockpit) + browser auto-open'
status: research
priority: important
created: 2026-04-17T19:59:26.716250+00:00
updated: 2026-04-17T19:59:26.716250+00:00
tags:
- cockpit
- backend
- phase-3
- type:build
parent: 920
depends_on:
- 934
- 936
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #920

## Objective

Wire `uv run cockpit` to start the FastAPI server serving the built SPA and auto-open the browser.

## Acceptance Criteria

- [ ] `pyproject.toml` script entry: `cockpit = "owlbear_cockpit.main:run"` (or equivalent CLI entry point)
- [ ] `uv run cockpit` starts uvicorn on `127.0.0.1:{port}` (default port: 8420 or configurable via `COCKPIT_PORT` env var)
- [ ] FastAPI mounts `/api/` routes + static file handler serving SPA from `dist/` directory
- [ ] Catch-all route for client-side routing (non-API paths serve `index.html`)
- [ ] Browser auto-opens to `http://127.0.0.1:{port}/` on startup (webbrowser module)
- [ ] Graceful shutdown on Ctrl+C (uvicorn default)
- [ ] Error message if `dist/` directory is missing (frontend not built)

## Files

- `serve/cockpit/src/owlbear_cockpit/main.py` (updated with run function + static mount)
- `serve/cockpit/pyproject.toml` (script entry)