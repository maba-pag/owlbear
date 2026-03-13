---
id: 182
title: Content extractor — trafilatura wrapper for Playwright HTML
status: archived
priority: important
created: 2026-02-27T22:10:49.0484179+01:00
updated: 2026-02-28T23:53:30.2807687+01:00
started: 2026-02-27T22:12:10.0227924+01:00
completed: 2026-02-28T23:53:30.2807687+01:00
tags:
    - phase-9
    - knowledge-graph
    - browser
depends_on:
    - 194
class: standard
---

Module: src/owlbear/tools/browser/content_extractor.py | Test: tests/test_content_extractor.py | See docs/research/web-crawling.md S3.2.

AC:
- ExtractionResult frozen Pydantic model: text: str, title: str | None, author: str | None, date: str | None, metadata: dict[str, Any]
- extract_content(html: str, url: str | None = None) -> ExtractionResult function
- Calls trafilatura.extract(html, output_format='markdown', include_links=True, url=url)
- Extracts metadata (title, author, date) via trafilatura.extract_metadata(html)
- Returns ExtractionResult with text='' on extraction failure (no exception raised)
- Handles None returns from trafilatura gracefully
- New dependency: add trafilatura to [project.optional-dependencies] crawl group in pyproject.toml
- Module named content_extractor.py (not extractor.py) to avoid confusion with knowledge/extractor.py
- ruff clean, all tests in tests/test_content_extractor.py pass
