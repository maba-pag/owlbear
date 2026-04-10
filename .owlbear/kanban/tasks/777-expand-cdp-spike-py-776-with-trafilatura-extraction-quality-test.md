---
id: 777
title: Expand cdp-spike.py (#776) with trafilatura extraction quality test
status: research
priority: needed
created: '2026-04-10T12:16:53.902954+00:00'
updated: '2026-04-10T12:16:53.902954+00:00'
tags:
- phase-0
- scope:browser
parent: 751
depends_on:
- 776
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
Add trafilatura extraction quality testing to the CDP spike script (#776).

After CDP connectivity and basic text extraction succeed, the script should:
1. `pip install trafilatura` (or include in spike deps)
2. For each navigated page, capture raw `page.content()` (full HTML)
3. Run `trafilatura.extract(html, output_format="markdown", include_links=True, url=page_url)`
4. Also run `trafilatura.extract(html, output_format="markdown", include_links=True, url=page_url, favor_precision=True)`
5. Log: text length, paragraph count, presence of boilerplate indicators (nav text, footer text, breadcrumb patterns)
6. Compare standard vs precision mode output
7. Test with 3+ SharePoint pages and 2+ Confluence pages (URLs configurable)

AC:
1. Spike script includes trafilatura extraction after CDP text extraction
2. Both standard and favor_precision modes tested
3. Output logged with quality metrics (text length, paragraph count, boilerplate indicators)
4. At least 5 URLs configured (3 SharePoint, 2 Confluence)

Context: From #774 research — AC 6 was not covered by original spike design.
Research: .owlbear/research/774-edge-cdp-spike.md §3.2
