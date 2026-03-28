# Build Setup Script (owlbear setup)

> **Owning task:** #12 — Build setup script (owlbear setup)
> **Date:** 2026-03-28 **Status:** Complete

## 1. Context and Question

Task #12 builds the "clone = install" entry point: a Python script run from any project directory that creates `.vscode/` configuration pointing to the owlbear installation. Key questions: implementation architecture, path resolution strategy, VS Code settings format, MCP config generation, idempotency approach, and kanban-md integration.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | v1 ProjectWorkspace | `v1/src/owlbear/projects/workspace.py` | .95 |
| 2 | VS Code Copilot customization docs | <https://code.visualstudio.com/docs/copilot/copilot-customization> | .90 |
| 3 | VS Code MCP config reference | <https://code.visualstudio.com/docs/copilot/reference/mcp-configuration> | .90 |
| 4 | Copier project scaffolder | <https://github.com/copier-org/copier> | .70 |
| 5 | Cookiecutter docs | <https://cookiecutter.readthedocs.io/en/stable/overview.html> | .65 |
| 6 | Python os.path.relpath docs | <https://docs.python.org/3/library/os.path.html#os.path.relpath> | .85 |
| 7 | npm init behavior | <https://docs.npmjs.com/cli/v10/commands/npm-init> | .75 |
| 8 | owlbear-project.json schema spec | `docs/research/owlbear-project-json-schema.md` | 1.0 |
| 9 | Current owlbear .vscode/settings.json | `.vscode/settings.json` (workspace) | .95 |
| 10 | Setup script JSON gen research | `docs/research/setup-script-project-json-generation.md` | .90 |

## 3. Analysis

### 3.1 Architecture: Single Script vs Modular Package

| Approach | Complexity | KISS | Deps | Testability |
|----------|-----------|------|------|-------------|
| **A: Single script with functions (.85)** | Low (~150 LOC) | **High** | stdlib only | Functions testable individually |
| B: Copier/cookiecutter template (.50) | Medium | Low | External dep | Harder to customize per-project |
| C: Package in packages/ (.60) | Medium | Medium | uv install | Over-engineered for one-time tool |

**Recommendation (.85):** Option A. v1's `workspace.py` is ~310 lines handling 4 templates (Source 1). Our setup is simpler — one function per artifact, stdlib-only. Copier (Source 4) and cookiecutter (Source 5) are template engines designed for repeated scaffolding; we need a one-time config writer.

### 3.2 Path Resolution

The script at `owlbear/scripts/setup.py` determines paths as:

- `owlbear_dir = Path(__file__).resolve().parent.parent`
- `project_dir = Path.cwd()`
- `rel_owlbear = PurePath(os.path.relpath(owlbear_dir, project_dir)).as_posix()`

Result: `"../owlbear"` (always forward slashes per Source 6, Source 10).

**Constraint:** `os.path.relpath` raises `ValueError` on Windows cross-drive paths. This is acceptable — same-drive layout is the expected case.

### 3.3 VS Code Settings Generation

From the current owlbear workspace (Source 9), the setup script should generate a `.vscode/settings.json` mapping agent, skill, and instruction locations to the owlbear installation:

```json
{
  "chat.agentFilesLocations": {
    "{rel}/agents": true,
    "{rel}/.github/agents": true
  },
  "chat.agentSkillsLocations": {
    "{rel}/skills": true,
    "{rel}/.github/skills": true
  },
  "chat.instructionsFilesLocations": {
    "{rel}/instructions": true,
    "{rel}/.github/instructions": true
  }
}
```

Where `{rel}` is the computed relative path (e.g., `../owlbear`). Uses dict-based format per VS Code settings schema (Source 2). The `chat.instructionsFilesLocations` setting is **missing from current AC** but required for consistency — all three location types should be set.

**Merge strategy:** If `.vscode/settings.json` already exists, the script should merge keys (not overwrite). This supports projects that already have VS Code settings.

### 3.4 MCP Server Config

The `.vscode/mcp.json` registers owlbear's three custom MCP servers. Per VS Code MCP reference (Source 3), servers use camelCase names and stdio type:

```json
{
  "servers": {
    "owlbearKanban": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--directory", "{rel}", "python", "-m", "mcp_kanban"]
    },
    "owlbearKnowledge": { "..." },
    "owlbearProject": { "..." }
  }
}
```

