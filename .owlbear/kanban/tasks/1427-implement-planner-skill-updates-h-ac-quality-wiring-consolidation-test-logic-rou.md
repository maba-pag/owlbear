---
id: 1427
title: Implement planner skill updates — h-ac-quality wiring, consolidation-test
  logic, routing enforcement
status: review
priority: needed
created: 2026-05-08T00:47:38.789879+00:00
updated: 2026-05-08T09:23:06.831808+00:00
tags:
- pipeline
- ws-ac-quality
- scope:agents
- agent
parent: 1405
depends_on:
- 1405
blocked: false
block_reason:
claimed_at: 2026-05-08T09:23:06.831808+00:00
archival_reason:
archival_refs: []
---

## Acceptance Criteria

P2: `w-task-decomposition/SKILL.md` Step 0 required_reading includes `h-ac-quality` — verified by field-presence check in the file
P2: `w-task-decomposition/SKILL.md` Durability Principles section references `h-ac-quality` as the authoritative expanded schema — verified by artifact inspection
P2: `w-task-decomposition/SKILL.md` contains a consolidation-test creation rule: when ≥2 implementation tasks exist under a common parent in decomposition mode, planner creates one task titled "consolidation test: {feature name}" with deps listing all sibling implementation task IDs — verified by artifact inspection of the new section
P2: `w-task-decomposition/SKILL.md` Step 6 explicitly prohibits creating tasks at `todo` status — verified by artifact inspection
P2: `planner.agent.md` `<required_reading>` section includes `h-ac-quality` — verified by field-presence check
P2: `planner.agent.md` `<critical_rules>` includes rule: "Never create tasks at `todo` — only architect moves `backlog→todo`" — verified by artifact inspection

## Scope

**In scope:** `share/skills/w-task-decomposition/SKILL.md` edits, `share/agents/planner.agent.md` edits
**Out of scope:** h-ac-quality content itself (A1, already done), architect/challenger updates (A3, separate task)

## Reference

Research doc: `.owlbear/research/planner-ac-quality-update.md`
Brief: see parent #1403 (`.owlbear/briefs/draft-pipeline-review-rethink/brief.md`)


## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | All changes scoped to planner skill/agent wiring |
| Interface clarity | PASS | AC specifies exact text patterns and verification methods |
| Dependency correctness | PASS | h-ac-quality skill exists; parent #1405 archived (prereq done) |
| Module layering | PASS | Agent and skill .md files only, no code dependencies |
| TDD compliance | N/A | Non-implementation (agent/skill files) |
| KISS/YAGNI | PASS | Minimal changes prescribed by brief |
| Premise challenge | PASS | Legitimate wiring — h-ac-quality, consolidation-test, and routing enforcement are brief deliverables |
| Pattern consistency | PASS | Follows existing skill required_reading and agent critical_rules patterns |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | All changes within agent/skill domain |

### Challenge Results
- Challenger: SKIPPED — all AC lines td:0
- Architect response: N/A

### Test Depth
- Max depth: 0
- Test-writer: SKIP (all td:0)

### Verdict: APPROVE
### Action Taken: Added `agent` pass-through tag. All AC lines annotated td:0. Advancing to todo.
[[2026-05-08]]
## Architecture Review

All 6 AC lines verified against workspace files — changes already present in both `share/skills/w-task-decomposition/SKILL.md` and `share/agents/planner.agent.md`. AC is precise, artifact-inspection scoped, single-domain (agent/skill files). All td:0. Added `agent` pass-through tag. Challenger skipped (all td:0).

Verdict: APPROVE
[[2026-05-08]]
## Test-Writer Notes
- All AC lines are (td:0) — test-writer skipped.
- Passing through to builder.
[[2026-05-08]]
## Builder Notes
- Implementation: no code changes required.
- Evidence: verified AC directly in `share/skills/w-task-decomposition/SKILL.md` and `share/agents/planner.agent.md`.
- AC checks confirmed:
  - `w-task-decomposition` Step 0 required_reading includes `h-ac-quality`.
  - `w-task-decomposition` Durability Principles references `h-ac-quality` as authoritative checklist.
  - `w-task-decomposition` includes consolidation-test rule for decomposition mode with >=2 implementation siblings under common parent, title pattern `consolidation test: {feature name}`, and deps on sibling implementation task IDs.
  - `w-task-decomposition` Step 6 explicitly prohibits creating tasks at `todo` status.
  - `planner.agent.md` `<required_reading>` includes `h-ac-quality`.
  - `planner.agent.md` `<critical_rules>` includes `Never create tasks at `todo` — only architect moves `backlog→todo`.`
- Tests: N/A (td:0 non-implementation pass-through from test-writer).
- Lint/Coverage: N/A (no source/test modifications).
- Approach: validated existing artifacts against AC and advanced without unnecessary edits.