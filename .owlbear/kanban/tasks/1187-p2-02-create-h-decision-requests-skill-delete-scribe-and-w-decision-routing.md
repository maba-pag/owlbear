---
id: 1187
title: 'P2-02: Create h-decision-requests skill + delete scribe and w-decision-routing'
status: todo
priority: needed
created: 2026-04-30T00:52:00.447027+00:00
updated: 2026-04-30T03:00:12.564560+00:00
tags:
- phase-2
- scope:agents
- type:impl
- agent
parent: 1179
depends_on:
- 1186
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- `share/skills/h-decision-requests/SKILL.md` created (~50 lines) documenting: when to create DR, how (create_dr tool params), body format, fire-and-forget semantics (td:0)
- `share/agents/scribe.agent.md` deleted (td:0)
- `share/skills/w-decision-routing/SKILL.md` deleted (td:0)
- New skill has valid frontmatter (name: h-decision-requests, description, user-invocable: false) (td:0)
- All tests from #1186 pass (deletion and existence checks) (td:0)

## Scope

- IN: new skill creation + two file deletions
- OUT: reference updates in other files (handled by #1188)

Brief: see parent #1179

[[2026-04-30]]
## Research
- Research doc: none (trivial — file expansion per existing brief spec)
- Sources: 2 studied (brief `draft-dr-script-replacement/brief.md`, `serve/kanban/src/owlbear_kanban/decisions.py`), 2 high-relevance
- Recommendation: expand current 18-line SKILL.md to ~50 lines per brief Phase 2 spec (confidence: 0.95)
- Follow-up tasks created: none (this task IS the implementation)
- Decision requests: none

## Findings
- All #1186 tests already pass (9/9 green)
- `scribe.agent.md` and `w-decision-routing/SKILL.md` already deleted
- Current `h-decision-requests/SKILL.md` exists with valid frontmatter but only 18 lines — AC requires ~50 lines documenting: when to create DR, create_dr params (task_id, agent, request_type in {decision|action}, body), body format (context + options + question), fire-and-forget semantics (auto-block, no follow-up, resolved on next pick_tasks)
- Implementation source: brief Phase 2 spec + decisions.py create_dr signature

## Challenge Results
- Challenger: SKIPPED — trivial markdown expansion with clear spec, no design decisions

## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One deliverable: expand skill content |
| Interface clarity | PASS | Brief specifies exactly what to document (when, params, format, semantics) |
| Dependency correctness | PASS | #1186 archived (done) |
| Module layering | PASS | N/A — markdown skill file only |
| TDD compliance | PASS | #1186 suite covers structural assertions |
| KISS/YAGNI | PASS | Minimal scope, brief-specified content |
| Premise challenge | PASS | Brief Phase 2 requires this step |
| Pattern consistency | PASS | Follows existing h-* skill handbook pattern |
| Security surface | PASS | No system boundaries |
| Single domain | PASS | scope:agents (agent skill docs) |

### Challenge Results
- Challenger: SKIPPED — all td:0, no design decisions

### Test Depth
- Max depth: 0
- Test-writer: SKIP

### Verdict: APPROVE
### Action Taken: Added `agent` pass-through tag, annotated all AC lines td:0. Advancing to todo.
[[2026-04-30]]
Architecture review complete. All AC lines td:0 (structural tests exist in #1186 suite, content expansion is documentation). Added `agent` pass-through tag. Test-writer: SKIP.