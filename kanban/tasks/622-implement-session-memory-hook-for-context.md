---
id: 622
title: Implement session-memory hook for context persistence across sessions
status: backlog
priority: important
created: 2026-03-07T05:21:06.0725486+01:00
updated: 2026-03-09T19:16:30.1678077+01:00
started: 2026-03-07T07:04:24.5342922+01:00
tags:
    - scope:core
    - phase-research
    - hooks
depends_on:
    - 711
blocked: true
block_reason: 'Blocked on #711 (SESSION_START/END emission) + AC refinement needed + test task creation'
class: standard
---

Add a SESSION_END hook handler that persists a concise context summary to per-project session memory. On SESSION_START, load previous summary into agent context.
File location: per-project at {workspace}/.owlbear/session-memory.md (not global config_dir).
See docs/openclaw-ecosystem-research.md S3b, S4.

depends_on: (prerequisite task for SESSION_START/SESSION_END emission  to be created)

AC:
- [ ] SessionMemoryHook class in src/owlbear/core/session_memory_hook.py (NOT memory/  layering)
- [ ] Constructor accepts workspace_root: Path and summarizer: Callable[[str], Awaitable[str]] (DI for LLM)
- [ ] register(hooks: HookRegistry) registers handlers for SESSION_END and SESSION_START
- [ ] On SESSION_END: receive session messages from event data dict, call summarizer to produce ~500-token markdown summary, write to {workspace}/.owlbear/session-memory.md
- [ ] On SESSION_START: if session-memory.md exists, read content and store under data[session_memory] key on event payload
- [ ] Summary target: ~500 tokens, structured markdown (headings: Key Decisions, Active Tasks, Workspace State)
- [ ] Graceful degradation: if summarizer call fails, skip persistence (log warning, never crash)
- [ ] Config field in OwlBearSettings: session_memory_enabled: bool = Field(default=False)
- [ ] bootstrap/hooks.py build_hooks() registers SessionMemoryHook when settings.session_memory_enabled is True, wiring summarizer callable
- [ ] Tests: persist on SESSION_END, load on SESSION_START, empty-state (no prior file), summarizer failure graceful skip, workspace_root directory creation
