# deer-flow Deep Dive: Memory System + Subagent Delegation Patterns

> **Owning task:** #428 — deer-flow deep dive: memory system + subagent delegation patterns
> **Date:** 2026-03-31 **Status:** Complete

## 1. Context and Question

Focused analysis of deer-flow's memory and subagent subsystems to extract transferable patterns for OwlBear's planned work: #387 (per-agent institutional knowledge via memory-mcp) and #228 (subagent nesting architecture, archived). The parent research (#386) identified these as the two highest-value areas for deeper investigation.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| S1 | deer-flow memory/updater.py | cloned repo `packages/harness/deerflow/agents/memory/updater.py` | .95 — LLM extraction engine |
| S2 | deer-flow memory/prompt.py | cloned repo `...memory/prompt.py` | .95 — extraction + injection prompts |
| S3 | deer-flow memory/queue.py | cloned repo `...memory/queue.py` | .90 — debounced update queue |
| S4 | deer-flow memory/storage.py | cloned repo `...memory/storage.py` | .90 — storage provider pattern |
| S5 | deer-flow MemoryMiddleware | cloned repo `...middlewares/memory_middleware.py` | .85 — lifecycle integration |
| S6 | deer-flow subagents/executor.py | cloned repo `...subagents/executor.py` | .95 — dual-pool execution |
| S7 | deer-flow subagents/config.py | cloned repo `...subagents/config.py` | .85 — SubagentConfig schema |
| S8 | deer-flow task_tool.py | cloned repo `...tools/builtins/task_tool.py` | .90 — delegation interface |
| S9 | deer-flow SubagentLimitMiddleware | cloned repo `...middlewares/subagent_limit_middleware.py` | .85 — concurrency control |
| S10 | deer-flow memory_config.py | cloned repo `...config/memory_config.py` | .85 — config defaults |
| S11 | OwlBear #387 task body | kanban task | .95 — target memory architecture |
| S12 | OwlBear #228 research doc | `docs/research/subagent-nesting-architecture.md` | .90 — subagent nesting baseline |

## 3. Analysis

### 3A. Memory Extraction Prompts — What the LLM Sees

deer-flow uses a single 80-line `MEMORY_UPDATE_PROMPT` (S2) that receives: (a) the full current memory JSON state, and (b) filtered conversation text (only human messages + final AI responses — tool messages and intermediate AI messages with tool_calls are stripped by `_filter_messages_for_memory`, S5).

The LLM returns structured JSON with `shouldUpdate` flags per section, `newFacts` with category/confidence, and `factsToRemove` IDs. Categories: `preference`, `knowledge`, `context`, `behavior`, `goal`. Confidence guidelines are explicit: 0.9-1.0 for stated facts, 0.7-0.8 for implied, 0.5-0.6 for inferred patterns (S2).

**Key insight:** The prompt instructs the LLM what _not_ to store — file upload events are explicitly excluded both in the prompt and via a regex-based post-processing scrub (`_strip_upload_mentions_from_memory`, S1). This "negative instruction" pattern prevents ephemeral session noise from polluting long-term memory.

### 3B. Fact Lifecycle: Creation → Dedup → Injection → Pruning

| Stage | Mechanism | Config | Source |
|-------|-----------|--------|--------|
| Creation | LLM extracts from conversation via `MEMORY_UPDATE_PROMPT` | — | S1, S2 |
| Confidence gate | Facts below `fact_confidence_threshold` are discarded | 0.7 default | S10 |
| Deduplication | Whitespace-normalized content comparison (`_fact_content_key`) | — | S1 |
| Removal | LLM returns `factsToRemove` IDs for contradicted facts | — | S1 |
| Pruning | When `max_facts` exceeded, lowest-confidence facts are dropped | 100 default | S1, S10 |
| Injection | Top facts sorted by confidence, token-counted via tiktoken | 2000 tokens max | S2, S10 |
| Persistence | JSON file via pluggable `MemoryStorage` ABC, mtime-cached | `memory.json` | S4 |

