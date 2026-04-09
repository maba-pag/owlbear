# Document Analysis CLI in Orchestration Workflow Skill

> **Owning task:** #692 — Document analysis CLI in orchestration workflow skill
> **Date:** 2026-04-08 **Status:** Complete

## 1. Context and Question

Research #682 concluded with a manual-first validation strategy (Phase 1): document the analysis CLI in `w-orchestration` so operators can run it as a post-session diagnostic. The CLI exists (`python -m owlbear_orchestrator.analysis`) but no workflow skill references it.

**Question:** Where in `w-orchestration` should the reference go, and what content is needed?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| 1 | `share/skills/w-orchestration/SKILL.md` (current orchestration workflow) | .95 |
| 2 | `serve/orchestrator/src/owlbear_orchestrator/analysis/_cli.py` (CLI flags) | .95 |
| 3 | `serve/orchestrator/src/owlbear_orchestrator/analysis/detectors.py` (4 detectors) | .90 |
| 4 | `.owlbear/research/analysis-detector-wiring.md` (#682 parent research) | .85 |

## 3. Analysis

### 3.1 Insertion Point

`w-orchestration` currently ends with Output Format → Verification Checklist. A `## Post-Session Diagnostics` section between these two is the natural location — it describes what to do *after* the dispatch loop completes.

### 3.2 Content Needed

| AC | Content | Size |
|----|---------|------|
| AC1 | CLI invocation: `python -m owlbear_orchestrator.analysis --format markdown` | 2 lines |
| AC2 | Detector summary table (4 rows) | ~8 lines |
| AC3 | No code changes | — |

### 3.3 Detector Reference (verified from source)

| Detector | Pattern | Fires When | Category |
|----------|---------|------------|----------|
| `high_error_rate_detector` | `high_error_rate` | Agent ≥ 40% failure rate over 3+ completions | reliability |
| `slow_agent_detector` | `slow_agent` | Agent avg duration > 2× other-agents avg (3+ completions) | performance |
| `repeated_failure_detector` | `repeated_failure` | Same task_id fails 2+ times | reliability |
| `stale_dispatch_detector` | `stale_dispatch` | Dispatch > 1h old with no matching completion | stability |

### 3.4 CLI Flags (verified from source)

| Flag | Default | Purpose |
|------|---------|---------|
| `--format json\|markdown` | `json` | Output format |
| `--window HOURS` | all history | Time window to scan |
| `--audit-dir PATH` | `store/audit/` | Audit log directory |

## 4. Recommendation (confidence: .95)

Add a `## Post-Session Diagnostics` section to `w-orchestration` between "Output Format" and "Verification Checklist" containing:

1. One-line description: optional post-session step to surface pipeline health patterns
2. CLI invocation with `--format markdown`
3. Detector summary table (4 rows from §3.3)
4. Note that proposals are informational — no automated action yet (per #682 Phase 1)

Challenge: skipped — trivial docs change, no architectural decision.

## 5. Follow-up Tasks

None required beyond this task. Phase 2 (deterministic router) is already tracked as a deferred recommendation in #682 research.
