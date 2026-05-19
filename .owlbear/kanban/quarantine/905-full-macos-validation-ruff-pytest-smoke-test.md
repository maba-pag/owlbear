---
id: 905
title: Full macOS validation (ruff + pytest + smoke test)
status: archived
priority: critical
created: 2026-04-16T22:54:53.396876+00:00
updated: 2026-04-17T10:53:11.848251+00:00
tags:
- phase-3
- scope:platform
- type:user-action
- platform
parent: 890
depends_on:
- 901
- 902
- 903
- 904
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #890 and `.owlbear/briefs/draft-macos-compat/brief.md`

## Acceptance Criteria

- [ ] `uv run ruff check .` exits 0 on macOS
- [ ] `uv run pytest` exits 0 on macOS (no test failures, no collection errors)
- [ ] All agents visible in VS Code on macOS (agent discovery works)
- [ ] At least one hook executes successfully on macOS (manual or automated smoke test)
- [ ] MCP servers start and respond on macOS (kanban, knowledge, memory)
- [ ] No .ps1 references remain anywhere in codebase: grep -r ".ps1" share/ seed/ setup/ .owlbear/hooks/ returns no results
- [ ] No powershell references remain in agent files: grep -r "powershell" share/agents/ returns no results
- [ ] Consumer workflow validated: setup/init.py seeds correctly into a fresh target on macOS

## Notes

This is the exit gate for the entire macOS compatibility feature (#890). All prior tasks must be complete before this runs. Type: type:user-action — requires physical macOS validation by the user.

## Files

- (validation only, no files changed)
[[2026-04-17]]

## Research

- Research doc: .owlbear/research/macos-validation-905.md
- Sources: 0 external (all evidence from codebase execution)
- Recommendation: macOS compat feature works; test failures are pre-existing platform-agnostic debt (confidence: .90)
- Follow-up tasks created: #909 (remove .ps1 comment), #910 (fix test hang), #911 (fix 254 test failures)
- Decision requests: none

### Automated AC results

| AC | Result |
|----|--------|
| ruff check exits 0 | PASS |
| pytest exits 0 | FAIL (254 pre-existing failures, not macOS-specific) |
| Hook execution | PASS (uv run python invocation works) |
| No .ps1 references | NEAR-PASS (1 attribution comment → #909) |
| No powershell in agents | PASS |
| Consumer workflow (init.py) | PASS (22 files seeded correctly) |
| MCP server imports | PASS (all 4 import OK) |

### Manual ACs requiring user action

- AC3: Agents visible in VS Code (Copilot Chat panel inspection)
- AC5: MCP servers respond to real requests (VS Code integration)
[[2026-04-17]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single validation gate for #890 |
| Interface clarity | REFINE | AC2 too broad — see below |
| Dependency correctness | PASS | All 4 deps (901–904) archived |
| Module layering | N/A | Validation task, no code changes |
| TDD compliance | N/A | type:user-action pass-through |
| KISS/YAGNI | PASS | Minimal scope |
| Premise challenge | PASS | Exit gate is necessary for #890 |
| Pattern consistency | N/A | No code changes |
| Security surface | N/A | No new boundaries |
| Single domain | PASS | Platform validation domain |

### AC Assessment

| AC | Status | Notes |
|----|--------|-------|
| AC1: ruff exits 0 | PASS | Verified in research |
| AC2: pytest exits 0 | NEEDS REFINE | 254 pre-existing Pydantic failures, not macOS-specific. Recommend refining to: "No macOS-specific test failures or collection errors" |
| AC3: agents visible | NEEDS USER | Requires VS Code Copilot Chat panel inspection |
| AC4: hook executes | PASS | uv run python invocation confirmed |
| AC5: MCP servers respond | NEEDS USER | Imports OK; full health check requires VS Code |
| AC6: no .ps1 refs | PASS | 0 matches (resolved since research) |
| AC7: no powershell in agents | PASS | 0 matches |
| AC8: consumer workflow | PASS | 22 files seeded correctly |

### AC2 Refinement Recommendation

Current: "uv run pytest exits 0 on macOS (no test failures, no collection errors)"
Proposed: "No macOS-specific test failures or collection errors in uv run pytest (pre-existing platform-agnostic failures documented separately and tracked in follow-up tasks)"
Rationale: 254 failures are Pydantic model drift — identical on any platform. Conflating with macOS validation makes this AC unachievable without unrelated test debt work.

### Challenge Results

- Challenger: SKIPPED (BLOCK verdict, not APPROVE)
- Scribe: FALLBACK — agent unavailable, AR documented inline

### User Action Required

To unblock, verify in VS Code on macOS:

1. **AC3:** Open Copilot Chat → verify all agents from share/agents/ appear in agent picker
2. **AC5:** Open Copilot Chat → invoke an agent that uses MCP → verify kanban, knowledge, and memory servers respond
Then add `## Action Completed` section to task body with results.

### Verdict: BLOCK

### Action Taken: Blocked for user-action (AC3 + AC5 manual verification). Recommended AC2 refinement to scope pytest criterion to macOS-specific failures only

[[2026-04-17]]

## Validation Results (macOS)

- AC1: ruff check → PASS (exit 0)
- AC2: pytest → 222 RED-phase failures (all pre-existing, platform-agnostic), 0 collection errors
- AC3: Agent visibility → PASS (user verified all agents visible in @ picker)
- AC4: Hook execution → PASS (uv run python works, session-context hook tested)
- AC5: MCP servers → PASS (user verified kanban, knowledge, memory all respond)
- AC6: .ps1 refs → PASS (0 matches)
- AC7: powershell refs → PASS (0 matches)
- AC8: Consumer workflow → PASS (init.py seeds 22 files correctly)
