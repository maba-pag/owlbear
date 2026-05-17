---
id: 9e953ab2-5e1b-49bf-82ba-b70bbfa6fb93
title: VS Code pytest fallback may need explicit plugins
categories:
- pitfall
- tool-usage
- env-context
confidence: 0.86
state: deleted
scope_agents:
- builder
- reviewer
- test-writer
source_agent: copilot
created_at: '2026-05-17T01:34:22.486614Z'
updated_at: '2026-05-17T03:04:16.874947Z'
approved_at: null
---

Some VS Code terminal sessions set `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, hiding plugins such as xdist, cov, asyncio, and timeout while repo addopts still reference them. If fallback pytest is needed, run `.venv/bin/pytest` with explicit `-p` plugin loads instead of assuming packages are missing.
