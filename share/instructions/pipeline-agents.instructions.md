---
description: "Channel B protocol and per-agent conventions for pipeline agents"
applyTo: "share/skills/r-pipeline-protocol/**"
---

## Channel B

Append your agent section to the task body via the `note` parameter of `end_work`. Include your section header, findings, and summary — all in one call. For tool reference, see `h-mcp-kanban` skill — section `## Agent Lifecycle Pattern`.

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

See r-pipeline-protocol §5 — User-Action Tasks for the full blocking flow, fast-path, and dry-run scenario.
