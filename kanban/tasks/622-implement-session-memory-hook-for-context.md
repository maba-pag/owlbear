---
id: 622
title: Implement session-memory hook for context persistence across sessions
status: backlog
priority: important
created: 2026-03-07T05:21:06.0725486+01:00
updated: 2026-03-07T07:04:24.5342922+01:00
started: 2026-03-07T07:04:24.5342922+01:00
tags:
    - scope:core
    - phase-research
    - hooks
class: standard
---

Add a SESSION_END hook handler that persists a concise context summary to per-project session memory. On SESSION_START, load previous summary into agent context.

File location: per-project at {workspace}/.owlbear/session-memory.md (not global config_dir).

See docs/openclaw-ecosystem-research.md S3b, S4.

AC:
- [ ] SessionMemoryHook class in src/owlbear/memory/session_memory_hook.py
- [ ] register(hooks: HookRegistry) registers handlers for SESSION_END and SESSION_START
- [ ] On SESSION_END: generate LLM summary of session (key decisions, active tasks, workspace state), write to {workspace}/.owlbear/session-memory.md
- [ ] On SESSION_START: if session-memory.md exists, load content and prepend to agent context
- [ ] Summary target: ~500 tokens, structured markdown
- [ ] Graceful degradation: if LLM call fails, skip persistence (log warning, never crash)
- [ ] Config field in OwlBearSettings: session_memory_enabled (bool, default False)
- [ ] bootstrap.py registers hook when session_memory_enabled=True
- [ ] Tests: persist on SESSION_END, load on SESSION_START, empty-state (no prior file), LLM failure graceful skip
