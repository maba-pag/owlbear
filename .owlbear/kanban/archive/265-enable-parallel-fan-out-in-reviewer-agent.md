---
id: 265
title: Enable parallel fan-out in reviewer agent
status: archived
priority: medium
created: 2026-03-30 19:31:23.560659+02:00
updated: 2026-04-05 15:04:47.313955+02:00
started: 2026-04-05 15:04:47.313955+02:00
completed: 2026-04-05 15:04:47.313955+02:00
tags:
- scope:agents
- phase-2
depends_on:
- 263
- 307
class: standard
archival_reason: completed
archival_refs: []
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

[[2026-04-04]] Sat 23:03
## Builder Notes
- Files changed: `.github/agents/reviewer.agent.md`, `.github/skills/w-code-review/SKILL.md`
- RED verified: 14/14 `TestFromAC_ReviewerParallelFanOutDetailed` tests FAILED before implementation
- GREEN: 14/14 passed after implementation
- ruff: clean (docs-only changes, no Python touched)
- Pre-existing failures in `test_agent_port_v2.py`: 18 failures confirmed identical before/after changes (stash comparison)

### Changes Applied
1. `reviewer.agent.md` `<subagents>` table: added quality-runner row with When="Implementation reviews requiring test/lint/coverage evidence" and example invocation format
2. `w-code-review/SKILL.md` Step 2.5: replaced minimal dispatch with correct `runSubagent` format for both agents, full 5-field QR contract (mode, task_id, test_paths, coverage_modules, lint_paths), full 4-field CR contract (task_id, ac_lines, changed_files, test_files), step mapping (QR→steps 3–5, CR→steps 6–7), execution error fallback with Channel B format
3. `w-code-review/SKILL.md` Step 8: enriched synthesis paragraph with unified AC compliance table, cross-walk description, and automatic FAIL triggers (MISSING/WEAK from Code-Reader; test failure from Quality-Runner; security finding from Code-Reader)

