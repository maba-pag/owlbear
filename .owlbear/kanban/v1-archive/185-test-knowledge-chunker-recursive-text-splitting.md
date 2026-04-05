---
id: 185
title: Test knowledge chunker — recursive text splitting
status: archived
priority: needed
created: 2026-02-27T22:17:15.4208924+01:00
updated: 2026-02-28T23:53:33.3337992+01:00
started: 2026-02-27T23:11:56.3152874+01:00
completed: 2026-02-28T23:53:33.3337992+01:00
tags:
    - phase-9
    - knowledge-graph
    - memory
    - test
class: standard
---

Write tests in tests/test_knowledge_chunker.py for src/owlbear/memory/knowledge/chunker.py. Test: (1) chunk() returns list[Chunk] with text, index, metadata (2) Respects separator hierarchy (\n## > \n### > \n\n > \n > space) (3) No chunk exceeds target_tokens + overlap_tokens (4) Empty/whitespace input returns empty list (5) Overlap tokens appear at chunk boundaries (6) Source tracking metadata (doc_id, start_char, end_char) preserved on each chunk (7) Configurable target_tokens and overlap_tokens (8) Single chunk returned for text shorter than target
