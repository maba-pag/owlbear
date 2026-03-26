# Dispatched Agent Runtime Context

> **Owning task:** #951 — Inject runtime task and workspace context into dispatched agent prompts
> **Date:** 2026-03-23 **Status:** Complete

## 1. Context and Question

OwlBear already has one proven runtime-instruction seam: `OwlBearAgent.turn()` appends board and knowledge context via PydanticAI's per-run `instructions=` argument. Child-agent dispatch does not use the same seam. `DelegationToolset._delegate()` forwards only the delegated task text plus copied deps and usage, and daemon `poll_tick()` builds builder prompts inline in both the retry and fresh-dispatch paths. Task #951 asks how to inject task, workspace, and channel context into dispatched agents without copying mutable text into the markdown agent definitions. [S1, S2, S5, S6, S7]

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | PydanticAI instructions docs | .95 | Static vs dynamic vs runtime instructions and append order |
| S2 | PydanticAI Agent.run() API | .95 | Per-run `instructions` and `metadata` parameters |
| S3 | PydanticAI multi-agent docs | .85 | Delegation and deps or usage passthrough patterns |
| S4 | Ruflo `AGENTS.md` | .80 | Layered coordination context around executor prompts |
| S5 | OwlBear `src/owlbear/core/agent.py` | 1.0 | Existing runtime instruction merge point in `turn()` |
| S6 | OwlBear `src/owlbear/core/delegation.py` | 1.0 | Current delegated child-agent call shape |
| S7 | OwlBear `src/owlbear/daemon.py` | 1.0 | Manual builder prompt assembly in retry + fresh dispatch |
| S8 | OwlBear `src/owlbear/bootstrap/__init__.py` and `src/owlbear/core/hooks.py` | .90 | Where workspace and channel identity already exist at runtime |
| S9 | OwlBear `tests/test_delegation.py` and `tests/test_daemon_coverage_gaps.py` | .90 | Existing verification seams for run kwargs and prompt construction |
| S10 | OwlBear prior research: `wire-board-context-into-turn.md` and `context-aware-knowledge-injection.md` | .90 | Existing repo decision to use per-run `instructions=` for dynamic context |

## 3. Analysis

### 3.1 Current Gap

`OwlBearAgent.turn()` already proves the core mechanism: gather runtime context, concatenate non-empty pieces, and pass one `instructions=` string into `inner.run(...)`. That keeps static instructions in markdown and dynamic context at call time. Child dispatch paths do not do this today: `delegate_to_agent` calls `agent.run(task, deps=inner_deps, usage=ctx.usage)`, while `poll_tick()` duplicates `Build task #...` prompt assembly in two branches and never passes runtime instructions or metadata. [S1, S2, S5, S6, S7, S10]

### 3.2 Option Matrix

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| A. Shared runtime dispatch builder returning `instructions` and optional `metadata` | Reuses OwlBear's existing per-run pattern; no agent-file duplication; works for delegation and daemon dispatch | Requires one small shared helper and a runtime context carrier | Recommend |
| B. Copy task/workspace/channel text into each agent markdown file | No runtime plumbing | Violates AC; duplicates mutable context across static files; drifts quickly | Reject |
| C. Keep putting all context into the user prompt string only | Small diff in daemon path | Leaves delegation inconsistent; mixes environment context with task body, WIP, and hydration text; duplicates formatting logic | Reject |
| D. Use `metadata` only | Good for tracing | Metadata is not LLM-visible, so agents would not actually receive the context | Reject |

### 3.3 Recommended Shape

Add one shared runtime helper that formats concise dispatch context blocks such as `Current Task`, `Workspace`, and `Channel`, then returns:

1. an `instructions` string for LLM-visible context
2. an optional `metadata` dict for structured observability

