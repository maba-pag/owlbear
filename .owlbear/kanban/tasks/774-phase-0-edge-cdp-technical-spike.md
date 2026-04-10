---
id: 774
title: 'Phase 0: Edge CDP Technical Spike'
status: research
priority: critical
created: '2026-04-10T11:45:08.130424+00:00'
updated: '2026-04-10T11:45:08.130424+00:00'
tags:
- browser
- phase-0
- spike
parent: 751
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
# Phase 0: Edge CDP Technical Spike

## Go/No-Go Gate

Validate Edge CDP connectivity and content extraction quality on the corporate laptop before investing in architecture.

## Acceptance Criteria

1. Edge launches (or attaches) with `--remote-debugging-port=9222` on corporate laptop
2. Playwright `connect_over_cdp("http://localhost:9222")` connects and returns browser contexts
3. Navigation to an SSO-protected SharePoint page succeeds with user's active session
4. Page content is extractable via CDP (accessibility tree or DOM methods)
5. EDR/DLP does NOT block CDP port or flag extraction as threat
6. trafilatura `extract()` produces clean markdown from corporate HTML (test with 3+ SharePoint pages and 2+ Confluence pages)
7. Content hash is stable across repeated extractions of the same page (no dynamic boilerplate flicker)

## If Blocked

- CDP blocked by EDR → Document specific error, escalate to Phase 4 (SharePoint REST API) or browser extension research
- DLP flags bulk extraction → Document trigger threshold, implement rate limiting in Phase 1
- trafilatura over-extracts → Fall back to readability-lxml + markdownify (test both during spike)

## Implementation Notes

- Script in `.owlbear/scratch/research/cdp-spike/` — delete after validation
- Test with `playwright.chromium.connect_over_cdp("http://localhost:9222", is_local=True)`
- Verify CDP binds to 127.0.0.1 only (security requirement)
- Check `ipconfig` / `netstat` output for port exposure
- Results documented in task body for architect review

## Context

- Parent: #751 — Authenticated Content Pipeline
- Research: `.owlbear/research/751-authenticated-content-pipeline.md`
- Brief: `.owlbear/briefs/draft-browser-knowledge-extraction/brief.md`
