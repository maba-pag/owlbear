# Design: Memory Universal Recall and Review Clarity

Status: complete candidate pending gates and approval

## Current Ownership

Recall/save/scope/rename/drift currently use active `AgentCatalog`; creation is unscoped pending; seven source-authority owners describe behavior; `MemoryTab.tsx` owns scope filtering/display. Three pending unscoped records contain obsolete catalog/schema advice but remain under regular curator ownership.

## Architecture

### Memory-derived identity

- Add private `_recognized_agent_names(entries)` in `serve/memory-mcp/src/owlbear_memory_mcp/tools.py`. It returns sorted exact nonblank, non-`*` source/scope names from non-deleted entries. Pending/disputed/stale count; deleted does not. Recognition has no reserved host/product-name denylist, grants no exclusive content, and is not authentication. Existing `copilot` provenance is therefore recognized; exact `GitHub Copilot` or `Agent` names are recognized only if observed.
- In `serve/memory-mcp/src/owlbear_memory_mcp/server.py`, give only the registered recall tool a dedicated optional strict-string-or-exact-numeric-0-or-null annotation with default `None`; omission equals explicit null. Explicitly reject bool, nonzero numbers, arrays, and objects. Do not relax or reuse the shared `_Agent` alias: save source, rename old/new, delete-agent, and assessment task validation retain their existing schemas.
- Recognized strings use current named-or-contains-`*` selection and block output without guidance. Other accepted values use contains-`*` selection and exact guidance: `This recall_memory caller is not a known agent. Known agents: {known_agents}. This caller is read-only and must not write memories. It therefore receives only memories scoped to all agents (*).`
- Sort/join names by `, ` or use `none discovered`; no trailing newline. Return guidance alone with no blocks, otherwise guidance + `\n\n` + current `\n\n`-joined blocks.

### Intake and curation

- Save accepts every nonblank source string including `*`, creates existing pending/unscoped, and performs no recognition check. Wildcard provenance does not establish identity.
- Curators classify content first. Low value is deleted. Keep-worthy unfamiliar named sources require exact corroboration from another reviewed non-pending memory or readable local definition; candidate text is insufficient. Periodic mode silently leaves identity-only uncertainty pending; manual mode may use user confirmation. Every named target uses the same evidence; `*` target is only for universal content. Identity evidence is not confidence.
- `w-mem-curation` owns the pending procedure. `memory-curator.agent.md` preserves conflict and ordinary-uncertainty reporting but excludes identity-only deferrals from `{K}`, entry-ID reporting, and conflict summaries.
- `memory-audit.prompt.md` retains its prohibition on pending promotion. Before a manual `curated`/`approved` salvage or maintenance edit changes named scope, require exact corroboration from another reviewed non-pending memory, readable local `.agent.md`, or explicit user confirmation. Candidate text cannot self-prove and identity evidence does not alter confidence. Artifact assertions pin this rescoping rule and the pending handoff.
- Literal `*` source is anonymous provenance: waive source corroboration, preserve immutable `*`, assess content normally, and retain target-scope evidence rules.
- Guidance is deterrence, not authorization. Compliant unknown onboarding is pre-existing memory or curator scope assignment; self-save is a possible side effect.
- Leave pending entries `aaddc796-275d-45d4-bfa6-643f1c0d8569`, `e7469ca6-9041-44d9-8692-04f1206376cd`, and `58aedea0-1607-424d-99cf-ba51c71fb669` for ordinary memory curation. They are unscoped and not recallable, but their source names remain recognized while non-deleted. Preserve `f8b6438e-1926-4d69-b9d2-daf8b18d9175`, whose `assess_memories` exposure claim remains valid. Delivery receives no `delete_memory` authority and does not edit `.owlbear/memory`.

### Scope and lifecycle

- Delete `serve/memory-mcp/src/owlbear_memory_mcp/agents.py`; remove `AgentCatalog` from server context and tools. Put recall-only recognition in `tools.py`, its direct behavioral owner.
- Replace `_require_scope` with private syntax validation in `tools.py`: scope/filter values must be nonblank strings; `*`, named values, and mixed arrays are accepted. Promotion/non-pending entries still require non-empty scope.
- Save retains the existing nonblank string schema and accepts `*`.
- Rename requires distinct nonblank non-`*` old/new and may create an unseen target. Delete-agent rejects blank and `*`.
- Delete-agent retains current scope removal and hard deletion of entries left without an audience. Retired recognition survives only through remaining non-deleted occurrences.
- Delete `.owlbear/scripts/validate_memory_agents.py` and the `validate-memory-agents` pre-commit hook. Remove catalog-specific assertions from `tests/test_memory_agent_identity.py` and repurpose that file for memory-derived identity, save, rename, delete, and syntax behavior. Do not replace semantic drift validation.
- Replace `tests/test_recall_memory.py::TestFromAC_WildcardAgentBlock::test_wildcard_agent_raises_tool_error` with guided universal-only fallback coverage for `agent="*"`; retain direct recall coverage elsewhere in that suite.
- Run `uv run py-index` after deleting the module so advisory `.owlbear/py-index.md` no longer inventories `AgentCatalog`; the generated index is not source authority.

### Authority ownership

Update exactly: `serve/memory-mcp/README.md`, `share/skills/h-mcp-memory/SKILL.md`, `share/skills/h-memory-structure/SKILL.md`, `share/skills/w-mem-curation/SKILL.md`, `share/instructions/owlbear-system.instructions.md`, `share/agents/memory-curator.agent.md`, and `share/prompts/memory-audit.prompt.md`. The workflow skill is pending-candidate procedural authority; the agent updates its boundary/output contract; the prompt updates manual curated/approved rescoping while preserving pending handoff.

