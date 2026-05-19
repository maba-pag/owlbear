---
id: 1002
title: Add agent-extraction markers to h-agent-structure
status: archived
priority: important
created: 2026-04-18 21:34:45.363367+00:00
updated: 2026-04-19 11:53:44.343429+00:00
tags:
- agent
- agent-ecosystem
parent: 984
depends_on:
- 1000
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Objective

Add a section to `share/skills/h-agent-structure/SKILL.md` defining concrete markers for when to extract a concern into a dedicated agent or subagent, and counter-markers for premature extraction.

## Context

No formal criteria exist for deciding when a concern warrants its own agent vs. remaining part of an existing agent. The quality-runner extraction from builder is a precedent but undocumented. The audit prompt (Task 2, sibling) will use these markers to flag missed extraction opportunities.

## Acceptance Criteria

- [ ] New `## Agent Extraction Markers` section in `share/skills/h-agent-structure/SKILL.md`.
- [ ] 3-5 extraction markers (signals a concern warrants its own agent), each as a single-line conditional. Examples: "Concern requires a distinct `tools:` allowlist"; "Concern has an independent failure domain (its failure should not abort the parent)"; "Same delegation pattern appears in 2+ agents."
- [ ] 2-3 counter-markers (signals extraction is premature), same format. Examples: "Concern is invoked from exactly one call site"; "No distinct tool or model requirements."
- [ ] At least one precedent from the current ecosystem cited inline (quality-runner extraction from builder, with 1-line rationale).
- [ ] No rationale prose beyond the precedent line — markers and counter-markers only.

## Files

- `share/skills/h-agent-structure/SKILL.md`

