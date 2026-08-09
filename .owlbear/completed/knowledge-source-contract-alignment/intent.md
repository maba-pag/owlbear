# Knowledge Source Contract Alignment

> **Status:** Complete candidate; final gates pending
> **Umbrella:** `website-to-knowledge-vertical`
> **Research:** `.owlbear/research/website-to-knowledge-opportunity-assessment.md`

## Problem

Knowledge source lifecycle tools exist, but `knowledge-ingestor` and `kb-ingest` expose only ingest/refresh. The required handbook omits registration, contains invalid examples, understates deletion results, and falsely claims its inventory determines callability. Existing changed-path guidance skips `share/` tests and no CI runs pytest, so drift is unprotected.

## Product Promise

The `kb-ingest` route and its authorized agent coherently support registering and intentionally deleting sources. Canonical handbook examples are accepted by the shipped model and real store, deletion results are accurate, and a focused automated contract check protects lifecycle authority and payload shape on the `dev` branch where its test dependencies exist.

## Scope

- Grant existing `register_knowledge_source` and `delete_knowledge_source` tools.
- Align agent description, argument hint, persona, lifecycle rule, output format, and workspace boundary, plus prompt description, input line, and capability list, with register/delete. Keep procedure canonical in `h-knowledge-ops`.
- Add registration to handbook reference/tree/exclusions; replace false exhaustiveness with agent-allowlist ownership.
- Delete the old `Config examples per source type` heading and shared commented config-only fence. Add **Registration payload examples**, stating each whole object is the complete tool argument mapping excluding framework context and `config` is nested. Mark canonical examples `json knowledge-registration-url-list` and `json knowledge-registration-file-glob`; use nested kind, plural patterns, and object metadata.
- Correct deletion output to the purge summary and retain destructive warning.
- Add `tests/test_knowledge_ops_contract.py` for required grants in the exact live MCPServer Knowledge registry through an explicitly `@pytest.mark.asyncio` test calling public async `mcp.list_tools()`, and every marked payload through production validation and real store registration.
- Add narrow `.github/workflows/knowledge-source-contracts.yml` for pull requests targeting `dev` and pushes to `dev`. It has no `workflow_dispatch` and its job requires canonical repository identity `maba-pag/owlbear`, so synced downstream copies cannot run without the dev-only test dependencies. It runs the agent validator and only the new test; filters cover root pytest configuration and all `serve/knowledge/**` and `serve/mcp-knowledge/**` runtime inputs.

## Accepted Exclusions

- No runtime/schema/refresh/extraction/Browser/setup/readiness/end-to-end/Cockpit behavior changes.
- No broad handbook cleanup: refresh-result drift, undocumented `lookup_knowledge_entity`, and missing `inline` Domain Reference entry remain outside scope; false exhaustiveness is removed.
- No package README, WIRING, MegaLinter, pre-commit, existing ecosystem test, general test mapping, manual workflow dispatch, or consumer-main test gate.
- No new tools/kinds, compatibility payloads, transport compatibility, or nullable-metadata normalization proof.
- No umbrella mutation, admission, planning, or orchestration.

## Preserved Behavior

Existing runtime, schemas, semantics, errors, other agent authority/tests, future additive grants/examples, later outcomes, existing workflow behavior, and wiring remain unchanged except the new dev-only focused gate.

## Success

- All loaded and user-visible role/entry interfaces permit register/ingest/refresh/delete while retaining no terminal/workspace writes; Channel A reports operation-appropriate source records, ingestion results, or purge summaries.
- Handbook guidance is coherent; invalid old fence is absent; full mappings and allowlist-owned availability are clear.
- Focused tests require both grants by containment, explicitly mark the registry test with `@pytest.mark.asyncio`, confirm `{tool.name for tool in await owlbear_mcp_knowledge.server.mcp.list_tools()}`, validate every marked fence with `SourceRegistration.model_validate(..., strict=False)`, and register through ensured in-memory `SqliteSourceStore`; required markers use containment and mismatch fails at the store.
- The focused workflow is valid and configured only for PRs targeting `dev` and pushes to `dev` in `maba-pag/owlbear`, across declared authority, test, pytest configuration, dependency, and complete Knowledge runtime path changes; it uses least-privilege permissions, a 15-minute timeout, immutable action SHAs, and explicit setup-uv caching keyed by `uv.lock`.

