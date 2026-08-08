# Knowledge Source Contract Alignment Design

> **Status:** Complete candidate; final gates pending
> **Umbrella:** `website-to-knowledge-vertical`

## Ownership And Evidence

Agent owns complete role interface; prompt owns user entry; handbook owns procedure. MCPServer owns the live callable registry and envelope/purge behavior; model/store own payload and mismatch. No focused test or automated pytest path exists. `.github` syncs to downstream repositories without root tests or `.owlbear`, so the new workflow must not execute outside canonical `maba-pag/owlbear` or expose main/manual execution.

## Architecture

1. Add grants; align agent description, argument hint, persona, lifecycle rule, output format, and workspace boundary. Channel A reports registration record, ingestion result, or purge summary. Retain no terminal/workspace writes.
2. Align prompt description, input line, capability list without procedure duplication.
3. Add handbook registration reference/tree/exclusion; correct deletion output; replace false exhaustiveness with allowlist-owned availability.
4. Remove old config-example heading and entire unmarked fence. Add `Registration payload examples`, label whole objects as tool argument mappings with nested config, and use exact markers `json knowledge-registration-url-list` and `json knowledge-registration-file-glob`, object metadata, nested kinds, current fields.
5. Add `tests/test_knowledge_ops_contract.py`:
   - parse agent frontmatter; require grants as subset;
   - import `mcp` from `owlbear_mcp_knowledge.server`, mark the async registry contract test explicitly with `@pytest.mark.asyncio` for strict asyncio mode, and use `{tool.name for tool in await mcp.list_tools()}` as the exact live public MCPServer registry; require both names;
   - parse exact marker pattern; reject duplicates; require URL/file subset; process all fences; JSON parse; require metadata object; strict-false model validation; isolated ensured store registration/kind proof; derived mismatch `ValueError`.
6. Add `.github/workflows/knowledge-source-contracts.yml`:
   - `pull_request.branches: [dev]` and relevant paths;
   - `push.branches: [dev]` and same paths;
   - no `workflow_dispatch` and no main event;
   - job guard `if: github.repository == 'maba-pag/owlbear'` so synced downstream copies never execute;
   - paths: agent, prompt, handbook, new test, validator, root `conftest.py`, `serve/knowledge/**`, `serve/mcp-knowledge/**`, `pyproject.toml`, `uv.lock`, `.python-version`, workflow;
   - permissions `{}`, job contents read, Ubuntu, 15 minutes; pinned existing checkout/setup-uv SHAs; setup-uv `enable-cache: true` and `cache-dependency-glob: uv.lock`; `uv python install`; validator; `uv run --frozen pytest -q tests/test_knowledge_ops_contract.py`.

No existing test changes. Root pytest configuration and whole Knowledge package filters close test and MCPServer import dependencies. Downstream repositories receive an inert workflow definition because the canonical-repository guard is false; main also has no matching event.

## Proof

Before approval run agent validator, current-boundary probe equivalent to proposed test, and YAML/actionlint against proposed workflow shape; then derive, checkpoint, validate exact package. Delivery runs new test and actionlint.

## Known Limits

- Destructive deletion has no confirmation UI/token; handbook remains detailed guard.
- Refresh-result drift, missing lookup tool, and missing inline entry remain outside scope; corrected untested prose relies on review.
- Canonical mappings exclude nullable normalization, transport/fetch/refresh/chunk/vector/enrichment/search proof.
- First actual dev workflow event/path execution is observable only after publication; pre-publication proof covers YAML/actionlint and commands.
- Whole Knowledge filters may run more often than necessary; accepted to avoid hidden imports.
- Workflow is inert on consumer main and has no manual trigger there.
- Required markers are URL/file; additions allowed; rendered/authenticated work is later.

## Delivery Shape

One outcome yields `SCOPE-001`; interfaces/docs, test, workflow may be separate tasks. No assembly scope.

## Unresolved Gates

No authored decision remains. Fresh derivation, challenge, baseline, checkpoint, validation, and explicit approval remain. Stop after approval; do not admit.
