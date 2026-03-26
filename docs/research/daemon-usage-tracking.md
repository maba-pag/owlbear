# Daemon Builder Dispatch Usage Tracking

> **Owning task:** #845 — Track LLM usage in daemon poll_tick builder dispatch
> **Date:** 2026-03-25 **Status:** Complete

## 1. Context and Question

The daemon's `poll_tick` dispatches builder agents via `agent_registry.get("builder").run(prompt, **run_kwargs)`. These are raw PydanticAI `Agent` instances — not `OwlBearAgent` — so usage is untracked. Task #844 wired `record_agent_usage()` to 8 secondary call sites but left the daemon dispatch (the highest token consumer in autonomous mode) untouched.

Question: What is the simplest way to record usage after each builder dispatch, using the infrastructure from #844?

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| PydanticAI Agent.run docs | <https://ai.pydantic.dev/api/agent/> | .95 | run returns AgentRunResult with .usage(); also accepts usage param as accumulator |
| PydanticAI RunUsage docs | <https://ai.pydantic.dev/api/usage/> | .90 | RunUsage dataclass with requests, tool_calls, input_tokens, output_tokens fields |
| OwlBear daemon.py | src/owlbear/daemon.py L759-975 | 1.0 | _run_builder_with_context wraps builder.run in async fallback; two dispatch sites |
| OwlBear record_agent_usage | src/owlbear/memory/usage.py L119-180 | 1.0 | Existing helper: no-op when tracker is None; swallows exceptions |
| OwlBear OwlBearDeps.tracker | src/owlbear/core/deps.py L30 | .85 | tracker field exists on deps but _build_builder_run_kwargs does not set it |
| OwlBear secondary wiring #844 | src/owlbear/core/condenser.py L88-100 | .90 | Established pattern: call record_agent_usage inline after Agent.run |

## 3. Analysis

### Option A — Inline wrapper in `_run_builder_with_context` (.85 confidence)

Modify `_run_builder_with_context` to accept `tracker`, `model`, `provider` and call `record_agent_usage()` after awaiting the result.

| Criterion | Assessment |
|-----------|------------|
| Diff size | ~20 LOC in daemon.py + signature changes at 2 call sites |
| Pattern consistency | Matches #844's condenser/hook pattern exactly |
| State management | None — result is captured inline |
| Error resilience | `record_agent_usage` already swallows exceptions |
| KISS | High |

### Option B — `RunUsage` accumulator on `RunningTask` + `reconcile_tasks` (.65 confidence)

Add `usage: RunUsage` to `RunningTask`, pass via `run_kwargs["usage"]`, read in `reconcile_tasks`.

| Criterion | Assessment |
|-----------|------------|
| Diff size | ~40 LOC across 3 functions + dataclass change |
| Pattern consistency | Different from #844's secondary sites (accumulator vs inline) |
| State management | Mutable `RunUsage` stored per task; need model/provider on `RunningTask` too |
| Error resilience | Usage lost on task crashes unless read from `RunningTask` in `reconcile_tasks` error path |
| KISS | Medium — more moving parts for the same outcome |

### Option C — Pass tracker via `OwlBearDeps` and rely on builder-internal recording (.50 confidence)

Set `tracker=` on the `OwlBearDeps` built by `_build_builder_run_kwargs`. The builder agent's tools could access `deps.tracker`.

| Criterion | Assessment |
|-----------|------------|
| KISS | Low — the raw PydanticAI Agent has no built-in recording logic; tools don't call `record_agent_usage()` |
| Completeness | Only captures tool-level calls, not the outer `Agent.run()` usage |

## 4. Recommendation (.85 confidence)

**Option A — inline wrapper.** It is the smallest diff, follows the exact pattern established by #844, and needs no dataclass changes. The `_run_builder_with_context` function already wraps the coroutine — adding a `record_agent_usage()` call after `await` is a natural extension.

Implementation sketch:

1. Add `tracker: UsageTracker | None`, `model: str | Model`, `provider: str` params to `_run_builder_with_context`.
2. In the `_await_run()` inner coroutine, capture `result = await run_coro`, call `record_agent_usage(tracker=tracker, result=result, model=model, provider=provider, session_id=f"background:builder_dispatch", operation="builder_dispatch")`, then `return result`.
3. Thread `tracker`/`provider` through `poll_tick` and `poll_loop` from `run_daemon` (where `agent.tracker` and `settings.provider` are available).
4. Get model from `builder.model` (PydanticAI Agent property) or from `settings`.

Risk: the TypeError fallback path (`builder.run(prompt)`) also needs recording. The wrapper should handle both code paths.

## 5. Follow-up Tasks

Refined AC for #845 based on research (replaces original AC):

1. Add `tracker: UsageTracker | None = None` and `provider: str = "copilot"` parameters to `poll_tick` and `poll_loop`.
2. Thread these from `run_daemon` using `agent.tracker` and `settings.provider`.
3. Add `tracker`, `model`, `provider` params to `_run_builder_with_context`; call `record_agent_usage()` with `operation="builder_dispatch"` and `session_id="background:builder_dispatch"` after both the normal and fallback `.run()` paths.
4. Both retry-dispatch and fresh-dispatch call sites pass tracker/model/provider.
5. Existing daemon tests pass; new tests verify recording in both dispatch paths.