**Debounced queue** (S3): When conversation ends, `MemoryMiddleware` (S5) queues the filtered messages. The queue deduplicates by `thread_id` (newer replaces older) and processes after `debounce_seconds` (default 30s). This batches rapid-fire conversations into a single LLM extraction call.

### 3C. deer-flow Memory vs OwlBear's Proposed 4-Dimensional Scoping (#387)

| Aspect | deer-flow | OwlBear #387 proposal | Transferable? |
|--------|-----------|----------------------|---------------|
| Scope model | Global or per-agent (2D) | 4D: general × project × agent × agent+project | **Partially** — per-agent is transferable; 4D scoping is OwlBear-specific |
| Storage | JSON file (`memory.json`), pluggable ABC | SQLite/JSON, MCP-served | **Yes** — pluggable storage ABC pattern |
| Extraction | LLM-based automatic from conversations | Agent writes via `record_learning` tool | **No** — OwlBear agents don't have continuous conversations |
| Confidence scoring | 0.0-1.0 per fact, threshold-gated | Not yet designed | **Yes** — confidence + threshold for quality filtering |
| Categories | 5 types (preference/knowledge/context/behavior/goal) | Not yet designed | **Yes** — category taxonomy is reusable |
| Deduplication | Content-normalized comparison | Not yet designed | **Yes** — simple and effective |
| Pruning | Max-facts limit, drop lowest confidence | Not yet designed | **Yes** — capacity management pattern |
| Injection | Top-N facts by confidence, token-budgeted | MCP tool returns token-budgeted set | **Yes** — token-budgeted injection pattern |
| Approval workflow | None (all facts auto-accepted) | Pending → approved → permanent | **No** — OwlBear needs human gatekeeping |

**Key transferable patterns for #387:** (1) fact schema with id/content/category/confidence/createdAt/source, (2) confidence threshold gating (0.7), (3) whitespace-normalized dedup, (4) max-capacity pruning by confidence, (5) token-budgeted injection format, (6) pluggable storage provider ABC.

**Not transferable:** LLM-based auto-extraction (OwlBear is on-demand, no continuous conversation to extract from), debounced queue (no persistent process), 6-section context model (OwlBear uses structured conclusions, not conversational summaries).

### 3D. Subagent Executor: Dual-Thread-Pool Architecture

deer-flow uses two `ThreadPoolExecutor` instances (S6):

| Pool | Workers | Purpose | Why separated |
|------|---------|---------|---------------|
| `_scheduler_pool` | 3 | Orchestrates lifecycle: creates result holder, submits to execution pool, monitors timeout | Prevents scheduler blocking when all execution workers are busy |
| `_execution_pool` | 3 | Runs the actual subagent LangGraph agent with tool loop | Isolated so timeout can be enforced via `Future.result(timeout=N)` |

**Execution flow:** `execute_async()` → scheduler_pool → creates `SubagentResult(PENDING)` → submits `self.execute()` to execution_pool → sets `RUNNING` → execution_pool runs `asyncio.run(self._aexecute())` (new event loop per thread) → on completion sets `COMPLETED`/`FAILED`/`TIMED_OUT`.

**Timeout mechanism:** The scheduler thread calls `execution_future.result(timeout=config.timeout_seconds)`. If `FuturesTimeoutError`, it cancels the future (best-effort) and sets `TIMED_OUT`. The `task_tool` (S8) polls `get_background_task_result()` every 5s.

**Why two pools (not one):** The scheduler must remain available to accept new task submissions even when all 3 execution slots are occupied. With a single pool, a 4th `execute_async()` call would deadlock — the scheduler function is queued behind 3 long-running executions, never reaching its timeout logic. The dual-pool pattern separates _control plane_ from _data plane_.

### 3E. Subagent Discovery/Registry

deer-flow's registry (S7, `registry.py`) is a simple dict mapping name → `SubagentConfig`. Two built-in subagents: `general-purpose` (full tool access minus `task`, model-inherited, 50 turns) and `bash` (5 sandbox tools, 30 turns). Both disallow `task`, `ask_clarification`, and `present_files` to prevent nesting and user interaction.

