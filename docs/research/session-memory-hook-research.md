# Session-Memory Hook for Context Persistence

> **Owning task:** #622 — Implement session-memory hook for context persistence across sessions
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

When OwlBear's daemon restarts or a session resets, all conversational context is lost. The JSONL session history persists raw messages but these can be enormous and aren't consumable as a concise context summary. The question: **What is the right mechanism to persist a compact, LLM-generated session summary that survives restarts and informs the next session?**

Key constraints: SESSION_START/SESSION_END exist in `HookEvent` but are **never emitted** by `daemon.py` or `agent.py` today. This is a prerequisite.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| S1 | LangGraph Checkpointer | github.com/langchain-ai/langgraph `checkpoint/base/__init__.py` | .70 |
| S2 | OpenHands Condenser | github.com/OpenHands/OpenHands `openhands/memory/condenser/` | .85 |
| S3 | OpenClaw session-memory hook | docs.openclaw.ai/gateway/hooks (via prior research) | .90 |
| S4 | OwlBear SummarizingCondenser | `src/owlbear/core/condenser.py` (internal) | .95 |
| S5 | OwlBear ContextManager | `src/owlbear/memory/context.py` (internal) | .90 |
| S6 | OwlBear ObservabilityHook | `src/owlbear/core/observability.py` (internal) | .80 |

## 3. Analysis

### 3a. Prerequisite: SESSION_START/SESSION_END Emission

`HookEvent.SESSION_START` and `SESSION_END` exist in the enum but **are never emitted**. The daemon emits only `DAEMON_STARTUP`. Two existing hooks register on these events (`ContextInjectionHook` on START, `TestVerificationHook` on END) but are never triggered.

**Options for emission point:**

| Option | Location | Trigger | Complexity |
|--------|----------|---------|------------|
| A. Per-message session | `channel_loop()` | Emit START before first `agent.turn()`, END on shutdown | Low (~10 LOC) |
| B. Daemon lifecycle | `run_daemon()` | START after DAEMON_STARTUP, END in finally block | Low (~6 LOC) |
| C. Explicit session mgmt | New `SessionManager` class | User-initiated session boundaries | High (new abstraction) |

**Recommendation (.85): Option B** — emit in `run_daemon()`. START fires once after DAEMON_STARTUP, END fires in the finally block. Simple, deterministic, enables all existing hooks. Option C is YAGNI.

### 3b. Persistence Approaches

| Criterion | LLM Summary (S2,S3,S4) | Raw History Snapshot | Structured Checkpoint (S1) |
|-----------|------------------------|---------------------|---------------------------|
| Token cost | ~500 tokens output | 0 (no LLM call) | 0 (no LLM call) |
| Context quality | High — distilled decisions | Low — noise-heavy | Medium — structured but verbose |
| Storage size | ~1 KB markdown | Full JSONL (unbounded) | JSON graph state (complex) |
| Restore simplicity | Read file, prepend to instructions | Replay history | Deserialize + rehydrate |
| KISS alignment | High | Medium | Low (over-engineered for our needs) |
| Failure mode | LLM call may fail → skip | None | Deserialization errors |

**Recommendation (.85): LLM Summary** — follows OpenHands condenser pattern (S2) and OpenClaw session-memory hook (S3). OwlBear already has `SummarizingCondenser` (S4) proving LLM summarization works in-codebase.

### 3c. Storage Location

| Option | Path | Scope | Integration |
|--------|------|-------|-------------|
| A. `.owlbear/session-memory.md` | Per-workspace | `ContextManager` reads it | Append to `instructions` property |
| B. Extend `MEMORY.md` | Per-workspace | Already read by `ContextManager` | Overwrites user content risk |
| C. Per-project config_dir | `~/.owlbear/projects/{id}/session-memory.md` | Per-project | Needs path plumbing |

**Recommendation (.80): Option A** — `.owlbear/session-memory.md` per-workspace. Clean separation from user-editable `MEMORY.md`. `ContextManager.instructions` already merges multiple files — adding a third is trivial (~5 LOC).

### 3d. Restore Mechanism

| Option | Mechanism | Complexity |
|--------|-----------|------------|
| A. ContextManager reads file | Add `session-memory.md` to `instructions` property | ~5 LOC change |
| B. SESSION_START hook injects | Hook reads file, adds to event payload | ~15 LOC new handler |
| C. History processor prepends | New HistoryProcessor that injects summary message | ~30 LOC |

**Recommendation (.80): Option A** — simplest. `ContextManager.instructions` already merges `context.md` + `MEMORY.md`. Adding `.owlbear/session-memory.md` is one `if` block. The summary is always available to the agent, no hook timing concerns.

### 3e. Summary Generation

Reuse the exact prompt pattern from `SummarizingCondenser._summarize()` (S4). The session-memory hook calls the same LLM with a slightly different prompt: "Summarize key decisions, active tasks, and workspace state from this session" instead of "Summarize this conversation segment."

Target: ~500 tokens structured markdown with sections for decisions, active tasks, and next steps.

## 4. Recommendation (.80 confidence)

**Architecture:**

