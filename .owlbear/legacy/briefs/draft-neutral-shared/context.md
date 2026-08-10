# Context — Neutral Shared Layer

## Problem Statement

OwlBear's `share/` directory (agents, skills, instructions, prompts) syncs from `dev` to `main` and is consumed by non-OwlBear projects via VS Code settings pointing at `{{owlbear_rel_path}}/share/*`. Many of these files contain OwlBear-specific references — folder paths like `serve/*/src/`, project-specific test markers, file placement rules — that don't apply to other consumers.

**The files themselves belong in `share/`.** The problem is project-specific content baked into otherwise-generic framework files. A consumer gets confused or incorrect instructions.

**No override hierarchy exists.** VS Code discovers skills/agents from all configured paths without priority. Two versions of the same skill = undefined behavior. This rules out "shadow with a local copy" as a general strategy.

## Project Type

existing-feature/refactor

## Affected Users

- Non-OwlBear projects consuming the main branch (2 projects, both user-controlled)
- OwlBear-dev itself (must preserve its specifics, just relocate them)

## Current State

- `share/` syncs to `main` → consumer-facing
- `.owlbear/` does NOT sync to `main` → dev-only
- `setup/init.py` wires consumers to: shared `share/*` + local `.owlbear/*` paths
- VS Code has no skill priority/shadowing — both paths are equal
- `.github/copilot-instructions.md` IS always loaded and IS project-specific
- `.owlbear/instructions/` files are additive (discovered alongside `share/instructions/`)
- `owlbear-project.json` exists per consumer (has `owlbear_rel_path`, `name`)

## What's Universal (keep hardcoded)

- `.owlbear/` as the project-ops folder
- Python + uv as the package manager
- Node + npm for frontend
- pytest, ruff, Vitest as tool defaults
- Porsche Design System as frontend default
- Kanban workflow, pipeline agent roles
- Commit format conventions
- `tests/` as test folder name

## What's OwlBear-Specific (must not be in shared)

- `serve/*/src/` monorepo layout paths
- `testpaths = ["tests", "serve"]`
- Directory structure table listing `serve/`, `share/`, `setup/`, etc.
- Architecture overview + namespace table listing OwlBear's `serve/` packages
- `serve/cockpit/web/` as frontend path in examples
- "OwlBear workspace" / "OwlBear project" naming in descriptions
- `arch-audit.prompt.md` (only audits `serve/` packages)

## What IS Consumer Product (NOT OwlBear-specific, keep in shared)

- ALL MCP server skills (h-mcp-kanban, h-mcp-memory, h-knowledge-ops) — consumers use these servers
- ALL pipeline agents (builder, reviewer, etc.) — consumers use this pipeline
- w-orchestration — consumers dispatch work this way
- r-pipeline-protocol — consumers follow this protocol
- All workflow skills (tdd, review, research, ideation) — consumer workflows
- Kanban operations, memory operations, knowledge operations — consumer tools

## Key Constraint

Consumer's accepted maintenance model: if a skill needs project-specific customization beyond what the generic version provides, the consumer copies it to `.owlbear/skills/` and modifies it. Manual sync on updates is acceptable.

## Outcomes (locked M2)

**Best realistic outcome:** Every `share/` file provides a good generic default for typical Python+TS projects. No OwlBear-specific references that would confuse consumers. OwlBear-dev's project-specifics (monorepo layout, directory table) live in its own `.github/copilot-instructions.md` and/or local `.owlbear/` files. A new consumer runs `setup/init.py` and gets a working agent system immediately.

**Minimum viable win:** Core instructions (always-loaded, like `owlbear-system.instructions.md`) and frequently-referenced skills (python conventions, pytest, project standards) are project-neutral.

**Scope boundary:**
- IN: content refactoring of `share/` files, creating OwlBear-dev local overrides, dead code removal
- OUT: new mechanisms (variable resolution, priority), architecture redesign, perfection for every possible project type
- ASSUMPTION: Python+uv, pytest, Vitest, npm are good universal defaults — keep them
- ASSUMPTION: `.owlbear/` folder name is universal for all consumers

## Active Tensions

1. `owlbear-system.instructions.md` is ~80% OwlBear-specific. Only §1 (Decision Heuristics) is genuinely generic.
2. Agent .md files can't be split — they're single files with both generic persona AND OwlBear-specific wiring (tools, MCP refs).
3. MCP skills (h-mcp-kanban, h-mcp-memory, h-knowledge-ops) are entirely OwlBear-specific — move, don't genericize.
4. Pipeline protocol (r-pipeline-protocol) is mixed: task lifecycle is generic, agent roster/section mappings are OwlBear-specific.
5. Three intervention types: move (entirely specific), split (mixed), parameterize (generic with hardcoded paths).
6. Need to confirm `.owlbear/` gitignore status on dev branch — OwlBear-dev needs its local skills tracked.
