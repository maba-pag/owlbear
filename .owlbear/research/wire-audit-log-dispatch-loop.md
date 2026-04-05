# Wire Audit Log into Orchestrator Dispatch Loop

> **Owning task:** #164 — Wire audit log into orchestrator dispatch loop
> **Date:** 2026-03-30 **Status:** Complete

## 1. Context and Question

Task #164 asks to integrate the completed AuditLog module (#163, done) into the orchestrator dispatch loop. The dispatch loop calls `log_dispatch()` before each agent invocation and `log_completion()` after, capturing outcome, duration, and files changed.

Key questions: (a) What is the correct integration pattern? (b) Where are the hook points? (c) How to capture duration and files_changed? (d) Are dependencies and AC sufficient?

## 2. Sources Studied

| # | Source | URL | Rel. |
|---|--------|-----|:----:|
| S1 | OwlBear AuditLog impl (codebase) | `packages/orchestrator/src/owlbear/audit/log.py` | .95 |
| S2 | OwlBear audit log research | `docs/research/orchestrator-audit-log.md` | .95 |
| S3 | OwlBear dispatch loop research | `docs/research/orchestrator-dispatch-loop.md` | .90 |
| S4 | CrewAI event listeners | <https://docs.crewai.com/concepts/event-listener> | .80 |
| S5 | AutoGen `logging.py` event classes | <https://github.com/microsoft/autogen/blob/main/python/packages/autogen-core/src/autogen_core/logging.py> | .75 |
| S6 | OwlBear AcpClient (codebase) | `packages/orchestrator/src/owlbear_orchestrator/acp_client.py` | .95 |
| S7 | OwlBear orchestration skill | `skills/orchestration/SKILL.md` | .90 |
| S8 | OWASP Logging Cheat Sheet | <https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html> | .85 |

## 3. Analysis

### 3.1 Critical: Missing Dependency on #146

Task #164 declares `depends_on: [163, 19]`. However, the dispatch loop itself (#146, backlog) does not exist yet — no `loop.py` or `waves.py` in the codebase. **#164 cannot be implemented until #146 is complete.** The `depends_on` must include #146.

### 3.2 Integration Pattern Options

| Criterion | A: Direct injection (.90) | B: Event bus (.50) | C: stdlib logging (.60) |
|-----------|--------------------------|--------------------|-----------------------|
| New deps | 0 | 1 (event bus lib) | 0 |
| LOC added | ~15 (3 call sites) | ~60 (bus + handlers) | ~30 (handlers) |
| KISS | High | Low — only 1 consumer | Medium |
| Type safety | Full (Pydantic models) | Full (typed events) | Low (untyped LogRecord) |
| Decoupling | Constructor injection | Fully decoupled | Module-level |
| YAGNI risk | Low | High | Medium |

**CrewAI** [S4] uses an event bus (singleton `CrewAIEventsBus`) with Started/Completed/Failed triplets — justified by 50+ event types and multiple listeners. **AutoGen** [S5] uses stdlib `logging` with typed event classes — untyped at the handler level. **OwlBear has exactly one audit consumer** (the retro/analytics skill). Event bus is over-engineering.

**Recommendation (.90):** Option A — direct injection. Pass `AuditLog` to the dispatch loop constructor. Call methods inline at three hook points. Matches KISS/YAGNI.

### 3.3 Integration Hook Points

Based on the dispatch loop design [S3, S7], the three hook points in `loop.py`:

1. **Bootstrap**: `AuditLog(Path("data/audit"))` created before the dispatch loop starts
2. **Pre-dispatch** (inside each wave, per-task): create and log `DispatchEvent`
3. **Post-dispatch** (after each `AcpClient.prompt()` returns or errors): create and log `CompletionEvent`

### 3.4 Duration Measurement

`time.monotonic()` before/after `AcpClient.prompt()`. Convert delta to `int` milliseconds for `CompletionEvent.duration_ms`. Monotonic clock avoids wall-clock jumps (NTP, DST) [S8].

### 3.5 files_changed Strategy

| Option | Approach | Accuracy | KISS |
|--------|----------|:--------:|:----:|
| A: git diff | `git diff --name-only HEAD` before/after dispatch | High | Medium |
| B: Empty list | Always `[]`, fill in later | Low | High |
| C: Parse subagent output | Extract from Channel B body | Low | Low |

**Recommendation (.75):** Option A (git diff). Run `git diff --name-only` before dispatch, snapshot. Run again after. Diff the two sets. This is the only reliable approach since subagents modify files via their own tools rather than reporting them in Channel A. Risk: concurrent agents may attribute files to wrong dispatch — mitigate by capturing diff per-task if dispatches are sequential within a wave.

### 3.6 session_id Flow

`AcpClient.new_session()` returns `NewSessionResponse` containing the session ID [S6]. This session ID serves double duty: ACP session tracking and audit log file partitioning. Pass it to both `DispatchEvent.session_id` and `AuditLog.log_dispatch(event, session_id)`.

### 3.7 prompt_summary Construction

Truncate the `format_prompt()` output to 100 characters (enforced by `DispatchEvent.prompt_summary` max_length=100 [S1]). Pattern: `f"{agent_prefix}: #{task_id}"[:100]`.

### 3.8 AC Gap Analysis

| Gap | Impact | Recommendation |
|-----|--------|---------------|
| Missing #146 dependency | Cannot implement | Add depends_on: 146 |
| No duration measurement spec | Builder guesses approach | Specify `time.monotonic()` |
| No files_changed strategy | Builder invents tracking | Specify git diff approach |
| No error handling for audit failures | Audit errors could crash loop | Specify: catch + log, never block dispatch |
| Thin AC (4 items) | Ambiguous implementation | Expand to 8 verifiable items |

## 4. Recommendation (.85 confidence)

**Direct injection with three hook points.** ~15 LOC in the dispatch loop (when #146 is implemented):

1. Constructor: `self._audit = AuditLog(Path("data/audit"))`
2. Pre-dispatch: `self._audit.log_dispatch(DispatchEvent(...), session_id)`
3. Post-dispatch: `self._audit.log_completion(CompletionEvent(...), session_id)`

Duration via `time.monotonic()`. Files changed via `git diff --name-only`. Audit failures caught silently (never block dispatch). #146 must be added to dependencies.

**Risks:**

| Risk | Mitigation |
|------|------------|
| #146 not implemented yet | Add dependency; task cannot start until #146 reaches review |
| Concurrent dispatches conflate git diffs | Per-wave sequential git snapshots; accept minor noise |
| Audit I/O error blocks dispatch | Wrap audit calls in try/except, log warning, never raise |

## 5. Follow-up Tasks

No new tasks needed — #164 itself is the implementation task. The AC needs refinement and #146 added to dependencies. These are metadata updates to #164, not new tasks.
