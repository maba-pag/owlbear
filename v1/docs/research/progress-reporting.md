# Progress Reporting — Periodic Status Updates to User

> **Owning task:** #298 — Progress reporting — periodic status updates to user
> **Date:** 2026-03-01
> **Status:** Complete

## 1. Context and Question

OwlBear runs as a daemon processing long-running tasks (research, code generation, test runs). During these operations, the user has no visibility into what OwlBear is doing. Task #298 requires a `ProgressReporter` that pushes periodic status updates through the active channel (CLI, Slack, future Voice).

Key questions investigated:

1. What mechanisms do other AI agent frameworks use for progress reporting?
2. How should updates be throttled to avoid spam without losing visibility?
3. How to aggregate progress from multiple concurrent tasks?
4. How to make reporting channel-agnostic via existing `ChannelPlugin`?
5. How to track kanban board state changes within progress updates?

Constraints: async/non-blocking, must not interrupt the agent's tool loop, channel-agnostic, KISS.

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| CrewAI Event System | <https://docs.crewai.com/concepts/event-listener> | .85 | BaseEventListener bus with 30+ typed events (TaskStartedEvent, ToolUsageStartedEvent, AgentExecutionCompletedEvent); scoped handlers; all events carry timestamp + type |
| AutoGen AgentChat | <https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/agents.html> | .75 | `run_stream()` yields `BaseAgentEvent` messages; `Console` UI renders progress; `ToolCallRequestEvent`/`ToolCallExecutionEvent` for tool-level visibility |
| PydanticAI AgentStreamEvent | <https://ai.pydantic.dev/agents/> | .90 | `event_stream_handler` callback, `agent.iter()` graph iteration, FunctionToolCallEvent/FunctionToolResultEvent/FinalResultEvent — our framework's native progress API |
| OwlBear NotificationHook | `src/owlbear/core/notification_hook.py` | .95 | Backend priority chain pattern (try backends in order, first success stops chain), register on configured events, errors logged and swallowed |
| OwlBear ObservabilityHook | `src/owlbear/core/observability.py` | .90 | PRE/POST_TOOL_USE timer tracking, structured JSONL events, `duration_ms` calculation — the data source for progress |
| OwlBear HookedToolset | `src/owlbear/tools/hooked.py` | .90 | Wraps all toolsets, emits PRE/POST_TOOL_USE hooks with tool_name and args/result — the event stream |
| Python asyncio patterns | <https://docs.python.org/3/library/asyncio-task.html> | .80 | `asyncio.create_task()` for background tickers, `asyncio.Event` for signaling, task cancellation patterns |

## 3. Analysis

### 3.1 Progress Reporting Patterns in AI Frameworks

| Criterion | CrewAI EventListener | AutoGen run_stream | PydanticAI event_stream_handler | OwlBear Hook + Timer |
|-----------|---------------------|-------------------|-------------------------------|---------------------|
| Architecture | Singleton event bus | AsyncIterator | Callback on stream | Hook registry + background task |
| Granularity | 30+ event types | Per-message | Per-part/tool-call | Per POST_TOOL_USE |
| User-facing? | No (monitoring) | Yes (Console UI) | Yes (stream to client) | Yes (channel.send) |
| Throttling | None built-in | None (streams all) | None (streams all) | Time-based (configurable) |
| Multi-task | Scoped handlers | Per-agent stream | Per-run | Per session_id dict |
| KISS fit | Medium (30+ types) | Medium (iterator) | Low (requires iter API) | High (reuses hooks) |

**Key insight:** All frameworks use event/callback mechanisms. None embed progress logic in the agent core. CrewAI and OwlBear both use event buses; PydanticAI uses streaming iterators. OwlBear's HookRegistry is the natural integration point.

### 3.2 Reporting Mechanism Options

| Option | Description | Non-blocking? | Channel-agnostic? | KISS | Recommendation |
|--------|-------------|:---:|:---:|:---:|:---:|
| A. Hook-only (check elapsed time on each POST_TOOL_USE) | On each tool completion, check if interval elapsed, send if so | Yes | Yes | Highest | .70 — misses updates during long tool calls |
| B. Background asyncio.Task ticker | Spawn task that wakes every N seconds, queries accumulated state | Yes | Yes | High | .80 — clean separation but needs lifecycle management |
| C. Hybrid (hook accumulates, timer sends) | Hook on POST_TOOL_USE tracks state; background timer sends updates | Yes | Yes | High | .85 — best of both: accurate state + regular cadence |

### 3.3 Throttling Strategies

| Strategy | Description | Pros | Cons | KISS |
|----------|-------------|------|------|:---:|
| Time-based (fixed interval) | Send every N seconds | Predictable, simple | May send "no change" updates | Highest |
| Event-count-based | Send after every N tool calls | Activity-proportional | Unpredictable timing | Medium |
| Time + activity gate | Send every N seconds, but only if activity occurred since last update | No spam when idle | Slightly more state | High |
| Adaptive (backoff on idle) | Increase interval when idle, decrease on activity | Optimal frequency | Complex state machine | Low |

