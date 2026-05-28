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
| researcher | DONE | ## Research |
| architect | APPROVED / REFINE / SPLIT / MERGE / REJECT / BLOCK | ## Architecture Review |
| test-writer | DONE | ## Test-Writer Notes |
| builder | DONE / REJECT | ## Builder Notes |
| reviewer | PASS / FAIL | ## Review Evidence |
| doc-writer | DONE / REJECTED | ## Docs Gate |
| auditor | ARCHIVED / REJECTED | ## Audit |
| planner | DONE | ## Planning |
| memory-curator | DONE | ## Curation |

## User-Action Detection Responsibilities

All agents should recognise — but only some must act on — `type:user-action` tasks:

| Agent | Responsibility | Action |
|-------|---------------|--------|
| researcher | Provisional detection | Tag `type:user-action` if AC meets any detection heuristic |
| architect | **Mandatory gate** | Confirm/remove tag; create AR via `create_dr`; block task |
| orchestrator | Mechanical enforcement | `pick_tasks` excludes blocked tasks |
| test-writer / builder / reviewer | Pass-through | `NON_IMPL_TAGS` exempts from TDD gate; process normally after unblock |
| auditor | Convention verification | Confirm AR was created, block was issued, and a `## Decision Request` summary with `response: approved` appears in task body |

See `w-arch-review` step 13 for detection heuristics (M/S/C rule) and `h-decision-requests` for the `create_dr` contract.
