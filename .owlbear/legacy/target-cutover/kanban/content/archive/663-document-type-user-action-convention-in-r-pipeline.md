---
id: 663
title: Document type:user-action convention in r-pipeline-protocol and agent-common
status: archived
priority: medium
created: 2026-04-06T16:39:07.7325145+02:00
updated: 2026-04-06T23:18:31.3354218+02:00
started: 2026-04-06T23:18:31.3354218+02:00
completed: 2026-04-06T23:18:31.3354218+02:00
tags:
    - phase-3
    - scope:agent-config
    - type:docs
parent: 661
class: standard
---

## Objective\nDocument the `type:user-action` tag convention, detection heuristics, and lifecycle flow in pipeline protocol and agent-common instructions.\n\n## Context\nFrom #661 research: convention needs documentation so all pipeline agents know how to detect, tag, and handle user-action tasks.\n\n## Acceptance Criteria\n- [ ] r-pipeline-protocol §5.Escalation adds `type:user-action` subsection with: tag purpose, detection heuristics, blocking flow, post-completion flow\n- [ ] agent-common.instructions.md adds user-action detection responsibility table (which agents detect, what they do)\n- [ ] Dry-run scenario documented showing #597-style loop prevented\n- [ ] r-project-standards tags section updated with `type:user-action` definition\n\n## Files Affected\n- share/skills/r-pipeline-protocol/SKILL.md\n- share/instructions/agent-common.instructions.md\n- share/skills/r-project-standards/SKILL.md