**Note:** Task #18 defines the MCP server registry content. The setup script generates the file with correct relative paths — content definition is #18's scope.

### 3.5 Idempotency Strategy

| Strategy | Behavior | KISS |
|----------|----------|------|
| **A: Per-file skip (.85)** | Check each file, skip if exists, report | **High** |
| B: All-or-nothing (.60) | Refuse if any file exists | Low (blocks partial re-runs) |

**Recommendation (.85):** Per-file skip with merge for settings.json. Matches `npm init -y` behavior (Source 7) and v1 pattern. Each artifact created independently — if kanban/ exists but .vscode/ doesn't, only create .vscode/.

### 3.6 kanban-md Integration

AC requires: copy `config.yml` template, ensure `kanban-md.exe` availability.

- Copy `kanban/config.yml` from owlbear to project's `kanban/config.yml` (strip `next_id` field, reset to clean state)
- Copy `kanban/setup.ps1` to project's `kanban/setup.ps1` (enables self-contained download)
- Create `kanban/tasks/` directory
- Print instruction: "Run `kanban\setup.ps1` to download kanban-md.exe"

### 3.7 Dependency Map

| Task | Status | Relationship |
|------|--------|-------------|
| #7 (monorepo skeleton) | **archived** | Direct dep — paths now known |
| #18 (MCP server registry) | ideation | Parallel — defines mcp.json content |
| #53 (project JSON schema) | **archived** | Schema defined |
| #68 (Pydantic model) | backlog | Dep for #69 |
| #69 (JSON generation) | backlog | Subtask of #12 |
| #75 (TDD for #69) | backlog | TDD for #69 |

## 4. Recommendation (.85 confidence)

Implement as a single `scripts/setup.py` script with stdlib-only dependencies. One function per artifact (settings, mcp, kanban, copilot-instructions, project JSON). Per-file idempotency with JSON merge for settings.json. Auto-detect owlbear path via `__file__` resolution.

**AC refinements for architect:**

1. **Add `chat.instructionsFilesLocations`** — AC lists agents and skills but omits instructions. All three should be set for consistency with current owlbear workspace config.
2. **Add merge behavior for settings.json** — "does not overwrite" should mean "merges keys" for settings.json specifically, since projects may have existing settings.
3. **Add `--name`/`--type` optional args** — needed by #69 for project JSON generation. Defaults: name from dirname, type `bare`.
4. **Cross-drive constraint** — document that owlbear and project must be on the same drive (Windows limitation of `os.path.relpath`).

**Risks:**

- MCP server entries reference module names (`mcp_kanban` etc.) that may not exist yet — setup script should generate the config regardless, servers fail gracefully when started.
- Settings merge could conflict with user's existing keys — but the owlbear-specific settings (`chat.agent*Locations`) are unlikely to pre-exist in a new project.

## 5. Follow-up Tasks

The parent task #12 itself advances to backlog. Subtasks #69, #75, #68 already exist. One new task needed:

1. **TDD RED: setup script core functions** — tests for settings generation, mcp generation, kanban copy, idempotency, path resolution. Excludes project JSON (covered by #75).

```powershell
kanban\kanban-md.exe create "Test: setup script core functions (settings, mcp, kanban, idempotency)" --priority needed --status ideation --tags "phase-1,scope:cli,type:test" --body "## Objective\nTDD RED phase: write failing tests for setup.py core functions before builder implements.\n\n## Test Scenarios\n- [ ] Creates .vscode/settings.json with correct agent/skill/instruction locations\n- [ ] Relative path uses forward slashes on all platforms\n- [ ] Creates .vscode/mcp.json with three owlbear MCP server entries\n- [ ] MCP server args reference correct relative owlbear path\n- [ ] Creates kanban/ with config.yml and tasks/ subdirectory\n- [ ] Copied config.yml has clean next_id (reset from owlbear source)\n- [ ] Creates data/knowledge/ directory\n- [ ] Creates .github/copilot-instructions.md with project name\n- [ ] Idempotent: does not overwrite existing .vscode/settings.json (merges)\n- [ ] Idempotent: does not overwrite existing kanban/config.yml\n- [ ] Path auto-detection from script location\n- [ ] Prints success message with next steps\n\n## Context\nParent task: #12. Excludes project JSON tests (covered by #75).\nSee docs/research/setup-script.md."
```
