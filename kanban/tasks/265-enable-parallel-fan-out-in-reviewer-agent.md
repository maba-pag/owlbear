---
id: 265
title: Enable parallel fan-out in reviewer agent
status: backlog
priority: important
created: 2026-03-30T19:31:23.5606586+02:00
updated: 2026-03-30T21:48:52.8109697+02:00
tags:
    - scope:agents
    - phase-2
depends_on:
    - 263
    - 307
blocked: true
block_reason: 'Pending decisions: 228-parallel-fan-out and 228-esub-utility-subagents (both approved: false). Dependencies #263 and #307 not done.'
class: standard
---

## Acceptance Criteria

- [ ] `reviewer.agent.md` frontmatter `agents:` changed from `[]` to `[quality-runner, code-reader]`
- [ ] Reviewer workflow section dispatches Quality-Runner (code-review steps 3-5) and Code-Reader (steps 6.0-6.6, 7.1-7.4) as parallel `runSubagent` calls
- [ ] Input contract for Quality-Runner call: task_id, test_paths, coverage_modules, lint_paths (per quality-runner agent contract)
- [ ] Input contract for Code-Reader call: task_id, ac_lines, changed_files, test_files (per code-reader agent contract, research doc S3b)
- [ ] Synthesis section merges both reports into unified AC compliance table: cross-walk Code-Reader AC coverage with Quality-Runner test pass/fail per line
- [ ] Automatic FAIL triggers: any MISSING/WEAK from Code-Reader, any test failure from Quality-Runner, any security finding
- [ ] Sequential fallback: if either `runSubagent` returns an execution error (crash, timeout, exception — not a FAIL verdict), reviewer runs the full 9-step sequential workflow from code-review skill
- [ ] Fallback noted in Channel B body: "Parallel fan-out failed: {reason}. Fell back to sequential."
- [ ] code-review SKILL.md updated: new Step 2.5 (parallel dispatch) and modified Step 8 (synthesis from reports) per research doc S3f
- [ ] Reviewer `tools:` list unchanged (required for fallback mode)

## Context

See docs/research/reviewer-parallel-fan-out.md for full design validation.
Split recommended by research doc S5: Code-Reader creation separated as #307.

Depends on: #263 (Quality-Runner subagent), #307 (Code-Reader subagent)
Blocked by: decisions 228-parallel-fan-out and 228-esub-utility-subagents (both pending)

[[2026-03-30]] Mon 21:45
## Architecture Review
**Verdict:** REFINE

### AC Assessment

| AC Line (original) | Assessment | Action |
|---------------------|------------|--------|
| Reviewer dispatches QR and CR as parallel subagents | Correct concept but lacks input contracts and dispatch mechanics | Rewritten with explicit contracts |
| Code-Reader agent.md created (read-only, assign mode) | Duplicates #307 scope | Removed: #307 handles Code-Reader creation |
| Reviewer synthesizes both results into verdict | Vague: no merge rules, no FAIL triggers | Rewritten: cross-walk reports, automatic FAIL triggers listed |
| Fallback to sequential if parallel call fails | Vague: "fails" undefined | Rewritten: execution error (crash/timeout/exception), not FAIL verdict |

### Architecture Notes

Research is thorough (docs/research/reviewer-parallel-fan-out.md). The step-to-subagent split is clean: steps 3-5 (Quality-Runner) and steps 6-7 (Code-Reader) have zero data dependencies. Merge at step 8 is the natural synthesis point. Matches VS Code "Thorough Reviewer" multi-perspective pattern.

Current reviewer.agent.md has `agents: []` and full tool set: both need updating (agents list) and preserving (tools for fallback).

Code-review SKILL.md changes (Step 2.5, Step 8) are same-domain (agent-config) and same logical change: kept in scope.

### Changes Made

- Rewrote body with 10 precise AC lines (all verifiable pass/fail)
- Removed Code-Reader creation from scope (handled by #307)
- Added formal depends_on: [263, 307]
- Blocked: pending decisions 228-parallel-fan-out and 228-esub-utility-subagents
- Created test task #437 (Test: parallel fan-out in reviewer agent)

### Dependencies

- Added: #307 (Code-Reader subagent): must be done before wiring
- Verified: #263 (Quality-Runner subagent): backlog, blocked by decision 228-esub
- Created: #437 (test task): preceding RED phase
- Blocking decisions: 228-parallel-fan-out (approved: false), 228-esub-utility-subagents (approved: false)
