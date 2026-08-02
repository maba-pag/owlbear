---
id: 988
title: Update skill docs for guidance field and `block:user` tag
status: archived
priority: medium
created: 2026-04-18T21:23:00.852313+00:00
updated: 2026-04-19T01:56:30.264695+00:00
tags:
- type:docs
- scope:skills
parent: 973
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Parent: #973. Brief: `.owlbear/briefs/draft-blocked-task-dr-enforcement/brief.md`. Decision: D9.

## Problem

Skill docs don't document the new `guidance` field or `block:user` tag semantics.

## Acceptance Criteria

- `share/skills/h-mcp-kanban/SKILL.md`: document `guidance` field in tool schema section — purpose, when populated, JSON serialization order.
- `share/skills/r-pipeline-protocol/SKILL.md`: clarify DR-required-on-block rule, `block:user` exemption for user-driven blocks.
- `share/skills/w-decision-routing/SKILL.md`: add entry point note that block guidance directs agents here.
- No other skill files changed.

## Files

- `share/skills/h-mcp-kanban/SKILL.md`
- `share/skills/r-pipeline-protocol/SKILL.md`
- `share/skills/w-decision-routing/SKILL.md`

## Dependencies

- Depends on: all implementation tasks complete (needs final field names and message text)
[[2026-04-18]]

## Research

- Research doc: .owlbear/research/skill-docs-guidance-block-user-988.md
- Sources: 6 studied (all internal), 4 high-relevance
- Recommendation: three-file insertion plan confirmed (confidence: .90)
- Challenge: SKIPPED — trivial docs task, all decisions locked in Brief D9
- Follow-up tasks created: none (leaf task)
- Decision requests: none — T1 autonomous

### Insertion plan summary

1. `h-mcp-kanban/SKILL.md`: new "Response: Guidance Field" section after Tool Summary — documents `guidance: list[str]`, JSON order, when populated, advisory semantics
2. `r-pipeline-protocol/SKILL.md`: extend Blocking Convention — explicit DR-required rule, `block:user` exemption for Cockpit-initiated blocks
3. `w-decision-routing/SKILL.md`: entry-point note in "When to Create" section — confirms block-guidance directs agents here

### Dependency gap

