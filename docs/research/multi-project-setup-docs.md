# Multi-Project Setup Documentation — Content Research

> **Owning task:** #175 — Document multi-project setup and sharing guide
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #175 writes two user-facing docs (`docs/setup-guide.md`, `docs/sharing-guide.md`) for the multi-project "clone = install" model. This research validates the task scope, gap-checks the AC, and provides the content blueprint so the writer can proceed without additional research.

Key questions: Is the AC complete? What content should each section cover? Are there gaps or dependencies blocking accurate documentation?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | VS Code Copilot customization overview | <https://code.visualstudio.com/docs/copilot/copilot-customization> | .95 |
| 2 | VS Code custom agents docs | <https://code.visualstudio.com/docs/copilot/customization/custom-agents> | .90 |
| 3 | VS Code agent skills docs | <https://code.visualstudio.com/docs/copilot/customization/agent-skills> | .90 |
| 4 | VS Code MCP configuration reference | <https://code.visualstudio.com/docs/copilot/reference/mcp-configuration> | .90 |
| 5 | VS Code troubleshooting docs | <https://code.visualstudio.com/docs/copilot/troubleshooting> | .85 |
| 6 | Setup script implementation | `scripts/setup.py` | 1.0 |
| 7 | Setup script research | `docs/research/setup-script.md` | .95 |
| 8 | Multi-project setup test research | `docs/research/multi-project-setup-test.md` | 1.0 |
| 9 | OwlbearProjectFile model | `packages/mcp-project/src/owlbear_mcp_project/models.py` | .85 |
| 10 | Setup script unit tests (39 passing) | `tests/test_setup_script.py` | .90 |

## 3. Analysis

### 3.1 Setup.py Artifacts (from Source 6)

The setup script creates exactly 6 artifacts. All must be documented:

| Artifact | Function | Idempotency |
|----------|----------|-------------|
| `.vscode/settings.json` | Agent/skill/instruction locations pointing to owlbear | Merges (owlbear keys as defaults) |
| `.vscode/mcp.json` | 4 MCP server entries (github + 3 owlbear stdio) | Skips if exists |
| `kanban/config.yml` | Board config (reset `next_id` to 1) | Skips if exists |
| `kanban/setup.ps1` | kanban-md download script | Skips if exists |
| `kanban/tasks/` | Empty task directory | Creates if missing |
| `.github/copilot-instructions.md` | Project-level Copilot instructions | Skips if exists |
| `owlbear-project.json` | Project metadata (name, type, owlbear path) | Skips if exists |
| `data/knowledge/` | Knowledge directory | Creates if missing |

### 3.2 VS Code Debugging Tools (from Sources 1, 5)

The AC references "Diagnostics view." Current VS Code offers two relevant tools:

| Tool | How to access | What it shows |
|------|---------------|---------------|
| **Diagnostics** | Right-click Chat view, select "Diagnostics" | All loaded agents, skills, instructions with source locations and errors (Source 2) |
| **Agent Debug Log** | Chat view ellipsis (…) menu, "Show Agent Debug Logs" | Chronological event log: tool calls, LLM requests, token usage, prompt discovery (Source 5) |
| **Chat Debug View** | Chat view ellipsis (…) menu, "Show Chat Debug View" | Raw LLM request/response payloads (Source 5) |

Both Diagnostics and Agent Debug Log should be referenced — Diagnostics for verifying loaded customizations, Agent Debug Log for troubleshooting runtime issues.

### 3.3 Known Limitations and Troubleshooting Content

| Issue | Root cause | Resolution |
|-------|-----------|------------|
| Cross-drive paths (Windows) | `os.path.relpath` raises `ValueError` | Keep owlbear and project on same drive |
| MCP server fails to start | Stub servers (knowledge, project partial) | Non-blocking — VS Code starts servers independently. Use `MCP: List Servers` command |
| Agent name collision | VS Code loads from ALL configured locations, no dedup | Use unique names for project agents (Source 8 §3.3) |
| `uv` not found | `uv run --project` needs `uv` on PATH | Install uv globally per README |
| Skills not auto-loading | `chat.agentSkillsLocations` not set or paths wrong | Check settings.json, use Diagnostics view |
| Instructions ignored | `chat.instructionsFilesLocations` missing | Setup.py sets this; verify in settings.json |

### 3.4 AC Gap Analysis

| AC Item | Status | Gap? |
|---------|--------|------|
| Setup-guide step-by-step | ✅ Covered | No |
| Troubleshooting section | ✅ Covered | No |
| Project customization section | ✅ Covered | No |
| Sharing guide | ✅ Covered | No |
| Reference Diagnostics view | ✅ Covered | Minor: also reference Agent Debug Log panel |
| Cross-drive limitation | ✅ Covered | No |
| `owlbear-project.json` explained | ❌ Not in AC | **Minor gap:** setup.py creates this file but AC doesn't mention documenting it |

**Recommendation:** Add `owlbear-project.json` explanation to setup-guide naturally (it's part of the step-by-step). No AC amendment needed — just a writer note.

### 3.5 Dependency Check

| Dependency | Status | Blocks #175? |
|------------|--------|-------------|
| #12 (setup script) | Archived | No — code exists |
| #167 (manual validation) | Ideation | **No** — docs can be written from code/research. If validation reveals issues, update docs later |
| #18 (MCP server registry) | Unknown | No — mcp.json config is implemented in setup.py |

## 4. Recommendation (.90 confidence)

**Task #175 is ready to proceed.** The AC is well-scoped, all necessary content is available from existing code and research docs, and there are no blocking dependencies. The writer should reference Sources 6–8 for content, Sources 1–5 for VS Code mechanism verification, and §3.2–3.3 above for troubleshooting content.

**Suggested doc structure for writer:**

**setup-guide.md:** Prerequisites → Clone & Install → Run Setup → Open VS Code → Verify (agents, skills, instructions, MCP) → Troubleshoot (table from §3.3 + Diagnostics/Debug tools from §3.2) → Customize (local agents, instructions, MCP servers)

**sharing-guide.md:** Overview (clone=install model) → Prerequisites → Share with Teammate (clone owlbear, clone project, run setup.py, run kanban/setup.ps1, verify) → Team Conventions (agent naming, project-specific customization) → Constraints (same-drive requirement)

**One minor AC note:** Mention `owlbear-project.json` in the setup walkthrough — it's created by setup.py but not listed in AC.

## 5. Follow-up Tasks

No new tasks needed. #175 itself is the follow-up from #25's research. The AC is complete and actionable. The only related task (#167 manual validation) already exists and is independent.
