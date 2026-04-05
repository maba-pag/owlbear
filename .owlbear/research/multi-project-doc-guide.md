# Multi-Project Documentation Guide — Research

> **Owning task:** #172 — Document multi-project setup and sharing guide
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #172 requires writing two user-facing docs: `docs/setup-guide.md` (clone to working) and `docs/sharing-guide.md` (sharing with teammates). The prior research (#25, `docs/research/multi-project-setup-test.md`) validated the technical model. This research determines the optimal structure, content scope, and known gaps for both guides.

Key questions: What doc structure works best for setup guides? What troubleshooting scenarios exist? What VS Code features should the guides reference? Are there new VS Code capabilities since the #25 research?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | VS Code Copilot customization docs (Mar 2026) | <https://code.visualstudio.com/docs/copilot/copilot-customization> | .95 |
| 2 | VS Code custom agents docs (Mar 2026) | <https://code.visualstudio.com/docs/copilot/customization/custom-agents> | .95 |
| 3 | Aider installation guide | <https://aider.chat/docs/install.html> | .75 |
| 4 | Claude Code getting-started guide | <https://code.claude.com/docs/en/getting-started> | .70 |
| 5 | OwlBear setup.py implementation | `scripts/setup.py` | 1.0 |
| 6 | Prior research: multi-project-setup-test | `docs/research/multi-project-setup-test.md` | 1.0 |
| 7 | OwlBear README.md | `README.md` | .90 |

## 3. Analysis

### 3.1 Doc Structure — Prior Art Comparison

| Element | Aider (Source 3) | Claude Code (Source 4) | Recommended for OwlBear |
|---------|------------------|----------------------|------------------------|
| Prerequisites section | Yes (Python version) | Yes (OS, RAM, network) | Yes — Python 3.12+, uv, VS Code + Copilot |
| Quick start (< 5 steps) | Yes (3 commands) | Yes (install, verify, auth) | Yes — clone, setup.py, open VS Code |
| Verification step | No explicit | Yes (`claude --version`, `claude doctor`) | Yes — Diagnostics view |
| Troubleshooting section | Separate page linked | Separate page linked | Inline (small scope) |
| Platform-specific notes | Yes (Mac/Win/Linux) | Yes (Mac/Win/Linux/Alpine) | Windows-only (project scope) |

**Pattern:** Both Aider and Claude Code use a Prerequisites → Install → Verify → Next Steps flow. OwlBear should follow this.

### 3.2 New VS Code Features (Since #25 Research)

| Feature | Source | Impact on Docs |
|---------|--------|---------------|
| Organization-level agents | Source 2 | sharing-guide.md should mention as alternative to filesystem sharing |
| Parent repository discovery | Source 1 | setup-guide.md should document `chat.useCustomizationsInParentRepositories` for monorepo use |
| Chat Customizations editor | Source 1 | Both guides should reference for verification and debugging |
| Agent Debug Logs | Source 1 | Troubleshooting section should reference alongside Diagnostics view |

### 3.3 Known Troubleshooting Scenarios

| Scenario | Cause | Resolution | Source |
|----------|-------|------------|--------|
| Agents not appearing in picker | Incorrect `chat.agentFilesLocations` path | Check Diagnostics view; verify relative path | Source 6, §3.2 |
| MCP server fails to start | Stub server (`mcp-knowledge`, `mcp-project`) or missing `uv` | Non-blocking; verify with operational server first | Source 6, §3.4 |
| Cross-drive `ValueError` | `os.path.relpath` fails across Windows drives | Place owlbear and project on same drive | Source 6, §3.6 |
| Instructions not loading | `.instructions.md` path wrong or file missing `applyTo` | Check Diagnostics view for loaded instructions | Source 1, 2 |
| Agent name collision | Both owlbear and project define same agent name | Use unique names for project agents | Source 6, §3.3 |
| Skills not auto-loading | Skill YAML frontmatter missing or `description` too generic | Check Diagnostics view for loaded skills | Source 2 |

### 3.4 Recommended Doc Outlines

**setup-guide.md (~80 lines):**
1. Prerequisites (Python, uv, VS Code + Copilot, same-drive constraint)
2. Quick Start (clone owlbear, create project dir, run setup.py, run kanban setup.ps1, open VS Code)
3. Verify It Works (Diagnostics view checklist: agents, skills, instructions, MCP tools)
4. Project-Specific Customization (local agents, override instructions, add MCP servers)
5. Troubleshooting (table of common issues from §3.3)

**sharing-guide.md (~60 lines):**
1. Sharing Model (owlbear is a shared installation; each project gets its own workspace)
2. Share via Filesystem (team clones owlbear to sibling dir, runs setup.py)
3. Share via Organization Agents (VS Code org-level agents — alternative for agents only)
4. What's Shared vs. Project-Local (table: agents/skills/instructions shared; kanban/data local)
5. Cross-Drive Limitation (Windows note)

## 4. Recommendation (.90 confidence)

The docs task is straightforward — the technical model is validated (60 passing tests), the resolution mechanisms are documented by VS Code, and the prior research covered all edge cases. The writer agent can produce both guides using the outlines above and the troubleshooting table.

**Risk:** Minimal. The only gap is that Organization-level agents require a GitHub org with Copilot Business/Enterprise — it may not apply to solo developers. The sharing guide should present it as an "alternative for teams with GitHub org access."

## 5. Follow-up Tasks

Both tasks below implement the documentation AC from #172. Since #172 itself IS the documentation task, these are not needed as separate tasks — #172's AC is ready for the pipeline as-is. The research validates the approach and provides the outlines.

No additional follow-up tasks needed — #172's existing AC covers all deliverables.