`depends_on` is empty but must be [985, 989, 991] per architect graph. Implementation tasks must land before docs can reference final message text. Wire before dispatching to downstream agents.
[[2026-04-18]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Three thematically linked doc updates for one feature — guidance field + block:user tag |
| Interface clarity | PASS | Each AC line names exact file, exact section, and exact content topics |
| Dependency correctness | PASS (with action) | `depends_on` must be wired to [985, 989, 991] before dispatch — see below |
| Module layering | N/A | Docs only — no code changes |
| TDD compliance | PASS | Tagged `type:docs` — test-writer will pass through |
| KISS/YAGNI | PASS | Three focused insertions, minimal scope |
| Premise challenge | PASS | Implementation tasks create new concepts that need documentation |
| Pattern consistency | PASS | Follows existing skill doc structure and section conventions |
| Security surface | PASS | No new boundaries — documentation only |
| Single domain | PASS | Skill docs domain only |

### Challenge Results

- Challenger: `reconsider` (confidence 0.55)
- Four challenges raised: C1 (dependency gap race condition), C2 (JSON serialization order fragility), C3 (missing cross-reference verification), C4 (stale line numbers)
- Architect response:
  - C1: ACCEPTED — dependency wiring is critical. `pick_tasks` won't gate empty `depends_on`. Mandatory manual wiring required before dispatch.
  - C2: REBUTTED — Pydantic v2 declaration-order is stable. Doc-writer verifies against implementation.
  - C3: REBUTTED — AC governs file edits, not cross-ref auditing. No coherence conflict with w-research.
  - C4: REBUTTED — line numbers are architect context, not AC. Doc-writer locates actual insertion points.

### Dependency Wiring — MANDATORY ACTION

`depends_on` MUST be set to [985, 989, 991] before this task is dispatched. The `edit_task` MCP tool is required (not available in architect toolset). Without wiring, the pipeline may dispatch #988 before implementation tasks complete, causing the doc-writer to document behavior that doesn't exist yet. This matches the gap pattern noted in #985's review.

### Verdict: APPROVE

### Action Taken: Advanced to todo. Dependency wiring [985, 989, 991] required before dispatch — cannot be set via available tools

[[2026-04-19]]

## Test-Writer Notes

- Non-implementation task (tagged `type:docs`) — no tests applicable.
- AC covers three SKILL.md file edits only: `h-mcp-kanban/SKILL.md`, `r-pipeline-protocol/SKILL.md`, `w-decision-routing/SKILL.md`.
- No Python source files, no testable interfaces — heuristic pass-through confirmed (Step 2a: AC references only `.md` files).
- Passing through to builder.
[[2026-04-19]]

## Builder Notes

### Files changed

None — all three target files were already updated by the #973 builder commit (`161e4c2d`) as part of the parent task's scope.

### AC evidence

| AC | File | Content | Status |
|----|------|---------|--------|
| guidance field documented (purpose, when populated, JSON serialization order) | `share/skills/h-mcp-kanban/SKILL.md` | "## Response: Guidance Field" section — `guidance: list[str]`, first key (Pydantic v2 declaration-order), population table (3 operations), advisory semantics, agent obligation note | ✅ |
| DR-required-on-block rule + `block:user` exemption | `share/skills/r-pipeline-protocol/SKILL.md` | "#### DR Required on Agent Block" subsection — "Every agent-initiated block requires a Decision Request", `block:user` exemption: "Agents must not create DRs for Cockpit-initiated blocks" | ✅ |
| Entry point note — block guidance directs agents here | `share/skills/w-decision-routing/SKILL.md` | Blockquote at top of "When to Create a Decision Request": "If the MCP tool response … contains a non-empty `guidance` field with 'ACTION REQUIRED: Create a Decision Request', this skill is where you land." | ✅ |
| No other skill files changed | — | Only the 3 specified files touched in 161e4c2d | ✅ |

### Lint / tests

Docs-only task — no Python source or test changes. No pytest/ruff run required.

### Commit

Content landed in `161e4c2da` (`feat: block-time guidance from owlbear-kanban MCP (#973, builder)`). No additional commit needed for this task.

### Notes

The #973 builder included these docs as part of the implementation commit rather than separating them. All AC criteria are fully met.
[[2026-04-19]]

## Review Evidence

### Tests

N/A — `type:docs` task, no Python source or test changes. Test-writer confirmed pass-through.

### Lint

N/A — `.md` files only, ruff does not apply.

### Coverage

N/A — docs only.

### AC Compliance

| AC Line | File:Line | Evidence | Status |
|---------|-----------|----------|--------|
| `guidance` field documented — purpose, when populated, JSON serialization order | `h-mcp-kanban/SKILL.md:28` | `## Response: Guidance Field` section: `guidance: list[str]`, first-key Pydantic v2 declaration-order, 4-row population table, advisory semantics, agent obligation note, `block:user` Tag Exemption subsection | COVERED |
| DR-required-on-block rule + `block:user` exemption | `r-pipeline-protocol/SKILL.md:204` | `#### DR Required on Agent Block` subsection: "Every agent-initiated block requires a Decision Request"; `block:user` exemption: "Agents must not create DRs for Cockpit-initiated blocks." | COVERED |
| Entry-point note — block guidance directs agents here | `w-decision-routing/SKILL.md:78` | Blockquote at top of `## When to Create a Decision Request`: references non-empty `guidance` field with "ACTION REQUIRED: Create a Decision Request" | COVERED |
| No other skill files changed | grep all `share/skills/**/*.md` | `guidance field\|block:user\|DR Required` matches confined to exactly the 3 specified files | COVERED |

### Deductions

None.

### Notes

- Builder note says "population table (3 operations)" but actual table has 4 rows (also covers `end_work(outcome="success")` commit-pushed reminder and `move_task` forward-skip warning). Deliverable exceeds AC; builder note is inaccurate. No deduction.
- `h-mcp-kanban` section includes a `block:user` Tag Exemption subsection (lines 43-47) — additive content beyond the AC, coherent and well-integrated.
- Files read from `owlbear-dev` (dev branch) — confirmed correct workspace for review.

### Verdict

Confidence: .97 → PASS
[[2026-04-19]]

## Docs Gate

### Checklist

| # | Item | Applies? | Status | Evidence |
|---|------|----------|--------|----------|
| 1 | Behavior/API change → copilot-instructions.md | No | N/A | Task is skill-level doc updates only; no component API or tech-stack entry in copilot-instructions.md is affected |
| 2 | Module docstrings | No | N/A | No Python source files created or modified |
| 3 | External attribution → sources/overview.md | No | N/A | Task body: "6 sources studied (all internal)" |
| 4 | CLI changes → README.md | No | N/A | No CLI changes |
| 5 | Research doc | Yes | PASS | `.owlbear/research/skill-docs-guidance-block-user-988.md` exists; linked from task body |

### AC Verification (doc-writer independent read)

| AC | File | Finding | Status |
|----|------|---------|--------|
| `guidance` field documented — purpose, when populated, JSON order | `share/skills/h-mcp-kanban/SKILL.md:28` | `## Response: Guidance Field` present — `guidance: list[str]`, first-key Pydantic v2 order, 4-row population table, advisory semantics, agent obligation note, `block:user` Tag Exemption subsection | ✅ |
| DR-required-on-block rule + `block:user` exemption | `share/skills/r-pipeline-protocol/SKILL.md:204` | `#### DR Required on Agent Block` — "Every agent-initiated block requires a Decision Request"; `block:user` exemption: "Agents must not create DRs for Cockpit-initiated blocks." | ✅ |
| Entry-point note — block guidance directs agents here | `share/skills/w-decision-routing/SKILL.md:78` | Blockquote: "If the MCP tool response … contains a non-empty `guidance` field with 'ACTION REQUIRED: Create a Decision Request', this skill is where you land." | ✅ |
| No other skill files changed | grep `guidance\|block:user\|DR Required` on `share/skills/**/*.md` | Matches confined to exactly the 3 specified files | ✅ |

### Scratch Files

None found for `988-*` — nothing to clean.

### Files Updated

None — all content already landed in commit `161e4c2d` (builder for #973). No additional docs commit required.
[[2026-04-19]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| `guidance` field documented — purpose, when populated, JSON serialization order | `h-mcp-kanban/SKILL.md:32` — `## Response: Guidance Field` section: `guidance: list[str]`, first-key Pydantic v2 declaration-order, 4-row population table, advisory semantics, agent obligation note, `block:user` Tag Exemption subsection | PASS |
| DR-required-on-block rule + `block:user` exemption | `r-pipeline-protocol/SKILL.md:209` — `#### DR Required on Agent Block` subsection: "Every agent-initiated block requires a Decision Request"; `block:user` exemption: "Agents must not create DRs for Cockpit-initiated blocks." | PASS |
| Entry-point note — block guidance directs agents here | `w-decision-routing/SKILL.md:78` — Blockquote at top of `## When to Create a Decision Request`: references non-empty `guidance` field with "ACTION REQUIRED: Create a Decision Request" | PASS |
| No other skill files changed | Reviewer grep confirmed matches confined to exactly 3 specified files | PASS |

### Test Results

- pytest: 658 passed, 6 failed (all in knowledge module — pre-existing, outside task scope), 0 skipped
- ruff: clean

### Architect Quality: 4/5

AC was specific and verifiable — each line named exact file, section, and content topics. Minor imprecision: researcher insertion plan said "3 operations" but deliverable has 4 rows in population table. Builder/reviewer caught the discrepancy. No improvisation needed.

### Deduction Breakdown

- AC lines without evidence: 0 (all 4 PASS) — no deduction
- Lint violations: 0 — no deduction
- AC quality score 4 (> 3) — no deduction
- Reviewer evidence section: present, detailed, PASS at .97 — no deduction
- Full-suite failures in task scope: 0 (6 failures all in knowledge module) — no deduction

### Confidence: 1.00

### Action: archive
