---
id: 31
title: 'P4-03: Port Copilot OAuth device-flow module'
status: done
priority: high
created: 2026-02-24T15:15:36.029406+01:00
updated: 2026-02-26T21:54:08.5291096+01:00
started: 2026-02-26T21:21:58.0975781+01:00
completed: 2026-02-26T21:54:08.5291096+01:00
tags:
    - phase-4
    - auth
depends_on:
    - 30
    - 7
class: standard
---

AC: Create src/owlbear/auth/copilot.py ported from Graphicator. Include: (1) COPILOT_CLIENT_ID constant (VS Code OAuth app), (2) request_device_code() async function, (3) poll_for_access_token() with authorization_pending/slow_down handling, (4) exchange_for_copilot_token() via api.github.com/copilot_internal/v2/token, (5) derive_base_url() parsing proxy-ep from token, (6) _EDITOR_HEADERS dict (Editor-Version, Editor-Plugin-Version, User-Agent, X-Github-Api-Version), (7) Token caching to ~/.owlbear/copilot_token.json with 60s safety margin on expiry, (8) load_or_refresh_token() convenience function. Use httpx for HTTP, truststore for SSL. Adapt all paths from graphicator to owlbear. Type hints on all functions. from __future__ import annotations. File: src/owlbear/auth/copilot.py
