# WIP Continuity Store for Multi-Cycle Agent Execution

> **Owning task:** #615 — WIP continuity store for multi-cycle agent execution
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

When OwlBear's daemon loop dispatches a builder agent for a kanban task, the agent runs a single `agent.run()` call. If the task spans multiple cycles (e.g., agent hits a turn limit, rate limit, or transient error), the next cycle starts from scratch — the agent has no memory of what it already accomplished. This is the "multi-cycle amnesia" problem.

**Question:** What storage pattern should OwlBear use to persist per-task work-in-progress summaries across cycles, and how should that WIP be injected into the agent's prompt?

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| quoroom-ai/room `agent-loop.ts` | <https://github.com/quoroom-ai/room/blob/main/src/shared/agent-loop.ts> | .90 | `save_wip` tool + `CONTINUE FORWARD` prompt injection; auto-WIP fallback from last output; adaptive momentum gap; per-worker `wip` column in DB |
| LangGraph durable execution | <https://docs.langchain.com/oss/python/langgraph/durable-execution> | .70 | Framework-level checkpointing with `MemorySaver`/`SqliteSaver`; thread-id keyed state; full graph state serialization; deterministic replay |
| OwlBear `JsonlStore` base | `src/owlbear/core/jsonl_store.py` | .95 | Proven pattern — `append()` + `load()`, Pydantic serialization, file-per-store |
| OwlBear `ErrorJournal` | `src/owlbear/memory/error_journal.py` | .90 | Concrete `JsonlStore` subclass with query, rotation, workspace-relative path |

## 3. Analysis

### 3.1 Storage Approach Comparison

| Criterion | JSONL per-task file (.85) | SQLite table (.65) | Single JSONL with all tasks (.55) |
|-----------|---------------------------|---------------------|-----------------------------------|
| KISS | High — one file per agent+task, trivial cleanup | Medium — needs schema migration | Low — must parse/filter all entries |
| Cleanup | `Path.unlink()` — delete file when task completes | `DELETE WHERE` | Rewrite entire file minus completed |
| Concurrency | Safe — separate files, no contention | Safe — SQLite handles locking | Risky — concurrent appends to same file |
| Codebase fit | Matches `JsonlStore`, `ErrorJournal`, `SessionStore` | New dependency pattern (no existing SQLite in core) | Possible but awkward with existing `JsonlStore` |
| Queryability | Read single file = O(n) lines for that task (small) | Full SQL | Must scan all lines |
| Dependencies | Zero new deps | sqlite3 (stdlib, but new pattern) | Zero new deps |

### 3.2 Key Design: Per-Task File vs. Per-Agent File

Quoroom stores WIP as a single text column per worker in SQLite. OwlBear's agents are stateless between cycles — there's no persistent worker row. Two options:

| Approach | Key Structure | File | Cleanup |
|----------|---------------|------|---------|
| **Per-task file** | `.owlbear/wip/{agent}_{task_id}.jsonl` | One file per active task | `unlink()` on completion |
| **Per-agent file** | `.owlbear/wip/{agent}.jsonl` | All tasks in one file | Filter + rewrite on completion |

**Recommendation (.85):** Per-task file. Simpler cleanup, no rewrite logic, matches KISS. The number of concurrent tasks is bounded by `max_concurrent_tasks` (default 3), so file count is trivially small.

### 3.3 Storage Format: Append-Only Log vs. Latest-Wins

| Pattern | Behavior | Complexity | Value |
|---------|----------|------------|-------|
| **Append-only** (JSONL log) | Every save appends; load returns last entry | Low, reuses `JsonlStore` | Keeps history for debugging |
| **Latest-wins** (overwrite) | Each save replaces file content | Lower | Sufficient for resume |

**Recommendation (.80):** Append-only JSONL using `JsonlStore`. History is useful for debugging stuck agents. Load returns the last entry (most recent WIP). Cost: negligible — files are deleted when tasks complete.

### 3.4 Injection Point

Quoroom injects WIP as `>>> CONTINUE FORWARD <<<` directive at highest priority in the prompt, before room objectives and goals. OwlBear has two injection candidates:

| Injection Point | How | Pros | Cons |
|-----------------|-----|------|------|
| **Prompt prefix** in `poll_tick` | Prepend WIP to the prompt string before `builder.run(prompt)` | Simple, no agent changes, caller controls content | Mixes data layers (daemon knows about WIP) |
| **`OwlBearAgent.turn()` via deps** | Pass `WipStore` on deps; agent reads WIP in `turn()` | Clean separation; agent owns its context | Requires `OwlBearDeps` change + agent code change |
| **System instructions** via `instructions` kwarg | Pass WIP as part of `instructions` override in `agent.run()` | PydanticAI-native | Overrides static instructions |

**Recommendation (.80):** Prompt prefix in `poll_tick`. The daemon already constructs the prompt (`f"Build task #{task_id}: ..."`). Prepending WIP here is 3 lines of code, zero API changes. The builder agent doesn't need to know about WIP — it just receives a richer prompt. This matches Quoroom's pattern where the loop injects WIP, not the agent.

