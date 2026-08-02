---
id: 528
title: Design curator workflow for memory-mcp
status: archived
priority: medium
created: 2026-04-01 16:11:51.042577+02:00
updated: 2026-04-03 10:22:07.083576+02:00
started: 2026-04-01 19:15:15.466078+02:00
completed: 2026-04-03 10:22:07.083576+02:00
tags:
- scope:agents
- phase-2
depends_on:
- 525
class: standard
archival_reason: completed
archival_refs: []
---

Update curator agent and curation-workflow skill for memory-mcp integration per docs/research/memory-mcp-server-design.md sec 3I. Depends on #525.

AC:
- [ ] Curator agent updated to use list_entries for reviewing pending entries
- [ ] Curator can call mark_for-deletion for noise entries
- [ ] Curator can call record_learning to cross-pollinate insights to broader scopes
- [ ] Curation report includes recommendations for user approval (promote to approved)
- [ ] CLI or admin tool for user to batch-approve curator recommendations

[[2026-04-01]] Wed 19:14
## Research
Doc: docs/research/curator-workflow-memory-mcp.md

Follow-up tasks: #529 #530 #531. All contingent on DR #387 approval.

[[2026-04-01]] Wed 19:14
## Challenge Results

[[2026-04-01]] Wed 19:14
Challenger: block, confidence .45. Researcher revised to .78. Adopted MCP-routed approval, source lineage, kept vscode/memory.

[[2026-04-03]] Fri 10:21
## Architecture Review
**Verdict:** Split (delete â€” follow-ups #529, #530, #531 already exist)
**DR Verification:** docs/decisions/resolved/387-memory-mcp-architecture.md approved: true

### AC Assessment
| AC Line | Assessment | Covered By |
|---------|------------|------------|
| Curator uses list_entries for pending entries | Precise | #530 AC line 3 |
| Curator calls mark_for-deletion for noise | Precise | #530 AC line 4 |
| Curator calls record_learning for cross-pollination | Precise | #530 AC line 5 |
| Report includes recommendations for user approval | Precise | #530 AC line 6 |
| CLI or admin tool for batch-approve | Precise | #531 (full task) |

### Architecture Notes
Task #528 was the research/design parent. The researcher properly decomposed it into 3 atomic tasks during the research phase:
- #529 (backlog): Add set_approval_state MCP tool â€” single MCP tool, mcp-memory domain
- #530 (ideation): Update curator agent and skill â€” agent config domain
- #531 (ideation): Build approve_memory CLI wrapper â€” scripts domain

All 5 AC lines of #528 are fully covered by the follow-ups. DR #387 is resolved (Option A approved). Dependency #525 is archived. #528 is redundant â€” deleting.

### Dependency Notes for Follow-Up Reviews
- #531 should add depends_on #529 (CLI wraps set_approval_state which #529 creates)
- #530 needs agent pass-through tag (updates .agent.md and SKILL.md files, no testable Python)

### Changes Made
- Verified DR #387 resolved, dep #525 archived
- Deleting #528 (decomposed into existing follow-ups)

### Challenge Results
- Challenger: SKIP (Split verdict)
