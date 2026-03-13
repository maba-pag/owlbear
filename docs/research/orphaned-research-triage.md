# Orphaned Research Task Triage

> **Owning task:** #766 — Triage orphaned research tasks — backfill follow-ups
> **Date:** 2026-03-13 **Status:** Complete

## 1. Context and Question

An audit found ~11 archived research tasks that produced docs but never executed `kanban-md create` commands to create follow-up implementation tasks. This triage reviews each, determines what's still relevant, and either creates follow-ups, justifies "no action needed," or files a decision request.

## 2. Review of Each Orphaned Task

| ID | Title | Research Doc | Follow-ups Status | Disposition |
|----|-------|-------------|-------------------|-------------|
| #16 | VS Code hooks format | (none — superseded) | Superseded by #38 HookRegistry | **No action** — task body says "Superseded by #38" |
| #22 | Agent patterns from external repos | agent-patterns.md | 13 follow-ups listed but never created | **Superseded** — all patterns now implemented (HookRegistry, channels, agent loop, etc.) |
| #127 | PydanticAI multi-agent patterns | agent-framework.md | 3 refinements + 3 new tasks listed | **Superseded** — AgentRegistry, AgentDefinition, delegation all implemented |
| #137 | MCP servers inventory | mcp-servers.md | 5 MCP follow-ups listed | **Partially superseded** — `mcp_registry.py` + `mcp_servers.py` exist; GitHub/Git/Fetch MCP server wiring not yet done |
| #141 | PydanticAI web UI / Logfire | agent-observability.md | 3 follow-ups listed | **Superseded** — `ObservabilityHook`, `EventStore`, `Agent.instrument_all()` all implemented |
| #246 | Moonshine streaming API | moonshine-streaming.md | AC edits for #241-#245 listed | **Superseded** — voice module (11 files) uses moonshine |
| #253 | Content hashing / delta re-ingest | content-hashing.md | 8 follow-ups listed | **Superseded** — `content_hash` column exists (24 hits), delta ingest implemented |
| #255 | Intra-document graph builder | intra-document-graph.md | 5 `kanban-md create` commands | **Superseded** — `IntraDocGraphBuilder` class exists, `enrichment.py` wired, provenance tracking done |
| #262 | Adopt existing pipeline vs build custom | knowledge-pipeline.md | 2 follow-ups + confirmation | **Partially superseded** — custom build confirmed + done; community detection not yet implemented |
| #263 | Bootstrap/assembly layer | bootstrap-assembly.md | 9 follow-ups listed | **Superseded** — `src/owlbear/bootstrap/` (15 files) exists, `bootstrap()` function implemented |
| #264 | Browser automation alternatives | browser-automation.md | 4 follow-ups listed | **Superseded** — "keep custom" decision implemented; browser module maintained |

### Root-Level Orphaned Docs (AC4)

| Doc | Has Follow-up Section? | Disposition |
|-----|----------------------|-------------|
| `docs/agent-quality-analysis.md` | No section, but §8 has implementation sequence (T1–T17) | **Superseded** — all tasks (instructions, skills, agent rewrites) have been implemented |
| `docs/code-quality-audit.md` | Yes — §"Follow-up Task Commands" | **Superseded** — audit findings became tasks in later board sweeps |
| `docs/graph-expansion-benchmark-results.md` | No | **No action** — benchmark output, not research. No follow-ups needed. |

## 3. Analysis: What Remains Actionable

Most follow-ups are fully superseded by subsequent implementation. Two gaps survive:

### Gap 1: Community detection (#262 follow-up)

The knowledge-pipeline.md recommended adding Leiden-algorithm community detection to the knowledge graph. No `community_detection` code or module exists in `src/`. This is a real enhancement opportunity.

### Gap 2: MCP server wiring (#137 follow-ups)

MCP infrastructure exists (`mcp_registry.py`, `mcp_servers.py`) but the specific GitHub/Git/Fetch server integrations from §5 of the research doc were never configured as concrete tasks. These remain potentially useful but the MCP module may already handle generic wiring — the specific server configs may just be user setup.

## 4. Recommendation (.90 confidence)

- **9 of 11 tasks: no action needed** — all follow-ups superseded by implementation
- **#262 gap (community detection): create 1 follow-up** at ideation
- **#137 gap (MCP server configs): no action** — the MCP infrastructure is generic enough; specific server configuration is user setup, not code changes
- **Root docs: no action** — all findings were acted on through other task flows

## 5. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Add graph community detection (Leiden algorithm) to knowledge graph" --priority nice-to-have --status ideation --tags "knowledge-graph,agent,enrichment" --body "## Context\nResearch task #262 (knowledge-pipeline.md S4) recommended applying GraphRAG community detection to the entity graph. This was never created as a follow-up task.\n\n## Acceptance Criteria\n- [ ] Implement community detection on GraphStore entities using python-igraph or leidenalg\n- [ ] Generate per-community summaries via PydanticAI agent\n- [ ] Expose communities as retrieval context for RAG queries\n- [ ] Tests for detection + summary generation with mocked LLM\n\n## References\n- docs/research/knowledge-pipeline.md S4\n- GraphRAG paper (arxiv.org/abs/2404.16130)\n- Existing enrichment.py pattern for background graph jobs"
```