[[2026-04-19]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One section added to one file |
| Interface clarity | PASS | AC specifies section name, marker counts (3-5/2-3), format (single-line conditionals), precedent requirement, no-prose constraint |
| Dependency correctness | PASS | #1000 archived/done — h-agent-structure already expanded with instruction taxonomy + boundary fitness |
| Module layering | PASS | Skill file only, no code dependencies |
| TDD compliance | PASS | Non-impl task; tagged `agent` for test-writer pass-through |
| KISS/YAGNI | PASS | Minimal scope; AC explicitly forbids rationale prose |
| Premise challenge | PASS | No extraction criteria exist in h-agent-structure (confirmed via full file read). Quality-runner is real undocumented precedent |
| Pattern consistency | PARTIAL | File uses tables (Boundary Fitness, Agent Tiers, Implicit Encoding); AC constrains to single-line conditionals. Format departure is intentional for terseness — acceptable but builder should be aware |
| Security surface | PASS | No system boundaries |
| Single domain | PASS | Agent-ecosystem only |

### Architecture Notes

1. **Counter-marker validation.** AC example "Concern is invoked from exactly one call site" doesn't hold against `fix-attempt` (single call-site from builder, yet extracted as T4 agent). Builder should validate all proposed markers against the full T4 extraction set: quality-runner, fix-attempt, code-reader — not just quality-runner.
2. **Boundary Fitness distinction.** Existing `### Boundary Fitness` section (line ~35) defines *where content goes*. New `## Agent Extraction Markers` defines *when to create an agent*. Builder should ensure the sections are clearly distinct and non-overlapping.
3. **Placement.** AC doesn't specify where in the file. Recommended: after `## Agent Tiers` (structural concern about agent creation, logically follows tier classification). Before `## Principles` also works.
4. **Downstream consumer.** Task #1003 (audit prompt rewrite) will reference these markers. Single-line prose format is sufficient — the audit prompt references rather than mechanically parses.

### Challenge Results

- Challenger: proceed (confidence 0.65)
- Key challenges: counter-marker examples contradict fix-attempt extraction (C1), format departs from file's table convention (C2), single-precedent evidence base (B1), Boundary Fitness overlap risk (B3)
- Architect response: Accepted all challenges as valid observations. Addressed via architecture notes above. None warrant blocking — all catchable in review.

### Verdict: APPROVE

### Action Taken: Advanced to todo with architecture notes for builder guidance

[[2026-04-19]]

## Test-Writer Notes

- Non-implementation task (tagged `agent`) — no tests applicable.
- AC targets only `share/skills/h-agent-structure/SKILL.md` (SKILL.md, non-Python file).
- Architecture review confirmed pass-through: "Non-impl task; tagged `agent` for test-writer pass-through".
- Passing through to builder.
[[2026-04-19]]

## Builder Notes

### Files Changed

- `share/skills/h-agent-structure/SKILL.md` — added `## Agent Extraction Markers` section

### Changes Applied

New section inserted after `## Agent Tiers`, before `## Principles`:

- **5 extraction markers** (`≥2` threshold): distinct `tools:` allowlist, independent failure domain, reuse across 2+ agents, distinct model profile, procedure exceeds one screen inline
- **3 defer markers** (`<2` extract conditions apply): no distinct tools/model, failure not independent, fits in single `<critical_rules>` bullet
- **Precedent**: quality-runner from builder (1-line rationale)
- No rationale prose beyond precedent line

### Architecture Note Addressed

Validated counter-markers against T4 extractions (quality-runner, fix-attempt, code-reader). "Concern is invoked from exactly one call site" intentionally excluded after arch review flagged fix-attempt as counterexample. Defer-when header threshold (`<2 extract conditions apply`) prevents counter-markers from incorrectly blocking legitimate single-call-site extractions like fix-attempt.

### Test Results

Non-implementation task — no tests applicable (pass-through per test-writer notes). No Python files changed.

### Lint

Not applicable (Markdown file only).

### Commit

`c1302e15` — `docs(h-agent-structure): add agent extraction markers section`
[[2026-04-19]]

## Review Evidence

### Test Results

N/A — non-implementation task (Markdown only). No Python files changed. Test-writer confirmed pass-through.

### Lint

N/A — Markdown file only.

### Coverage

N/A

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

No `TestFromAC_*` classes — skip (conditional per skill).

#### Security Review

No issues. Markdown-only change, no system boundaries.

#### Test Integrity

No `TestFromAC_*` classes — skip (conditional per skill).

#### Test Quality

N/A

#### Data Safety

No issues.

#### Implementation-Aware Gaps

N/A — no code paths.

#### Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL

None.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| New `## Agent Extraction Markers` section in SKILL.md | `SKILL.md:54` — section header present | N/A | PASS |
| 3-5 extraction markers, single-line conditional format | `SKILL.md:57-61` — 5 markers, each a single-line bullet | N/A | PASS |
| 2-3 counter-markers, same format | `SKILL.md:64-66` — 3 defer markers, each a single-line bullet | N/A | PASS |
| Quality-runner precedent with 1-line rationale | `SKILL.md:69` — precedent line cites quality-runner + 1-line rationale | N/A | PASS |
| No rationale prose beyond precedent line | `SKILL.md:56-69` — section contains only markers, counter-markers, and one precedent line | N/A | PASS |

### Architecture Notes Addressed

- Counter-marker "invoked from exactly one call site" excluded (fix-attempt counterexample). Threshold (`< 2 extract conditions apply`) prevents incorrect blocking. ✓
- Boundary Fitness overlap: distinct sections (Boundary Fitness = where content goes; Extraction Markers = when to create an agent). ✓
- Placement: inserted after `## Agent Tiers`, before `## Principles` — matches arch recommendation. ✓

### Verdict

5/5 AC lines PASS. No security concerns. Builder process CLEAN. 0 deductions.
Confidence: .97 → PASS
[[2026-04-19]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Skill file content addition only; `copilot-instructions.md` has no reference to `h-agent-structure`, no system behavior changed |
| 2 | Module docstrings | No | N/A | No Python files changed (Markdown only) |
| 3 | External attribution | No | N/A | Quality-runner precedent is internal OwlBear ecosystem — no external sources |
| 4 | CLI changes | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | No research doc produced; arch review was inline in task body |

### Files Updated

- None (SKILL.md itself is the deliverable; content verified correct at lines 54–72: 5 extract markers, 3 defer markers, precedent line — all AC items confirmed)

### Scratch Files Cleaned

- None found matching `.owlbear/scratch/1002-*`
[[2026-04-19]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| New `## Agent Extraction Markers` section in SKILL.md | `SKILL.md:54` — section header present | PASS |
| 3-5 extraction markers, single-line conditional format | `SKILL.md:58-62` — 5 markers, each a single-line bullet | PASS |
| 2-3 counter-markers, same format | `SKILL.md:65-67` — 3 defer markers, single-line bullets | PASS |
| Quality-runner precedent with 1-line rationale | `SKILL.md:70` — precedent line cites quality-runner + 1-line rationale | PASS |
| No rationale prose beyond precedent line | `SKILL.md:56-71` — only markers, counter-markers, headings, and one precedent line | PASS |

### Test Results

- pytest: 658 passed, 6 failed (all in mcp-knowledge domain — pre-existing, not in task scope)
- ruff: clean

### Architect Quality: 5/5

AC was highly specific: section name, marker counts (3-5/2-3), format (single-line conditionals), precedent requirement, no-prose constraint. Architecture notes were actionable — counter-marker validation against T4 set, Boundary Fitness overlap warning, placement recommendation. Builder addressed all notes.

### Deduction Breakdown

- AC lines with no evidence: 0 (5/5 verified) → -0
- Lint violations: 0 → -0
- AC quality ≤ 3: no (5/5) → -0
- Missing reviewer evidence: no (present, detailed) → -0
- Full-suite failures in task scope: 0 → -0

### Confidence: 1.00

### Action: archive
