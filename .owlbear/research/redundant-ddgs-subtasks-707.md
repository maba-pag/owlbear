# Redundant ddgs Subtasks #707–#711

> **Owning task:** #707 — Tests: ddgs dependency in pyproject.toml and seed MCP config entry
> **Date:** 2026-04-09 **Status:** Complete

## 1. Context and Question

Task #707 (and siblings #708–#711) are subtasks of parent #686, created by the planner during the 2nd architecture pass. The question: are these subtasks still actionable, or did the parent's pipeline execution already cover their deliverables?

## 2. Sources Studied

| Source | Relevance | What |
|--------|-----------|------|
| Parent #686 task body (full pipeline trail) | .95 | Test-writer, builder, reviewer, doc-writer notes spanning 5 pipeline stages |
| `tests/test_ddgs_mcp_integration_686.py` (317 LOC) | .95 | 17 tests across 5 TestFromAC classes covering all 5 parent ACs |
| Live test run (12 selected, 12 passed) | .95 | Verified all #707/#708 AC-mapped tests pass in current codebase |
| Subtask bodies #707–#711 | .90 | AC definitions, dependency chains, file targets |
| Git commits: 3c867b7, d11638c, 62430da, ed38427, df85cff | .85 | Parent pipeline execution trail |

## 3. Analysis

### 3.1 Subtask Redundancy Matrix

| Task | Title | AC Met By Parent? | Evidence | Status |
|------|-------|-------------------|----------|--------|
| #707 | Tests: ddgs dep + seed config | YES | TestFromAC_DdgsDependency (3), TestFromAC_SeedMcpConfig (4) — all 7 pass | research |
| #708 | Tests: agent allowlists | YES | TestFromAC_ResearcherAgentTools (3), TestFromAC_IdeatorAgentTools (2) — all 5 pass | todo |
| #709 | Impl: agent allowlists | YES | researcher.agent.md + ideator.agent.md updated at commit d11638c | backlog |
| #710 | Impl: dep + seed config | YES | pyproject.toml + seed/.vscode/mcp.json updated at commits d11638c/62430da | backlog |
| #711 | Smoke test | YES | TestFromAC_DdgsMcpSmoke (5 tests including 3 subprocess probes) — all pass | backlog |

### 3.2 Root Cause

Pipeline sequencing artifact. Timeline:
1. Architect 2nd pass decomposed #686 → subtasks #706–#711
2. Parent #686 continued through test-writer → builder → reviewer → docs
3. Parent pipeline completed all ACs, including those delegated to subtasks
4. Subtasks entered the board post-completion — deliverables already exist

### 3.3 Risk Assessment

| Option | Risk | Mitigation |
|--------|------|------------|
| Archive all (#707–#711) | Loses tracking granularity | Parent #686 is `done` with full audit trail |
| Run subtasks through pipeline anyway | Wastes pipeline cycles on no-op work; AC3 ("tests fail red") unsatisfiable | None — fundamentally blocked |
| Partial archive | Inconsistent board state | No benefit over full archive |

## 4. Recommendation (confidence: .92)

Archive all five subtasks (#707–#711) as redundant. The parent #686 (`done`, reviewer confidence .97) already delivered every AC these subtasks specify. Running them through the pipeline would produce no-op work and AC violations (red-phase tests cannot fail when implementation exists).

Challenge: skipped — recommendation is archival of already-completed work, not a new capability decision.

## 5. Follow-up Tasks

Single follow-up task to archive #707–#711 with documented rationale.