**Recommendation (.85):** Time-based with activity gate. Send every `progress_interval` seconds, skip if `_tool_count` hasn't changed since the last update. ~5 LOC over pure time-based, eliminates idle spam.

### 3.4 Multi-task Aggregation

The daemon currently processes one message at a time in `run_daemon`'s sequential loop. However, sub-agents (via `DelegationToolset`) can create nested execution contexts. `POST_TOOL_USE` events already carry `agent_name` via `ObservabilityHook`. For multi-task:

| Approach | Description | Complexity | KISS |
|----------|-------------|:---:|:---:|
| Single counter (no per-task) | One global tool_count + last_tool | Lowest | Highest |
| Per-session tracking | Dict keyed by session_id from hook data | Medium | High |
| Per-agent tracking | Dict keyed by agent_name from hook data | Medium | High |

**Recommendation (.80):** Start with single-counter (YAGNI). The daemon loop is sequential — one turn at a time. Add per-agent tracking only when concurrent delegation is actually implemented. The data model should allow extension (use a `@dataclass` for state).

### 3.5 Channel-Agnostic Reporting

The existing `ChannelPlugin.send()` is the natural output path. The `ProgressReporter` receives a `ChannelPlugin` reference at construction (same pattern as `AskUserToolset`). No new protocol needed.

| Approach | Description | KISS |
|----------|-------------|:---:|
| Send via ChannelPlugin.send() | Direct call to active channel | Highest |
| Send via NotificationHook backends | Reuse notification backend chain | Medium (over-engineered for text updates) |
| New ProgressChannel protocol | Dedicated progress output protocol | Low (YAGNI) |

**Recommendation (.90):** Use `ChannelPlugin.send()` directly. Progress updates are conversational output (like agent responses), not alerts. The channel is the right abstraction.

### 3.6 Message Format

Brief: `⏳ Working on task... (5 tools called, last: run_command, 45s elapsed)`
Detailed: `⏳ Progress: 5 tool calls in 45s | Last: run_command (args: pytest tests/) | Agent: coder | Session: abc123`

Both fit a single Slack message, CLI line, or TTS sentence.

### 3.7 Lifecycle Management

The `ProgressReporter` must start/stop with the daemon turn:

1. **Start** — when `OwlBearAgent.turn()` begins (ON_MESSAGE hook)
2. **Stop** — when turn completes (natural exit or error)
3. **Cleanup** — cancel background timer task on stop

This maps to ON_MESSAGE (start timer) and turn completion (cancel timer). The reporter can also hook TASK_COMPLETE to send a final summary.

### 3.8 Configuration

Add to `OwlBearSettings` (matches existing `notification_*` pattern):

```python
progress_enabled: bool = True
progress_interval: float = 30.0  # seconds between updates
progress_detail: Literal["brief", "detailed"] = "brief"
```

Environment variables: `OWLBEAR_PROGRESS_ENABLED`, `OWLBEAR_PROGRESS_INTERVAL`, `OWLBEAR_PROGRESS_DETAIL`.

## 4. Recommendation (.85 confidence)

**Implement `ProgressReporter` as a hook-based class with a background asyncio timer, sending updates via `ChannelPlugin.send()`.**

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Architecture | Hook accumulates + timer sends | Clean separation: hooks are event collectors, timer is the reporter |
| Throttling | Time-based + activity gate | Predictable cadence, no spam when idle |
| Multi-task | Single counter initially | YAGNI — sequential daemon loop, extend later if needed |
| Channel output | ChannelPlugin.send() | Reuses existing abstraction, channel-agnostic |
| Configuration | OwlBearSettings fields | Matches notification_* pattern, env-var override |
| Lifecycle | ON_MESSAGE starts, turn-end stops | Timer lives exactly as long as a turn |
| Detail levels | brief / detailed | User choice: minimal vs. full context |
| Integration point | build_hooks() in bootstrap.py | Same wiring pattern as NotificationHook |

Estimated implementation: ~120 LOC for `ProgressReporter`, ~20 LOC for config, ~30 LOC for bootstrap wiring, ~100 LOC for tests. Total: ~270 LOC.

Risks:

| Risk | Severity | Mitigation |
|------|----------|------------|
| Timer races with daemon shutdown | Low | Cancel timer in finally block, swallow CancelledError |
| Channel.send() blocks on Slack API | Low | Fire-and-forget via `asyncio.create_task(channel.send(...))` |
| Update noise annoys user | Medium | Default 30s interval, activity gate, `progress_enabled=False` to disable |
| State accumulation memory leak on long sessions | Low | Reset counters on each turn start |

## 5. Follow-up Tasks

1. **Add progress config to OwlBearSettings** — `progress_enabled`, `progress_interval`, `progress_detail` fields
2. **Create ProgressReporter class** — hook-based accumulator + background timer + channel output
3. **Wire ProgressReporter in bootstrap** — register in `build_hooks()`, pass channel reference
4. **Unit tests for ProgressReporter** — mock channel, verify cadence, activity gate, format
