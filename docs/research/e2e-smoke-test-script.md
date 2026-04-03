# E2E Smoke Test Script — Research Findings

> **Owning task:** #157 — Create E2E smoke test script for real Copilot CLI
> **Date:** 2026-04-01 **Status:** Complete

## 1. Context and Question

Task #157 implements the manual smoke test script (Layer 2) from the layered
test architecture in `docs/research/e2e-dispatch-test.md` §3.3. The script
validates the full owlbear stack with real Copilot CLI, supplementing the
automated integration test (Layer 1 in `test_e2e_dispatch.py`).

Key questions: (1) What cleanup strategy ensures temp task deletion on all exit
paths? (2) How to invoke `owlbear dispatch` and verify completion? (3) What
prerequisite checks are needed? (4) How to configure timeout?

## 2. Sources Studied

| # | Source | URL/Location | Relevance |
|---|--------|-------------|:---------:|
| S1 | OwlBear `test_e2e_dispatch.py` — seed task, subprocess dispatch, cleanup | `tests/test_e2e_dispatch.py` | .95 |
| S2 | OwlBear `test_integration.py` — kanban-md subprocess patterns | `packages/mcp-kanban/tests/test_integration.py` | .90 |
| S3 | Python `subprocess` docs — timeout, TimeoutExpired handling | [docs.python.org](https://docs.python.org/3/library/subprocess.html) | .90 |
| S4 | Parent research: `e2e-dispatch-test.md` §3.3 (Layer 2) | `docs/research/e2e-dispatch-test.md` | .95 |
| S5 | OwlBear `cli.py` — dispatch command interface | `packages/orchestrator/src/owlbear/cli.py` | .90 |
| S6 | Python `atexit` docs — exit handler tradeoffs | [docs.python.org](https://docs.python.org/3/library/atexit.html) | .80 |

## 3. Analysis

### 3.1 Dependency Status

| Dep | Task | Status | Pipeline distance |
|-----|------|--------|:-----------------:|
| #20 | Build dispatch planner | review | 3 stages to archived |
| #22 | Build CLI trigger commands | done | 1 stage to archived |

#22 is done. #20 is in review — could still be rejected. Task can enter
backlog now; builder starts only when deps clear.

### 3.2 Cleanup Strategy

| Strategy | Normal | Ctrl+C | Timeout | Untestable? |
|----------|:------:|:------:|:-------:|:-----------:|
| try/finally only [S1] | Yes | Yes | Yes | No |
| try/finally + atexit | Yes | Yes | Yes | Yes (atexit) |

**Choice: try/finally only (.90 confidence).** `test_e2e_dispatch.py` uses
this pattern exclusively [S1]. `atexit` adds an untestable cleanup path —
the project's own research flagged atexit as risky. try/finally covers all
Python-controlled exit paths including Ctrl+C and TimeoutExpired [S3].

### 3.3 Timeout Configuration

| Approach | KISS | Dependencies | Convention |
|----------|:----:|:------------:|:----------:|
| A: `E2E_TIMEOUT` env var | High | None | 12-factor |
| B: `sys.argv` parsing | Medium | None | scripts/*.py |
| C: `argparse` | Low | stdlib | Not used in scripts/ |

**Choice: env var + sys.argv fallback (.85 confidence).** Environment variable
is simplest. `python scripts/e2e_smoke.py [timeout_seconds]` with env override.
Matches KISS; no CLI framework needed for a single parameter.

### 3.4 Implementation Pattern (from test_e2e_dispatch.py)

The existing test [S1] provides all building blocks:

1. **UUID isolation**: `f"E2E-smoke-{uuid.uuid4()}"` — collision-proof titles
2. **Task creation**: `kanban-md create <title> --status todo --tags e2e-smoke`
3. **ID resolution**: `kanban-md list --json --tag e2e-smoke --status todo`
4. **Dispatch**: `subprocess.run(["owlbear", "dispatch", str(id)], timeout=T)`
5. **Verification**: `kanban-md show <id> --json` → check status != "todo"
6. **Cleanup**: `kanban-md delete <id> --yes` in finally block
7. **Prerequisite check**: `shutil.which("gh")` [S1, S5]

Zombie task recovery: tag `e2e-smoke` enables manual discovery via
`kanban-md list --tag e2e-smoke` if crashes leave orphaned tasks.

### 3.5 AC Refinements

| Original AC line | Refinement |
|------------------|------------|
| Configurable timeout | `E2E_TIMEOUT` env var, default 300s |
| Checks board state | Verify status advanced past "todo" |
| Cleans up on exit | try/finally only (no atexit) |
| (not specified) | Exit code: 0=PASS, 1=FAIL, 2=prereq error |
| (not specified) | Tag `e2e-smoke` for orphan discovery |

## 4. Recommendation (.85 confidence)

T1 classification confirmed — standalone script using established patterns,
no architecture changes. Implementation follows `test_e2e_dispatch.py` [S1]
directly: UUID task isolation, subprocess dispatch with timeout, try/finally
cleanup, kanban-md --json for board verification.

Challenge: reconsider — confidence in original: .70. Revised per challenger
feedback: dropped atexit (contradicted by project prior art), switched from
argparse to env var (KISS), softened no-import constraint.

## 5. Follow-up Tasks

No new tasks. #157 covers the full scope. AC refinements applied to task body.
