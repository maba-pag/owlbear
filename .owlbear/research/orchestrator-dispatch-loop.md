# Orchestrator Dispatch Loop — Research Validation

> **Owning task:** #146 — Implement orchestrator dispatch loop
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #146 (subtask of #20) implements the Python orchestrator dispatch loop at
`packages/orchestrator/src/owlbear/orchestrator/loop.py`. It consumes a
`DispatchPlan` from the planner module (#144, #145), manages ACP sessions via
`AcpClient` (#19), and implements wave assembly, error handling, and re-planning.

Key questions: (1) What's the correct module structure for the orchestrator loop?
(2) How should ACP sessions map to dispatch entries? (3) Is the wave assembly
algorithm implementable in typed Python without LLM reasoning? (4) What's the
right error handling strategy? (5) Are there AC gaps?

## 2. Sources Studied

| # | Source | Rel. | What |
|---|--------|:----:|------|
| S1 | `orchestration` SKILL.md (local) | .95 | Full dispatch loop spec: wave assembly, rate-limit fallback, error retry |
| S2 | `dispatch-planning` SKILL.md (local) | .90 | Agent dispatch mapping, gate algorithm, DispatchPlan output format |
| S3 | `build-dispatch-planner.md` S3.2 (local) | .90 | Concern separation: orchestrator owns loop + prompt + error handling |
| S4 | `acp_client.py` (codebase) | .95 | AcpClient API: initialize(), new_session(), prompt(), ErrorCategory |
| S5 | `process_supervisor.py` (codebase) | .95 | ProcessSupervisor: spawn, ensure_running, mark_healthy, restart budget |
| S6 | ACP SDK quickstart + `duet.py` example | .85 | `connect_to_agent`, `spawn_agent_process`, session lifecycle |
| S7 | `hello_world.py` (codebase) | .85 | ACP session lifecycle: initialize → new_session → prompt → shutdown |
| S8 | `orchestration-agent-frameworks.md` (local) | .80 | Symphony poll-dispatch-reconcile pattern, wave patterns from nWave |
| S9 | `symphony.md` (local) | .80 | Poll → dispatch → reconcile, exponential backoff retry, stale detection |
| S10 | `planner-gate-checker-selector.md` (local) | .85 | DispatchPlan output format, DispatchEntry fields |

## 3. Analysis

### 3.1 Module Structure

| Option | Structure | LOC est. | KISS |
|--------|-----------|----------|:----:|
| A. Single `loop.py` | All loop logic in one file | ~250 | Low |
| B. `loop.py` + `waves.py` | Loop + wave assembly separated | ~120 + ~100 | High |
| C. `loop.py` + `waves.py` + `prompt.py` | Three files | ~100 + ~100 + ~50 | Medium |

**Recommendation (.85):** Option B. Wave assembly is a pure algorithm (input:
dispatch list → output: list of waves) with clear test boundaries. The loop is
async orchestration logic. `format_prompt()` is 5-10 lines and belongs in `loop.py`.
Matches the planner's `gates.py` + `selector.py` pattern. [S1, S3]

### 3.2 ACP Session Lifecycle per Dispatch

Each dispatch entry needs a full ACP session. From S4, S5, S6, S7:

```
ProcessSupervisor.ensure_running() → (stdin, stdout)
connect_to_agent(client, stdin, stdout) → conn
AcpClient(conn).initialize() → InitializeResponse
AcpClient(conn).new_session(cwd=...) → NewSessionResponse
AcpClient(conn).prompt(session_id=..., prompt=[text_block(...)]) → PromptResponse
```

**Key design decision:** One `ProcessSupervisor` per orchestrator session (long-lived
Copilot CLI process), reused across dispatches. Each dispatch creates a new ACP
session via `new_session()`. The process persists; sessions are per-task. [S5, S7]

After each successful prompt, call `ProcessSupervisor.mark_healthy()` to reset
the restart budget. [S5]

### 3.3 Wave Assembly in Python

The orchestration skill S1 defines a 7-step four-bucket algorithm. Analysis of
implementability as typed Python:

| Step | Complexity | Python pattern |
|------|-----------|----------------|
| 1. Bucket sort | Low | Dict of lists keyed by category enum |
| 2. Auditor waves | Low | Pop 1 auditor + fill from light flex |
| 3. Builder waves | Medium | Pop 1 builder + fill light first, then heavy |
| 4. Overflow | Low | Chunk remaining flex agents by wave size |
| 5. Periodic curator | Low | Cycle counter mod 5 check |
| 6. Consolidation | SKIP | Deactivated per skill doc |
| 7. Drop rule | Low | Filter solo non-auditor waves |

**Finding (.90):** Fully implementable as pure functions. No LLM reasoning needed.
The algorithm is deterministic given the input list and cycle number. [S1]

Agent category mapping (from S1):

```python
AGENT_CATEGORY = {
    "auditor": "restricted",
    "builder": "restricted",
    "researcher": "light_flex",
    "writer": "light_flex",
    "architect": "light_flex",
    "kanban-planner": "light_flex",
    "curator": "light_flex",
    "reviewer": "heavy_flex",
    "test-writer": "heavy_flex",
}
```

### 3.4 Error Handling Strategy

Three error categories from the orchestration skill [S1]:

| Error type | Detection | Response |
|-----------|-----------|----------|
| Normal crash | Agent raises non-rate-limit exception | Retry once in next wave |
| Rate limit | Error contains "rate-limited", "rate_limited", "rate limits" | Sequential fallback (3 dispatches) |
| Double crash | Same task crashes on retry | Record as failure, pass to planner |

The AcpClient already classifies errors into `ErrorCategory` [S4]. The orchestrator
loop maps these to retry decisions:

- `TRANSIENT` → retry in next wave (matches normal crash)
- `AUTH` → retry once after refresh
- `PERMANENT` → record as failure immediately (no retry)
- `TOOL_SEMANTIC` → retry once (model self-correction)

Rate-limit detection is string-based (not category-based) per S1 — check error
message text. This is correct because rate limits may come from the Copilot API
layer above ACP, not from ACP error codes. [S1, S4]

### 3.5 format_prompt() Design

Per orchestration skill S1: "Dispatch prompt contains ONLY the task ID."

```python
def format_prompt(entry: DispatchEntry) -> list[TextContentBlock]:
    prompt = f"{AGENT_PROMPT_PREFIX[entry.agent]}: #{entry.task_id}"
    if entry.retry_hint:
        prompt += f"\nRetry context: {entry.retry_hint}"
    return [text_block(prompt)]
```

Agent prompt prefix mapping (from S1 examples):

| Agent | Prefix |
|-------|--------|
| architect | "Architect Review" |
| builder | "Build" |
| reviewer | "Review" |
| test-writer | "Write tests" |
| researcher | "Research" |
| writer | "Docs" |
| auditor | "Audit" |
| kanban-planner | "Plan" |
| curator | "Curate: Periodic curation" (no task ID) |

### 3.6 Re-planning and Loop Termination

The loop follows Symphony's poll-dispatch-reconcile pattern [S8, S9]:

1. Call planner module's `select_tasks(read_board())` → `DispatchPlan`
2. Assemble waves from `DispatchPlan.entries`
3. Dispatch each wave, collect successes/failures
4. If failures exist, pass failure context to next plan cycle
5. Re-plan from scratch (fresh board read)
6. Stop only when `DispatchPlan.entries` is empty

**Stale tracking** requires cross-cycle state [S1]:
- `stale_retried: set[int]` — task IDs dispatched with `retry_hint` (carry across cycles)
- `sequential_remaining: int` — counter for rate-limit sequential fallback (reset each cycle)
- `crash_failures: set[int]` — task IDs that crashed twice (passed to planner)

### 3.7 AC Gap Analysis

| Gap | Impact | Recommendation |
|-----|--------|---------------|
| No module structure specified | Builder guesses file layout | Recommend `loop.py` + `waves.py` (§3.1) |
| No AcpClient session lifecycle | Builder guesses spawn strategy | Specify: 1 process, N sessions (§3.2) |
| format_prompt() undefined | Builder invents prompt format | Add prefix table + function signature (§3.5) |
| No agent category mapping | Builder guesses categories | Add AGENT_CATEGORY dict (§3.3) |
| Rate-limit detection method unspecified | Ambiguous error handling | Specify string-based detection (§3.4) |
| No re-planning data flow | Builder guesses state passing | Specify stale_retried, crash_failures (§3.6) |
| Logging undefined | Vague "logs each dispatch" | Specify structured logging events |
| Tests bundled with impl | Violates TDD | Separate test task |
| Wave size hardcoded | No config source | Reference orchestration skill Configuration |
| Curator handling missing | AC omits curator exception | Add curator prompt format (no task ID) |

### 3.8 Testing Strategy

- **Wave assembly:** pure function tests with various dispatch list compositions
  (auditor+builders+flex, empty list, solo items, drop rule edge cases)
- **format_prompt():** verify prefix per agent, retry_hint appended, curator exception
- **Error handling:** mock AcpClient to raise different ErrorCategory errors, verify
  retry-once + rate-limit sequential fallback behavior
- **Loop termination:** mock planner returning empty plan after N cycles
- **Stale tracking:** simulate stale_retried cross-cycle state
- No real Copilot CLI needed — all tests use mocked AcpClient and planner

## 4. Recommendation (.85 confidence)

The AC is directionally correct but needs significant refinement:

1. **Split into `loop.py` + `waves.py`** — different concerns, cleaner testing
2. **Add ACP session lifecycle spec** — 1 ProcessSupervisor, N sessions per task
3. **Add format_prompt() with prefix table** — prevents builder guesswork
4. **Add AGENT_CATEGORY dict** — explicit category mapping for wave assembly
5. **Specify error handling chain** — rate-limit detection + retry-once + failure recording
6. **Add cross-cycle state spec** — stale_retried, sequential_remaining, crash_failures
7. **Separate test task** — TDD RED phase should precede implementation

Risks:
- ACP SDK API stability (v0.9.0) — mitigated by wrapping via AcpClient
- Rate-limit string detection is fragile — but matches VS Code orchestrator behavior [S1]
- ProcessSupervisor restart budget (3) may be insufficient for long sessions — mitigated
  by `mark_healthy()` resets after each successful prompt [S5]

## 5. Follow-up Tasks

Task #146 AC should be refined by the architect using §3.7 gap analysis. A test
task should be created (following #144/#153 pattern). No additional tasks needed
beyond #146 itself — the scope is well-defined by the orchestration skill.
