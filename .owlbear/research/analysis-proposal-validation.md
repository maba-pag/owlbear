# Analysis Proposal Validation — Blocked by Missing Audit Data

> **Owning task:** #693 — Validate analysis proposal utility over 2-3 orchestration cycles
> **Date:** 2026-04-08 **Status:** Complete

## 1. Context and Question

Research #682 deferred automatic proposal consumption (YAGNI) and proposed a 3-phase plan: (1) manual CLI validation, (2) deterministic router if demand proven, (3) agent integration if needed. Task #693 is the Phase 1 gate — run `python -m owlbear_orchestrator.analysis --format markdown` after real orchestration sessions and assess whether proposals drive useful action.

**Question:** Do analysis proposals produce actionable findings in practice? Is Phase 2 warranted?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| 1 | `serve/orchestrator/src/owlbear/cli.py` (production CLI `run` and `dispatch` commands) | .95 |
| 2 | `serve/orchestrator/src/owlbear/orchestrator/loop.py` (`orchestrate()`, `run_loop()`, audit_log param) | .95 |
| 3 | `serve/orchestrator/src/owlbear/audit/log.py` (`AuditLog` class, store path) | .90 |
| 4 | `store/` directory listing + `.gitignore` (`store/audit/` gitignored, non-existent) | .95 |
| 5 | `share/skills/w-orchestration/SKILL.md` (VS Code agent orchestration workflow) | .90 |
| 6 | `.owlbear/research/analysis-detector-wiring.md` (#682 parent research) | .85 |
| 7 | `.owlbear/research/document-analysis-cli-orchestration.md` (#692 research) | .80 |
| 8 | Test files: `test_audit_log.py`, `test_dispatch_audit_wiring.py` (only test consumers of AuditLog) | .75 |

## 3. Analysis

### 3.1 The Data Gap

| Evidence | Finding |
|----------|---------|
| `store/audit/` directory | Does not exist |
| JSONL files in workspace | None found (0 matches for `*.jsonl`) |
| `cli.py` `run` command | Uses `_do_dispatch()` — never creates `AuditLog`, never calls `orchestrate()` |
| `cli.py` `dispatch` command | Same — uses `_do_dispatch()`, no audit logging |
| `orchestrate()` function | Accepts `audit_log: AuditLog | None = None` — optional, defaults to None |
| Production instantiation of `AuditLog` | Zero call sites outside test files |
| VS Code orchestrator agent | Uses `runSubagent` per `w-orchestration` skill — entirely separate from Python loop |

**Conclusion:** No production execution path generates audit JSONL data. The analysis CLI has no data to analyze.

### 3.2 Two Execution Models

| Aspect | VS Code Agent (actual) | Python ACP Loop (designed) |
|--------|----------------------|---------------------------|
| Entry point | `runSubagent` calls in w-orchestration | `orchestrate()` via `owlbear run --all` |
| Dispatch mechanism | Copilot chat agent invocation | ACP protocol over stdio |
| Audit capability | None — agents can't write JSONL | Wired (if `audit_log` param provided) |
| Wave assembly | Agent decides per w-orchestration rules | `assemble_waves()` in Python |
| Production use | Active — all orchestration sessions | Never used with real tasks |

The analysis module was built for the ACP execution model, but production orchestration uses the VS Code agent model.

### 3.3 Blocker Assessment

| AC | Status | Reason |
|----|--------|--------|
| AC1: Run CLI after 2-3 sessions | **BLOCKED** | No audit data generated; `store/audit/` doesn't exist |
| AC2: Document useful proposals | **BLOCKED** | Depends on AC1 |
| AC3: Decide Phase 2 | **Decidable** | Phase 2 is NOT warranted — prerequisite (data) is missing |
| AC4: Create follow-up if warranted | **Applicable** | Follow-up is to fix the data gap, not build Phase 2 |

### 3.4 Options to Unblock

| Option | LOC | Fits Model | Risk |
|--------|-----|-----------|------|
| A: Wire `AuditLog` into `cli.py` `run` command | ~15 | ACP model (unused) | Wiring audit into an unused CLI path proves nothing |
| B: Create MCP audit-log tool for VS Code agent | ~40 | VS Code model (actual) | Adds complexity; agent must call tool per dispatch |
| C: Wait for ACP orchestrator to reach production | 0 | Future | Unknown timeline; blocks validation indefinitely |
| D: Abandon analysis module as premature | 0 | — | Sunk cost (~400 LOC + tests), but YAGNI says accept it |

## 4. Recommendation (confidence: .88)

**Phase 2 is NOT warranted. The analysis module is premature — no execution path generates the data it needs.**

The analysis module (4 detectors, CLI, formatters) is well-built and well-tested (~400 LOC, comprehensive test coverage), but it was designed for an ACP-based Python orchestrator loop that has never been used in production. The actual orchestrator is a VS Code agent following `w-orchestration`. These are fundamentally different execution models.

**Recommended disposition:**
1. Do not build Phase 2 (deterministic router) or Phase 3 (agent integration)
2. Keep the module as-is — no deletion (it works, tested, low maintenance burden)
3. When/if the ACP orchestrator reaches production use, wire `AuditLog` into the CLI and re-evaluate
4. Mark this validation as "deferred — no data source" rather than "failed"

Challenge: skipped — info-only finding, no architectural recommendation to challenge. The finding is empirical (no data exists), not a design opinion.

## 5. Follow-up Tasks

1. **Defer #692 (doc update)** — Documenting the CLI in `w-orchestration` is pointless when there's no data to analyze. Recommend deprioritizing to `someday`.
