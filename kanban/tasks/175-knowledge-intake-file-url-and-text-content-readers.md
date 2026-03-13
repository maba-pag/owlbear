---
id: 175
title: Knowledge intake — file, URL, and text content readers
status: archived
priority: needed
created: 2026-02-27T22:10:00.8979603+01:00
updated: 2026-02-28T23:53:24.9558404+01:00
started: 2026-02-27T22:12:00.2658348+01:00
completed: 2026-02-28T23:53:24.9558404+01:00
tags:
    - phase-9
    - knowledge-graph
    - memory
depends_on:
    - 187
class: standard
---

Module: src/owlbear/memory/knowledge/intake.py | Test: tests/test_knowledge_intake.py | See docs/research/knowledge-ingestion.md S3.4.

AC:
- IntakeResult frozen Pydantic model: content: str, source: str, metadata: dict[str, Any]
- Metadata includes source_type ('file'|'url'|'text') and fetched_at ISO timestamp
- async read_file(path: Path) -> IntakeResult — reads text/markdown files from disk
- read_file raises FileNotFoundError for missing files
- async read_url(url: str) -> IntakeResult — fetches URL content with httpx AsyncClient
- read_url raises httpx.HTTPStatusError on non-2xx response
- read_text(text: str, source: str = 'inline') -> IntakeResult — wraps raw text synchronously
- Each function populates IntakeResult.metadata with appropriate source_type
- ruff clean, all tests in tests/test_knowledge_intake.py pass
