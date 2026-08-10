# Memory Universal Recall and Review Clarity

Status: complete candidate pending gates and approval

## Problem

`recall_memory` rejects callers outside locally discovered active agents, although local `.agent.md` discovery cannot reliably enumerate imported agents. Its schema also rejects omitted `agent`, host `null`, and numeric `0`. Cockpit separately conflates no filter, universal scope, and empty unscoped candidates.

## Product Promise

- Recognition comes only from memory data: exact nonblank, non-`*` names in `source_agent` or `scope_agents` on any non-deleted entry. Definitions are curator evidence, not runtime authority.
- Recognition has no reserved host/product-name denylist. Existing provenance such as `copilot`, and future exact names such as `GitHub Copilot` or `Agent`, are ordinary recognized names only when observed in qualifying memory data. The previous explicit host-product rejection is superseded.
- Recognized strings receive current named-or-universal recall without guidance. Unknown strings become recognized after a pending save or assigned scope unless all non-deleted occurrences disappear.
- Omitted `agent`, explicit `null`, numeric `0`, blank/whitespace strings, `*`, and unknown strings use unknown-caller recall and receive only recallable entries whose scope contains `*`.
- Every unknown response starts with these exact UTF-8 bytes, without a trailing newline:

```text
This recall_memory caller is not a known agent. Known agents: {known_agents}. This caller is read-only and must not write memories. It therefore receives only memories scoped to all agents (*).
```

- `{known_agents}` is the observed recognized-name set sorted lexicographically and joined by `, `; use `none discovered` when empty. The user-approved label remains `Known agents` although pending names are unreviewed.
- With no selected blocks, including zero matches and `limit=0`, return guidance alone. With blocks, return guidance, `\n\n`, then the current `\n\n`-joined blocks. Guidance is not a memory or limit slot.
- `save_memory` accepts every nonblank string source, including `*`, without recognition checks and creates the existing unscoped pending candidate. Null, numeric `0`, blank/whitespace, and non-string values cannot save. Wildcard provenance is excluded from recognition.
- Guidance deliberately discourages unknown writes although unknown named callers and `*` can submit pending candidates. The enforcement mismatch and delayed onboarding are accepted. Compliant onboarding is pre-existing memory or curator assignment to a corroborated agent; first-save recognition is a possible side effect, not the promised route.
- Curators classify content first. Low-value candidates are deleted normally. A keep-worthy unfamiliar named source requires the exact name on another reviewed non-pending memory or a readable local `.agent.md`; candidate text cannot self-prove. Periodic mode silently leaves identity-only uncertainty pending and may reconsider it each cycle. Identity-only deferrals are excluded from the periodic verdict's deferred count, entry-ID list, and conflict summary; conflicts and other uncertainty retain current reporting. Manual mode may use explicit user confirmation. Identity evidence is never memory confidence.
- Literal `*` source is anonymous provenance: waive source-identity corroboration, assess content normally, preserve immutable `*` provenance, and retain all target-scope evidence rules. It never establishes a recognized name.
- Every named scope target requires the same corroboration. Otherwise choose a corroborated target, use `*` only for genuinely universal content, or leave pending. Manual memory review applies this rule before rescoping curated or approved entries and still delegates pending promotion to `memory-curator`.
- Rename explicitly authorizes an unseen target. Old/new must be distinct nonblank non-`*` names. Delete-agent rejects `*`; universal scope changes only through per-entry curation/deletion.
- Retirement retains current behavior: remove the named scope and hard-delete entries left without an audience. A retired source remains recognized only while another non-deleted occurrence survives; no archival state is added.
- Recall rejects booleans, nonzero numbers, arrays, and objects.
- Cockpit provides `Any agent` for no filter/default/reset, `All agents` for scope containing `*`, `Unscoped` for exact empty scope, and loaded-scope-derived named options for named-or-universal matching excluding empty. These filters are not the recall recognition directory; source-only recognized names may be absent and loaded deleted scopes may appear.
- Empty displays `Unscoped`; any scope containing `*` displays `All agents`; named-only displays names. Encoded filter values cannot collide with stored names such as `mode:all`.
- Unscoped creation, scope-driven promotion, recallable states, scoring, assessment, timestamps, purge, and OCC remain unchanged.

## Workflows

1. Recognized names receive named-or-universal recall without guidance; omitted or unknown callers receive guidance plus universal blocks or guidance alone.
2. Any nonblank-string writer submits pending/unscoped; non-`*` provenance enters recognition and `*` remains anonymous.
3. Curators classify content, corroborate named source/targets, apply the wildcard exception, then promote/rescope, silently defer identity-only uncertainty, report other uncertainty, or delete.
4. Manual memory review corroborates any named target before rescoping curated or approved entries and leaves pending promotion to `memory-curator`.
5. Rename rewrites source/scope names atomically; retirement removes scopes/orphans with conditional historical recognition.
6. Cockpit filters loaded scope data independently from recall recognition.

