# Synthesis — Dead Code Sweep

## Panel Convergence

Both panelists approve the removal. No objections to the core action. Convergences:

1. **`serve/orchestrator/` removal is clean** — zero cross-package import coupling, safe to delete.
2. **`owlbear-project.json` removal from generation is safe** — KB isn't consumer-ready; env var fallback exists.
3. **Removal order matters for `test_package_boundary.py`** — directory deletion and ALLOWED_IMPORTS edit must land in one commit.

## Architect Amendments (Verified)

Five additional coupling points the original manifest missed:

| # | File | Issue | Action |
|---|------|-------|--------|
| 1 | `pyproject.toml` L160 | `source_pkgs` list includes `owlbear_orchestrator` | Remove entry |
| 2 | `uv.lock` L1494 | Editable source entry for orchestrator | Run `uv lock` after deletion |
| 3 | `share/prompts/arch-audit.prompt.md` L21 | Lists `serve/orchestrator/` as example audit unit | Edit: remove or replace example |
| 4 | `share/diagrams/` (3 files) | `pipeline.excalidraw`, `project-overview.excalidraw`, `mcp-topology.excalidraw` all show orchestrator/ACP | Edit: remove orchestrator elements |
| 5 | `tests/test_pipeline_diagram.py` L141–146 | Test asserts "orchestrator" text exists in diagram | Edit: remove the assertion |

Plus: set `OWLBEAR_GLOBAL_KB_PATH` in dev environment or accept that mcp-knowledge sync tools won't work in the dev workspace without the file.

## End-User Amendment (Verified)

One follow-up item: `scope_transfer.py` error message says "owlbear-project.json not found in cwd" without mentioning the env var fallback. File as follow-up task — one-line fix, not blocking.

## Remaining Decision

**Excalidraw diagrams:** Editing JSON element trees in 3 excalidraw files is non-trivial. Options:
- (A) Edit them now (requires careful JSON surgery on each diagram)
- (B) Defer diagram updates to a follow-up task (they're visual docs, not code)
- (C) Delete and regenerate the affected diagrams

## Final Removal Manifest (Amended)

### Delete
- `serve/orchestrator/` (entire directory)
- `tests/fixtures/mock_acp_agent.py`
- `.owlbear/scripts/e2e_smoke.py`
- `owlbear-project.json` (root)
- `seed/owlbear-project.json`

### Edit
- `tests/test_package_boundary.py` — remove `owlbear`/`owlbear_orchestrator` from ALLOWED_IMPORTS + docstring
- `pyproject.toml` — remove `"serve/orchestrator/src"` from ruff src AND `"owlbear_orchestrator"` from coverage source_pkgs
- `README.md` — remove Copilot CLI prerequisite, orchestrator rows/sections
- `.github/copilot-instructions.md` — "built around Copilot CLI" → "built around VS Code and GitHub Copilot agents"
- `share/skills/r-architecture-standards/SKILL.md` — remove ACP dispatch intro + orchestrator package entry
- `share/skills/w-research/SKILL.md` — "Copilot CLI" → "VS Code"
- `share/prompts/arch-audit.prompt.md` — remove/replace orchestrator example
- `setup/init.py` — remove `_write_project_json()` + dispatch + frozenset entry
- `setup/setup-guide.md`, `setup/sharing-guide.md` — remove owlbear-project.json rows
- `README-consumer.md` — remove owlbear-project.json mention
- `tests/test_pipeline_diagram.py` — remove orchestrator auxiliary assertion
- Excalidraw diagrams (3 files) — TBD per decision above

### Regenerate
- `uv.lock` (run `uv lock`)
- `.owlbear/doc-index.md` (run `uv run doc-index`)

### Update (not delete)
- `tests/test_pipeline_diagram.py` — the orchestrator auxiliary assertion tests a concept that's still valid for the live VS Code orchestrator. Reframe the assertion if needed, don't delete it blindly.

### Follow-up Task
- Improve `scope_transfer.py` error message to mention `OWLBEAR_GLOBAL_KB_PATH`

## Critic Validation (O15)

### Pass 1 — Synthesis Consistency
- **Nonsense (rejected):** Critic confused `serve/orchestrator/` (dead Python ACP package) with `share/agents/orchestrator.agent.md` (live VS Code agent). These are different systems. All `share/` orchestration references stay.
- **Material (accepted):** Excalidraw mcp-topology diagram has bound elements (rect→arrow→label). Implementation must handle `boundElements`, `startBinding`, `endBinding`, `containerId` — not just delete visible elements.
- **Minor (noted):** "One commit" constraint is practically correct (same green changeset). Boundary test edit + directory deletion must go together.

### Pass 2 — Final Design Merit
- **Material (accepted):** Pipeline diagram test assertion about orchestrator-as-auxiliary is conceptually still correct for the live VS Code orchestrator. Don't delete it — update or keep it.
- **Minor (noted):** owlbear-project.json trade-off is deliberate (user decision), not an oversight.
