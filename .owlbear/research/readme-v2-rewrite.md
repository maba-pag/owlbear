# README.md v2 Rewrite

> **Owning task:** #28 — Update README.md for v2
> **Date:** 2026-03-28 **Status:** Complete

## 1. Context and Question

The current README describes OwlBear v1: a standalone daemon with BearClaw CLI, PydanticAI agents, Slack integration, browser automation, and approval gates. v2 is an on-demand agentic dev chain on Copilot CLI with custom agents, MCP servers, and git as the safety net. The README must be rewritten to reflect v2 while staying concise (quick-start, not full docs).

**Key questions:**
1. What sections should the v2 README contain?
2. What structure best serves a quick-start audience?
3. What v1 content must be removed vs adapted?

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| Claude Code README | `github.com/anthropics/claude-code` | .85 | Concise structure: one-liner, get started, plugins, links |
| VS Code Custom Agents docs | `code.visualstudio.com/docs/copilot/customization/custom-agents` | .90 | `.agent.md` format, workspace discovery, prerequisites |
| VS Code MCP Servers docs | `code.visualstudio.com/docs/copilot/customization/mcp-servers` | .85 | MCP server config via `.vscode/mcp.json`, tool discovery |
| v2 Architecture Decision | `docs/decisions/resolved/v2-architecture.md` | 1.0 | 20 key decisions defining v2 scope |
| copilot-instructions.md | `.github/copilot-instructions.md` | 1.0 | v2 tech stack, directory layout, principles |
| Instruction cleanup research | `docs/research/instruction-files-v2-cleanup.md` | .80 | v1 removal checklist, v2 replacements |

## 3. Analysis

### 3.1 v1 Content Disposition

| Section | Lines | Verdict | Rationale |
|---------|-------|---------|-----------|
| Title + tagline | 1-3 | **UPDATE** | Drop "always-on"; use "on-demand" |
| Overview | 5-9 | **REWRITE** | Remove daemon, Slack, voice, approval gates |
| Prerequisites | 11-19 | **REWRITE** | Add VS Code + Copilot; drop browser automation |
| Quick Start | 21-26 | **REWRITE** | Replace bearclaw with git clone + VS Code |
| CLI — BearClaw | 28-66 | **REMOVE** | v2 has no custom CLI; Copilot CLI is the interface |
| Slack Integration | 68-117 | **REMOVE** | v2 has no Slack integration |
| Architecture | 119-131 | **REWRITE** | Replace daemon/PydanticAI with Copilot agents/MCP |
| Inspiration | 133-137 | **UPDATE** | Review for v2 relevance |
| Development | 139-151 | **UPDATE** | Commands are still valid (uv, pytest, ruff) |
| License | 153 | **KEEP** | Unchanged |

### 3.2 Recommended v2 README Structure

Based on Claude Code (minimal, get-started focused) and VS Code docs (agent/MCP setup patterns):

| Section | Content | Est. Lines |
|---------|---------|------------|
| **Title + tagline** | "On-demand AI development system built on GitHub Copilot" | 3 |
| **Overview** | 2-3 sentences: what it is, how it works, what it replaces | 5 |
| **Prerequisites** | Python 3.12+, uv, VS Code + Copilot extension, Copilot CLI | 6 |
| **Quick Start** | `git clone`, `uv sync`, open in VS Code, select agent | 10 |
| **Directory Layout** | Table of top-level dirs with purpose | 15 |
| **How It Works** | Agents, skills, MCP servers — 1 paragraph each | 12 |
| **Development** | uv sync, pytest, ruff commands | 8 |
| **License** | MIT | 2 |
| **Total** | | ~61 |

### 3.3 Key Content for Each Section

**Prerequisites** (from v2 architecture decision + VS Code docs):
- Python 3.12+ and uv (for MCP servers and scripts)
- VS Code with Copilot extension (agent host)
- GitHub Copilot subscription (Pro/Pro+, or Free tier)
- Copilot CLI (`code` command available from terminal)
- Windows primary; Linux/macOS untested

**Quick Start** (clone = install model per decision #9):
1. `git clone` the repo
2. `uv sync` to install Python deps
3. `kanban/setup.ps1` to download kanban-md
4. Open folder in VS Code — agents and MCP servers auto-discover

**Directory Layout** (from copilot-instructions.md):
- `agents/` — custom agent definitions (`.agent.md`)
- `skills/` — agent skills (`SKILL.md`, agentskills.io standard)
- `instructions/` — shared instruction files
- `packages/` — Python packages (MCP servers, orchestrator, knowledge)
- `kanban/` — task board data
- `docs/` — research, decisions, supporting docs
- `v1/` — archived v1 codebase

**How It Works** (from v2 architecture):
- Custom agents in `agents/` appear in VS Code's agent picker
- Agent skills in `skills/` auto-load by relevance
- MCP servers (kanban, knowledge, project) expose tools to agents
- Orchestrator dispatches work via ACP protocol over Copilot CLI
- Git is the safety net — no approval gates, no daemon

## 4. Recommendation (.90 confidence)

**Single follow-up task** to rewrite the README. The structure above is well-supported by v2 architecture decisions and VS Code documentation patterns. The target is ~60 lines — concise enough for quick-start, comprehensive enough to onboard.

**Risks:**
- Some MCP servers aren't built yet — README should describe the target state but note WIP status
- Setup for downstream projects (clone = install) may need a separate doc once the model stabilizes

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Rewrite README.md for v2 architecture" --status ideation --priority needed --tags "phase-1,scope:docs,type:docs" --body "Rewrite README.md per docs/research/readme-v2-rewrite.md. Use the recommended structure: title, overview, prerequisites, quick start, directory layout, how it works, development, license. Target ~60 lines.\n\nAC:\n- [ ] Title: 'On-demand AI development system built on GitHub Copilot'\n- [ ] Overview: 2-3 sentences, no v1 references\n- [ ] Prerequisites: Python 3.12+, uv, VS Code + Copilot, Copilot CLI\n- [ ] Quick Start: git clone, uv sync, kanban setup, open VS Code\n- [ ] Directory layout table matching copilot-instructions.md\n- [ ] How It Works: agents, skills, MCP servers, orchestrator\n- [ ] Development: uv sync, pytest, ruff (keep existing commands)\n- [ ] No v1 references: no daemon, bearclaw, PydanticAI, Slack, approval gates, browser automation, Qdrant\n- [ ] Total length under 80 lines\n- [ ] License section preserved" --depends-on 28
```
