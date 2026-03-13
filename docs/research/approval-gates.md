# Approval Gates — Explicit User Confirmation for Destructive Actions

> **Owning task:** #299 — Approval gates — explicit user confirmation for destructive actions
> **Date:** 2026-03-01
> **Status:** Complete

## 1. Context and Question

`CommandSafetyGuard` exists as a `PRE_TOOL_USE` hook that blocks dangerous commands via regex blocklists. However, `HookRegistry.emit()` swallows all exceptions — so `BlockedCommandError` is logged at WARNING but the tool call **still proceeds**. The guard effectively only warns, it cannot enforce.

For a real autonomous system, destructive actions (git push, file delete, PR creation, `pip install`) need **interactive user approval** before proceeding. The approval mechanism must work across all channels (CLI, Slack, voice) with timeout-to-cancel semantics and session-level pre-grants.

**Key questions:**

1. Which operations should require approval?
2. What approval mechanism fits OwlBear's architecture (hook-based vs toolset-based)?
3. How should timeout, pre-grants, and observability integrate?
4. How to annotate actions as requiring approval?

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| PydanticAI Deferred Tools | <https://ai.pydantic.dev/deferred-tools/> | .90 | `ApprovalRequired` exception, `DeferredToolRequests/Results`, `ApprovalRequiredToolset` — framework-native approval gates |
| PydanticAI ApprovalRequiredToolset | <https://ai.pydantic.dev/toolsets/#requiring-tool-approval> | .95 | `.approval_required(fn)` wrapper on any toolset; returns `DeferredToolRequests` output |
| LangGraph Interrupts | <https://docs.langchain.com/oss/python/langgraph/interrupts> | .70 | `interrupt()` function pauses graph execution, `Command(resume=...)` continues; approve/reject pattern |
| OwlBear CommandSafetyGuard | `src/owlbear/core/command_guard.py` | 1.0 | Existing PRE_TOOL_USE hook with regex blocklists; raises `BlockedCommandError` (swallowed by emit) |
| OwlBear HookedToolset | `src/owlbear/tools/hooked.py` | .95 | `WrapperToolset` emitting PRE/POST hooks; current interception layer for tool calls |
| OwlBear AskUserToolset | `src/owlbear/tools/ask_user.py` | .90 | Channel-based ask_user with timeout, option validation, `TimeoutAction.ABORT/SKIP` |
| OwlBear HookRegistry | `src/owlbear/core/hooks.py` | .95 | Hook emit swallows all exceptions — hooks cannot block execution |

## 3. Analysis

### 3.1 Critical Architecture Observation

`HookRegistry.emit()` catches all exceptions from handlers and logs them (line 80–88 of `hooks.py`). This means `BlockedCommandError` raised by `CommandSafetyGuard` is **swallowed** — the tool call proceeds regardless. Test `test_emit_blocked_command_swallowed_by_registry` in `test_command_guard.py` explicitly confirms this behavior.

**Implication:** Approval gates cannot be implemented as hooks under the current `emit()` semantics. We need either (a) toolset-level interception or (b) a new `emit_blocking()` variant.

### 3.2 Approval Mechanism Options

| Criterion | A: PydanticAI `ApprovalRequiredToolset` (.70) | B: Custom `ApprovalGateToolset(WrapperToolset)` (.85) | C: Hook-level with `emit_blocking()` (.50) |
|-----------|------|------|------|
| Framework alignment | Native PydanticAI | Custom but follows `HookedToolset` precedent | Requires changing hook semantics |
| Run loop changes | Must handle `DeferredToolRequests` output type in `OwlBearAgent.run_turn()` | None — approval resolves inline via `channel.receive()` | Must propagate exceptions from `emit()` |
| Session pre-grants | Hard — deferred flow exits agent run, re-enters with results | Easy — check grant set before asking | Possible but mixes concerns |
| Channel integration | Caller handles approval UI outside agent | Injected channel used directly in `call_tool()` | Channel not available in hook context |
| Composability | Chains with `.filtered()`, `.prefixed()`, etc. | Nests inside/outside `HookedToolset` | Conflicts with existing swallow semantics |
| KISS score | Medium — deferred tool flow is powerful but complex for our use case | High — ~100 LOC, uses existing patterns | Low — changes core infrastructure |
| Timeout handling | Caller must implement timeout around approval UI | Built-in via `asyncio.wait_for()` on `channel.receive()` | Would need timeout in hook |

### 3.3 Why NOT PydanticAI-native `ApprovalRequiredToolset`?

PydanticAI's `ApprovalRequiredToolset` is designed for architectures where the agent run must **end** so an external system (web UI, API client) can display the approval prompt and resume later. OwlBear is a **daemon with live channel connections** — when `git_push` needs approval, we can ask the user via CLI/Slack and wait for their answer within the same tool call. The deferred-tool flow adds unnecessary complexity:

- Agent run ends with `DeferredToolRequests` → caller parses approvals → asks user → builds `DeferredToolResults` → resumes run with message history
- vs. simply: tool call pauses → asks user via channel → proceeds or cancels

