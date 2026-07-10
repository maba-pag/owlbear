---
id: 9b49127d-8575-493a-9d4b-b542ab867d57
title: Playwright route handlers are LIFO
categories:
- pitfall
- tool-usage
- domain-knowledge
confidence: 0.9
state: approved
scope_agents:
- builder
- verifier
source_agent: copilot
created_at: '2026-05-17T01:34:35.497571Z'
updated_at: '2026-05-17T03:13:27.704406Z'
approved_at: '2026-05-17T03:13:27.704415Z'
---

Playwright `page.route()` handlers are matched last-in-first-out. Register broad catch-all routes such as `/api/**` before registering specific stubs, or the catch-all can override the specific route and make the app receive empty or wrong API responses.
