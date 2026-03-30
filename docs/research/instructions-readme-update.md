# Update instructions/README.md for v2

> **Owning task:** #109 — Update instructions/README.md for v2
> **Date:** 2026-03-28 **Status:** Complete

## 1. Context and Question

`instructions/README.md` still describes the directory as a "transition placeholder"
pointing to `.github/instructions/` as authoritative. That directory was deleted during
the v1→v2 migration (task #10). The README needs to reflect reality: `instructions/`
is now the primary and only location for instruction files.

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| VS Code custom instructions docs | https://code.visualstudio.com/docs/copilot/copilot-customization | .90 — defines `.instructions.md` format, `applyTo`, YAML frontmatter |
| OwlBear copilot-instructions.md | `.github/copilot-instructions.md` (local) | 1.0 — project conventions, directory structure table |
| Task #10 (Port instruction files) | `kanban/tasks/010-port-instruction-files.md` | 1.0 — confirms migration completed, `.github/instructions/` deleted |
| test_port_instruction_files.py | `tests/test_port_instruction_files.py` | .85 — tests verify `.github/instructions/` does not exist |

## 3. Analysis

N/A — trivial change, rationale: single-file README update with known correct content.

**Current state:** README says "Transition placeholder directory. The authoritative
instruction files live in `.github/instructions/`." — factually wrong post-migration.

**Required state:** README describes `instructions/` as the primary location and lists
the 4 instruction files with their `applyTo` scopes.

### Stale references elsewhere (out of scope, noted for awareness)

| File | Stale reference | Notes |
|------|----------------|-------|
| `docs/decisions/README.md` L49 | `.github/instructions/decision-requests.instructions.md` | That file doesn't exist |
| `.github/prompts/agent-audit.prompt.md` L15 | `.github/instructions/*.instructions.md` | Should reference `instructions/` |
| `scripts/setup.py` L40 | `.github/instructions` in settings mapping | May need cleanup |
| `kanban/tasks/007-create-monorepo-skeleton.md` | References `.github/instructions/` as authoritative | Historical task, low priority |

These are separate concerns and should not be bundled into #109.

## 4. Recommendation (.95 confidence)

Replace the README content with a directory description listing each instruction file,
its `applyTo` scope, and a one-line description. The content already exists in the
YAML frontmatter of each file — just surface it.

## 5. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Implement: update instructions/README.md for v2" --priority nice-to-have --status ideation --tags "phase-1,scope:docs,type:docs" --body "## Objective
Update instructions/README.md to accurately describe the directory.

## AC
- [ ] Remove 'transition placeholder' text and .github/instructions/ reference
- [ ] Describe instructions/ as the primary location for VS Code instruction files
- [ ] List all 4 files with applyTo scopes:
  - agent-common.instructions.md (applyTo: **) — Cross-agent rules
  - python.instructions.md (applyTo: **/*.py) — Python conventions
  - frontend.instructions.md (applyTo: src/**/ui/**,...) — Frontend conventions
  - research-docs.instructions.md (applyTo: docs/research/*.md) — Research guardrails
- [ ] Keep it under 20 lines

## Context
Research: docs/research/instructions-readme-update.md
Parent: #109"
```

```powershell
kanban\kanban-md.exe create "Clean up stale .github/instructions/ references" --priority nice-to-have --status ideation --tags "phase-1,scope:docs,type:docs" --body "## Objective
Remove remaining stale references to .github/instructions/ across the repo.

## AC
- [ ] docs/decisions/README.md L49: fix reference to decision-requests instructions
- [ ] .github/prompts/agent-audit.prompt.md L15: update to instructions/
- [ ] scripts/setup.py L40: remove .github/instructions from settings mapping
- [ ] Grep verify no remaining .github/instructions/ references in active files

## Context
Found during #109 research. See docs/research/instructions-readme-update.md § 3."
```