Add `test_memory_curator_identity_deferral_reporting_split` and `test_memory_audit_rescoping_requires_corroborated_agent_names` to `tests/test_agent_ecosystem_validation.py`. They read the workflow, agent, and prompt bytes and assert literal rules that identity-only deferrals stay pending without entering deferred counts/IDs/summaries, conflicts and ordinary uncertainty remain reported, manual named rescoping requires bounded corroboration, and pending promotion remains delegated. These artifact assertions, not structural validators alone, falsify the prose contracts.

### Cockpit

Use `mode:any`, `mode:all`, `mode:unscoped`, `agent:<name>`. Parse modes before names; preserve loaded-scope-derived options excluding `*`; match any, contains-`*`, exact empty, or named-or-contains-`*` excluding empty. Label empty Unscoped and contains-`*` All agents. Stored `mode:all` encodes as `agent:mode:all`. This projection intentionally includes loaded deleted scopes and excludes source-only recognition.

## Changed Interfaces

Recall schema/default/classification/output; dedicated recall annotation in `server.py`; identity owner and reserved-name policy; save/scope/rename/delete validation; curator and manual-review workflow/output; catalog/drift removal; generated index refresh; seven source-authority files; Cockpit filter/display. No persistence format, state transitions, recallable states, score, timestamps, purge, OCC, assessment exposure, shared non-recall server schema, backend filter, option-discovery source, pending-review ownership, or Delivery tool-authority change.

## Planning Scopes

- `SCOPE-001` binds `OUT-001`: `serve/memory-mcp/src/owlbear_memory_mcp/server.py` dedicated recall-only annotation/default preserving shared `_Agent`; `tools.py` identity/syntax helpers and exact output; open string intake; catalog/script/hook deletion; generated Python index refresh; rename/delete safeguards; wildcard-rejection test replacement; curator and manual-review rules; seven source-authority files; reporting/rescoping artifact assertions; direct behavior tests; and new live `serve/memory-mcp/tests/test_server.py` using `mcp.Client(mcp)` in a temporary workspace. Obsolete pending memory remains outside Delivery under regular curation.
- `SCOPE-002` binds `OUT-002`: `MemoryTab` modes/options/reset/predicates/labels and new `serve/cockpit/web/src/__tests__/MemoryTab.test.tsx` result/collision/composition/count/projection tests using fetch stubbing and bubbling PDS `change` events.
- Outcomes are domain-local. Authority is empty pre-checkpoint.

## Migration And Failure Semantics

No persistence migration. Existing non-deleted source/scope initializes recognition, including host/product-style names and pending source names. Omitted and explicit fallback succeeds universal-only. Any nonblank source saves pending; wildcard remains anonymous. Active definitions without memory are unknown. Retirement may remove orphaned records and recognition; rename rewrites identity atomically. Known block formatting and shared non-recall server validation remain unchanged. Obsolete pending records remain unscoped/non-recallable until ordinary curation and do not block Delivery completion.

## Tradeoffs And Known Limits

- Recognition is unauthenticated/self-registering; pending typos and host/product-style provenance enter guidance until deletion.
- Guidance may delay onboarding; identity-only deferred keepers may be reprocessed silently.
- `Known agents` is an approved label for observed memory names, not verified principals.
- Anonymous wildcard provenance can be promoted without named attribution.
- Cockpit filters loaded scopes, not recognized identities.
- Retirement history/recognition is conditional on surviving records.
- Three obsolete pending records remain for regular curation. They are not recallable but keep their source names recognized.

## Delivery Proof

- Add and run `serve/memory-mcp/tests/test_server.py` for live schema/tool calls, including unchanged shared `_Agent` consumer validation.
- Run focused direct tests including repurposed `tests/test_memory_agent_identity.py`, updated wildcard behavior in `tests/test_recall_memory.py`, lifecycle/voting/assessment/review-contract suites, and `tests/test_agent_ecosystem_validation.py`.
- Assert absence of catalog module/script/hook; run `uv run py-index`, `uv run python .owlbear/scripts/validate_agents.py`, and `uv run python .owlbear/scripts/validate_skills.py`.
- Add and run `serve/cockpit/web/src/__tests__/MemoryTab.test.tsx`; run full `npm test` and `npm run build` from `serve/cockpit/web`.

## Pre-Implementation Baselines

- `uv run pytest tests/test_recall_memory.py tests/test_memory_agent_identity.py tests/test_memory_state_machine.py tests/test_memory_voting_integration.py tests/test_assess_memories.py tests/test_memory_review_contract.py tests/test_agent_ecosystem_validation.py -q --tb=short`
- `uv run python .owlbear/scripts/validate_agents.py`
- `uv run python .owlbear/scripts/validate_skills.py`
- `npm test` and `npm run build` from `serve/cockpit/web`.

## Review Resolution

User chose memory-derived recognition, omitted-agent fallback, all nonblank string intake including wildcard, no runtime definition authority or reserved host/product denylist, exact guidance, accepted onboarding/typo risk, content-first corroborated curation, anonymous wildcard provenance, identity-only silent defer with other reporting preserved, corroborated named scopes in pending and manual-review paths, unseen rename, wildcard lifecycle rejection, orphan deletion, conditional retirement recognition, and regular rather than Delivery-owned curation of obsolete pending memory. Reviews established a dedicated recall-only server annotation, preservation of shared `_Agent`, Cockpit divergence, exact separator, live MCP proof, exhaustive seven-file source-authority ownership, `tools.py` helper ownership, artifact assertions for prose behavior, generated-index refresh, explicit wildcard-test replacement, and no expansion of Builder memory authority.
