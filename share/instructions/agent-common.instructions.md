---
description: "Common kanban and Channel B conventions for all pipeline agents"
applyTo: "share/agents/**"
---

## Channel B

Append your agent section to the task body via the `note` parameter of `end_work`. Include your section header, findings, and summary — all in one call. For tool reference, see `h-mcp-kanban` skill — section `## Agent Lifecycle Pattern`.

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
| test-curator | DONE | ## Curation |

## User-Action Detection Responsibilities

All agents should recognise — but only some must act on — `type:user-action` tasks:

| Agent | Responsibility | Action |
|-------|---------------|--------|
| researcher | Provisional detection | Tag `type:user-action` if AC meets any detection heuristic |
| architect | **Mandatory gate** | Confirm/remove tag; create AR via scribe; block task |
| orchestrator | Mechanical enforcement | `pick_tasks --not-blocked` already excludes blocked tasks |
| test-writer / builder / reviewer | Pass-through | `NON_IMPL_TAGS` exempts from TDD gate; process normally after unblock |
| auditor | Convention verification | Confirm AR was created, block was issued, `## Action Completed` appears in task body |

See r-pipeline-protocol §5 — User-Action Tasks for the full blocking flow, fast-path, and dry-run scenario.

## Diagram Rendering Paths

Three rendering paths are available in OwlBear chat — choose based on what the user needs:

| Path | When to use | How to invoke |
|------|-------------|---------------|
| Mermaid code block | Quick flowcharts, sequence diagrams, ERDs in chat | Wrap diagram source in ` ```mermaid ` fence; requires `mermaid-chat.enabled: true` (set in seed template) |
| HTML + Mermaid CDN | Rich styled output — tables, diagrams, colour, layout | Load `h-visual-output` skill; render via `<div>` with inline `<script src="mermaid CDN">` |
| Excalidraw JSON | Editable whiteboard-style diagrams | Load `h-excalidraw-diagram` skill; produce valid Excalidraw JSON for VS Code Excalidraw extension |
