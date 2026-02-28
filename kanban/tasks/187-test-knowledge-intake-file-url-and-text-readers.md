---
id: 187
title: Test knowledge intake — file, URL, and text readers
status: archived
priority: needed
created: 2026-02-27T22:17:31.9453159+01:00
updated: 2026-02-28T23:53:36.9643224+01:00
started: 2026-02-27T23:12:00.3810007+01:00
completed: 2026-02-28T23:53:36.9643224+01:00
tags:
    - phase-9
    - knowledge-graph
    - memory
    - test
class: standard
---

Write tests in tests/test_knowledge_intake.py for src/owlbear/memory/knowledge/intake.py. Test: (1) read_file() returns IntakeResult with content, source path, metadata (2) read_file() raises FileNotFoundError for missing files (3) read_url() returns IntakeResult with content and URL as source (mock httpx) (4) read_url() raises httpx.HTTPStatusError on non-2xx status (5) read_text() wraps raw text with source='inline' default (6) IntakeResult is frozen Pydantic model with content: str, source: str, metadata: dict (7) Metadata includes source_type ('file', 'url', 'text') and fetched_at timestamp