Both dispatched-agent paths should call the same helper. `DelegationToolset._delegate()` should keep passing the delegated task as the user prompt, but add the helper's `instructions=` and `metadata=` kwargs to `agent.run(...)`. `poll_tick()` should keep the task body, hydrated excerpts, and WIP summary in the main prompt, but move environment context out of the prompt-string f-strings and into the same runtime helper in both the retry and fresh-dispatch branches. [S1, S2, S4, S6, S7, S9, S10]

The helper needs access to runtime state that static markdown files do not have. The lowest-diff carrier is immutable run state, not rewritten agent definitions. A small dispatch-context object on `OwlBearDeps` can hold `workspace_root`, `channel_name`, and optional kanban task fields. `delegate_to_agent()` already clones deps, so inherited workspace or channel or current-task context naturally flows to subagents; daemon builder dispatch should construct the same deps shape before calling `builder.run(...)` instead of invoking the raw agent without deps. Missing task fields must remain optional so interactive chat delegation does not invent a fake kanban task. [S3, S6, S7, S8]

### 3.4 Scope Boundary

Do not move static role instructions, skills, or workflow rules into the runtime layer. Those already belong in the markdown agent files and `ContextManager`. Do not move pre-hydrated task references or WIP summaries into runtime instructions either; those are task content and existing daemon tests already treat them as prompt text. The runtime layer should carry only dispatch environment: which task is active, which workspace is in scope, and which channel invoked the run. [S2, S5, S7, S9, S10]

### 3.5 Testing Strategy

Use the existing narrow test seams instead of inventing a new integration harness:

| Area | Test seam | Assertion |
|------|-----------|-----------|
| Delegation | `tests/test_delegation.py` | Child `run()` gets `instructions` and `metadata` kwargs, while usage passthrough and depth increment still hold |
| Fresh daemon dispatch | `tests/test_daemon_coverage_gaps.py` | Builder `run()` receives runtime instructions for task/workspace/channel and still keeps task body in the prompt |
| Retry daemon dispatch | `tests/test_daemon_coverage_gaps.py` | Retry path uses the same helper as fresh dispatch, not a second formatter |
| Hydration coexistence | `tests/test_hydration_integration.py` | Pre-hydrated content remains appended to the prompt, not duplicated into runtime instructions |

This keeps #951 focused on runtime prompt assembly rather than broad AgentRegistry refactors. [S2, S7, S9]

## 4. Recommendation (.87 confidence)

Implement option A: a shared runtime dispatch builder plus a small immutable dispatch-context carrier. Keep markdown agent files unchanged. Pass task/workspace/channel context through PydanticAI per-run `instructions=` so child agents actually see it, and use per-run `metadata=` only for traceability. Wire the same helper into both `delegate_to_agent()` and daemon `poll_tick()` so OwlBear stops maintaining two different dispatch-context conventions. [S1, S2, S5, S6, S7, S10]

Risks and constraints:

- `poll_tick()` currently calls child agents without `deps`, so the implementation must standardize builder runs before delegation and daemon dispatch can share the same runtime carrier. [S6, S7]
- Interactive delegation may not have a kanban task ID; the formatter must omit unknown fields instead of fabricating them. [S6, S8]
- Keep the runtime instructions short. This layer is environment context, not another place to paste the task body. [S1, S2, S7]

## 5. Follow-up Tasks

No new follow-up tasks needed — #951 itself is already the implementation task.

### Refined AC for #951

1. Add a runtime dispatch-context carrier with `workspace_root`, `channel_name`, and optional task metadata.
2. Add one shared formatter that turns that carrier into per-run `instructions=` and optional `metadata=`.
3. Update `DelegationToolset._delegate()` to pass the shared runtime context while preserving usage passthrough and depth increment.
4. Update daemon `poll_tick()` retry and fresh-dispatch branches to use the same formatter and the same deps shape.
5. Leave markdown agent definitions unchanged; do not duplicate task/workspace/channel text across agent files.
6. Keep WIP and pre-hydrated task content in the main prompt, not the runtime instruction layer.
7. Add or update tests in the existing delegation and daemon suites for both fresh and retry dispatch paths.