YAGNI applies — we don't need the deferred flow's ability to serialize approval requests to external systems.

### 3.4 Actions Requiring Approval

| Category | Tool / Action | Risk Level | Default |
|----------|--------------|------------|---------|
| Git push | `git_push` | High — publishes code | Require |
| Force push | `run_command` with `git push --force` | Critical — rewrites history | Block (keep in CommandSafetyGuard) |
| PR creation | `create_pr` | High — creates external artifact | Require |
| File deletion | `run_command` with `rm`, `del` | Medium — data loss | Require |
| Package install | `run_command` with `pip install` (non-uv) | High — supply chain risk | Block (keep in CommandSafetyGuard) |
| Deploy commands | `run_command` with `deploy`, `publish` | Critical — production impact | Require |
| Task archival | `kanban_move` to `done` | Low — reversible | Optional |
| Branch creation | `git_branch` | Low — non-destructive | Skip |

**Two-tier model:** `CommandSafetyGuard` hard-blocks always-forbidden actions. `ApprovalGateToolset` gates actions that are allowed but need confirmation.

### 3.5 Recommended Design

```
┌─────────────────────────────────────────────────┐
│               ApprovalGateToolset               │
│  (WrapperToolset — checks ApprovalPolicy)       │
│  ┌─────────────────────────────────────────────┐│
│  │             HookedToolset                   ││
│  │  (emits PRE/POST hooks)                     ││
│  │  ┌─────────────────────────────────────────┐││
│  │  │   Inner Toolset (GitLocal, Terminal…)   │││
│  │  └─────────────────────────────────────────┘││
│  └─────────────────────────────────────────────┘│
└─────────────────────────────────────────────────┘
```

**Components:**

1. **`ApprovalPolicy`** (Pydantic BaseModel) — configurable list of tool names + optional arg patterns requiring approval. Loaded from `OwlBearSettings`.

2. **`ApprovalSession`** — per-session state: tracks pre-granted tool names, approval history.

3. **`ApprovalGateToolset(WrapperToolset)`** — wraps toolsets, intercepts `call_tool()`:
   - Check if `(tool_name, args)` matches policy
   - Check session pre-grants → if pre-granted, proceed
   - Ask user via `channel.send()/receive()` with `asyncio.wait_for(timeout)`
   - On approve: proceed + log event
   - On deny: return cancellation message to model + log event
   - On timeout: return cancellation message (safe default) + log event
   - On "approve all {tool} this session": add to pre-grants + proceed

4. **`ObservabilityHook`** integration — approval events logged as `ObservabilityEvent` with `event_type="approval_gate"`.

### 3.6 Timeout and Fallback

| Scenario | Behavior | Rationale |
|----------|----------|-----------|
| User approves | Proceed with tool call | Normal flow |
| User denies | Return `"Action '{tool}' denied by user."` to model | Model adapts |
| Timeout (default 120s) | Return cancellation message | Safe default per AC |
| User says "approve all X" | Add to `ApprovalSession.pre_grants`, proceed | Reduces friction |
| Channel disconnected | Return cancellation message | Safe default |

### 3.7 Testing Strategy

- Unit test `ApprovalPolicy.requires_approval()` with various tool/arg combos
- Unit test `ApprovalSession` pre-grant logic
- Unit test `ApprovalGateToolset.call_tool()` with mock channel: approve, deny, timeout paths
- Integration test with `HookedToolset` nesting
- Verify observability events are logged for each path

## 4. Recommendation (.85 confidence)

**Custom `ApprovalGateToolset(WrapperToolset)`** with `ApprovalPolicy` config and `ApprovalSession` pre-grants.

- ~150 LOC for the toolset + policy model
- Follows existing patterns (`HookedToolset`, `AskUserToolset`)
- No changes to `OwlBearAgent.run_turn()` or hook semantics
- Works across all channels via `ChannelPlugin.send()/receive()`
- Session pre-grants reduce friction for batch operations
- Observability integration via existing `ObservabilityHook`

**Secondary recommendation (.70):** Fix `CommandSafetyGuard` enforcement separately — `emit()` swallowing `BlockedCommandError` means the guard is ineffective. This should be a separate task (add `emit_blocking()` or have `HookedToolset.call_tool()` check for `BlockedCommandError` specifically).

## 5. Follow-up Tasks

1. **Test ApprovalPolicy model** — TDD: approval_required check for tool names, arg patterns, wildcard, empty policy
2. **Implement ApprovalPolicy + ApprovalSession** — Pydantic models for policy config and session state
3. **Test ApprovalGateToolset** — TDD: approve/deny/timeout/pre-grant/observability paths with mock channel
4. **Implement ApprovalGateToolset** — WrapperToolset with channel-based approval flow
5. **Wire ApprovalGateToolset into bootstrap** — wrap destructive toolsets in `build_toolsets()`
6. **Add approval_policy to OwlBearSettings** — TOML config for which tools require approval
7. **Fix CommandSafetyGuard enforcement** — ensure `BlockedCommandError` actually prevents tool execution (separate from approval gates)