Discovery: `get_available_subagent_names()` filters by sandbox config (bash only available when host bash is allowed). Config overrides: `get_subagent_config()` applies `config.yaml` timeout overrides via `dataclasses.replace()`.

**OwlBear comparison:** OwlBear uses `.agent.md` files with YAML frontmatter — more declarative and git-tracked. deer-flow's approach is code-defined (Python dataclasses). OwlBear's approach is superior for a multi-project system because agent definitions travel with the project.

### 3F. Subagent Delegation vs OwlBear Orchestrator Dispatch

| Aspect | deer-flow `task()` tool | OwlBear orchestrator dispatch |
|--------|------------------------|------------------------------|
| Invocation | LLM calls `task()` tool inline during conversation | Planner builds wave JSON, dispatches via ACP/runSubagent |
| Context isolation | Subagent gets clean context (only task prompt) | Each agent gets fresh VS Code chat session |
| Tool filtering | allowlist/denylist per SubagentConfig | `tools:` field in `.agent.md` (assign/inherit) |
| Concurrency | 3 max (SubagentLimitMiddleware truncates excess calls) | Wave size 4 (ACP dispatch) |
| Result passing | Polling via `get_background_task_result()`, SSE events | Channel A signal + Channel B task body |
| Trace ID | UUID propagated parent→child via metadata | Not yet implemented (see #434) |
| Nesting prevention | `task` tool excluded from subagent tool lists | `disable-model-invocation: true` on pipeline agents |
| Timeout | Per-subagent configurable (default 900s) | VS Code session-level only |

**Key differences:** deer-flow is _model-driven_ delegation (LLM decides when to delegate), OwlBear is _planner-driven_ delegation (orchestrator determines dispatch order). deer-flow's approach gives the LLM more autonomy; OwlBear's approach gives the human more control via the kanban board.

**Transferable patterns:** (1) SubagentLimitMiddleware's approach of silently truncating excess parallel calls rather than erroring — applicable to OwlBear's wave dispatch, (2) trace ID propagation (#434 already planned), (3) structured SubagentResult with status enum — OwlBear's Channel A/B system is more sophisticated but could benefit from an enum-based status model.

## 4. Recommendations

| Pattern | Target | Conf | Priority | Action |
|---------|--------|------|----------|--------|
| Fact schema (id/content/category/confidence/source) | #387 | .85 | needed | Adopt as basis for memory-mcp entry schema |
| Confidence threshold gating | #387 | .80 | needed | Use 0.7 default, configurable per scope |
| Content-normalized dedup | #387 | .85 | needed | Adopt whitespace-normalized comparison |
| Max-capacity pruning | #387 | .75 | important | Drop lowest-confidence when capacity exceeded |
| Token-budgeted injection | #387 | .80 | needed | MCP tool returns token-counted response |
| Pluggable storage ABC | #387 | .70 | important | Storage provider interface for SQLite/JSON backends |
| Category taxonomy (5 types) | #387 | .75 | important | Adopt preference/knowledge/context/behavior/goal |
| Dual-pool separation concept | Informational | .65 | N/A | Not directly applicable — OwlBear has no persistent executor |
| Trace ID propagation | #434 | .80 | nice-to-have | Already captured by #434 |

## 5. Tier Classification and Follow-up

**T3 classification:** This research recommends adoption of patterns into #387 (new capability: memory-mcp server). A T3 blocking decision request was created and resolved by the user on 2026-04-01.

**Decision:** `docs/decisions/resolved/428-adopt-deer-flow-memory-patterns.md` — User approved a custom selection: patterns 1 (fact schema), 2 (confidence threshold gating), and 6 (category taxonomy) adopted unchanged; pattern 4 (max-capacity pruning) customized to soft-delete only (mark for deletion/hide from output; only user may permanently delete). Patterns 3, 5 not approved.

**Follow-up tasks created at `ideation`:**

- #499 — Incorporate deer-flow memory patterns into memory-mcp design (#387)
- #500 — Evaluate deer-flow subagent patterns for wave dispatch
