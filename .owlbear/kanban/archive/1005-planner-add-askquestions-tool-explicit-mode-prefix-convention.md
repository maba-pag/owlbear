---
id: 1005
title: 'Planner: add askQuestions tool + explicit mode prefix convention'
status: archived
priority: medium
created: 2026-04-18 21:54:25.167093+00:00
updated: 2026-04-19 03:09:24.370526+00:00
tags:
- type:improvement
- scope:agents
parent: 998
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Problem

planner.agent.md lacks `vscode/askQuestions` and has no explicit mode detection for user-invoked vs dispatch contexts. The current "parent task ID" detection is natural-language inference and unreliable (failed in #973).

## Changes Required

1. Add `vscode/askQuestions` to planner.agent.md tools list.
2. Replace the existing dual-mode detection with explicit mode prefix convention:
   - `Plan and create: #{id} — ...` → dispatch mode (claim task, auto-create subtasks)
   - `Plan: ...` (default) → user mode (present plan → askQuestions → create on approve)
3. Update the `<critical_rules>` execution mode section with the new prefix convention.
4. Document fallback: if mode unclear, default to approval mode (safe default).
5. Add `<examples>` showing both prefix patterns.

## Acceptance Criteria

- planner.agent.md has `vscode/askQuestions` in tools list.
- Execution mode section documents the explicit prefix convention with both modes.
- Default (no "and create" prefix) uses askQuestions for approval before creating tasks.
- "Plan and create" prefix skips approval and auto-creates.
- Fallback to approval mode when prefix is ambiguous.

## Affected Files

- `share/agents/planner.agent.md`

## Context

See `.owlbear/research/998-planner-askquestions-approval.md` for trade-off analysis.
[[2026-04-18]]

## Research

- Research doc: .owlbear/research/1005-planner-askquestions-mode-prefix.md
- Sources: 5 studied, 4 high-relevance
- Recommendation: Proceed with parent #998 design — 5 changes to planner.agent.md (tools list, argument-hint, execution mode section, fallback behavior, examples). Confidence: 0.85.
- Validation pass: parent research current, codebase unchanged, architecture review approved at 0.88
- Challenge: skipped (validation pass — parent challenged twice)
- Follow-up tasks created: none (this task IS the follow-up; siblings #1006-#1008 exist)
- Decision requests: none (T1 — user-directed agent instruction change)
[[2026-04-18]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One file (`planner.agent.md`), one concern (mode detection + askQuestions) |
| Interface clarity | REFINE | Three AC gaps found — refined below |
| Dependency correctness | PASS | No deps. Siblings #1006-#1008 depend on this task correctly |
| Module layering | N/A | Agent instruction file only |
| TDD compliance | PASS | Non-implementation. Added `agent` tag for pass-through |
| KISS/YAGNI | PASS | Minimal scope — 5 specific changes to one file |
| Premise challenge | PASS | Addresses real #973 failure. NL-based detection is documented as unreliable |
| Pattern consistency | PASS | Extends askQuestions pattern from ideator. Prefix convention is new but simple |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Agents domain only |

### AC Refinements (BINDING — supersede original AC)

Original AC line 5 ("Fallback to approval mode when prefix is ambiguous") is imprecise and the parent #998 architecture review's "pipeline markers → abort" fallback is underspecified. The original AC also omits the `argument-hint` update (parent arch review C2), the `output_format` update (research finding), and the rejection path.

**Refined Acceptance Criteria:**

- [ ] `vscode/askQuestions` added to tools list in planner.agent.md frontmatter.
- [ ] `argument-hint:` field reflects dual-prefix convention (both "Plan:" and "Plan and create:" modes visible in hint text).
- [ ] `<critical_rules>` execution mode section defines three detection tiers:
  1. "Plan and create: #{id} — ..." prefix → dispatch mode (claim task, auto-create subtasks, no askQuestions).
  2. "Plan: ..." prefix → user mode (present plan, askQuestions for approval, create only on approve).
  3. Neither prefix detected → fall back to existing NL-based parent-task-ID heuristic (temporary compatibility until #1007/#1008 ship). If NL heuristic inconclusive → default to approval mode (safe default).
- [ ] User-mode rejection path: if user rejects at askQuestions, planner stops without creating tasks and reports cancellation.
- [ ] `<output_format>` section: "When user-invoked without a parent task" wording updated to reference the "Plan:" prefix as the trigger for user-invoked context.
- [ ] `<examples>` section includes: (1) good example of "Plan:" prefix → askQuestions → create on approve, (2) good example of "Plan and create:" prefix → auto-create, (3) bad example of prefix-less pipeline dispatch triggering askQuestions mid-pipeline.
- [ ] Existing NL-based dispatch detection PRESERVED (not replaced) — annotated as temporary compatibility layer pending #1007/#1008. The "Plan and create:" prefix is additive, not a replacement of the NL detection.

### Critical Design Decision: Phased Transition (addresses challenger C1)

The original design assumed atomic rollout of all four sibling tasks. Challenger identified that the dependency graph enforces build ORDER (#1007/#1008 after #1005) but not co-deployment. Between #1005 completion and #1007/#1008 completion, pipeline dispatchers (architect, ideator) still use `Plan: ...` — which under a prefix-only scheme would trigger approval mode mid-pipeline, reproducing the #973 failure.

**Resolution:** #1005 is now ADDITIVE, not a replacement:

- ADDS "Plan and create:" prefix detection (dispatch mode)
- ADDS "Plan:" prefix detection (user approval mode with askQuestions)
- PRESERVES existing NL-based detection as tier-3 fallback
- #1007/#1008 update callers to use "Plan and create:" prefix
- NL detection can be removed in a cleanup task after all callers adopt prefixes

This eliminates the temporal gap. Pipeline dispatches continue working via NL detection during transition. User invocations get the new askQuestions flow immediately.

### Non-Implementation Tagging

Task modifies agent instruction file only — no testable Python code. Requires `agent` tag for test-writer pass-through. Current tags: `type:improvement`, `scope:agents`. **Builder/orchestrator must add `agent` tag before test-writer processes this task.**

### Challenge Results

- Challenger: reconsider (0.55)
- Key concerns: C1 partial rollout temporal gap (critical), C2 "pipeline markers" underspecified (moderate), C3 output_format AC not verifiable (minor), C4 agent tag missing (minor), B2 rejection path undefined
- Architect response: C1 accepted — redesigned as phased/additive transition; C2 accepted — removed "pipeline markers" requirement, simplified to tier-3 NL fallback; C3 accepted — rewrote AC line; C4 accepted — flagged for tagging; B2 accepted — added rejection AC
- Post-refinement confidence: 0.85

### Verdict: APPROVE (REFINE → APPROVE)

### Action Taken: Advanced to todo with binding AC refinements. Phased transition design replaces atomic-rollout assumption. NL detection preserved as temporary compatibility layer

[[2026-04-19]]

## Test-Writer Notes

- Non-impl pass-through: AC references only `share/agents/planner.agent.md` — a `.agent.md` instruction file. No testable Python interfaces.
- Step 2a heuristic: no `implement`, `function`, `class`, `module`, `src/`, `.py` keywords in AC. All AC lines describe changes to agent frontmatter, `<critical_rules>`, `<output_format>`, and `<examples>` sections.
- Architecture Review (in task body) explicitly flags: "Task modifies agent instruction file only — no testable Python code."
- No tests written. Passing through to builder.
[[2026-04-19]]

## Builder Notes

**Files changed:** `share/agents/planner.agent.md` (1 file)

**Changes applied (all 5 refined AC items):**

1. `vscode/askQuestions` added to tools list in frontmatter.
2. `argument-hint` updated to show both modes: `"Plan: {description}  |  Plan and create: #{id} — {description}"`.
3. `<critical_rules>` execution mode section replaced with three-tier detection (dispatch prefix → user approval prefix → NL heuristic compatibility fallback), with rejection path and compatibility-layer annotation.
4. `<output_format>` updated: "When user-invoked without a parent task" → "When invoked with a `Plan:` prefix (user mode)" + references askQuestions approval flow.
5. `<examples>` section: added 3 new examples (Plan: → askQuestions → create on approve; Plan and create: → auto-create; bad: prefix-less dispatch mid-pipeline stall).

**NL detection preserved** as tier-3 compatibility fallback annotated with #1007/#1008 removal note.

**Test results:** Non-implementation task — no tests written (agent instruction file only). Architecture Review explicitly flagged no testable Python code.
**Lint status:** N/A (Markdown file)
**Evidence:** All 6 refined AC checkboxes satisfied per file inspection.
[[2026-04-19]]

## Review Evidence

### Test Results

- pytest: N/A — non-implementation task (agent instruction file only; test-writer pass-through confirmed)

### Lint: N/A — Markdown file

### Coverage: N/A

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

No `TestFromAC_*` classes exist. Architecture Review and test-writer both explicitly flagged no testable Python code. Conditional skipped.

#### Security Review

- Markdown `.agent.md` instruction file only. No code paths, no data handling, no dependencies added.
- No OWASP Top 10 concerns applicable. No issues.

#### Test Integrity

No `TestFromAC_*` classes exist. Conditional skipped.

#### Test Quality

Non-implementation task. No tests to evaluate. Conditional skipped.

#### Data Safety

- No data handling introduced. No issues.

#### Implementation-Aware Gaps

- No executable code changed. Conditional skipped.

#### Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL

- None

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| `vscode/askQuestions` added to tools list | `planner.agent.md` line 9: `[vscode/memory, vscode/askQuestions, ...]` | N/A | PASS |
| `argument-hint` reflects dual-prefix convention | `planner.agent.md` line 4: `"Plan: {description}  \|  Plan and create: #{id} — {description}"` | N/A | PASS |
| Three-tier execution mode in `<critical_rules>`: tier 1 = dispatch prefix, tier 2 = Plan: prefix + askQuestions + rejection path, tier 3 = NL heuristic fallback | `planner.agent.md` lines 41–46: numbered list with all three tiers present, rejection path on tier 2, NL fallback on tier 3 | N/A | PASS |
| User-mode rejection path: stop without creating tasks, report cancellation | `planner.agent.md` line 44: "If user rejects, stop and report cancellation without creating tasks." | N/A | PASS |
| `<output_format>` updated: "When user-invoked without a parent task" → "Plan: prefix" wording | `planner.agent.md` line 62: "When invoked with a `Plan:` prefix (user mode)…" | N/A | PASS |
| `<examples>`: good Plan:→askQuestions→approve, good Plan and create:→auto-create, bad prefix-less→stall | `planner.agent.md` lines 91–96 (Plan: good), 98–103 (Plan and create: good), 105–111 (prefix-less bad) | N/A | PASS |
| NL detection PRESERVED as tier-3 compatibility layer, annotated with #1007/#1008 | `planner.agent.md` line 45–46: tier 3 present with `*(Tier 3 is a temporary compatibility layer — will be removed once callers adopt "Plan and create:" prefix via tasks #1007/#1008.)*` | N/A | PASS |

### Confidence: .97

### Verdict: PASS

[[2026-04-19]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `planner.agent.md` is an agent instruction file only. `.github/copilot-instructions.md` tracks tech stack + backend endpoints — no per-agent argument-hint conventions documented there. No update needed. |
| 2 | Module docstrings | No | N/A | No Python modules created or modified. |
| 3 | External attribution | No | N/A | All 5 research sources are internal (research doc, codebase files, kanban task body). External VS Code Custom Agents and Subagents docs already attributed under Task #998 in `sources/overview.md`. No new external sources. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/1005-planner-askquestions-mode-prefix.md` exists and is linked in task body. Follow-up tasks noted as N/A — siblings #1006–#1008 handle caller updates. |

### Files Updated

- None

### Scratch Files Cleaned

- None (no `.owlbear/scratch/1005-*` files existed)
[[2026-04-19]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| `vscode/askQuestions` added to tools list | `planner.agent.md` L9: tools list includes `vscode/askQuestions` | PASS |
| `argument-hint` reflects dual-prefix convention | `planner.agent.md` L4: `"Plan: {description}  \|  Plan and create: #{id} — {description}"` | PASS |
| Three-tier execution mode in `<critical_rules>` | `planner.agent.md` L41-46: dispatch prefix, user approval prefix, NL heuristic fallback — all present | PASS |
| User-mode rejection path | `planner.agent.md` L44: "If user rejects, stop and report cancellation without creating tasks." | PASS |
| `<output_format>` references Plan: prefix | `planner.agent.md` L62: "When invoked with a `Plan:` prefix (user mode)…" | PASS |
| Three examples (good Plan:, good Plan and create:, bad prefix-less) | `planner.agent.md` L101-120: all 3 examples present with correct why annotations | PASS |
| NL detection preserved as tier-3 with #1007/#1008 annotation | `planner.agent.md` L45-46: tier 3 present with removal note referencing #1007/#1008 | PASS |

### Test Results

- pytest: 658 passed, 6 failed (all in serve/mcp-knowledge/tests/ — pre-existing, unrelated to task scope)
- ruff: clean

### Architect Quality: 5/5

Refined AC was specific, verifiable, and complete. Phased transition design (addressing challenger C1) eliminated temporal gap risk. All challenger concerns addressed with binding refinements. No improvisation required by builder.

### Deduction Breakdown

- AC lines without evidence: 0 (-.02 each) = 0
- Lint violations: 0 (-.05) = 0
- AC quality score <=3: no (-.03) = 0
- Missing reviewer evidence: no (-.02) = 0
- Full-suite failures in task scope: 0 (-.05) = 0

### Confidence: 1.00

### Action: archive
