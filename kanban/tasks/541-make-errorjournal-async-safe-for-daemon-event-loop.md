---
id: 541
title: Make ErrorJournal async-safe for daemon event loop
status: backlog
priority: nice-to-have
created: 2026-03-04T07:38:45.7339339+01:00
updated: 2026-03-07T00:43:58.2924613+01:00
started: 2026-03-07T00:36:40.6260778+01:00
tags:
    - audit
    - resilience
    - scope:core
class: standard
---

J-2: ErrorJournal uses blocking file I/O (path.open('a')). In async daemon loop, rotation of 10K entries blocks event loop.

Research complete (2026-03-07): asyncio.to_thread at call site is the recommended approach (.85 confidence). Make _log_to_journal async in daemon.py, wrap journal.log() in asyncio.to_thread(). Zero new deps, follows existing codebase pattern (3 prior uses). See docs/research/error-journal-async.md for full analysis.

Research checklist:
1. Theoretical validity: wrapping sync I/O in asyncio.to_thread is well-established
2. Prior art: Python stdlib docs, aiofiles library, 3 existing uses in codebase
3. Technical feasibility: asyncio.to_thread is stdlib since 3.9, we are on 3.12+
4. Architecture fit: matches context_hook.py, tts.py, web_search.py patterns
5. Implementation approach: ~15 line diff in daemon.py only
