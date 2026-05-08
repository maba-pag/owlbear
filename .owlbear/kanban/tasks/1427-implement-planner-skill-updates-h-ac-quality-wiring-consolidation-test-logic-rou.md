---
id: 1427
title: Implement planner skill updates — h-ac-quality wiring, consolidation-test
  logic, routing enforcement
status: backlog
priority: needed
created: 2026-05-08T00:47:38.789879+00:00
updated: 2026-05-08T00:47:54.032311+00:00
tags:
- pipeline
- ws-ac-quality
- scope:agents
parent: 1405
depends_on:
- 1405
blocked: false
block_reason:
claimed_at:
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