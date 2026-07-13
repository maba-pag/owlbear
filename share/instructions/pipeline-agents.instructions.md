---
description: "Channel B protocol and per-agent conventions for pipeline agents"
applyTo: "share/skills/r-pipeline-protocol/**"
---

## Channel B

Append your agent section to the task body via the `note` parameter of `end_work`. Include your section header, findings, and summary — all in one call. For tool reference, see `h-mcp-kanban` skill — section `## Agent Lifecycle Pattern`.

### end_work Memory Assessment

When `recall_memory` was called during the task, run `assess_memories` before `end_work` and include all recalled memory IDs.

For each recalled memory entry, categorize your experience:

- **Outstanding** — this entry's guidance was genuinely great for this task
- **Used but unremarkable** — I applied or referenced this entry's guidance and it was adequate
- **Didn't use** — I didn't apply or reference this entry's guidance
- **Factually wrong** — this entry contains incorrect information

"Apply or reference" includes: following guidance, avoiding a warned pitfall, or confirming your approach was correct.

## Per-Agent Section Mapping

| Agent | Verdict tokens | Body section |
|-------|---------------|--------------|
| shaper | user-facing human summary; route recorded in task state | ## Shape Notes |
| builder | DONE / REJECT / BLOCK | ## Builder Notes |
| verifier | PASS / REJECT / RESHAPE | ## Verify Notes |
| collector | ARCHIVED / REJECT | ## Collect Notes |
| memory-curator | DONE | ## Curation |

## User-Action Detection Responsibilities

All agents should recognise — but only some must act on — `type:user-action` tasks:

| Agent | Responsibility | Action |
|-------|---------------|--------|
| shaper | **Mandatory gate** | Confirm/remove tag; create AR via `create_request`; block task |
| orchestrator | Mechanical enforcement | `pick_tasks` excludes blocked tasks; `shape` remains prompt-driven through `/shape` |
| builder / verifier | Pass-through | Process normally after unblock when the action is complete |
| collector | Convention verification | Confirm AR was created, block was issued, and a `## Decision Request` summary with `response: approved` appears in task body for parent/EPIC closure |

See `h-decision-requests` for the request tool contracts.