### 3.5 Save Trigger

| Trigger | When | Agent awareness |
|---------|------|-----------------|
| **Agent tool** (`save_wip`) | Agent calls explicitly during execution | High — agent must be instructed to call it |
| **Auto-save from output** | Daemon extracts summary from agent's last response | Zero — fully transparent |
| **Both** (Quoroom approach) | Agent calls `save_wip`; fallback auto-extracts from output | Graceful degradation |

**Recommendation (.75):** Auto-save only (for now). OwlBear agents don't have a `save_wip` tool yet, and adding one requires tool registration + prompt instructions + testing. Auto-extracting from the agent's output (last 500 chars, like Quoroom's fallback) gives 80% of the value with 20% of the effort. A `save_wip` tool can be added later if auto-save proves insufficient. YAGNI.

### 3.6 Cleanup Semantics

WIP files must be cleaned up to avoid stale data. Cleanup points:

1. **Task succeeds** → `reconcile_tasks()` calls `wip_store.clear(agent, task_id)` after moving to review
2. **Task fails permanently** → `reconcile_tasks()` calls `wip_store.clear()` after removing from claimed
3. **Daemon restart** → Stale files from previous runs persist harmlessly; they'll be used if the same task is re-dispatched, or ignored if the task was already completed

No rotation needed (unlike `ErrorJournal`) — files are short-lived and deleted on completion.

## 4. Recommendation (.85 confidence)

Implement `WipStore` as a thin class wrapping per-task JSONL files under `.owlbear/wip/`:

- **Model:** `WipEntry(timestamp: str, agent: str, task_id: str, summary: str)`
- **Storage:** `JsonlStore` per task at `.owlbear/wip/{agent}_{task_id}.jsonl`
- **API:** `save(agent, task_id, summary)` → append; `load(agent, task_id) -> str | None` → last entry's summary; `clear(agent, task_id)` → delete file
- **Injection:** `poll_tick` prepends WIP to prompt before `builder.run()`
- **Save trigger:** Auto-save in `reconcile_tasks()` from task output (first cycle); `save_wip` tool deferred to a future task
- **Cleanup:** `clear()` called in `reconcile_tasks()` on success or permanent failure
- **Risk:** Auto-save quality depends on agent output being a useful summary. Mitigation: truncate to 500 chars, prefix with `[auto]` marker (Quoroom pattern).

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Implement WipStore class in owlbear.memory.wip" --priority needed --status backlog --tags "scope:core,agent" --depends-on 614 --body "Create WipStore class under src/owlbear/memory/wip.py.\n\nAC:\n- [ ] WipEntry Pydantic model: timestamp, agent, task_id, summary\n- [ ] WipStore with save(agent, task_id, summary), load(agent, task_id) -> str | None, clear(agent, task_id)\n- [ ] Per-task JSONL files at .owlbear/wip/{agent}_{task_id}.jsonl via JsonlStore\n- [ ] load() returns most recent entry summary (last line)\n- [ ] clear() deletes the file\n- [ ] Tests: save/load round-trip, load empty returns None, clear deletes file, multiple saves returns latest"

kanban\kanban-md.exe create "Inject WIP into poll_tick dispatch prompt" --priority needed --status backlog --tags "scope:core,agent" --depends-on 614 --body "Wire WipStore into the daemon poll-dispatch loop.\n\nAC:\n- [ ] poll_tick receives wip_store parameter\n- [ ] Before building prompt, load WIP via wip_store.load('builder', task_id)\n- [ ] If WIP exists, prepend CONTINUE FORWARD directive to prompt\n- [ ] Auto-save: after task completes in reconcile_tasks, extract summary from output and call wip_store.save()\n- [ ] On task success: call wip_store.clear(agent, task_id)\n- [ ] On task permanent failure: call wip_store.clear(agent, task_id)\n- [ ] Tests: mock WipStore, verify prompt contains WIP, verify cleanup on success/failure"

kanban\kanban-md.exe create "Add save_wip agent tool for explicit WIP persistence" --priority nice-to-have --status ideation --tags "scope:core,agent" --body "Optional: let agents explicitly save WIP summaries via a tool call. Supplements auto-save.\n\nAC:\n- [ ] WipToolset with save_wip(ctx, task_id, summary) tool\n- [ ] Registered on builder agent toolset\n- [ ] Agent system prompt instructs: 'Before your cycle ends, save progress with save_wip'\n- [ ] Tests: tool call saves to WipStore, load returns saved content"
```

## 6. Attribution

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| quoroom-ai/room | <https://github.com/quoroom-ai/room/blob/main/src/shared/agent-loop.ts> | WIP save/load pattern, CONTINUE FORWARD prompt injection, auto-WIP fallback, momentum gap | `docs/research/wip-continuity-store.md` | 2026-03-07 |
| LangGraph durable execution | <https://docs.langchain.com/oss/python/langgraph/durable-execution> | Checkpoint persistence concept, thread-id keyed state, resume semantics | `docs/research/wip-continuity-store.md` | 2026-03-07 |
