---
id: 194
title: Test content extractor — trafilatura wrapper
status: archived
priority: important
created: 2026-02-27T22:18:35.4581171+01:00
updated: 2026-02-28T23:53:43.7722323+01:00
started: 2026-02-28T00:26:33.4216082+01:00
completed: 2026-02-28T23:53:43.7722323+01:00
tags:
    - phase-9
    - knowledge-graph
    - browser
    - test
class: standard
---

Write tests in tests/test_content_extractor.py for src/owlbear/tools/browser/content_extractor.py. Test: (1) extract_content() returns ExtractionResult with text, title, author, date, metadata (2) ExtractionResult is frozen Pydantic model (3) Calls trafilatura.extract with output_format='markdown' (mock trafilatura) (4) Extracts metadata via trafilatura.extract_metadata (mock) (5) Returns ExtractionResult with empty text on extraction failure (no exception) (6) Passes url parameter to trafilatura for link resolution (7) Handles None returns from trafilatura gracefully
