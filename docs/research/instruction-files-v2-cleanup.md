# Instruction Files v2 Cleanup — Section-by-Section Analysis

> **Owning task:** #27 — Clean up instruction files for v2
> **Date:** 2026-03-26 **Status:** Complete

## 1. Context and Question

Two instruction files need updating for v2: `copilot-instructions.md` and `agent-common.instructions.md`. The v2 architecture (per `docs/decisions/resolved/v2-architecture.md`) drops the daemon, PydanticAI, BearClaw name, approval gates, and 25+ custom toolsets — replacing them with on-demand Copilot CLI, ACP protocol, 3-4 MCP servers, and git-as-safety-net.

**Key constraint:** Many workflow patterns (TDD, kanban lifecycle, agent communication, commit discipline) carry over unchanged. The risk is over-deletion, not under-deletion.

## 2. Sources

| Source | URL | Relevance |
|--------|-----|-----------|
| v2 architecture decision | `docs/decisions/resolved/v2-architecture.md` | 1.0 |
| v2 repo memory | `/memories/repo/v2-architecture-decisions.md` | 1.0 |
| Task #7 (monorepo skeleton AC) | `kanban/tasks/007-create-monorepo-skeleton.md` | .90 |
| Task #10 (port instruction files) | `kanban/tasks/010-port-instruction-files.md` | .85 |
| Task #8 (port agents AC) | `kanban/tasks/008-port-agents-to-agent-md-format.md` | .80 |

## 3. Analysis — copilot-instructions.md

### Section disposition matrix

| Section | Lines | Verdict | Rationale |
|---------|-------|---------|-----------|
| Project purpose | 3-5 | **UPDATE** | Remove "always-on daemon", "Slack/voice", "approval gates". Replace with on-demand Copilot CLI description |
| Core values | 9-16 | **KEEP** | Universal principles, unchanged |
| Coding discipline | 18-23 | **KEEP** | Universal, unchanged |
| Process habits | 25-33 | **KEEP** | TDD, kanban, verification — all carry over |
| Command Surface Selection | 35-42 | **UPDATE** | Path examples need updating (`.github/` to root dirs) |
| Formatting rules | 44-47 | **KEEP** | File format rules are universal |
| Tech stack table | 49-68 | **REWRITE** | ~80% of rows are v1-only. See §3.1 |
| kanban-md usage | 70-108 | **KEEP** | Board structure, priorities, lifecycle, tags — all unchanged |
| Directory structure | 110-123 | **UPDATE** | Replace with v2 layout (packages/, agents/, skills/, instructions/) |
| File placement rules | 125-140 | **UPDATE** | Add packages/ paths, remove src/bearclaw references |
| Confidence scores | 142-143 | **KEEP** | Universal convention |
| Attribution | 145-155 | **KEEP** | Universal convention |

### 3.1 Tech stack table — rewrite spec

Current table has 18 rows. Disposition per row:

