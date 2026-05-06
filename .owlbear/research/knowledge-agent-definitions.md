# Knowledge Agent Definitions + Prompts

> **Owning task:** #1333 — P3-17: Agent definitions + prompts (knowledge-ingestor + knowledge-enricher)
> **Date:** 2026-05-06 **Status:** Complete

## 1. Context and Question

Task #1333 requires creating two agent files and two prompt files for the knowledge engine's ingest and enrichment workflows. The question: do the planned artifacts fit within VS Code agent/prompt capabilities, and what patterns should the implementation follow?

## 2. Sources Studied

| Source | Relevance | What was taken |
|--------|-----------|----------------|
| `share/agents/` (26 existing agents) | 1.0 | Frontmatter structure, model array syntax, tool prefix patterns |
| `share/prompts/` (12 prompts) | 1.0 | `agent:` binding, `${input:}` syntax, body documentation |
| `.owlbear/briefs/draft-knowledge-activation/brief.md` §4.10 | 1.0 | Agent roles, tool assignments, enricher loop spec |
| `.owlbear/briefs/draft-knowledge-activation/decisions.md` D7, D8 | 1.0 | Worker pattern, model selection + fallback chain |
| `serve/mcp-knowledge/src/.../server.py` | 0.9 | Actual tool implementations, parameter signatures |
| `share/skills/h-agent-structure/SKILL.md` | 0.9 | Required sections, frontmatter rules, extraction markers |

## 3. Analysis

### Tool Availability

| Tool | Status | Ingestor | Enricher |
|------|--------|:--------:|:--------:|
| `search_knowledge` | ✅ implemented | ✓ | ✓ |
| `list_sources` | ✅ implemented | ✓ | |
| `get_stats` | ✅ partial (no enrichment progress yet) | ✓ | ✓ |
| `ingest_document` | ✅ implemented | ✓ | |
| `refresh_source` | ✅ implemented | ✓ | |
| `get_next_batch` | ✅ implemented | | ✓ |
| `store_enrichment` | ✅ implemented | | ✓ |
| `get_consolidation_candidates` | ❌ #1330 in research | | ✓ |

Agent definitions are declarative — referencing an unimplemented tool is safe. The enricher's Phase 2 loop won't work until #1330 completes, but Phase 1 works today.

### Model Selection (D8)

VS Code format: `model: [GPT-5.4 mini (copilot), GPT-5 mini (copilot), Claude Haiku 4.5 (copilot)]`

Ingestor needs judgment (content validation, user interaction) → heavier model: `[Claude Sonnet 4.6 (copilot), GPT-5.4 (copilot)]`

### Parallelism (D7)

VS Code has no built-in multi-instance dispatch from a prompt. User manually opens 1-6 chat sessions with the enricher agent. The prompt documents this option and `get_next_batch` coordinates atomically via `BEGIN IMMEDIATE` + lease claims.

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| `user-invocable: true` for both | Triggered by user prompts, not orchestrator |
| `disable-model-invocation: true` | L1 agents, not called as subagents by other pipeline agents |
| No `agents:` array needed | Neither agent delegates to subagents |
| `vscode/askQuestions` for ingestor | User validates browser content (D9 flow) |
| No hooks needed | No enforcement hooks required for these roles |

## 4. Recommendation (confidence: 0.90)

Proceed with implementation. Patterns are clear, dependencies met (modulo #1330 which doesn't block definition). Implementation is ~4 files, each following well-established templates.

Challenge: SKIPPED — T1 autonomous, config/documentation work, no architectural trade-offs to challenge.

## 5. Follow-up Tasks

None needed — this task IS the implementation task. Research validates feasibility; advance to backlog for builder execution.