[[2026-04-06]] Mon 17:32
## Research
- Research doc: .owlbear/research/document-type-user-action-convention.md
- Sources: 6 studied, 4 high-relevance (all internal — parent #661 research + target files)
- Recommendation: Document as specified — 3 insertions across r-pipeline-protocol §5, agent-common, r-project-standards §5 (confidence: .90)
- Follow-up tasks created: none (this task IS the documentation work)
- Decision requests: none (T1 — documenting an existing convention)

### Insertion Points
1. **r-pipeline-protocol**: New `### User-Action Tasks` subsection between `### Decision Tiers` (L201) and `### Handoff` (L203) — ~40 lines covering tag purpose, detection heuristics table, blocking flow, post-completion fast-path, dual-nature tasks, dry-run scenario
2. **agent-common.instructions.md**: New `## User-Action Detection Responsibilities` section after existing mapping table — ~15 lines with 5-row agent responsibility table
3. **r-project-standards §5**: Add `type:user-action` to Type row examples with pipeline-behavior note

### Challenge
Skipped — no novel recommendation; documenting existing convention from #661 (which was challenged: block → revised to .78).

[[2026-04-06]] Mon 18:05
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | All 4 AC items document one convention (type:user-action) across its canonical locations |
| Interface clarity | PASS | AC1/2/4 specify exact files, sections, content elements. AC3 location implicit from research body (r-pipeline-protocol subsection) — clear in context |
| Dependency correctness | PASS | No deps listed; independent Chain B. #664 correctly depends on this task |
| Module layering | N/A | Documentation only |
| TDD compliance | PASS | type:docs — test-writer pass-through |
| KISS/YAGNI | PASS | 3 targeted insertions, minimal scope |
| Premise challenge | PASS | Convention designed in #661 research. Documentation required for agent awareness |
| Pattern consistency | PASS | Adding subsections to skill files follows existing structure patterns |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | All agent-config/pipeline-protocol documentation domain |

### AC Assessment
| AC Line | Verifiable? | Action |
|---------|------------|--------|
| AC1: r-pipeline-protocol §5 subsection (tag purpose, heuristics, blocking/post-completion flow) | Yes — specific file, section, 4 content elements | None |
| AC2: agent-common detection responsibility table | Yes — specific file, table with agent/action columns | None |
| AC3: Dry-run scenario showing #597-style loop prevented | Yes — research body specifies location in r-pipeline-protocol subsection | Note: doc-writer should place within AC1 subsection per research insertion points |
| AC4: r-project-standards tag taxonomy update | Yes — specific file (§5 Type row), specific tag to add | None |

### Architecture Notes
- Insertion points verified against live files. r-pipeline-protocol §5 currently mentions "physical user action" in Blocking Convention prose (L188) — the new subsection formalizes this into a standalone reference.
- agent-common.instructions.md is short (~24 lines); new section matches existing table-based structure.
- r-project-standards Type row expansion is a 1-line addition + behavioral note row — minimal surface.
- Cross-references between the 3 files are forward-compatible (each section stands alone).

### Challenge Results
- Challenger: FALLBACK — challenger agent not available in current session
- Architect assessment: all 10 criteria PASS, AC is verifiable, documentation-only scope carries low risk

### Verdict: APPROVE
### Action Taken: Advanced to todo. AC3 note added for doc-writer: dry-run scenario belongs in r-pipeline-protocol §5 subsection per research insertion points.

[[2026-04-06]] Mon 18:47
## Test-Writer Notes
- Non-implementation task (tagged type:docs) — no tests applicable.
- Passing through to builder.

[[2026-04-06]] Mon 21:50
## Builder Notes

### Files Changed
- `share/skills/r-pipeline-protocol/SKILL.md` — inserted `### User-Action Tasks` subsection (~50 lines) between `### Decision Tiers` and `### Handoff` in §5 Escalation
- `share/instructions/agent-common.instructions.md` — appended `## User-Action Detection Responsibilities` section with 5-row agent responsibility table
- `share/skills/r-project-standards/SKILL.md` — expanded Type row with `type:user-action` and added behavioral note row

### AC Coverage
- AC1 ✅ r-pipeline-protocol §5 has `### User-Action Tasks` with: tag purpose, detection heuristics table (4 rows), blocking flow (7-step), post-completion fast-path, dual-nature guidance
- AC2 ✅ agent-common has `## User-Action Detection Responsibilities` with 5-row table (researcher/architect/orchestrator/test-writer+builder+reviewer/auditor)
- AC3 ✅ Dry-run scenario in r-pipeline-protocol subsection — 8-step walkthrough showing 2 cycles vs #597's 4+ futile cycles
- AC4 ✅ r-project-standards Type row updated with `type:user-action` + pipeline-behavior note referencing r-pipeline-protocol §5

### Test Results
Non-implementation task (type:docs) — no tests applicable.

### Lint
No Python files changed — no ruff run required.

### Notes
Retry: previous attempt treated as pure non-impl pass-through without writing documentation. This attempt performs the actual documentation work as the AC specifies.

[[2026-04-06]] Mon 22:31
## Review Evidence

### Type:docs Review
Non-implementation task (type:docs) — no tests, no lint applicable.

### AC Compliance Table

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: r-pipeline-protocol §5 `### User-Action Tasks` subsection (tag purpose, heuristics, blocking flow, post-completion flow) | share/skills/r-pipeline-protocol/SKILL.md §5: purpose statement ✓; 4-row heuristics table ✓; 7-step blocking flow ✓; post-completion fast-path ✓; dual-nature guidance ✓ | PASS |
| AC2: agent-common detection responsibility table | share/instructions/agent-common.instructions.md: `## User-Action Detection Responsibilities` 5-row table (researcher/architect/orchestrator/test-writer+builder+reviewer/auditor), Responsibility + Action columns ✓ | PASS |
| AC3: Dry-run scenario showing #597-style loop prevented | share/skills/r-pipeline-protocol/SKILL.md §5: 8-step walkthrough, result note "2 architect cycles vs #597's 4+ futile cycles" ✓ | PASS |
| AC4: r-project-standards tags section updated | share/skills/r-project-standards/SKILL.md §5 L83-84: Type row expanded with `type:user-action`, behavioral note row with r-pipeline-protocol §5 cross-reference ✓ | PASS |

### Structural Verification
- Subsection placement: between `### Decision Tiers` and `### Handoff` — matches research insertion points
- Cross-references consistent across all three files
- agent-common table appended after existing Per-Agent Section Mapping table as specified

### Deductions
0

### Verdict
confidence: .97 → PASS #663 -> docs

[[2026-04-06]] Mon 23:03
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A (already in target files) | New `type:user-action` convention documented in 3 skill/instruction files by builder. `.github/copilot-instructions.md` covers only project identity and repo branches — no pipeline/tag content to update. |
| 2 | Module docstrings | No | N/A | No Python files modified. |
| 3 | External attribution | No | N/A | Research notes confirm all sources internal (parent #661 research + target files). |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/document-type-user-action-convention.md` exists; linked in task body under `## Research`. |

### Content Verification
- `r-pipeline-protocol/SKILL.md` §5: `### User-Action Tasks` subsection present between `### Decision Tiers` and `### Handoff` — tag purpose ✓, 4-row detection heuristics table ✓, 7-step blocking flow ✓, post-completion fast-path ✓, dual-nature guidance ✓, 8-step dry-run scenario (#597 reference) ✓
- `agent-common.instructions.md`: `## User-Action Detection Responsibilities` present with 5-row table (researcher/architect/orchestrator/test-writer+builder+reviewer/auditor), cross-reference to r-pipeline-protocol §5 ✓
- `r-project-standards/SKILL.md` L83–84: Type row expanded with `type:user-action`; behavioral note row with r-pipeline-protocol §5 cross-reference ✓

### Files Updated
- None — builder committed all documentation changes; no gaps found.

### Scratch Files Cleaned
- None — no `.owlbear/scratch/663-*` files found.

[[2026-04-06]] Mon 23:18
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: r-pipeline-protocol S5 User-Action Tasks subsection | SKILL.md L203-244: tag purpose, 4-row heuristics table, 7-step blocking flow, post-completion fast-path, dual-nature guidance | PASS |
| AC2: agent-common detection responsibility table | agent-common.instructions.md L24-36: 5-row table (researcher/architect/orchestrator/test-writer+builder+reviewer/auditor) | PASS |
| AC3: Dry-run scenario showing #597-style loop prevented | SKILL.md L235-244: 8-step walkthrough, result "2 architect cycles vs #597's 4+ futile cycles" | PASS |
| AC4: r-project-standards tags section updated | SKILL.md L83-84: Type row expanded with type:user-action + behavioral note with r-pipeline-protocol S5 cross-reference | PASS |

### Test Results
- pytest: 3201 passed, 420 failed (all pre-existing, unrelated to #663), 18 skipped. No cross-task regressions from this task.
- ruff: N/A (no Python files changed)

### Architect Quality: 4/5
AC lines are specific and verifiable. AC3 placement not explicit in AC text but clarified in research insertion points (minor gap, not blocking).

### Deduction Breakdown
- AC lines with no evidence: 0 (deduction: 0)
- Lint violations: 0 (deduction: 0)
- AC quality score 4/5: no deduction
- Reviewer evidence section: present, detailed, PASS at .97 (deduction: 0)
- Full-suite failures in task scope: 0 (deduction: 0)
- Builder deliverables uncommitted: -.02

### Confidence: .98
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 7e27723 | docs | r-pipeline-protocol/SKILL.md, agent-common.instructions.md, r-project-standards/SKILL.md | #663 |
