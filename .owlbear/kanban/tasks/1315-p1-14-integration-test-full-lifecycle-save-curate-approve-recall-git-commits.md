---
id: 1315
title: 'P1-14: Integration test — Full lifecycle (save → curate → approve → recall
  + git commits)'
status: todo
priority: important
created: 2026-05-04T01:32:27.514360+00:00
updated: 2026-05-06T07:13:25.454922+00:00
tags:
- phase-2
- scope:mcp-memory
- memory
- mcp
- test
parent: 1301
depends_on:
- 1311
- 1308
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
\nBrief: see parent #1301\n\n## Acceptance Criteria\n\n- [ ] Integration test exercises full lifecycle: save_memory -> list_memories -> read_memory -> curate_memory (with scope_agents) -> approve_memory -> recall_memory (td:2)\n- [ ] Verifies persisted state at each step via engine re-read (not just return values): pending -> curated -> approved (td:1)\n- [ ] Verifies recall_memory(agent=\"scoped-agent\") returns the approved entry in body-only format (\"## {title}\\n{content}\") (td:1)\n- [ ] Verifies recall_memory(agent=\"other-agent\") returns empty string for non-scoped agents (td:1)\n- [ ] Verifies git semantics: no new commit after save_memory; exactly 1 new commit after explicit commit_batch(session_type=\"curation\"); exactly 1 more commit after explicit commit_batch(session_type=\"review\") (td:2)\n- [ ] Test uses real async tool handlers from tools.py with MemoryEngine on git-init'd tmp_path (td:1)\n\n## Scope\n\n- In: end-to-end integration test covering tool handler + engine + git layers\n- Out: consumer wiring verification (manual), performance testing, MCP transport layer\n\n## Builder Guidance\n\n- Use established pattern: `_make_ctx(engine)` helper wiring `ctx.request_context.lifespan_context.engine`\n- `commit_batch` is NOT auto-triggered — call it explicitly between phases\n- State check via `engine.get_entry(entry_id).state` after each tool call\n- Git commit count via `git rev-list --count HEAD` in tmp_path\n- File: `tests/test_memory_lifecycle_1315.py`\n\n[[2026-05-06]]\n## Research\n\nAnalyzed mcp-memory codebase: tools.py (save/list/read/curate/approve/recall), engine.py (MemoryEngine, MtimeScanCache), git.py (commit_batch), models.py (MemoryEntry, MemoryState lifecycle).\n\nKey findings:\n- All tool handlers are async and use MagicMock ctx pattern (established in tests 1272, 1308, 1310)\n- commit_batch is NOT auto-triggered by tool handlers — must be called explicitly between phases\n- recall_memory filters by scope_agents list membership and returns body-only markdown\n- State transitions: pending→curated (via curate_memory with scope_agents), curated→approved (via approve_memory)\n\nTest design: single async integration test with explicit phases exercising all 6 AC. Uses git-init'd tmp_path with real MemoryEngine. Verifies state at each step + git commit count after batch operations.\n\nDoc: .owlbear/research/memory-full-lifecycle-integration-test.md\n\n## Architecture Review\n\n**Verdict:** APPROVED (refined)\n\n| AC line | Assessment | Action |\n|---------|-----------|--------|\n| Full lifecycle exercise | Clear, names exact tool functions | Refined: added function names |\n| State verification | Was ambiguous (return vs persisted) | Refined: requires engine re-read |\n| Recall scoped format | Clear | Refined: added expected format |\n| Recall scope exclusion | Clear | Refined: added agent param example |\n| Git semantics | Was missing explicit commit_batch call | Refined: made batch calls explicit |\n| Real tool handlers | Was ambiguous about layer | Refined: specifies tools.py + MemoryEngine + tmp_path |\n\n**Architecture notes:**\n- Follows established mcp-memory test patterns (tests 1308, 1310)\n- Dependencies #1311, #1308 confirmed done (implementations exist in tools.py, git.py)\n- No new abstractions introduced; composition test of existing surfaces\n- Builder Guidance section added for implementation clarity\n\n**Challenger result:** reconsider (0.64) — addressed persistence proof gap via AC2 refinement; dismissed recall-visibility concern (already covered by #1308); dismissed layer-boundary concern (established pattern). Override justified: task is a standard composition test.\n\n**Test-writer:** Process normally (AC1, AC5 are td:2; rest td:1).")
</invoke>
[[2026-05-06]]
Architecture review complete. Refined all 6 AC lines for precision: added exact function names, required persisted-state verification via engine re-read, specified expected recall format, made commit_batch calls explicit. Added Builder Guidance section. Challenger override justified (0.64 → proceed): persistence gap addressed, other concerns dismissed with evidence.