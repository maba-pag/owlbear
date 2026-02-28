---
id: 173
title: Knowledge chunker — recursive separator-based text splitting
status: archived
priority: needed
created: 2026-02-27T22:09:46.5453465+01:00
updated: 2026-02-28T23:53:23.6362545+01:00
started: 2026-02-27T22:11:59.1722112+01:00
completed: 2026-02-28T23:53:23.6362545+01:00
tags:
    - phase-9
    - knowledge-graph
    - memory
depends_on:
    - 185
class: standard
---

Module: src/owlbear/memory/knowledge/chunker.py | Test: tests/test_knowledge_chunker.py | See docs/knowledge-ingestion-research.md S3.2.

AC:
- TextChunker class with configurable target_tokens (default 512), overlap_tokens (default 50), and separators list
- Default separator hierarchy: ['\n## ', '\n### ', '\n\n', '\n', ' ']
- chunk(text: str, metadata: dict) -> list[Chunk] method
- Chunk frozen Pydantic model: text: str, index: int, metadata: dict (includes source doc_id, start_char, end_char)
- Chunks respect separator hierarchy: tries largest separator first, falls back to smaller
- No chunk exceeds target_tokens + overlap_tokens hard maximum
- Overlap tokens appear at chunk boundaries (last N tokens of prev chunk prepended to next)
- Empty/whitespace-only text returns empty list
- Text shorter than target returns single chunk
- Token counting via len(text.split()) as word-count heuristic (KISS — no tiktoken dep)
- ruff clean, all tests in tests/test_knowledge_chunker.py pass
