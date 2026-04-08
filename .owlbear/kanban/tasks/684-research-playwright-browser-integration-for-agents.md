---
id: 684
title: 'Research: Playwright browser integration for agents'
status: research
priority: nice-to-have
created: 2026-04-08T19:18:22.1617576+02:00
updated: 2026-04-08T19:18:22.1617576+02:00
tags:
    - scope:tools
    - ' type:research'
    - ' source:analysis'
class: standard
---

## Context

v1 had a full Playwright browser management suite:
- `BrowserManager` — launch/connect via CDP (Chrome DevTools Protocol)
- Browser actions — navigate, click, type, extract content
- Content guards and safety filters
- Crawler (BFS with depth/page limits, robots.txt, rate limiting)
- Screenshot capture from browser sessions
- CLI commands: `bearclaw browser start [--port 9222]`, `stop`, `status`

v2 has none of this. The knowledge engine has dead `SourceType.CRAWL` stubs but no actual crawler handler. No agent can programmatically browse or capture web page state.

## Research Questions

1. **What use cases need browser integration?**
   - Knowledge ingestion from web pages (beyond `fetch_webpage`)
   - Visual verification / screenshot capture
   - Interactive web application testing
   - Authenticated page access (corporate intranets)

2. **What's the right scope?**
   - Option A: Minimal — just add a `capture_screenshot(url)` tool
   - Option B: Read-only — navigate + extract content + screenshot (no mutations)
   - Option C: Full — v1-equivalent BrowserManager with CDP control
   - Option D: MCP server — expose as owlbear-browser MCP with tool surface

3. **Integration with existing infrastructure?**
   - Could wire into knowledge engine's dead crawl handler
   - Could become standalone MCP server
   - Corporate proxy/auth considerations (Edge CDP on Windows)

4. **Dependencies** — Playwright already in v2's dependency tree? What's the install footprint?

## Acceptance Criteria

- [ ] AC1: Use case inventory with priority assessment
- [ ] AC2: Evaluate scope options against use cases
- [ ] AC3: Assess Playwright dependency and install impact
- [ ] AC4: Recommendation with follow-up implementation task(s)