| Row | Verdict | v2 replacement |
|-----|---------|----------------|
| Language (Python 3.12+) | **KEEP** | Unchanged |
| Runtime (Standalone daemon) | **REMOVE** | Replace: "On-demand via Copilot CLI" — one line, no 500-word hook description |
| Agents (PydanticAI) | **REMOVE** | Replace: "VS Code / Copilot CLI agents" — .agent.md format, nested subagents |
| LLM provider (Copilot OAuth) | **UPDATE** | Simplify: "GitHub Copilot" — flat-rate, no custom OAuth flow |
| Retry (tenacity) | **REMOVE** | No custom retry layer in v2 |
| CLI (Typer/BearClaw) | **REMOVE** | Replace: "Copilot CLI + owlbear orchestrator" (Typer for orchestrator CLI only) |
| HTTP (httpx) | **REMOVE** | No direct HTTP calls in v2 core |
| Config (pydantic-settings) | **REMOVE** | No pydantic-settings daemon config; MCP servers may have simple config |
| Knowledge (SQLite+Qdrant) | **KEEP** | Extracted to packages/knowledge, exposed via MCP |
| Web search (ddgs) | **REMOVE** | Built-in Copilot web search, or deferred |
| Browser (Playwright) | **REMOVE** | Community MCP server or deferred |
| Messaging (Slack) | **REMOVE** | Not in v2 core |
| Safety (6-layer) | **REMOVE** | Replace: "Git as safety net; --allow-all-tools; audit log for self-improvement only" |
| Errors (OwlBearError) | **REMOVE** | No custom exception hierarchy needed for MCP servers |
| Projects (JSON store) | **UPDATE** | Replace: owlbear-project.json + mcp-project server |
| Diagrams (Kroki) | **KEEP** | Still useful for visual output |
| Self-improvement | **REMOVE** | Replaced by Copilot Memory + audit log |
| Voice (planned) | **REMOVE** | Separate addon, not core (decision #19) |
| Task board (kanban-md) | **UPDATE** | Keep kanban-md, but note MCP abstraction layer |

New rows to add:

| Row | Content |
|-----|---------|
| Orchestrator | ACP protocol; Python client spawns `copilot --acp --stdio`; NDJSON over stdin/stdout |
| MCP servers | 3-4 custom (kanban, knowledge, project); community servers for browser, GitHub |
| Distribution | Clone = install; `owlbear setup` configures project .vscode/ settings |

### 3.2 Directory structure — v2 layout

| Directory | Purpose |
|-----------|---------|
| `packages/orchestrator/` | ACP client, dispatch planner, CLI triggers |
| `packages/knowledge/` | Knowledge engine (graph + vector) |
| `packages/mcp-kanban/` | MCP server wrapping kanban-md |
| `packages/mcp-knowledge/` | MCP server wrapping knowledge engine |
| `packages/mcp-project/` | MCP server for project metadata |
| `agents/` | Agent definitions (.agent.md) |
| `skills/` | Agent skills (agentskills.io format) |
| `instructions/` | Instruction files (.instructions.md) |
| `docs/` | Research, sources, decisions, scratch |
| `kanban/` | Task board and binary |
| `v1/` | Archived v1 codebase (reference only) |

## 4. Analysis — agent-common.instructions.md

### Section disposition matrix

| Section | Lines | Verdict | Rationale |
|---------|-------|---------|-----------|
| Task discipline | 7-10 | **KEEP** | Universal |
| Task coordination | 12-29 | **KEEP** | Universal claiming/handoff protocol |
| Handoff / blocked | 31-38 | **KEEP** | Universal |
| Defer-to-user boundary | 40-55 | **KEEP** | Universal decision-making rules |
| Blocking convention | 57-65 | **KEEP** | Universal |
| Commit discipline | 67-96 | **KEEP** | Universal |
| Evidence over claims | 98-101 | **KEEP** | Universal |
| Skill authority | 103-106 | **KEEP** | Universal |
| Self-defense table | 108-122 | **KEEP** | Universal anti-degradation rules |
| Follow-up task quality | 124-137 | **KEEP** | Universal |
| Placeholder rejection | 139-143 | **KEEP** | Universal |
| Post-task reflection | 145-170 | **KEEP** | Universal |
| Common red flags | 172-179 | **KEEP** | Universal |
| Terminal discipline | 181-192 | **KEEP** | Universal PowerShell rules |
| Defense-in-depth table | 194-205 | **KEEP** | Universal pipeline model |
| Confidence thresholds | 207-214 | **KEEP** | Universal |
| Inter-agent comms | 216-295 | **KEEP** | Channel A/B protocol, tables, escaping — all universal |

### 4.1 Specific v1 references to remove/update

Only **4 surgical changes** needed in agent-common.instructions.md:

1. **Line ~6**: preamble references `.github/copilot-instructions.md` — update path if instructions move to root
2. **Line ~92**: "Who commits what" table references specific agents — these are the same agents, keep as-is
3. **Line ~188**: "pytest/ruff/coverage" reference — keep, still applies to MCP server packages
4. **No PydanticAI references exist** in this file — it's already framework-agnostic

**Conclusion:** agent-common.instructions.md needs almost no changes. It is already v2-compatible because it describes workflow patterns, not implementation details.

## 5. Recommendation (.90 confidence)

**Split into two implementation tasks:**

1. **copilot-instructions.md rewrite** (~70% of the work) — rewrite project purpose, tech stack, directory structure, file placement, command surface examples. Keep everything else.
2. **agent-common.instructions.md patch** (~10% of the work) — only update path references if instruction files move to root dirs.

**Risk:** Over-deletion. The task AC says "when in doubt, keep." The analysis confirms most of agent-common is already v2-compatible.

**Approach:** Do NOT rewrite from scratch. Make surgical edits to copilot-instructions.md sections flagged UPDATE/REWRITE/REMOVE above. For agent-common, it's nearly a no-op.

## 6. Follow-up Tasks

These are the builder tasks. Task #27 itself is research; execution lives in #10 (port instruction files) which already depends on #27.

Since #10 already exists and covers the porting work, the primary follow-up is to ensure #10's AC is refined with this analysis. No new tasks needed — #10 is the implementation task, and this research doc is its input.