## Preserved Behavior

Recognized selection and block formatting; pending unscoped creation; scope-driven promotion; ordinary source immutability; conflict and ordinary-uncertainty reporting; current orphan deletion; recallable states; ranking; assessment; timestamps; purge; OCC; manual-review pending handoff; and loaded-scope Cockpit option discovery remain unchanged except where explicitly listed.

## Accepted Exclusions And Risks

- No runtime definition scan, imported-agent discovery claim, authentication, reserved host-name rejection, result-based identity inference, case folding, non-string provenance, placeholder, separate registry, defer marker, archival state, persistence migration, backend Cockpit filter, timestamp redesign, or recognition-backed Cockpit options.
- Unknown guidance is normative, not enforced authorization. Delayed onboarding is accepted.
- Pending typos can suppress guidance and enter `Known agents` until deletion; curation is the only correction path.
- Identity-only deferrals are silent and may repeat. Manual curation and ordinary pending views are incidental re-entry. Other deferrals remain reported.
- Caller names are unauthenticated; candidate text cannot corroborate identity.
- Retirement can hard-delete orphan-only history and recognition; surviving provenance remains recognized.
- Anonymous wildcard provenance can be promoted without named attribution.
- Three pending records containing obsolete `AgentCatalog` or recall-schema advice remain for ordinary memory curation; they are unscoped and not recallable, but their source names still participate in recognition until curated. The adjacent `assess_memories` exposure record remains valid.

## Success Evidence

- Identity tests cover both fields, all states, deleted/blank/`*` exclusion, existing `copilot` recognition, no reserved-name rejection, first save, last occurrence, retirement, rename, and sorting.
- Recall tests cover preserved recognized bytes, omitted/explicit fallback, wildcard fallback replacing the current wildcard-rejection assertion, universal-only selection, exact guidance/separator with matches, guidance alone for empty/`limit=0`, and no named leakage.
- `serve/memory-mcp/tests/test_server.py` uses `mcp.Client(mcp)` in a temporary OwlBear workspace to prove the dedicated recall-only optional nullable schema and calls accept omitted `agent`, strings, JSON null, and exact numeric `0`, while rejecting booleans, nonzero numbers, arrays, and objects; shared `_Agent` consumers retain their existing schemas.
- Save tests prove every nonblank string including `*` creates unscoped pending; wildcard grants no identity.
- Curator authority tests pin content-first handling, bounded source/target corroboration, anonymous wildcard treatment, silent identity-only defer excluded from reports, preserved other defer reporting, manual confirmation, confidence separation, and corroborated manual rescoping with pending handoff.
- Lifecycle tests cover unseen rename, wildcard rejection in rename/delete, orphan deletion, and conditional recognition.
- Active-catalog runtime wiring, catalog module, drift script, pre-commit hook, and obsolete catalog assertions are absent; `uv run py-index` removes generated catalog references.
- `serve/cockpit/web/src/__tests__/MemoryTab.test.tsx` covers modes/reset, mixed universal arrays, labels/sets, composition/count, deleted/source-only projection divergence, and `mode:all` collision.
- Exactly seven affected source-authority files are updated: `serve/memory-mcp/README.md`, `share/skills/h-mcp-memory/SKILL.md`, `share/skills/h-memory-structure/SKILL.md`, `share/skills/w-mem-curation/SKILL.md`, `share/instructions/owlbear-system.instructions.md`, `share/agents/memory-curator.agent.md`, and `share/prompts/memory-audit.prompt.md`.
- Focused Python tests, agent/skill validators, full frontend tests, and frontend build pass.

## Technically Done But Wrong

Runtime definition authority; placeholders; counting deleted/blank/`*`; retaining the host-product denylist; weakening shared `_Agent` validation to implement recall fallback; non-string save provenance; treating omitted `agent` as an error; named leakage; omitted guidance/separator; leaving the wildcard-rejection test unchanged; candidate self-proof; identity as confidence; reporting identity-only deferrals; suppressing other deferred reporting; uncorroborated named scope; manual rescoping without corroboration; promoting pending from memory audit; rejecting keep-worthy wildcard provenance solely for anonymity; claiming Cockpit filters are recognition; preserving all retirement history; wildcard lifecycle operations; retaining drift validation; expanding Builder authority for memory cleanup; editing memory files directly; leaving the generated Python index stale; proving schema only by direct coroutine calls; or changing timestamps.

## Confirmed Decisions

