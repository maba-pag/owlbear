---
id: 788
title: owlbear_browser content extractor and HTML-to-MD cleaner
status: backlog
priority: needed
created: '2026-04-10T12:31:12.692743+00:00'
updated: '2026-04-10T12:31:12.692743+00:00'
tags:
- phase-1
- scope:browser
parent: 775
depends_on:
- 783
- 787
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `serve/browser/src/owlbear_browser/extractor.py` — DOM content extraction from HTML string
- `serve/browser/src/owlbear_browser/cleaner.py` — HTML-to-markdown with noise stripping (nav, footers, cookie banners, script tags)
- Headings, lists, tables, links preserved in markdown output
- All #783 tests pass
- Files: `serve/browser/src/owlbear_browser/extractor.py`, `cleaner.py`

## Context
- WS-C: Browser Packages
- Scope item 1 (part 2) from #775
