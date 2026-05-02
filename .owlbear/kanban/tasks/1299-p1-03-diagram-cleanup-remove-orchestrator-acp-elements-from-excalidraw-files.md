---
id: 1299
title: 'P1-03: Diagram cleanup — remove orchestrator/ACP elements from excalidraw
  files'
status: todo
priority: important
created: 2026-05-02T19:40:07.803534+00:00
updated: 2026-05-02T19:40:47.966725+00:00
tags:
- cleanup
parent: 1296
depends_on:
- 1297
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective

Remove orchestrator/ACP visual elements from excalidraw diagrams with proper binding cleanup. Preserve the orchestrator-as-auxiliary concept in the pipeline diagram (it still applies to the live VS Code orchestrator agent).

Brief: see parent #1296 and `.owlbear/briefs/draft-dead-code-sweep/brief.md`

## Scope

### Edit
- `share/diagrams/mcp-topology.excalidraw` — remove `s1_orchestrator_rect`, `s1_orchestrator_text`, `s1_acp_arrow`, `s1_acp_label`; clean up `boundElements` arrays and `startBinding`/`endBinding` fields on surviving elements that referenced deleted IDs
- `share/diagrams/pipeline.excalidraw` — remove Copilot CLI / ACP text references (simpler, text-only)
- `share/diagrams/project-overview.excalidraw` — remove Copilot CLI / ACP text references (simpler, text-only)
- `tests/test_pipeline_diagram.py` — reframe the orchestrator auxiliary assertion: the concept is still valid for the live VS Code orchestrator, so update the assertion to verify the diagram shows the orchestrator in its supervisory role (don't delete the test)

### Out of scope
- Any non-diagram code edits
- Removing references to the live VS Code orchestrator agent

## AC

1. `python -m json.tool share/diagrams/mcp-topology.excalidraw` succeeds (valid JSON)
2. `python -m json.tool share/diagrams/pipeline.excalidraw` succeeds (valid JSON)
3. `python -m json.tool share/diagrams/project-overview.excalidraw` succeeds (valid JSON)
4. No element in `mcp-topology.excalidraw` references deleted IDs in `boundElements`, `startBinding`, or `endBinding`
5. `grep -l "acp\|agent-client-protocol" share/diagrams/` returns zero hits
6. `uv run pytest tests/test_pipeline_diagram.py` passes
7. The pipeline diagram still visually represents the orchestrator in a supervisory/auxiliary role (test assertion confirms)
8. `grep "Copilot CLI" share/diagrams/` returns zero hits