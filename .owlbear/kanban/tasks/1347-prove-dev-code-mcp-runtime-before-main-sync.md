---
id: 1347
title: Prove dev-code MCP runtime before main sync
status: backlog
priority: critical
created: 2026-05-04T18:02:22.883451+00:00
updated: 2026-05-04T18:02:22+00:00
tags:
- sync-blocker
- mcp-kanban
- ci
- dev-experience
parent:
depends_on:
- 1340
- 1352
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

The dev workspace MCP config launches OwlBear MCP servers with `uv --project ../owlbear`, which points at the sibling consumer checkout rather than the `owlbear-dev` source tree. That is correct for dogfooding consumer behavior, but it is not a valid proof that current dev MCP code is ready to sync. The sibling consumer checkout is also dirty and stale relative to dev, so MCP tool success in the dev editor can be a false green.

Audit decision: add a sync-readiness smoke/proof path that launches and validates MCP from current dev source before main sync.

## Acceptance Criteria

1. Add a deterministic dev-code MCP smoke command, test, or CI gate that launches `owlbear_mcp_kanban` from the current `owlbear-dev` checkout, not from `../owlbear`.
2. The smoke proves the module path resolves under the current checkout and not the sibling consumer checkout.
3. The smoke verifies the exported kanban MCP surface includes the deployment contract: 9 tools including `create_dr`, and `end_work` exposes `success`, `fail`, `reject`, `block`, and `release` after `#1339` lands.
4. The proof path does not depend on VS Code's live `.vscode/mcp.json` server configuration.
5. Document the distinction between consumer MCP config (`../owlbear` or seed placeholder) and dev-code verification so future audits do not treat consumer-runtime MCP tool success as dev-source evidence.
6. Add the proof to the pre-sync checklist or sync validation path so it runs before a deployment sync is declared ready.
7. The check must be read-only against the real kanban board unless it uses an isolated temporary board fixture.

## Key Files

- `.vscode/mcp.json`
- `seed/.vscode/mcp.json`
- `.github/workflows/sync-to-main.yml`
- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`
- `serve/mcp-kanban/tests/`
- `tests/`

## Audit Evidence

- Dev `.vscode/mcp.json` uses `uv --project ../owlbear` for `ob-kanban`.
- `sync-to-main` prunes `.vscode/` from the consumer branch, so consumer projects use seed-generated MCP config instead.
- Local sibling `owlbear` is on `main`, dirty, and stale relative to `owlbear-dev` for kanban, mcp-kanban, and Cockpit paths.
- The deployment audit must validate the code that will be synced, not whichever stale checkout the editor happens to launch.

## Source

Deployment audit finding group 5, 2026-05-04.
