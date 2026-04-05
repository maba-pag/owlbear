---
applyTo: "share/agents/**"
description: "Common kanban and Channel B conventions for all pipeline agents"
---

## Channel B

Append agent notes to the task body using `edit_task` (with `append_body` and `timestamp=True`). For tool reference, see `h-mcp-kanban` skill — section `## Agent Lifecycle Pattern`.

## Per-Agent Section Mapping

| Agent | Verdict tokens | Body section |
|-------|---------------|--------------|
| researcher | DONE | ## Research |
| architect | APPROVED / REFINE / SPLIT / REJECT | ## Architecture Review |
| test-writer | DONE | ## Test-Writer Notes |
| builder | DONE / REJECT | ## Builder Notes |
| reviewer | PASS / FAIL | ## Review Evidence |
| doc-writer | DONE / REJECTED | ## Docs Gate |
| auditor | ARCHIVED / REJECTED | ## Audit |
| planner | DONE | ## Planning |
| curator | DONE | ## Curation |
