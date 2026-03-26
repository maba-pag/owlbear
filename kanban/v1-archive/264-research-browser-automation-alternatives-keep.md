---
id: 264
title: 'Research: Browser automation alternatives — keep custom vs adopt OSS'
status: archived
priority: needed
created: 2026-02-28T13:32:20.3411731+01:00
updated: 2026-02-28T23:54:30.1900035+01:00
started: 2026-02-28T13:57:47.3063661+01:00
completed: 2026-02-28T23:54:30.1900035+01:00
tags:
    - research
    - browser
    - phase-6
class: standard
---

## Context
The full project audit (2026-02-28) identified the browser module (12 files, ~1200 LOC) as a potential OSS reimplementation candidate. User directive: 'do a full research on what is out there. i assume we have to keep the implementation because its custom to our unusual situation (no admin, browser locked down by IT dep with no additional addons allowed etc).'

## Environmental Constraints
- No admin access on Windows corporate laptop
- Edge browser policy-locked by IT (no extension sideloading)
- No additional browser addons allowed
- Must use Edge with existing CDP protocol support
- Playwright is already a dependency (browser extra)

## Research Questions
1. What browser automation libraries exist? (browser-use, crawl4ai, AgentQL, etc.)
2. Do any support CDP attach mode (connect to running Edge)?
3. Do any work without admin install / browser extensions?
4. How does our custom BrowserToolset compare feature-by-feature?
5. Can we use an OSS lib as foundation and add our Edge CDP launcher on top?
6. What about our WebCrawler — does crawl4ai / Scrapy overlap?
7. What about content extraction — trafilatura vs readability vs custom?

## OwlBear Browser Module Inventory
- BrowserConfig + BrowserManager (launch/CDP modes)
- 6 browser action tools (navigate, click, type, select, read_text, screenshot)
- BrowserToolset (FunctionToolset wrapping actions)
- URLSafetyGuard (blocklist/allowlist)
- Edge CDP launcher (find/launch/probe/kill)
- WebCrawler (async BFS, robots.txt, rate limiting)
- content_extractor (trafilatura)
- url_utils (normalize, discover_links, RobotsTxtChecker)
- integration.py (crawl_and_ingest bridge)

## Acceptance Criteria
- [ ] Comparison table: feature vs OwlBear vs each alternative
- [ ] Decision: keep custom / adopt OSS / hybrid approach
- [ ] If keep: document why (cite constraints)
- [ ] If adopt: migration plan and follow-up tasks
- [ ] Sources documented in docs/sources.md
