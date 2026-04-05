# Monorepo Skeleton Implementation

> **Owning task:** #7 — Create monorepo skeleton
> **Date:** 2026-03-27 **Status:** Complete

## 1. Context and Question

Task #7 creates the v2 monorepo directory structure with uv workspace configuration.
The upstream research (#6, `docs/research/monorepo-tooling.md`) validated the workspace
pattern with practical evidence. This research verifies the remaining implementation
details: current repo state gaps, VS Code settings, pre-commit corrections, and module
naming.

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| uv workspace docs | <https://docs.astral.sh/uv/concepts/projects/workspaces/> | 1.0 |
| uv project init docs | <https://docs.astral.sh/uv/concepts/projects/init/> | .95 |
| VS Code Copilot settings ref | <https://code.visualstudio.com/docs/copilot/reference/copilot-settings> | .90 |
| VS Code customization docs | <https://code.visualstudio.com/docs/copilot/copilot-customization> | .85 |
| Task #6 research doc | `docs/research/monorepo-tooling.md` | 1.0 |
| pydantic-ai monorepo | <https://github.com/pydantic/pydantic-ai> | .85 |

## 3. Analysis

### 3.1 Gap Analysis — Current State vs. AC

| AC Item | Exists? | Notes |
|---------|---------|-------|
| Root pyproject.toml | No | Must create; v1/ has its own |
| packages/orchestrator/ | No | Create with src/owlbear/ module |
| packages/knowledge/ | No | Create with src/owlbear_knowledge/ module |
| packages/mcp-kanban/ | No | Create with src/owlbear_mcp_kanban/ module |
| packages/mcp-knowledge/ | No | Create with src/owlbear_mcp_knowledge/ module |
| packages/mcp-project/ | No | Create with src/owlbear_mcp_project/ module |
| agents/ (repo root) | No | .github/agents/ exists; add root agents/ |
| skills/ (repo root) | No | .github/skills/ exists; add root skills/ |
| instructions/ (repo root) | No | .github/instructions/ exists; add root instructions/ |
| kanban/ | Yes | Already exists |
| docs/ structure | Yes | research/, sources/, decisions/, scratch/ present |
| scripts/ with setup.py | No | Must create |
| data/knowledge/general/ | No | Must create |
| .gitignore v2 paths | Partial | Missing packages patterns, data/knowledge/ |
| .pre-commit-config.yaml | Needs update | bandit targets src/ (v1); needs packages/*/src/ |
| .vscode/settings.json agents | Needs update | No chat.agentFilesLocations set |
| .vscode/settings.json skills | Needs update | No chat.agentSkillsLocations set |

### 3.2 Module Naming Convention

Package names use hyphens; Python module names use underscores. Confirmed by uv
init docs (uv converts automatically) and pydantic-ai precedent.

| Package dir | Package name | Module path |
|-------------|-------------|-------------|
| packages/orchestrator/ | owlbear | src/owlbear/ |
| packages/knowledge/ | owlbear-knowledge | src/owlbear_knowledge/ |
| packages/mcp-kanban/ | owlbear-mcp-kanban | src/owlbear_mcp_kanban/ |
| packages/mcp-knowledge/ | owlbear-mcp-knowledge | src/owlbear_mcp_knowledge/ |
| packages/mcp-project/ | owlbear-mcp-project | src/owlbear_mcp_project/ |

Note: The orchestrator package uses `owlbear` as module name (it's the core package),
matching the v1 convention where `src/owlbear/` was the main module.

### 3.3 VS Code Settings — Verified Setting Names

The AC references `chat.agentFilesLocations` and `chat.agentSkillsLocations`. Both are
real VS Code settings confirmed in the official Copilot settings reference:

| Setting | Default | Needed value |
|---------|---------|-------------|
| `chat.agentFilesLocations` | `{ ".github/agents": true }` | `{ ".github/agents": true, "agents": true }` |
| `chat.agentSkillsLocations` | `{ ".github/skills": true, ... }` | Add `"skills": true` |
| `chat.instructionsFilesLocations` | `{ ".github/instructions": true, ... }` | Add `"instructions": true` |

The instructions location setting isn't in the AC but follows the same transition pattern
and should be updated for consistency.

### 3.4 Pre-commit Corrections

Current `.pre-commit-config.yaml` has bandit targeting `src/` (v1 layout). For v2:

```yaml
- id: bandit
  args: [-c, pyproject.toml, -r, packages/]
```

This points bandit at the packages directory root. The `-r` flag recurses into all
package src dirs. The ruff hooks need no change (they already scan all `.py` files).

### 3.5 Gitignore Additions

Current `.gitignore` needs these v2 entries:

```gitignore
# v2 package artifacts
packages/*/__pycache__/
packages/*/.pytest_cache/
packages/*/dist/

# Knowledge data
data/knowledge/*.db

# uv lock (generated)
# NOTE: uv.lock should be committed per uv docs for reproducible builds
```

The existing `__pycache__/` glob already covers nested dirs, but explicit package paths
make intent clear. `uv.lock` should be committed (not gitignored) per uv best practice
for applications.

### 3.6 Root agents/skills/instructions — Transition Strategy

During the transition period, customization files stay in `.github/` (current location)
while empty root directories are created as placeholders. The VS Code settings point to
both locations. This avoids breaking existing agent resolution while enabling future
migration.

## 4. Recommendation (.90 confidence)

Proceed with implementation as specified in the AC. The task is well-scoped, the
upstream research (#6) validated the uv workspace pattern, and all VS Code settings
are confirmed to exist. Two minor additions to the AC:

1. Also update `chat.instructionsFilesLocations` in settings.json (same transition
   pattern as agents/skills).
2. Commit `uv.lock` after `uv sync` succeeds — it's the reproducible build artifact.

**Risks:**
- `uv_build` backend is relatively new (v0.11.x) — if package build fails, per-package
  fallback to hatchling is trivial (identified in #6 research).
- Empty root agents/skills/instructions/ dirs during transition may confuse contributors
  expecting files there. Mitigate with README.md in each explaining the transition.

## 5. Follow-up Tasks

No new follow-up tasks needed. Task #7 already covers the full implementation scope
with detailed AC. The findings here feed directly into the builder's implementation.

The AC is comprehensive (19 items) and correctly scoped. No gaps were identified that
would require additional tasks.
