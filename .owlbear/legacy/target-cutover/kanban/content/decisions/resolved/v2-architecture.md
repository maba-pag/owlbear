# Decision: OwlBear v2 Architecture

**Date:** 2026-03-26
**Status:** Resolved
**Participants:** User + Copilot planning session

## Context

OwlBear v1 is a PydanticAI-based always-on daemon with 25+ Python toolsets, 6-layer security model, and deep integration with a custom LLM provider. VS Code 1.113 and Copilot CLI 1.0.11 now provide native agent infrastructure (custom agents, MCP servers, agent skills, nested subagents) that replaces most of v1's custom code.

## Decision

Redesign OwlBear as an on-demand agentic dev chain on Copilot CLI, keeping v1 intact for reference.

## Key Decisions

1. **v2 lives in the same repo.** v1 code moved to `v1/` subfolder. Don't destroy v1.
2. **Everything is "owlbear."** Bearclaw name dropped.
3. **On-demand triggers, no daemon.** YAGNI.
4. **Copilot CLI is the LLM engine** (flat-rate, subagents free). Locked in, no fallbacks.
5. **ACP protocol** for orchestrator-to-CLI dispatch (spawn process, NDJSON over stdio).
6. **3-4 custom MCP servers** (kanban, knowledge, project). Built-in tools for the rest.
7. **MCP as abstraction over kanban-md** (future-proof for replacement).
8. **Three-layer knowledge:** Copilot Memory (agent learning), general KB (company/tech, shared), project KB (product/process, per-project).
9. **Clone = install.** Projects point to `../owlbear/` via VS Code settings, not copying.
10. **No approval gates.** `--allow-all-tools`. Git is the safety net. Audit log for self-improvement only.
11. **Monorepo** with `packages/` subfolder. `agents/` and `skills/` at repo root (markdown, no Python).
12. **Fresh kanban** at task #1. v1 tasks archived to `kanban/v1-archive/`.
13. **Use v1 VS Code agents** to build v2.
14. **Reuse** all v1 research docs, source attributions, decision records.
15. **Agent Skills** follow agentskills.io open standard.
16. **Custom agents** follow .agent.md format (VS Code + CLI + coding agent compatible).
17. **Nested subagents** assumed stable.
18. **v2 agents/skills/instructions** go to repo root dirs, NOT `.github/`. `.github/` stays active during transition.
19. **Voice** is a separate system (standalone addon, not integrated into core).
20. **No predefined cadence** — create tasks with correct dependency graph, let the pipeline decide.

## Alternatives Considered

- **Hybrid (PydanticAI + MCP):** Rejected — too complex, PydanticAI integration is deep and v2 should be simpler.
- **New git repo:** Rejected — same repo with v1 in subfolder keeps everything accessible.
- **Copy agents/skills to each project:** Rejected — central installation via settings is simpler and changes propagate automatically.
- **Always-on daemon:** Rejected — on-demand is sufficient, YAGNI.
- **Approval gates:** Rejected — git is the safety net, over-engineered for the use case.

## Consequences

- v1 code is preserved but not maintained
- 31 seed tasks created with dependency graph covering research, foundation, MCP servers, orchestrator, and integration
- v1 agents usable during v2 development via `.github/agents/`
- Total rewrite of orchestrator (~50 lines vs v1's ~1000 lines in daemon.py)
