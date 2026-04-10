---
id: 783
title: Tests — owlbear_browser content extractor and HTML-to-MD cleaner
status: backlog
priority: needed
created: '2026-04-10T12:30:44.046816+00:00'
updated: '2026-04-10T12:30:44.046816+00:00'
tags:
- phase-1
- scope:browser
- type:test
parent: 775
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Tests verify content extraction from HTML string returns structured text
- Tests verify HTML-to-markdown conversion (headings, lists, tables, links preserved)
- Tests verify noise removal (nav bars, footers, cookie banners, script tags stripped)
- File: `tests/test_browser_content_775.py`

## Context
- WS-C: Browser Packages
- Scope item 1 (part 2) from #775
