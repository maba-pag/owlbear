---
id: 663
title: Document type:user-action convention in r-pipeline-protocol and agent-common
status: in-progress
priority: nice-to-have
created: 2026-04-06T16:39:07.7325145+02:00
updated: 2026-04-06T18:47:23.5772942+02:00
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
