---
id: 517
title: Reduce ingest.py complexity after pipeline refactor
status: done
priority: important
created: 2026-03-04T07:38:27.4728203+01:00
updated: 2026-03-08T03:00:36.4139254+01:00
started: 2026-03-06T23:58:22.1903475+01:00
tags:
    - audit
    - modularity
    - knowledge
class: standard
---

SUPERSEDED: Split into #671 (DocumentStore extraction), #672 (GraphEnricher extraction), #673 (re-exports), #674 (tests). Original task was an umbrella covering 3 extraction operations plus re-exports -- not atomic. See docs/ingest-complexity-reduction-research.md for full research.
