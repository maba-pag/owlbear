# Brief — Dead Code Sweep

## Problem

The OwlBear repo contains dead code from an abandoned direction: Copilot CLI / ACP orchestration. The `serve/orchestrator/` Python package, its test infrastructure, and references scattered across README, skills, instructions, and diagrams all describe a system that no longer exists. Additionally, `owlbear-project.json` generation infrastructure serves no current consumer (the only live reader has an env var fallback that is also being removed).

This dead code misleads agents reading docs as authoritative, inflates the repo, and creates maintenance drag.

## Scope

**In scope:**
- Complete removal of `serve/orchestrator/` and all its dependents/references
- Removal of `owlbear-project.json` from root, seed, and generation infrastructure
- Gutting `scope_transfer.py`'s resolution logic (replace with TODO)
- All stale Copilot CLI / ACP references in live docs, skills, and diagrams
- Excalidraw diagram cleanup (with proper binding handling)

**Out of scope:**
- `.owlbear/research/` docs (historical record — kept)
- `share/agents/orchestrator.agent.md` and `share/skills/w-orchestration/` (live VS Code pipeline orchestrator — different system, same name)
- Any refactoring or feature work — pure removal only

## Removal Manifest

### Delete (5 items)

| Target | Rationale |
|--------|-----------|
| `serve/orchestrator/` (entire directory) | Dead ACP client package — zero external imports |
| `tests/fixtures/mock_acp_agent.py` | Test double for Copilot CLI — only consumer was orchestrator |
| `.owlbear/scripts/e2e_smoke.py` | Copilot CLI E2E smoke test |
| `owlbear-project.json` (root) | No live consumer in dev workspace |
| `seed/owlbear-project.json` | Template for file that's no longer generated |

### Edit (14 files)

| File | Change |
|------|--------|
| `pyproject.toml` | Remove `"serve/orchestrator/src"` from ruff `src` list; remove `"owlbear_orchestrator"` from coverage `source_pkgs` |
| `tests/test_package_boundary.py` | Remove `"owlbear"` and `"owlbear_orchestrator"` entries from `ALLOWED_IMPORTS`; update docstring |
| `tests/test_pipeline_diagram.py` | Reframe orchestrator auxiliary assertion (concept still valid for live VS Code orchestrator — update, don't delete) |
| `README.md` | Remove Copilot CLI prerequisite, orchestrator directory row, orchestrator description paragraph, and CLI commands section |
| `README-consumer.md` | Remove `owlbear-project.json` from setup output mention |
| `.github/copilot-instructions.md` | "built around Copilot CLI" → "built around VS Code and GitHub Copilot agents" |
| `share/skills/r-architecture-standards/SKILL.md` | Remove ACP dispatch intro paragraph + orchestrator row from package table |
| `share/skills/w-research/SKILL.md` | "Copilot CLI" → "VS Code" in stack check |
| `share/prompts/arch-audit.prompt.md` | Remove/replace `serve/orchestrator/` as example audit unit |
| `setup/init.py` | Remove `_write_project_json()` function, dispatch block, and frozenset entry |
| `setup/setup-guide.md` | Remove `owlbear-project.json` table row |
| `setup/sharing-guide.md` | Remove `owlbear-project.json` table row |
| `serve/knowledge/src/owlbear_knowledge/scope_transfer.py` | Gut `resolve_global_db_path()` — replace file/env-var logic with TODO comment |
| `share/diagrams/` (3 excalidraw files) | Remove orchestrator/ACP elements with proper binding cleanup |

### Regenerate (2 items)

| Target | Command |
|--------|---------|
| `uv.lock` | `uv lock` |
| `.owlbear/doc-index.md` | `uv run doc-index` |

## Implementation Notes

### Ordering Constraint

`tests/test_package_boundary.py` has bidirectional validation: it fails if ALLOWED_IMPORTS contains keys for non-existent packages, AND fails if discovered packages are missing from the dict. The `serve/orchestrator/` deletion and the ALLOWED_IMPORTS edit **must be in the same commit** to avoid an intermediate broken state.

### Excalidraw Binding Handling

`share/diagrams/mcp-topology.excalidraw` encodes the orchestrator as interconnected bound elements:
- `s1_orchestrator_rect` — rectangle element
- `s1_orchestrator_text` — text contained within the rect
- `s1_acp_arrow` — arrow connecting to the rect
- `s1_acp_label` — label contained within the arrow

When removing these, also clean up:
- `boundElements` arrays on any surviving element that references the deleted IDs
- `startBinding`/`endBinding` fields on surviving arrows pointing to deleted elements
- `containerId` fields (will be deleted with their containers)

`pipeline.excalidraw` and `project-overview.excalidraw` have simpler text-only references — straightforward removal.

### Pipeline Diagram Test

`test_pipeline_diagram.py` asserts "orchestrator" appears as an auxiliary annotation. This concept is still valid for the live VS Code orchestrator. The test should be preserved or reframed — verify the diagram still shows the orchestrator in its supervisory role after the excalidraw edit.

### Name Collision Awareness

The word "orchestrator" survives in the project (VS Code agent, pipeline skill, prompt, wiring). Only the `serve/orchestrator/` Python package and Copilot CLI/ACP references are dead. Builders must not remove references to the live VS Code orchestrator agent.

## Acceptance Criteria

1. `serve/orchestrator/` directory does not exist
2. `grep -r "serve/orchestrator" . --include="*.py" --include="*.toml" --include="*.md"` returns zero hits outside `.owlbear/research/`, `.owlbear/kanban/`, `.owlbear/scratch/`, and `.owlbear/briefs/`
3. `grep -r "Copilot CLI" . --include="*.md"` returns zero hits outside `.owlbear/research/`, `.owlbear/kanban/`, `.owlbear/scratch/`, and `.owlbear/briefs/`
4. `grep -r "agent-client-protocol" . --include="*.toml"` returns zero hits outside `.owlbear/research/`, `.owlbear/kanban/`, and `.owlbear/scratch/`
5. `owlbear-project.json` does not exist at root; `seed/owlbear-project.json` does not exist
6. `uv sync` succeeds (lockfile is valid)
7. `uv run pytest` passes on touched files and files referencing touched files
8. `uv run ruff check` passes on touched files
9. `.owlbear/doc-index.md` is regenerated and does not reference orchestrator CLI
10. Excalidraw diagrams load without JSON errors (validated via `python -m json.tool` on each file)
11. `tests/test_pipeline_diagram.py` still passes (orchestrator-as-auxiliary concept preserved)

## Decomposition Guidance

Suggested task split for the planner:

1. **Core removal** — delete `serve/orchestrator/`, fixtures, e2e_smoke, owlbear-project.json files; edit pyproject.toml, test_package_boundary.py, setup/init.py, scope_transfer.py; run `uv lock`. (Must be atomic — boundary test constraint.)
2. **Doc/skill reference cleanup** — edit README.md, README-consumer.md, copilot-instructions.md, r-architecture-standards, w-research, arch-audit.prompt.md, setup docs; regenerate doc-index.
3. **Diagram cleanup** — edit 3 excalidraw files with binding handling; verify test_pipeline_diagram still passes.

## Follow-up Tasks

| Task | Priority | Rationale |
|------|----------|-----------|
| Rework `scope_transfer.py` global DB path resolution | deferred | KB feature not yet consumer-ready; approach TBD when KB launches |
