# Decision: Five-Tier Folder Restructure (.owlbear/ migration)

**Date:** 2026-04-04
**Status:** Resolved
**Participants:** User + Copilot planning session

## Context

OwlBear is a laptop-resident AI dev system cloned alongside target projects. Currently, agents/skills/instructions/prompts live in `.github/` — a GitHub convention folder that creates namespace confusion when shared to target projects that have their own `.github/`.

A previous attempt (v2 architecture decision #18) moved agents/skills to repo root (`agents/`, `skills/`), but this was reversed because it cluttered the project root.

A new approach is needed that:
1. Gives owlbear content a clear, dedicated namespace
2. Separates "what owlbear exports" from "what each project consumes"
3. Works identically in the owlbear repo and target projects
4. Keeps the root clean

## Decision

Restructure the owlbear repo into a five-tier model, each with a single role and delivery mechanism.

### The Five Tiers

| Folder | Role | Delivery | Scope |
|--------|------|----------|-------|
| `share/` | VS Code customization files | File linking (VS Code settings) | Linked by targets |
| `serve/` | Python runtime services | MCP/CLI execution | Used by targets |
| `store/` | Global persistent state | MCP server read/write | Cross-project |
| `seed/` | Project templates | File copy (setup/init.py) | Copied into targets |
| `.owlbear/` | Project operational data | MCP server read/write | Per-project |

### Naming Convention

share/serve/store/seed — alliterative verbs describing what each folder does. Grammatically consistent.

### `.github/` Remains (Thin)

`.github/` retains only convention-mandated files:
- `copilot-instructions.md` — VS Code auto-discovers this path
- `dependabot.yml` — GitHub convention

Owlbear-specific system instructions are extracted to `share/instructions/owlbear-system.instructions.md` (loaded via `chat.instructionsFilesLocations`).

### Target Project Layout

After `setup/init.py` bootstraps a target project:
```
my-project/
  .owlbear/
    kanban/config.yml, setup.ps1, tasks/
    hooks/deny-writes.ps1, lint-changed.ps1
    knowledge/
  .vscode/settings.json, mcp.json
  owlbear-project.json
```

### Setup is Data-Driven

`seed/` mirrors the target project structure. `setup/init.py` reads templates from `seed/`, processes placeholders, and writes to the target. Changes to defaults require only template edits, no Python changes.

## Key Decisions

1. **Five-tier model** — share, serve, store, seed, .owlbear.
2. **`packages/` renamed to `serve/`** — low risk (pyproject.toml config only; Python imports, MCP launch, uv commands unaffected).
3. **`data/` renamed to `store/`** — global cross-project stores (memory, general knowledge).
4. **Hooks seeded to `.owlbear/hooks/`** — agent hook commands resolve from workspace root; `.owlbear/hooks/` is the only path consistent across all projects.
5. **CI scripts to `.owlbear/scripts/`** — project-specific tooling, not product.
6. **User docs to `setup/`** — setup-guide and sharing-guide live with the setup script.
7. **`copilot-instructions.md` stays in `.github/`** — VS Code convention. System instructions extracted to `share/instructions/`.
8. **`setup/init.py`** replaces `scripts/setup.py` — convention: `git init`, `npm init`, `owlbear init`.
9. **`seed/` structure mirrors target** — data-driven setup eliminates hardcoded paths in Python.
10. **Knowledge split: global + local** — `store/knowledge/` for cross-project baseline, `.owlbear/knowledge/` for project-local.
11. **Decisions, research, sources, scratch** move to `.owlbear/` — process artifacts are project ops data.

## Migration Map

| Current | New |
|---------|-----|
| `.github/agents/` | `share/agents/` |
| `.github/skills/` | `share/skills/` |
| `.github/instructions/` | `share/instructions/` |
| `.github/prompts/` | `share/prompts/` |
| `packages/` | `serve/` |
| `data/` | `store/` |
| `kanban/` | `.owlbear/kanban/` |
| `docs/decisions/` | `.owlbear/decisions/` |
| `docs/research/` | `.owlbear/research/` |
| `docs/sources/` | `.owlbear/sources/` |
| `docs/scratch/` | `.owlbear/scratch/` |
| `docs/setup-guide.md` | `setup/setup-guide.md` |
| `docs/sharing-guide.md` | `setup/sharing-guide.md` |
| `scripts/setup.py` | `setup/init.py` |
| `scripts/hooks/` | `seed/.owlbear/hooks/` + `.owlbear/hooks/` |
| `scripts/validate_*.py` | `.owlbear/scripts/` |
| `scripts/e2e_smoke.py` | `.owlbear/scripts/` |
| `scripts/skills_ref/` | `.owlbear/scripts/skills_ref/` |

## Alternatives Considered

- **Keep `.github/`:** Status quo. Namespace confusion persists.
- **Root-level `agents/`/`skills/`:** Previously tried and reversed — clutters project root.
- **Single `.owlbear/` folder:** Mixed shared product + project data. Breaks single-responsibility.
- **Non-alliterative names (`packages/`, `data/`):** Grammatically inconsistent, less memorable.

## Risks

1. **kanban-md binary** may assume `kanban/` directory — needs path verification.
2. **setup.py shallow merge bug** in `chat.*Locations` — pre-existing, must fix.
3. **Large diff** — one-time migration touching hundreds of files.
4. **Historical docs not updated** — archived tasks/research reference old paths (intentional).
5. **VS Code auto-discovery lost** — `.github/agents/` auto-discovered; `share/agents/` requires explicit settings.

## Kanban Path Verification

**Verified:** 2026-04-05 | Task #599 | kanban-md.exe v0.33

All CRUD operations work correctly when `config.yml` and `tasks/` reside in `.owlbear/kanban/`.

| Operation | Command | Exit | Result |
|-----------|---------|------|--------|
| AC1a Create (relative path) | `kanban-md --dir .owlbear\kanban\ create "Test task"` | 0 | PASS — task created, file written to `.owlbear\kanban\tasks\` |
| AC1b List --json (absolute path) | `kanban-md --dir <abs>\.owlbear\kanban list --json` | 0 | PASS — JSON array returned, parseable |
| AC1c Show --json (relative path) | `kanban-md --dir .owlbear\kanban\ show <id> --json` | 0 | PASS — task details returned |
| AC1d Move (relative path) | `kanban-md --dir .owlbear\kanban\ move <id> todo` | 0 | PASS — status changed |
| AC1e Edit/append (relative path) | `kanban-md --dir .owlbear\kanban\ edit <id> -a "body text"` | 0 | PASS — body appended, confirmed via show |

### Path Assumptions and Limitations (AC2)

- **No directory name constraint.** The directory does not need to be named `kanban/`. Tested with `.owlbear/board-test/` — succeeded identically.
- **Relative paths resolve from process cwd.** `.owlbear/kanban/` is relative to wherever `kanban-md.exe` is invoked. The MCP server must be started from the project root (or use an absolute path via `KANBAN_DIR` env var — handled by task #606).
- **Both separators accepted on Windows.** Both `.\owlbear\kanban\` (backslash) and `.owlbear/kanban/` (forward slash) work correctly on Windows. Exit 0 with identical output.
- **Missing directory gives clear error.** `--dir` pointing to a non-existent directory returns `{"error": "no kanban board found ...","code": "INTERNAL_ERROR"}` with exit code 2.
- **config.yml must be present.** The board requires a valid `config.yml` (copied from existing board). kanban-md auto-repairs `next_id` if needed when config is copied.

### Hardcoding Assessment (AC3)

No hardcoding found in the kanban-md binary itself. The `--dir` flag is fully functional with arbitrary paths. No workarounds (symlinks, wrapper scripts, config overrides) are needed at the binary level.

The MCP server (`packages/mcp-kanban/src/mcp_kanban/server.py`) does hardcode `_DEFAULT_KANBAN_DIR = Path("kanban")` and ignores `KANBAN_DIR` env var — but that is a server-layer concern handled by task #606, not the binary.

## Consequences

- `.github/` becomes a thin GitHub/VS Code convention folder
- `docs/` folder eliminated entirely
- Root becomes clean: four s-product folders + setup + tests + config
- Every project has the same `.owlbear/` structure
- setup/init.py becomes data-driven (templates in seed/)
