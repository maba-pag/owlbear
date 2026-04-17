# Legacy kanban-md.exe Cleanup

> **Owning task:** #902 — Clean up legacy kanban-md.exe references
> **Date:** 2026-04-17 **Status:** Complete

## 1. Context and Question

Parent #890 (macOS compat) decision D4: `kanban-md.exe` is legacy, cleanup only. The `.exe` extension is a Windows artifact — macOS/Linux executables don't use it. What references exist, and what's the minimal change to satisfy the AC?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `serve/orchestrator/src/owlbear/cli.py` | Codebase | 1.0 — hardcoded `_KANBAN_BIN = Path("kanban/kanban-md.exe")` at L24 |
| 2 | `tests/fixtures/mock_acp_agent.py` | Codebase | 1.0 — `_DEFAULT_KANBAN_BIN = "kanban/kanban-md.exe"` at L24 |
| 3 | `tests/test_mock_acp_agent.py` | Codebase | 1.0 — 3 assertions verify `.exe` fallback (L316–324) |
| 4 | `tests/test_dispatch_integration.py` | Codebase | 1.0 — fixture looks for `.exe` on disk (L74–83) |
| 5 | `tests/test_orchestrator_loop.py` | Codebase | 0.9 — 7 calls pass `Path("kanban/kanban-md.exe")` (all mocked) |
| 6 | `tests/test_reviewer_execute_tools_457.py` | Codebase | 0.5 — validates `.exe` is NOT in skills (keep as-is) |

## 3. Analysis

### Reference Inventory

| File | Line(s) | Nature | Action |
|------|---------|--------|--------|
| `cli.py` | 24 | Hardcoded `.exe` default | Replace with `os.environ.get("KANBAN_BIN", "kanban-md")` |
| `mock_acp_agent.py` | 24 | Hardcoded `.exe` default | Change to `"kanban-md"` |
| `test_mock_acp_agent.py` | 316–324 | Asserts fallback is `.exe` | Update assertion to `"kanban-md"` |
| `test_dispatch_integration.py` | 74, 83 | Looks for `.exe` file | Remove `.exe` from path; keep skip-if-not-found |
| `test_orchestrator_loop.py` | 612–799 | 7 mocked `Path(…)` args | Change all to `Path("kanban/kanban-md")` |
| `test_reviewer_execute_tools_457.py` | 259–260 | Negative guard (checks absence) | **Keep as-is** — validates skills stay clean |

### Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Tests break after rename | Low | All loop/agent tests are fully mocked — path value is cosmetic |
| `cli.py` breaks on Windows | Low | `kanban-md` without extension still works if the binary is on PATH or resolved via env var |
| Integration test fixture fails | None | Already skips when binary not found |

## 4. Recommendation

**Drop the `.exe` extension from all defaults; prefer env var.** (Confidence: 0.92)

`cli.py` should read `KANBAN_BIN` env var with fallback to `"kanban-md"` (no path prefix, no extension). This matches how `mock_acp_agent.py` already uses the env var. Test files update to match the new default string.

Challenge: SKIPPED — trivial cleanup, no design alternatives. Decision D4 already made.

**Tier: T1 — Autonomous.** Rename/cleanup, no architecture change, no new capability.

## 5. Follow-up Tasks

Single implementation task: #902 itself carries the concrete AC. No additional decomposition needed — 6 files, ~15 changed lines, all surgical string replacements.
