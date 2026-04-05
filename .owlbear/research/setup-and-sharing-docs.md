# Setup & Sharing Documentation — Research

> **Owning task:** #169 — Document multi-project setup experience and sharing guide
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #169 requires writing `docs/setup-guide.md` and `docs/sharing-guide.md`. Key questions: what content structure works best, what gotchas should be documented beyond the AC, and what VS Code features should the troubleshooting section reference?

Additionally, tasks #171, #172, #174, #175 are duplicates of #169 with near-identical AC and should be cleaned up.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | VS Code Copilot customization overview | https://code.visualstudio.com/docs/copilot/copilot-customization | .95 |
| 2 | VS Code custom agents docs | https://code.visualstudio.com/docs/copilot/customization/custom-agents | .95 |
| 3 | VS Code MCP configuration reference | https://code.visualstudio.com/docs/copilot/reference/mcp-configuration | .90 |
| 4 | OwlBear setup.py implementation | `scripts/setup.py` | 1.0 |
| 5 | Prior research: multi-project-setup-test.md | `docs/research/multi-project-setup-test.md` | 1.0 |
| 6 | Claude Code README & setup pattern | https://github.com/anthropics/claude-code | .70 |
| 7 | OwlBear README.md | `README.md` | .85 |
| 8 | kanban/setup.ps1 (kanban-md download) | `kanban/setup.ps1` | .90 |

## 3. Analysis

### 3.1 AC Completeness Assessment

The AC in #169 is solid. **Gaps to add:**

| Gap | Why it matters | Source |
|-----|---------------|--------|
| `uv` must be on PATH for MCP servers | MCP servers use `uv run --project` — fails silently if uv missing | S4 |
| `mcp.json` skip-if-exists behavior | Unlike settings.json (merge), mcp.json is not updated if it exists | S4 |
| VS Code "Show Agent Debug Logs" menu | Second troubleshooting tool beyond Diagnostics view | S1 |
| `MCP: List Servers` command | Shows running/failed MCP servers in Command Palette | S3 |
| `chat.useCustomizationsInParentRepositories` | Relevant for monorepo users, alternative to sibling-dir model | S1 |
| Organization-level agent sharing | VS Code org agent discovery as future sharing option | S2 |
| Agent name collision convention | Same-name agents from different locations both appear — use unique names | S5 |
| `kanban/setup.ps1` is Windows-only | PowerShell script; macOS/Linux users need manual kanban-md download | S8 |

### 3.2 Recommended Doc Structures

**setup-guide.md** (~120 lines target):

1. **Prerequisites** — Python 3.12+, uv, VS Code + Copilot extension, Git
2. **Quick Start** — clone → `python ../owlbear/scripts/setup.py` → `kanban/setup.ps1` → `code .`
3. **What Setup Creates** — table of generated files/dirs and their purpose
4. **Verification Checklist** — agents in picker, skills auto-load, MCP tools work, Diagnostics view
5. **Troubleshooting** — MCP server fails, agents missing, instructions not loading, debug logs
6. **Customization** — adding project agents, overriding instructions, adding MCP servers
7. **Known Limitations** — cross-drive Windows, agent name collision, kanban-md Windows-only

**sharing-guide.md** (~60 lines target):

1. **Sharing Model** — owlbear is a shared installation; projects reference it via relative paths
2. **Setup for a Teammate** — clone owlbear, clone project, run setup.py, verify
3. **Organization-Level Sharing** — VS Code org agent discovery as alternative (S2)
4. **Troubleshooting** — path issues, different drive letters, uv not on PATH

### 3.3 Doc Quality Patterns (from Source Analysis)

| Pattern | Claude Code approach | OwlBear recommendation |
|---------|---------------------|----------------------|
| README length | Ultra-short, links to external docs site | Keep README short, detailed guides in docs/ |
| Prerequisites | Listed in README; detailed in setup docs | Mirror: list in README, expand in setup-guide |
| Troubleshooting | Separate page linked from setup | Inline in setup-guide.md (single file) |
| Verification | Not explicit — assumes it works | Explicit checklist with Diagnostics view reference |

### 3.4 Duplicate Task Inventory

| Task | Title | Status | Difference from #169 |
|------|-------|--------|---------------------|
| #171 | Document multi-project setup and sharing guide | ideation | Shorter AC (no details in parens) |
| #172 | Document multi-project setup and sharing guide | ideation | Presumed duplicate |
| #174 | Document multi-project setup and sharing guide | ideation | Presumed duplicate |
| #175 | Document multi-project setup and sharing guide | ideation | Claimed by researcher; same AC as #169 |

These were created by multiple overlapping `kanban-md create` executions from the #25 research task. #169 has the most detailed AC and should be the canonical task.

## 4. Recommendation (.90 confidence)

**Proceed with #169 as the canonical task.** The AC covers the required scope. The doc writer should incorporate the 8 gaps identified in §3.1 and follow the structures in §3.2. The duplicates (#171, #172, #174, #175) should be cleaned up before the task enters the pipeline.

Risk: The sharing-guide.md scope is thin — it's essentially "clone, setup, verify" plus the org-sharing mention. Consider whether it justifies a standalone file or should be a section within setup-guide.md. Since the AC specifies two files, the writer should follow the AC but keep sharing-guide.md concise (~60 lines).

## 5. Follow-up Tasks

Cleanup of duplicates:
```
kanban\kanban-md.exe create "Clean up duplicate setup-guide tasks (#171 #172 #174 #175)" --priority needed --status ideation --tags "phase-2,scope:build,type:build" --body "## Objective\nRemove duplicate tasks created by overlapping kanban-md create executions from #25 research.\n\n## Acceptance Criteria\n- [ ] Archive or delete tasks #171, #172, #174, #175 (duplicates of #169)\n- [ ] Verify #169 is the only remaining setup-guide docs task\n- [ ] Release any stale claims on duplicate tasks\nSee docs/research/setup-and-sharing-docs.md §3.4 for details."
```
