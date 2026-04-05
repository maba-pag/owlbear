---
id: 615
title: 'First sync: validate clean main branch'
status: todo
priority: needed
created: 2026-04-04T21:55:56.253579+02:00
updated: 2026-04-05T07:19:41.5936864+02:00
tags:
    - scope:infra
    - type:build
    - phase-2
    - test
parent: 610
depends_on:
    - 613
    - 614
class: standard
---

## Summary

After the sync workflow (#613) is created and #614 (skills-ref optional group) is complete, run the first sync from dev to main. Verify the clean main branch works for consumers.

## Acceptance Criteria

- [ ] AC1: `gh workflow run sync-to-main.yml` (or GitHub UI manual dispatch) completes with exit code 0
- [ ] AC2: `git ls-tree --name-only main` shows only: share/, serve/, seed/, setup/, pyproject.toml, uv.lock, .python-version, .gitignore, README.md (synced from README-consumer.md per #613), SECURITY.md -- no other top-level entries
- [ ] AC3: None of these dev-only paths exist on main: .owlbear/, store/, tests/, v1/, .github/, scripts/, docs/, conftest.py, owlbear-project.json, Owlbear.code-profile, kanban/
- [ ] AC4: `git clone --branch main <repo-url> /tmp/test-clone; cd /tmp/test-clone; uv sync` exits 0; `uv pip list` does not include skills-ref
- [ ] AC5: Consumer init: from a fresh empty directory, `python <clone-path>/setup/init.py` creates .vscode/mcp.json, .vscode/settings.json, and owlbear-project.json without errors
- [ ] AC6: All 4 stdio MCP server modules import cleanly: `uv run python -c 'from owlbear_mcp_kanban.server import mcp'` exits 0, repeat for owlbear_mcp_knowledge, owlbear_mcp_memory, owlbear_mcp_project. Import check verifies dependency resolution; full mcp.run() blocks on stdio and is not suitable for non-interactive validation.

## Notes

This is the validation task. If anything fails, fix on dev and re-sync.
Verification commands in ACs are illustrative -- the builder may use equivalent checks.
AC2 allow-list must match #613's sync include-list. If they diverge, AC2 correctly catches it as a validation failure.

[[2026-04-05]] Sun 07:19
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | All ACs validate one concern: first sync output correctness |
| Interface clarity | PASS (refined) | Original had 5 vague ACs. Rewrote 7 into 6 mechanically verifiable ACs with explicit commands. |
| Dependency correctness | PASS | #613 (sync workflow) + #614 (skills-ref) correct. Transitive #611, #612 covered via #613. |
| Module layering | N/A | No code changes -- validation task |
| TDD compliance | PASS (fixed) | Added 'test' pass-through tag. Task IS a test. |
| KISS/YAGNI | PASS | Appropriate scope for final integration validation |
| Premise challenge | PASS | #613 creates mechanism; #615 validates end-to-end. Necessary. |
| Pattern consistency | N/A | No code patterns to check |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | scope:infra only |

### Codebase Evidence

- setup/init.py: creates .vscode/mcp.json, .vscode/settings.json, owlbear-project.json from seed/ templates
- seed/.vscode/mcp.json: 4 stdio MCP servers (kanban, knowledge, memory, project) + github HTTP
- serve/mcp-*/src/*/__main__.py: each imports mcp from server.py and calls mcp.run()
- No sync workflow exists yet (613 will create it)
- No README-consumer.md exists yet (612 will create it)

### Refinements Applied

1. AC1: Added workflow name and exit-code-0 verification
2. AC2: Added git ls-tree method + README.md origin note (from README-consumer.md per 613)
3. AC3: Replaced vague 'etc.' with exhaustive exclusion list
4. Merged redundant AC4 ('working installation') into AC4 (uv sync) and AC5-AC6
5. AC5: Specified exact files setup/init.py produces
6. AC7 became AC6: Named all 4 MCP servers, clarified import-check rationale (mcp.run blocks on stdio)
7. Added 'test' pass-through tag
8. Added AC2 drift-catch note per challenger feedback

### Challenge Results

- Challenger: RECONSIDER (confidence: 0.68)
- Concerns: (1) AC2 allow-list may drift from 613 sync list, (2) AC6 import-only doesnt test mcp.run()
- Architect response: REBUTTED/INTEGRATED. (1) Drift is caught by design -- AC2 validation fails if lists diverge, added explicit note. (2) mcp.run() starts infinite stdio loop, not testable non-interactively; import check verifies dependency resolution which is the first-sync concern. Both concerns addressed as clarifying notes in ACs.

### Verdict: APPROVE (after refinement)
### Action Taken: Rewrote 7 vague ACs into 6 precise, verifiable ACs. Added 'test' pass-through tag. Integrated challenger feedback. Advancing to todo.

[[2026-04-05]] Sun 07:19
APPROVED #615 -> todo | Refined 7 vague ACs into 6 precise, verifiable ACs with explicit commands. Added test pass-through tag. Challenger RECONSIDER (0.68) on AC2 drift and AC6 import-only -- both integrated as clarifying notes.