- Recognition is exact non-`*` source/scope names from any non-deleted entry, without a reserved host/product-name denylist.
- Omitted `agent` equals explicit `null` fallback through a dedicated recall-only server annotation; shared `_Agent` validation remains unchanged.
- Save accepts every nonblank string including `*`; wildcard grants no identity and is curated anonymously.
- Definitions are curator evidence only. Named keepers/targets use bounded corroboration; identity-only periodic deferrals are silent while other deferrals remain reported; manual confirmation is allowed.
- Manual review corroborates named targets before rescoping curated/approved entries and retains its pending handoff.
- Rename permits unseen non-wildcard targets; rename/delete reject wildcard.
- Retirement preserves orphan deletion; historical recognition is conditional on surviving records.
- Warning/enforcement, pending-typo, repeated-deferral, delayed-onboarding, anonymous-provenance, stale-pending-memory, and Cockpit projection divergence are accepted.
- Active-catalog runtime validation, drift script, and hook are removed; the generated Python index is refreshed.
- Obsolete pending memory is left for regular curation rather than widening Delivery authority.

## Superseded Decisions

Active `AgentCatalog` runtime membership, explicit host-product identity rejection, permanent aliases, approval timestamp changes, required scope at creation, and Delivery-owned cleanup of obsolete pending memory are superseded or withdrawn.

## Delivery Contract

```yaml target-contract
kind: commitment
id: COM-001
class: dealbreaker
provenance: User-confirmed memory-derived recognition and fallback
statement: recall_memory must recognize exact non-* source or scope names from any non-deleted entry without a reserved host/product-name denylist, preserve named-or-universal recall for recognized names, and accept omitted agent, null, numeric 0, blank or whitespace, *, and unrecognized strings as guided universal-only callers with exact guidance and separator; other JSON values remain invalid.
```

```yaml target-contract
kind: commitment
id: COM-002
class: protected-request
provenance: Existing lifecycle and user-confirmed intake/lifecycle
statement: Except for COM-001, every-nonblank-string source intake, anonymous wildcard curation, identity-only silent defer, removal of active-agent runtime validation/drift, generated-index refresh, confirmed curator and manual-review workflow, confirmed rename/retirement safeguards, and COM-003/COM-004 Cockpit changes, unscoped creation, promotion, conflict and ordinary-uncertainty reporting, recallable states, ranking, assessment, timestamps, purge, concurrency, ordinary provenance, shared non-recall server validation, and scope-option discovery must remain unchanged.
```

```yaml target-contract
kind: commitment
id: COM-003
class: dealbreaker
provenance: User-confirmed Cockpit semantics
statement: Cockpit must provide Any agent for no filter and initial/reset, All agents for scope containing *, Unscoped for exact empty scope, and loaded-scope-derived named options for named-or-universal applicability excluding empty, with collision-proof identities and existing composition.
```

```yaml target-contract
kind: commitment
id: COM-004
class: important-reviewed
provenance: Empty versus universal scope
statement: Cockpit must display empty scope as Unscoped and every scope containing * as All agents without stored-data rewriting or a backend filter endpoint.
```

```yaml target-contract
kind: outcome
id: OUT-001
title: Memory-derived recall identity with open candidate intake
promise: Existing memory establishes recognized recall names, omitted and unknown callers receive universal guidance, and any nonblank-string writer can submit a quarantined candidate for corroborated or anonymous curation.
acceptance:
  - Exact non-* source or scope names on any non-deleted entry, including host/product-style names, receive named-or-universal output without guidance; deleted-only names and * do not.
  - Omitted agent and explicit fallback inputs receive exact guidance alone for zero matches and limit=0 or exact guidance plus two newlines plus current blocks for matches; only entries containing * are returned and other JSON fails.
  - Every nonblank string source including * saves unscoped pending; blank/non-string fails and wildcard grants no identity.
  - Curator and manual-review authority enforce content-first handling, bounded named source/target corroboration, anonymous wildcard handling, identity-only silent defer without changing other deferred reporting, manual confirmation, confidence separation, corroborated manual rescoping, and pending handoff, with artifact assertions that falsify the reporting and rescoping rules.
  - Rename/retirement/wildcard safeguards and catalog/drift removal are tested; the seven enumerated source-authority files document the boundary and the generated Python index is refreshed.
commitments:
  - COM-001
  - COM-002
dependencies: []
```

```yaml target-contract
kind: outcome
id: OUT-002
title: Unambiguous Cockpit memory scope filtering
promise: A human distinguishes no restriction, universal scope, unscoped candidates, and loaded named scope applicability without mistaking the filter for recall identity.
acceptance:
  - Any agent is initial/reset; All agents matches scope containing *; Unscoped matches exact empty.
  - Named options remain loaded-scope-derived and match named or *, excluding empty.
  - Empty displays Unscoped; scope containing * displays All agents; named-only retains names.
  - Mode values cannot collide with stored name mode:all; filters compose with state/category/text/count and projection divergence is explicit.
commitments:
  - COM-002
  - COM-003
  - COM-004
dependencies: []
```
