# ACP Client Library — Research Gate Validation

> **Owning task:** #19 — Build ACP client library
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #19 defines an ACP client library with 11 AC items. Previous research
(acp-client-library-decomposition.md, 2026-03-28) validated the decomposition
into 7 subtasks. This research validates the current completion state and
determines #19's disposition for the architect gate.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | OwlBear decomposition research | `docs/research/acp-client-library-decomposition.md` | .95 |
| 2 | OwlBear ACP error handling research | `docs/research/acp-error-handling-strategy.md` | .90 |
| 3 | ACP Python SDK `core.py` | <https://github.com/agentclientprotocol/python-sdk/blob/main/src/acp/core.py> | .90 |
| 4 | ACP Python SDK `client/connection.py` | <https://github.com/agentclientprotocol/python-sdk/blob/main/src/acp/client/connection.py> | .85 |
| 5 | OwlBear AcpClient implementation | `packages/orchestrator/src/owlbear_orchestrator/acp_client.py` | .95 |
| 6 | OwlBear ProcessSupervisor impl | `packages/orchestrator/src/owlbear_orchestrator/process_supervisor.py` | .95 |

## 3. Analysis

### 3.1 Subtask Completion Status (as of 2026-03-29)

| # | Subtask | Status | AC Items Covered |
|---|---------|--------|------------------|
| #45 | ACP hello-world script | archived | AC 11 (integration test) |
| #46 | Add agent-client-protocol deps | archived | (dependency for all) |
| #58 | ProcessSupervisor | archived | AC 2, 6, 8 |
| #59 | AcpClient wrapper | **ideation** | AC 3, 4, 5, 8, 9 |
| #60 | Extend classify_error | archived | (error classification) |
| #73 | Test: ProcessSupervisor | archived | AC 10 (partial) |
| #94 | Test: AcpClient | archived | AC 10 (partial) |

**6/7 subtasks archived.** #59 is at ideation but its implementation already
exists (`owlbear_orchestrator/acp_client.py`, 121 LOC) and tests pass (13/13).

### 3.2 AC Coverage Map (Current State)

| # | AC Item | Status | Evidence |
|---|---------|--------|----------|
| 1 | Module in `packages/orchestrator/src/owlbear/acp/` | **Path diverged** | Actual: `owlbear_orchestrator/acp_client.py` + `process_supervisor.py` |
| 2 | `spawn_copilot()` | Done | `ProcessSupervisor.ensure_running()` (#58 archived) |
| 3 | `send_initialize()` | Done | `AcpClient.initialize()` (Source 5, L94-99) |
| 4 | `send_new_session()` | Done | `AcpClient.new_session()` (Source 5, L101-106) |
| 5 | `send_prompt()` streams | Done | `AcpClient.prompt()` (Source 5, L108-121) |
| 6 | Process lifecycle | Done | `ProcessSupervisor` (Source 6, full file) |
| 7 | NDJSON parsing + error recovery | Done | SDK-handled (Source 3, confirmed in decomposition) |
| 8 | Async interface (asyncio) | Done | Both modules fully async |
| 9 | Timeout handling per exchange | Done | 30s/15s/300s in AcpClient (Source 5) |
| 10 | Unit tests with mocked subprocess | Done | 13 + 24 tests pass (test_acp_client + test_process_supervisor) |
| 11 | Integration test with real CLI | Done | hello_world.py (#45 archived) |

**11/11 AC items satisfied.** AC item 1 path diverged from original spec — the
architect refined the module layout during #58's review (flat modules in
`owlbear_orchestrator/` instead of `owlbear/acp/` subpackage). This is simpler
(KISS) and consistent with the package's `pyproject.toml` build target.

### 3.3 Remaining Pipeline Gap: #59

Task #59 (AcpClient wrapper) is at `ideation` but its code and tests already
exist because the builder implemented ahead of the TDD pipeline (noted in #94
audit). The implementation is sound (13 tests pass, ruff clean) but #59 has
not passed through the architect, builder, reviewer, or writer gates formally.

Options:

| Option | Pros | Cons | Confidence |
|--------|------|------|------------|
| A: Advance #59 through full pipeline | Formal verification, consistent process | Redundant — code is done and #94 audited tests | .70 |
| B: Fast-track #59 with architect review only | AC already satisfied, saves pipeline cycles | Skips reviewer/writer gates | .80 |

**Recommendation (.80):** Option B — the architect should review #59's AC
against the existing implementation and fast-track it. The code was already
verified by #94's full audit cycle. #19 can then be archived as a tracker.

### 3.4 LOC Assessment

| Component | LOC | KISS Target | Assessment |
|-----------|-----|-------------|------------|
| ProcessSupervisor | 96 | ~80 | Slightly over; clean design |
| AcpClient | 121 | ~80 | Over target; includes error types (40 LOC) |
| Total | 217 | ~160 | Acceptable — error infrastructure adds LOC |

Test coverage: 37 tests across 2 files. No custom NDJSON parser (SDK-handled).

## 4. Recommendation (.90 confidence)

**#19 is fully satisfied** — all 11 AC items have working, tested implementations.
The task should advance to backlog as a tracker pending #59's formal pipeline
completion. No new research gaps found; no new subtasks needed.

The module path divergence (AC item 1) is an intentional architect decision and
should be noted in AC refinement, not treated as a defect.

## 5. Follow-up Tasks

No new tasks needed. The single remaining action is advancing #59 through its
pipeline, which is an architect concern (not a new task).