## Grounding And Decisions

- **Observed:** role/entry interfaces are ingest-framed, including output format.
- **Observed:** handbook has stated defects; production uses strict-false validation and store mismatch rejection.
- **Observed:** broad ecosystem test has unrelated inputs. No current automated pytest path exists.
- **Observed:** `.github` syncs to consumer `main`, while root tests and `.owlbear` do not. A manual trigger would therefore be invalid on `main`; branch-constrained automatic events avoid that distribution defect.
- **Decided:** one Knowledge-specific async test uses MCPServer's public `list_tools()` registry boundary, matching current ecosystem validation. Whole Knowledge package filters close its import boundary. Workflow authority is dev-only by event branch and canonical-repository job guard.

No unresolved user-owned product or architecture decision remains.

## Technically Done But Wrong

- Hidden lifecycle wording/output, invalid old examples retained, or false callability claims.
- Broad tests behind narrow filters, ambiguous registry selection, incomplete import-closure filters, or tests without automation.
- A consumer-visible manual trigger whose dependencies are absent on `main`.
- Arbitrary extraction, copied fixtures, exact full sets, wrong strictness, mirrored invariants, transport claims, or runtime changes.

## Delivery Contract

```yaml target-contract
kind: commitment
id: COM-001
class: dealbreaker
provenance: Ordered child scope and complete agent plus prompt interfaces
statement: The knowledge-ingestor must receive existing registration and deletion tools, and every loaded or user-visible role and kb-ingest interface, including output, must support that lifecycle while detailed procedure remains in the required handbook.
```

```yaml target-contract
kind: commitment
id: COM-002
class: dealbreaker
provenance: Handbook, SourceRegistration, SqliteSourceStore, deletion-result, and availability boundaries
statement: The handbook must replace invalid config-only examples and coherently document registration and deletion with labeled full argument payloads accepted through production validation and the real store, current purge fields, exclusion guidance, and allowlist-owned availability.
```

```yaml target-contract
kind: commitment
id: COM-003
class: protected-request
provenance: Ordered focused-child and distribution boundary
statement: Existing runtime, schemas, lifecycle and destructive semantics, other agent authority and tests, future additive grants/examples, later outcomes, consumer-main behavior, and unrelated automation must remain unchanged.
```

```yaml target-contract
kind: commitment
id: COM-004
class: important-reviewed
provenance: Absent focused tests and automated share-authority protection
statement: One focused Knowledge contract module and matching canonical-repository, dev-only workflow must detect missing required grants through the public MCPServer live registry and validate every marked canonical payload through production validation and the real store, with filters covering root pytest configuration and the complete Knowledge runtime import closure.
```

```yaml target-contract
kind: outcome
id: OUT-001
title: Enforced Knowledge source lifecycle contract
promise: A user can enter through kb-ingest and rely on an authorized role and handbook whose registration and intentional-deletion contract is automatically checked against shipped Knowledge boundaries on dev.
acceptance:
  - Every role and entry interface acknowledges register/delete, operation output is representable, and the agent declaration contains both live tools by containment.
  - Handbook replaces the invalid config-only fence and documents registration, exclusion, purge results, allowlist-owned availability, and full marked mappings with nested config.
  - Every marked fence uses canonical object metadata, passes strict-false SourceRegistration validation, and registers through an ensured store; current markers are required by containment and mismatch is rejected.
  - The explicitly `@pytest.mark.asyncio` focused test proves grants against the public async MCPServer registry and payload contracts without unrelated registries or broad ecosystem-test dependency.
  - "A valid path-filtered workflow is configured only for dev-targeting PRs and dev pushes in `maba-pag/owlbear` across authority, test, pytest configuration, dependency, and complete Knowledge runtime inputs, without executable downstream or consumer-main copies; it has top-level empty permissions, job-level contents read, a 15-minute timeout, SHA-pinned actions, and setup-uv cache enabled with `cache-dependency-glob: uv.lock`."
commitments:
  - COM-001
  - COM-002
  - COM-003
  - COM-004
dependencies: []
```