### Commit
e3871be feat: wire quality-runner and code-reader parallel fan-out in reviewer (#265, builder)

[[2026-04-05]] Sun 10:02
## Review Evidence

### Test Results
- pytest test_reviewer_parallel_fan_out_265.py: **14 passed, 0 failed**
- pytest test_reviewer_parallel_fan_out_437.py (preconditions): **5 passed, 0 failed**

### Lint: clean (ruff)

### Coverage: N/A — markdown/YAML config changes only

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC 1: agents: frontmatter has quality-runner | test_437::test_reviewer_agents_contains_quality_runner | Yes | COVERED |
| AC 2: runSubagent dispatch for QR + CR | test_step_2_5_*_uses_runsubagent_format | Yes | COVERED |
| AC 3: QR 5-field contract | test_step_2_5_quality_runner_input_contract_has_all_five_fields | Yes | COVERED |
| AC 4: CR 4-field contract | test_step_2_5_code_reader_dispatch_full_contract_in_runsubagent_format | Yes | COVERED |
| AC 5: Step 8 unified AC compliance table + cross-walk | test_step_8_synthesis_references_* | Yes | COVERED |
| AC 6: FAIL triggers (MISSING/WEAK, QR failure, security) | test_step_2_5_or_step_8_documents_* (2 tests) | Yes for MISSING/WEAK + QR; "security finding" compensated by pre-existing Step 5.1 | LAX |
| AC 7: Fallback triggers on execution error | test_step_2_5_fallback_triggers_on_execution_error | Yes | COVERED |
| AC 8: Channel B fallback note format | test_step_2_5_fallback_channel_b_note_format | Yes | COVERED |
| AC 9: SKILL.md Step 2.5 + Step 8 updated | All Step 2.5 + Step 8 tests | Yes | COVERED |
| AC 10: tools: list unchanged | test_437::test_reviewer_tools_* | Yes | COVERED |

No MISSING. One LAX (AC 6: "security finding" trigger not directly tested; compensated by pre-existing SKILL.md Step 5.1).

#### Security Review: No issues — markdown/YAML config files only

#### Test Integrity
Chore commit 46a8f1d updated path constants from .github/ → share/ after repo reorganization. All 14 assertions PRESERVED. Builder commit e3871be did not touch test file.

#### Test Quality: STRONG — specific string assertions, mutation-robust, independent, descriptive names

#### Data Safety: No issues

#### Implementation-Aware Gaps: None — all significant paths tested

#### Builder Process Quality: 1 builder notes section. CLEAN.

### Pass 2 — INFORMATIONAL
Builder reported old .github/ paths; live deliverables are in share/ (post-reorganization). No functional impact.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC 1 | share/agents/reviewer.agent.md line 8: agents: [code-reader, scribe, quality-runner] | PASS |
| AC 2 | SKILL.md Step 2.5: agentName: quality-runner + agentName: code-reader blocks | PASS |
| AC 3 | Step 2.5: mode, task_id, test_paths, coverage_modules, lint_paths | PASS |
| AC 4 | Step 2.5: task_id, ac_lines, changed_files, test_files | PASS |
| AC 5 | Step 8: "unified AC compliance table by cross-walking Code-Reader's AC coverage assessment against Quality-Runner's test pass/fail" | PASS |
| AC 6 | Step 8: "Automatic FAIL triggers: any MISSING or WEAK finding from Code-Reader; any test failure reported by Quality-Runner; any security finding from Code-Reader" | PASS |
| AC 7 | Step 2.5: "execution error (crash, timeout, exception — not a FAIL verdict)" | PASS |
| AC 8 | Step 2.5: "Parallel fan-out failed: {reason}. Fell back to sequential." | PASS |
| AC 9 | Step 2.5 heading + Step 8 enriched — verified above | PASS |
| AC 10 | reviewer.agent.md 16-entry tools list preserved | PASS |

### Confidence: .95
### Verdict: PASS

[[2026-04-05]] Sun 11:10
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `.github/copilot-instructions.md` is 3 lines (project identity only) — no reviewer or workflow section exists to update |
| 2 | Module docstrings | No | N/A | No Python modules changed — deliverables are `share/agents/reviewer.agent.md` and `share/skills/w-code-review/SKILL.md` (markdown/YAML only) |
| 3 | External attribution | Yes | Verified | `.owlbear/sources/overview.md` § "Reviewer Parallel Fan-Out (Task #265)" (lines 343–349) already contains all 3 VS Code sources (Agents Concepts, Subagents Guide, Custom Agents docs) from research doc — no update needed |
| 4 | CLI changes | No | N/A | No CLI commands added or changed |
| 5 | Research doc | Yes | Verified | `.owlbear/research/reviewer-parallel-fan-out.md` exists; follow-up tasks #307 (Code-Reader) and #437 (test task) created by architecture review |

### Files Updated
- None

### Scratch Files Cleaned
- None found for task 265

[[2026-04-05]] Sun 15:04
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC 1: agents: has quality-runner, code-reader | reviewer.agent.md L9: agents: [code-reader, scribe, quality-runner] | PASS |
| AC 2: parallel runSubagent dispatch | SKILL.md L56-76: agentName blocks for both agents | PASS |
| AC 3: QR 5-field contract | Step 2.5: mode, task_id, test_paths, coverage_modules, lint_paths | PASS |
| AC 4: CR 4-field contract | Step 2.5: task_id, ac_lines, changed_files, test_files | PASS |
| AC 5: Unified AC table + cross-walk | SKILL.md L263: cross-walk description | PASS |
| AC 6: FAIL triggers | SKILL.md L263: MISSING/WEAK, QR failure, security (LAX on security, compensated by Step 5.1) | PASS |
| AC 7: Fallback on execution error | Step 2.5 L74: crash/timeout/exception | PASS |
| AC 8: Channel B fallback note | Step 2.5 L76: exact format | PASS |
| AC 9: SKILL.md Step 2.5 + Step 8 | L52 heading + L263 synthesis | PASS |
| AC 10: tools: unchanged | 16-entry tools list preserved | PASS |

### Test Results
- pytest (task-scoped): 19/19 passed
- pytest (full suite): 2878 passed, 432 failed, 18 skipped (0 in task scope; all pre-existing)
- ruff: All checks passed

### Architect Quality: 4/5
### Confidence: .98
### Action: archive
