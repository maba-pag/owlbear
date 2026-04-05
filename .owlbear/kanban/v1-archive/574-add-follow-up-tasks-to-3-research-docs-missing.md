---
id: 574
title: Add follow-up tasks to 3 research docs missing them
status: archived
priority: someday
created: 2026-03-04T07:39:16.215824+01:00
updated: 2026-03-22T19:20:09.4329461+01:00
started: 2026-03-07T04:53:05.0766832+01:00
completed: 2026-03-22T19:20:09.4329461+01:00
tags:
    - audit
    - docs
    - research
blocked: true
block_reason: Superseded by current doc state; target docs already contain follow-up/no-action sections
class: standard
---

DOC-F-06: 78/83 research docs have Follow-up Tasks. Missing from: agent-quality-analysis.md, code-quality-audit.md, graph-expansion-benchmark-results.md. See docs/documentation-audit.md.

## AC

- [ ] agent-quality-analysis.md has Follow-up Tasks section (or explicit no-action-needed note)
- [ ] code-quality-audit.md has Follow-up Tasks section (or explicit no-action-needed note)
- [ ] graph-expansion-benchmark-results.md has Follow-up Tasks section (or explicit no-action-needed note)
- [ ] 83/83 research docs have follow-up section

[[2026-03-21]] Sat 06:18
## Architecture Review
**Verdict:** Block

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| agent-quality-analysis.md has Follow-up Tasks section (or explicit no-action-needed note) | Already satisfied: docs/agent-quality-analysis.md contains `## 9. Follow-up Tasks` at line 350. | Reject stale task; no builder work needed. |
| code-quality-audit.md has Follow-up Tasks section (or explicit no-action-needed note) | Already satisfied in substance: docs/code-quality-audit.md contains `## Follow-up Task Commands` at line 379, which is the concrete follow-up-command pattern used by audit docs. | Reject stale task; renaming the heading would be churn, not meaningful work. |
| graph-expansion-benchmark-results.md has Follow-up Tasks section (or explicit no-action-needed note) | Already satisfied: docs/graph-expansion-benchmark-results.md contains `## Follow-up Tasks` at line 47 with an explicit `No action needed` note at line 49. | Reject stale task; no builder work needed. |
| 83/83 research docs have follow-up section | Superseded by later reconciliation: docs/research/orphaned-research-triage.md records all three root docs as compliant (table rows at lines 30-32) and explicitly marks #574 stale at line 48. | Route out of backlog; current premise is invalid. |

### Architecture Notes
This is a single-domain documentation hygiene task, but it is no longer actionable. The current tree already contains the required follow-up or no-action content in all three target docs. Sending this to todo would create a no-op builder task and encourage unnecessary documentation churn.

TDD compliance is not applicable here because the task does not introduce or modify executable behavior. No failure-mode map is required because the task is documentation-only and adds no security or runtime surface.

### Changes Made
- Claimed task #574 as cove-willow
- Verified current file state in docs/agent-quality-analysis.md, docs/code-quality-audit.md, and docs/graph-expansion-benchmark-results.md
- Verified later reconciliation in docs/research/orphaned-research-triage.md
- Rejected backlog routing and returned task to ideation with a block note indicating the premise is stale

### Dependencies
- Verified: no task dependencies listed
- Verified: no preceding RED task required for this documentation-only verification task
