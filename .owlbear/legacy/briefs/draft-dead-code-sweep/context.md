# Context — Dead Code Sweep

## Problem Statement

The OwlBear project has accumulated dead code and stale references from two abandoned directions:

1. **Copilot CLI / ACP orchestration** — `serve/orchestrator/` is an entire package built around spawning Copilot CLI as an ACP agent. The project now stays with VS Code's native agent system. This package, its tests, its fixtures, and references throughout docs/skills/instructions are all potentially dead.

2. **Pydantic AI** — v1 of the project explored Pydantic AI for agent runtime. The `pydantic-ai` dependency no longer appears in any `pyproject.toml`, but research docs, design references, and possibly stale code patterns may remain.

3. **`owlbear-project.json`** — a minimal config (`name`, `owlbear_path`, `created_at`) whose consumers and purpose are unclear. Also exists in `seed/`.

The dead code inflates the repo, misleads contributors reading docs/skills, and creates maintenance drag.

## Project Type

`existing-feature/refactor` — removal/cleanup of abandoned code paths in a live project.

## Known Affected Areas (Brownfield Check)

- `serve/orchestrator/` — full package (cli.py, examples/, tests/, pyproject.toml)
- `tests/fixtures/mock_acp_agent.py`
- `README.md` — Copilot CLI install instructions, orchestrator description
- `share/skills/r-architecture-standards/SKILL.md` — references ACP/Copilot CLI
- `share/skills/w-research/SKILL.md` — references Copilot CLI in stack check
- `.owlbear/research/` — multiple PydanticAI and ACP research docs
- `owlbear-project.json` (root + `seed/`)
- `share/WIRING.md` — likely references orchestrator

## Locked Outcomes

**Best realistic outcome:**
- `serve/orchestrator/` removed entirely (package, examples, tests, fixture)
- `owlbear-project.json` removed from root, `seed/`, `setup/init.py` generation, and setup docs
  - `scope_transfer.py` left untouched (has env var fallback, KB not fully implemented)
- All pyproject.toml workspace/dependency entries referencing orchestrator removed
- All references to Copilot CLI / ACP in README, skills, instructions, agents updated or removed
- No surviving import paths or package cross-references to orchestrator or ACP
- `doc-index.md` regenerated after removal
- Test suite passes cleanly

**Minimum viable win:**
- `serve/orchestrator/` removed with confidence nothing depends on it
- README and live skills/instructions no longer reference Copilot CLI as a requirement
- pyproject.toml workspace config updated

**Scope boundaries:**
- `.owlbear/research/` docs NOT removed (historical record)
- `scope_transfer.py` NOT touched (KB feature in progress, has fallback)
- Active dev work not touched — only clearly dead/abandoned code
- No refactoring of live code — pure removal
- Surgical: if other dead code surfaces, file as follow-up task

## Open Questions (for Phase 2)

- Does `tests/test_package_boundary.py` have orchestrator-only content or is it broader?
- Are there CI workflows or git hooks referencing `uv run owlbear`?
- How should `r-architecture-standards` be rewritten — just remove the ACP language, or describe the current VS Code agent model?
