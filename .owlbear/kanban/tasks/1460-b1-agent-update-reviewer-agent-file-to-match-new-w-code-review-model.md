---
id: 1460
title: 'B1-agent: Update reviewer agent file to match new w-code-review model'
status: todo
priority: needed
created: 2026-05-08T19:47:16.726901+00:00
updated: 2026-05-09T07:00:15.311401+00:00
tags:
- pipeline
- ws-reviewer
- scope:agents
- agent
parent: 1403
depends_on:
- 1458
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Update `share/agents/reviewer.agent.md` to align with rewritten w-code-review skill. Changes: remove quality-runner from default dispatch (read from task body instead), update persona to remove "run tests yourself" language, update critical_rules to remove "Never trust builder self-reports", remove TestFromAC enforcement from boundaries, update examples to new output format (Review Evidence + Observations).


## Acceptance Criteria

- [ ] `critical_rules`: Replace "Delegate test and lint execution to the `quality-runner` subagent. Assess the report, not the commands. Never trust builder self-reports." with: review builder-provided evidence first; dispatch quality-runner only when evidence is missing, contradictory, or insufficient (td:0)
- [ ] Remove all confidence-threshold references (`critical_rules` "≥ .90 = PASS", `pipeline_position` "confidence ≥ .90"); new model uses binary PASS/FAIL without numeric confidence (td:0)
- [ ] `boundaries`: Remove TestFromAC immutability rule ("Any `TestFromAC_*` modification...") and replace rationalization row "Run tests yourself. Builder self-reports are claims, not evidence." with new-model-aligned response (review evidence quality; escalate when insufficient) (td:0)
- [ ] `agents` table: Update quality-runner description from default dispatch ("Implementation reviews requiring test/lint/coverage evidence") to conditional dispatch (when builder evidence is insufficient or needs independent verification) (td:0)
- [ ] `output_format` Channel B: Update to reference new output structure — `## Review Evidence` (verdict + blocking findings table) + `## Observations` (non-blocking notes) (td:0)
- [ ] `examples`: Rewrite to new output format. Remove TestFromAC audits, deductions, confidence scores. Maintain evidence-based rigor in examples. (td:0)
- [ ] No contradictions remain between `reviewer.agent.md` and rewritten `w-code-review` skill after all changes (td:0)

### Architecture Notes

- **Persona unchanged.** Task body referenced "remove 'run tests yourself' language" from persona, but that text is in `boundaries` (rationalization table) and `critical_rules`, not `persona`. The FDA inspector metaphor is compatible with the new model. AC line 3 covers the actual text.
- **`agents:` frontmatter unchanged.** quality-runner stays in the list — still used for conditional dispatch. code-reader and planner also stay.
- **pipeline_position routing unchanged** except PASS condition (confidence removal). The "loop-breaker → batch-review-cycle" terminology update is handled by sibling task #1462.
- Reference: new `w-code-review` output template is `## Review Evidence` (verdict, PASS confirmation line, blocking findings table) + `## Observations` (non-blocking notes).

[[2026-05-09]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One file (`reviewer.agent.md`), one purpose (align with rewritten skill) |
| Interface clarity | PASS | AC refined into 7 verifiable lines with exact text/section targets |
| Dependency correctness | PASS | #1458 (w-code-review rewrite) is archived/done |
| Module layering | N/A | Agent markdown file, no code modules |
| TDD compliance | PASS | All td:0, `agent` pass-through tag added |
| KISS/YAGNI | PASS | Minimal scope — alignment changes only, no new features |
| Premise challenge | PASS | Skill was rewritten (#1458); agent file must match |
| Pattern consistency | PASS | Follows agent file structure conventions |
| Security surface | N/A | No system boundaries affected |
| Single domain | PASS | Agent configuration only |

### AC Refinement Notes

- Original body listed 5 prose changes; refined to 7 verifiable AC lines
- Added 3 missing consistency items: confidence threshold removal, output_format Channel B update, agents table update
- Corrected persona reference: "run tests yourself" language is in `boundaries`, not `persona`; persona needs no changes
- Scoped out loop-breaker→batch-review-cycle terminology (sibling #1462)

### Challenge Results
- Challenger: SKIPPED — all AC lines are td:0

### Test Depth
- Max depth: 0
- Test-writer: SKIP (all td:0)

### Verdict: APPROVE
### Action Taken: Refined AC from prose to 7 verifiable checkboxes. Added `agent` pass-through tag. Advanced to todo.