1. **Prerequisite:** Emit `SESSION_START`/`SESSION_END` in `run_daemon()` (Option B from §3a)
2. **SessionMemoryHook** class in `src/owlbear/memory/session_memory_hook.py`
3. Registers on `SESSION_END` → generates LLM summary → writes `.owlbear/session-memory.md`
4. Restore via `ContextManager.instructions` reading the file (no SESSION_START handler needed)
5. Config: `session_memory_enabled: bool = False` in `OwlBearSettings`
6. Registration: `build_hooks()` in bootstrap creates and registers when enabled

**Risks:**

- LLM call on SESSION_END may fail (network, token) → mitigated by graceful skip (log warning)
- Summary quality depends on LLM → mitigated by structured prompt template
- SESSION_END never fires if process is killed (SIGKILL) → acceptable; only graceful shutdown persists

**What NOT to build (YAGNI):**

- No session versioning/history of summaries (single file, overwritten each time)
- No structured checkpoint format (markdown is sufficient)
- No user-editable summary (auto-generated only)
- No SESSION_START hook handler (ContextManager reads the file automatically)

## 5. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Emit SESSION_START and SESSION_END hooks in run_daemon" --priority needed --tags "scope:core,hooks" --body "SESSION_START and SESSION_END exist in HookEvent but are never emitted. Emit SESSION_START in run_daemon() after DAEMON_STARTUP, emit SESSION_END in the finally block before 'Daemon stopped' log. Payload: {session_id: str(agent.session.path), channel: channel.name}. Prerequisite for #622 and unblocks ContextInjectionHook + TestVerificationHook which register on these events but never fire.\n\nSee docs/session-memory-hook-research.md S3a.\n\nAC:\n- [ ] SESSION_START emitted in run_daemon() try block after DAEMON_STARTUP emit\n- [ ] SESSION_END emitted in run_daemon() finally block before logger.info('Daemon stopped')\n- [ ] Payload is {session_id: str(agent.session.path), channel: channel.name}\n- [ ] Test: SESSION_START fires before first channel.receive()\n- [ ] Test: SESSION_END fires in finally block even on shutdown\n- [ ] Existing hooks (ContextInjectionHook, TestVerificationHook) now trigger\n- [ ] uv run ruff check clean\n- [ ] All existing tests pass"

kanban\kanban-md.exe create "Implement SessionMemoryHook for session-end context persistence" --priority important --tags "scope:core,hooks,phase-research" --depends-on "TASK_ID_FROM_ABOVE" --body "SessionMemoryHook class that generates an LLM summary on SESSION_END and writes to {workspace}/.owlbear/session-memory.md. ~500 token structured markdown. Graceful degradation on LLM failure.\n\nSee docs/session-memory-hook-research.md S3b, S3e.\n\nAC:\n- [ ] SessionMemoryHook class in src/owlbear/memory/session_memory_hook.py\n- [ ] register(hooks) registers async handler on SESSION_END\n- [ ] On SESSION_END: loads session history from agent.session, generates LLM summary, writes .owlbear/session-memory.md\n- [ ] Summary prompt produces structured markdown (~500 tokens): decisions, active tasks, next steps\n- [ ] If LLM call fails: log warning, skip write, never crash\n- [ ] Tests: mock LLM, verify file written with expected structure\n- [ ] Tests: LLM failure path logs warning and skips gracefully\n- [ ] Tests: empty session history produces no file\n- [ ] uv run ruff check clean"

kanban\kanban-md.exe create "Add session-memory.md to ContextManager instructions" --priority important --tags "scope:core,hooks" --depends-on "TASK_ID_FROM_ABOVE" --body "Extend ContextManager.instructions property to include .owlbear/session-memory.md content when present. This is the restore mechanism for session memory.\n\nSee docs/session-memory-hook-research.md S3d.\n\nAC:\n- [ ] ContextManager.instructions reads {workspace}/.owlbear/session-memory.md if it exists\n- [ ] Content appended after MEMORY.md section\n- [ ] Missing file is silently skipped (no error)\n- [ ] Tests: instructions includes session-memory content when file exists\n- [ ] Tests: instructions unchanged when file is absent\n- [ ] uv run ruff check clean"

kanban\kanban-md.exe create "Add session_memory_enabled config and bootstrap wiring" --priority important --tags "scope:core,config,hooks" --depends-on "TASK_ID_FROM_ABOVE" --body "Add session_memory_enabled bool field to OwlBearSettings (default False). Wire build_hooks() to create and register SessionMemoryHook when enabled. Hook needs workspace_root and model for LLM calls.\n\nSee docs/session-memory-hook-research.md S4.\n\nAC:\n- [ ] session_memory_enabled: bool = False in OwlBearSettings\n- [ ] build_hooks() creates SessionMemoryHook when session_memory_enabled=True\n- [ ] Hook receives workspace_root path and model reference\n- [ ] Tests: hook registered when enabled, not registered when disabled\n- [ ] uv run ruff check clean"
```

**Note:** Original task #622 should be split into these 4 focused tasks. #622 can be closed or converted to a tracking parent.
