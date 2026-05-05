# Consumer Updates: save_memory / recall_memory Rollout

> **Owning task:** #1313 — P1-12: Consumer updates Phase 2-3
> **Date:** 2026-05-05 **Status:** Complete

## 1. Context and Question

Task #1313 requires rolling out `ob-memory/save_memory` and `ob-memory/recall_memory` to all pipeline agent tool arrays, removing `vscode/memory`, and updating the `r-pipeline-protocol` skill text to reference the new tool names. Dependencies #1312 (memory-curator done) and #1308 (recall_memory tool implemented) are complete.

Key questions: (a) exact agent scope, (b) tool entry format, (c) what "agent-common.instructions.md" means (file doesn't exist), (d) stale tool names in skill text.

## 2. Sources Studied

| # | Source | Path | Relevance |
|---|--------|------|-----------|
| S1 | MCP memory server tools.py | `serve/mcp-memory/src/owlbear_mcp_memory/tools.py` L275-320 | 1.0 |
| S2 | h-mcp-memory skill | `share/skills/h-mcp-memory/SKILL.md` | 1.0 |
| S3 | r-pipeline-protocol skill | `share/skills/r-pipeline-protocol/SKILL.md` L38-48, L250-268 | 1.0 |
| S4 | All 26 agent.md files | `share/agents/*.agent.md` (tools: arrays) | 1.0 |
| S5 | Brief decisions | `.owlbear/briefs/draft-memory-mcp-ux/decisions.md` D32,D37 | .90 |
| S6 | memory-curator agent (reference) | `share/agents/memory-curator.agent.md` | .85 |

## 3. Analysis

### 3A. Agent Scope — Who Gets Changed

| Agent | Current state | Action |
|-------|--------------|--------|
| researcher | `vscode/memory` | Replace with `ob-memory/save_memory, ob-memory/recall_memory` |
| architect | `vscode/memory` | Same |
| builder | `vscode/memory` | Same |
| reviewer | `vscode/memory` | Same |
| auditor | `vscode/memory` | Same |
| doc-writer | `vscode/memory` | Same |
| orchestrator | `vscode/memory` | Same |
| planner | `vscode/memory` | Same |
| test-writer | `vscode/memory` + `'ob-memory/*'` | Remove `vscode/memory`; narrow `'ob-memory/*'` → explicit pair |
| test-curator | `vscode/memory` + `'ob-memory/*'` | Same as test-writer |

**Pipeline subagents (challenger, code-reader, quality-runner):** Have `vscode/memory` but don't perform pre-flight or reflection. Remove `vscode/memory`, don't add ob-memory (minimal privilege — they're short-lived).

**Ideation agents (10 agents):** Have `vscode/memory`. Out of scope per AC ("In: all pipeline agent.md files"). These use vscode/memory for creative session notes, not institutional knowledge.

**Total: 13 file edits** (10 pipeline + 3 subagents).

### 3B. Tool Entry Format

AC specifies `ob-memory/save_memory` and `ob-memory/recall_memory` — individual tool names, not wildcard. Test-writer/test-curator's current `'ob-memory/*'` grants curator tools unnecessarily (violates minimal privilege). Narrow to explicit pair.

### 3C. "agent-common.instructions.md" — Stale AC Reference

No file named `agent-common.instructions.md` exists anywhere in the workspace. The Knowledge Pre-flight and Post-task Reflection sections in `r-pipeline-protocol/SKILL.md` serve this function. AC items 3 and 4 refer to the same file — just update `r-pipeline-protocol/SKILL.md`.

### 3D. Stale Tool Names in r-pipeline-protocol/SKILL.md

| Location | Current | Correct |
|----------|---------|---------|
| L44 (Knowledge Pre-flight) | `query_memory()` | `recall_memory(agent="{agent_name}")` |
| L254 (Post-task Reflection) | `store_learning` with `scope_agents=[<agent_name>]` | `save_memory` with `source_agent="{agent_name}"` |

`recall_memory` signature (S1): `agent` (required str), `categories` (optional), `limit` (optional, default 20). Returns body-only markdown.

`save_memory` signature (S2): `title`, `content`, `categories`, `confidence`, `source_agent` (all required).

### 3E. Risk Assessment

| Risk | Probability | Mitigation |
|------|------------|------------|
| Agent can't recall without MCP server running | Low — graceful degradation already documented in pre-flight | Keep "if call fails, proceed normally" |
| Over-privileged test-writer/test-curator | Already present — fix by narrowing from wildcard | Part of this task |
| Ideation agents stranded on vscode/memory | None — out of scope, separate follow-up if needed | Note for later |

## 4. Recommendation

**Confidence: .92** — Mechanical replacement with clear scope. No architecture decisions needed.

T1 Autonomous. Proceed directly to implementation.

Challenge: skipped — trivial mechanical rollout, no design alternatives to challenge.

## 5. Follow-up Tasks

1. **Implementation task:** Apply all 13 agent file edits + r-pipeline-protocol skill text updates (move to backlog, tag `phase-2,scope:agents,memory`)
