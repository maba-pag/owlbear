# Mission Control — Research Analysis

> **Owning task:** #598 — MeisnerDan/mission-control
> **Date:** 2026-03-06 **Status:** Complete

## 1. Context and Question

Evaluate Mission Control (v0.9.0) for patterns applicable to OwlBear: daemon orchestration, task management UI, agent communication, loop detection, cost tracking, session resilience, and token-optimized context injection.

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| Mission Control README | https://github.com/MeisnerDan/mission-control | .90 |
| Mission Control CLAUDE.md (agent ops manual) | (cloned repo analysis) | .85 |
| Mission Control daemon/ (dispatcher, runner, scheduler, security, health, config, prompt-builder) | (cloned repo analysis) | .90 |
| Mission Control data layer (data.ts, validations.ts, types.ts, generate-context.ts) | (cloned repo analysis) | .80 |

## 3. Analysis

### 3.1 Architecture Comparison

| Criterion | Mission Control | OwlBear | Delta |
|-----------|----------------|---------|-------|
| Language | TypeScript/Next.js | Python/PydanticAI | Different stacks |
| Storage | JSON flat files + async-mutex | SQLite + Qdrant + JSONL | OwlBear more robust |
| Agent execution | Spawns `claude -p` CLI | In-process PydanticAI agents | OwlBear more integrated |
| Task board | Next.js web UI (Eisenhower + Kanban) | kanban-md (file-based CLI) | MC has visual UI |
| Daemon | Node.js process, cron, polling | Planned standalone daemon | MC is ahead here |
| Agent comms | JSON file inbox + decisions queue | Slack + CLI channels | OwlBear richer channels |
| Knowledge | None | SQLite graph + Qdrant vectors | OwlBear significantly ahead |

### 3.2 Patterns Worth Adopting

| Pattern | MC Implementation | OwlBear Applicability | Confidence |
|---------|-------------------|----------------------|------------|
| **Loop detection** | `LoopDetectionState`: per-task attempt counter + error history; escalates to user decision after 3 failures | High — OwlBear orchestrator has no failure loop detection; ErrorJournal exists but isn't wired to circuit-break | .85 |
| **Token-optimized context snapshot** | `generate-context.ts` compresses all workspace state into ~650 tokens as `ai-context.md` | Medium — OwlBear's `KnowledgeQueryService` does per-turn injection but has no compact board-state summary for agents | .70 |
| **Session resilience (continuations)** | Agents that timeout/max-turns auto-spawn continuation sessions; progress preserved in task notes + subtasks; configurable `maxTaskContinuations` | Medium — OwlBear agents run in-process so timeouts are less common, but long tasks could benefit from checkpointing | .65 |
| **Cost/usage tracking** | Captures cost + full token breakdown (input, output, cache read, cache creation) per session; aggregated on daemon dashboard | High — OwlBear has no cost tracking; useful for budget awareness and optimization | .80 |
| **Credential scrubbing** | 15+ regex patterns for API keys, tokens, SSH keys, connection strings; applied before logging/storing | Medium — OwlBear has `error_to_user_message()` but MC's regex library is more comprehensive | .60 |
| **Retry queue with exponential backoff** | Persistent JSONL retry queue; delay = `base * 2^(attempt-1)`, capped at 60 min | Low — OwlBear uses tenacity for HTTP retries; daemon dispatch retries are a future concern | .50 |
| **Eisenhower matrix prioritization** | 2-axis (importance × urgency) → 4 quadrants (Do/Schedule/Delegate/Eliminate) | Low — OwlBear uses 5-tier linear priority; Eisenhower adds UI complexity without clear benefit for single-operator use | .35 |
| **Safe env for child processes** | `buildSafeEnv()` strips all env vars except PATH, HOME, APPDATA, TEMP, SystemRoot; prevents credential leakage | Medium — OwlBear's `TerminalToolset` confines working_dir but doesn't sanitize env for subprocesses | .65 |

### 3.3 Patterns Not Applicable

| Pattern | Reason for Rejection |
|---------|---------------------|
| JSON flat-file storage | OwlBear uses SQLite + Qdrant — strictly better for concurrent access |
| Spawning external CLI as agent executor | OwlBear runs agents in-process via PydanticAI — tighter integration, lower latency |
| Web UI dashboard | OwlBear uses CLI + Slack as channels; a web UI is out of scope per YAGNI |
| Agent command file auto-generation | OwlBear uses `.agent.md` files directly — no sync layer needed |
| Zod validation schemas | Pydantic models serve the same purpose in OwlBear's stack |

## 4. Recommendation (.80 confidence)

**Adopt two patterns immediately, investigate one more:**

1. **Loop detection for orchestrator** (.85) — Add per-task failure counting to the orchestrator's wave dispatch. After N failures (configurable, default 3), skip the task and escalate to user via Slack/CLI channel with retry/skip/stop options. Wire into existing `ErrorJournal` for persistence.

2. **Cost/usage tracking** (.80) — Add per-session token/cost capture to agent runs. OwlBear already gets usage data from PydanticAI's `result.usage()` — surface it in session logs and provide a `bearclaw stats` CLI command.

3. **Investigate: compact board-state context** (.70) — MC's `ai-context.md` approach (compressed workspace snapshot) could improve agent situational awareness. Evaluate whether a `kanban-md list --compact` dump injected into agent system prompts via `KnowledgeQueryService` achieves the same goal without a custom generator.

The credential scrubbing patterns and safe-env subprocess isolation are useful but lower priority — OwlBear already has partial coverage and these are incremental improvements.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Implement loop detection in orchestrator dispatch" --priority needed --tags "phase-daemon,agent,orchestrator" --body "Add per-task failure counting to orchestrator wave dispatch. After configurable max failures (default 3), skip task and escalate to user via channel (Slack/CLI) with retry/skip/stop options. Persist attempt counts in ErrorJournal. See docs/mission-control-research.md §3.2 and §4."

kanban\kanban-md.exe create "Add per-session cost/token tracking to agent runs" --priority important --tags "phase-daemon,agent,observability" --body "Capture token usage (input, output, cache_read, cache_creation) and estimated cost from PydanticAI result.usage() after each agent run. Store in session log (JSONL). Add 'bearclaw stats' CLI command for aggregated view. See docs/mission-control-research.md §3.2 and §4."

kanban\kanban-md.exe create "Evaluate compact board-state context injection for agents" --priority nice-to-have --tags "research,agent,knowledge" --body "Investigate injecting a compressed kanban board snapshot into agent system prompts for situational awareness. Compare MC's generate-context.ts approach (~650 tokens) vs piping kanban-md list --compact output. Determine if KnowledgeQueryService is the right injection point. See docs/mission-control-research.md §3.2 and §4."
```
