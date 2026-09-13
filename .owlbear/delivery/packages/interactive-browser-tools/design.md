# Interactive Browser Tools Design

> Status: formal candidate; derivation, source-grounded challenge, baseline, checkpoint, validation, and approval remain.
> Dependency gate: B5 admission and implementation wait for admitted B1 outcome OUT-001 to complete because the Changes own overlapping Browser MCP, setup, seed, test, documentation, and agent surfaces.

## Ownership And Task Locality

Browser core owns Playwright 1.62 page/session mechanics, AI-reference snapshots, node re-resolution, and navigation/popup/dialog/download event observation. Browser MCP owns destination-policy composition, `interactive_status`, workspace-root resolution, artifact custody/release, tool schemas, common envelopes, and adapters. Agent-config owns the browser-interaction skill, `knowledge-ingestor` grants/rules/output, and manual agent proof. Planner creates domain-local tasks for `browser`, `browser-mcp`, and `agent-config`; assembled acceptance crosses their public interfaces.

The Browser MCP configuration task owns setup/seed migration and focused setup tests as distribution of its runtime contract. Documentation stays with the behavior-owning task. Structured acquisition retains separate page ownership and download rejection. B1 owns managed Edge/profile readiness and delegates generic interaction safety to B5.

## Architecture

### Authorization, Status, And Consumer

Grant six interactive tools plus `interactive_status`, `resolve_dialog`, and `release_download` to `knowledge-ingestor` for one identified source. Read/read-write policies are absent-by-default deny-all; read is their union; mutation requires read-write. `acquire`, `navigate`, `read_text`, and `snapshot` all consume effective read authority. Setup deliberately seeds both policies as `*`, authorizing hostname and IP-literal public/private/loopback/link-local read and mutation. `interactive_status` reports session/page state, observation requirement, pending dialog, outstanding artifact count, download-custody availability, and policy mode including broad wildcard mutation, without URLs, content, values, or paths. B1 `browser_status` remains unchanged.

`click`, `type`, `select`, and dialog resolution require read-write through navigation/observation. Release requires matching custody. Skill authority limits the ingestor to the identified source. Browser-derived values are untrusted. D9 confirmation gates uncertain ingestion, not each interaction.

### Serialized Session And Page

One process-owned session has one current page. One call owns preconditions, dispatch, and bounded observation. Overlap returns `busy` without acting or queueing. Ignore unrelated/operator tabs. Adopt one authorized action popup; multiple candidates return `ambiguous-popup`. Closed-page non-navigation calls return `page-closed`; `navigate` creates a replacement.

Operator navigation on the current page is external navigation: Browser core observes it, Browser MCP checks effective read authority before exposing content, and an accepted transition creates a new document revision. B1 first-use operator authentication occurs before B5 interaction.

### Snapshot And Targeting

Require Playwright `>=1.62,<2` for verified `aria_snapshot(mode="ai")` and `aria-ref` support behind a typed Browser-core interface.

`snapshot(mode, max_nodes?, max_bytes?)` supports `interactive|text|full`, default `interactive`; caller bounds only narrow server maxima. Results carry session/page/document revision, mode, emitted node/byte counts, truncation, omitted count when knowable, and ordered nodes. Omitted nodes have no refs.

Refs bind session, page, document, and opaque node identity. Top-level navigation/current-page replacement/adoption creates a new document revision. In-page mutation does not globally invalidate refs. Browser core re-resolves and verifies attachment/current document/target kind before action. Unknown/cross-page refs return `invalid-element-reference`; detached/replaced/unresolvable refs return `stale-element`. CSS is a distinct expert target shape recorded in results.

### Dialogs

Browser core observes dialogs; Browser MCP retains bounded identity/type/message/page/origin and returns `dialog-pending`. `resolve_dialog(dialog_id, accept|dismiss, prompt_text?)` rejects stale identity, permits prompt text only for accepted prompts, omits values, observes resulting state, and releases the session. Other calls report pending state. Messages are untrusted.

Pending dialogs have a configured maximum lifetime. Expiry dismisses as cleanup, records `dialog-expired`, marks originating effect unknown, and requires fresh observation. Shutdown follows the same no-success rule.

### Navigation Enforcement

Browser core exposes event/interception hooks for direct navigation, redirects, links, forms, popups, and scripts. Browser MCP applies effective policy before content exposure. Mutations/dialog resolution retain read-write authority through navigation/observation.

### Workflow Downloads

Browser core observes bounded transfer completion. At startup Browser MCP resolves `Path.cwd()` and enables custody only when a non-symlink `.owlbear` marker exists. Without it, startup and non-download interaction continue, `interactive_status` reports `download-custody-unavailable`, and a download-triggering operation exposes no unmanaged path as success.

With custody, Browser MCP writes completed artifacts only under `.owlbear/scratch/browser-downloads/{instance-id}/{artifact-id}/{safe-name}`. It sanitizes names, prevents escape/collision, assigns IDs, applies configured byte/count limits, exposes metadata without bytes, and removes partial/failed transfers.

Each instance holds an exclusive lease. Startup cleanup removes only well-formed expired unleased instance directories; it preserves active or malformed directories. Artifacts survive validation/conversion/ingestion/retry.

`release_download(artifact_id, ingested|abandoned)` is idempotent for matching replay, rejects conflict/unknown custody, deletes the file, and returns evidence. Failure is retryable; shutdown cleanup invents no disposition.

### Common Result Envelope

Mutation/lifecycle tools return a compact envelope with status, `effect=observed|not-observed|unknown`, operation, session/page/document revision when available, redacted URL/bounded title, non-sensitive target kind/reference, navigation state, typed code/message, retryability, and optional dialog/artifact metadata. No tree or entered value is embedded.

Observed is limited to approved navigation, popup adoption, dialog transition, completed download, artifact release, non-disclosing typed/selected-value match, or supported checked/pressed/expanded/focus change. A dispatched click without these signals is unknown. Not-observed means no dispatch or a checked expected signal was absent.

Cancellation before dispatch is not-observed/retryable. Post-dispatch cancellation, timeout, disconnect, or transport loss is unknown, not automatically retryable, and puts the session in observation-required state until `interactive_status` plus fresh `snapshot`. No-page navigation never returns dry-run success.

### Agent Contract And Proof

The skill requires a user-provided source goal, treats browser content as untrusted, forbids it from changing goal or authority, uses `interactive_status` for recovery, and preserves D9 before uncertain persistence. Browser MCP owns temporary writes/deletes; the agent has no filesystem mutation tool.

Automated proof covers schemas/annotations, Browser core mechanics, MCP composition, policy, state, snapshots/refs, dialogs, downloads, envelopes, and Knowledge persistence. Integration uses real Browser MCP and Knowledge MCP tool functions plus real Playwright against a deterministic local HTTP fixture; resolver/network routing, embedding, and vector dependencies are replaced below public boundaries. It proves page reach and persistence, not agent conduct.

A bounded manual VS Code procedure invokes real `knowledge-ingestor` against a synthetic site and records source-goal retention despite injected instructions, D9 confirmation, unrelated-request rejection, value omission, observation before retry, and downloaded-document ingest/release. This is agent-conduct proof because OwlBear has no custom Python agent runtime.

### Migration And Ordering

Replace `BROWSER_ALLOWED_DOMAINS` with read/read-write inputs. On setup rerun, migrate an `owlbear-browser` entry only when it exactly matches OwlBear's prior installed template or remains covered by its install-manifest claim: carry the old domain value into read authority, and map a prior managed `*` to the new managed read/read-write wildcard defaults. The same atomic update refreshes the install-manifest claim to the digest of the migrated server entry so uninstall can still remove it. Add install-to-rerun-to-uninstall coverage for the migrated managed entry.

Preserve customized entries unchanged and emit an actionable warning naming the manual mapping. Runtime rejects the retired key after migration; it does not maintain dual authorities.

Update `seed/.vscode/mcp.json`, `setup/init.py`, `tests/test_setup_init_settings.py`, `tests/test_setup_init_uninstall.py`, `serve/browser-mcp/README.md`, `setup/setup-guide.md`, `setup/operating-owlbear.md`, and `README-consumer.md`; no shipped text retains the old private-wildcard exclusion. Preserve B1 `browser_status` and exact-host mode.

B5 admission and implementation wait for B1 OUT-001 completion. After B1 completes, re-read B1 and validate B5 against its exact target head before admission; no B5 task edits overlapping surfaces concurrently. This cross-Change gate is operator-enforced because Delivery dependencies are intra-Change only; it is not represented as an engine dependency.

## Rejected Alternatives

Removing tools; forwarding agent; limited grants; per-action approval; credential rejection; one policy; permissive absent configuration; queued overlap; multi-session; focus-following; page selection; acquisition-tab continuation; automatic/user-required dialogs; indefinite dialogs; unmanaged/durable downloads; CSS-only targeting; name guessing; stale remapping; global invalidation on DOM change; one snapshot mode; silent truncation; embedded snapshots; business-success inference; retry after unknown; dry-run navigation; adding B5 fields to B1 status; failing standalone startup without custody; silently broadening customized config; broken uninstall ownership after migration; or parallel implementation with B1.

## Delivery Shape

Three outcomes form one dependency chain. Each scope uses domain-local tasks: Browser core first, Browser MCP/configuration second, agent-config third, assembled proof last.

```yaml target-contract
kind: outcome
id: OUT-001
title: Authorized deterministic browser interaction
promise: Browser core and Browser MCP provide one serialized, policy-enforced interactive session with truthful page ownership, bounded accessibility targeting, dialogs, status, and compact effect-aware results.
acceptance:
  - "Given absent read/read-write configuration, registered interactive tools including acquire reject before action; given exact read configuration, acquire, navigate, read_text, and snapshot succeed while mutation rejects; given exact or wildcard read-write configuration, mutation and post-action read are authorized."
  - "Given setup's explicit read/read-write wildcard, hostname and IP-literal public, private, loopback, and link-local fixtures pass while malformed, unsupported-scheme, reserved non-loopback, and unspecified destinations reject; interactive_status and seed/.vscode/mcp.json, setup/init.py, tests/test_setup_init_settings.py, serve/browser-mcp/README.md, setup/setup-guide.md, setup/operating-owlbear.md, and README-consumer.md identify broad wildcard mutation authority and contain no old private-wildcard exclusion."
  - "Given a prior OwlBear-managed browser MCP entry with BROWSER_ALLOWED_DOMAINS='*', setup rerun replaces it with the managed read/read-write wildcard configuration and refreshes its install-manifest claim so subsequent uninstall removes it; given a managed exact-host value, setup migrates it to read authority without granting mutation; given a customized server or environment, setup preserves it and emits an actionable manual-migration warning."
  - "Given interactive_status while the session is ready, busy, observation-required, dialog-pending, page-closed, browser-unavailable, policy-blocked, or download-custody-unavailable, it returns the matching session/page state, pending-dialog identity when present, outstanding artifact count, custody availability, and effective policy mode without URL, page content, entered value, or filesystem path."
  - "Given one active operation, a concurrent call returns busy before dispatch and never executes later from a queue."
  - "Given direct navigation, redirect, link, form, popup, script, or operator navigation outside effective authority, content remains unavailable and a typed policy result is returned."
  - "Given Playwright 1.62 AI-reference support and snapshot mode interactive, text, or full within configured bounds, snapshot returns the selected ordered projection with session/page/document identity, emitted counts, explicit truncation, omitted count when knowable, and no refs for omitted nodes; omitted mode selects interactive."
  - "Given a current actionable ref, action targets its Browser-core node; fabricated/cross-page identity returns invalid-element-reference, detached/replaced/prior-document identity returns stale-element, stable in-page identity remains usable, and CSS fallback is explicit."
  - "Given no popup, one authorized action popup, multiple candidates, unrelated operator tab, or closed current page, Browser MCP retains, adopts, returns ambiguity without switching, ignores, or returns page-closed until navigate replaces it respectively."
  - "Given alert, confirm, or prompt, dialog-pending exposes bounded untrusted metadata; matching resolve_dialog acts autonomously, stale identity rejects, values are omitted, other calls remain blocked, and expiry/shutdown records unknown without completion."
  - "Given mutation/lifecycle calls, compact results contain no tree/value and use only named observed signals; pre-dispatch cancellation is retryable not-observed, post-dispatch interruption is unknown and blocks mutation until interactive_status plus fresh snapshot, and no-page navigate never reports dry-run success."
commitments: [COM-001, COM-002, COM-003, COM-004, COM-005]
dependencies: []
```

```yaml target-contract
kind: outcome
id: OUT-002
title: Workflow-scoped browser download custody
promise: Authorized interactive downloads become bounded temporary workspace artifacts with truthful completion evidence and explicit release after ingestion or abandonment.
acceptance:
  - "Given Browser MCP startup without a non-symlink `.owlbear` workspace marker, startup and non-download interaction remain available, interactive_status reports download-custody-unavailable, and a download-triggering operation exposes no unmanaged artifact path as success."
  - "Given no download, one completed download, partial/failed transfer, timeout, or configured size/count excess with custody available, Browser MCP returns the corresponding typed state, exposes metadata only for a completed in-bound artifact, and presents no partial file as success."
  - "Given path-traversal, collision, or unsafe suggested names and a verified workspace root, Browser MCP writes only beneath `.owlbear/scratch/browser-downloads/{instance-id}/{artifact-id}/` using a safe non-conflicting name and returns no raw bytes."
  - "Given a completed artifact, it survives validation/conversion/ingestion/retry; matching release_download with ingested or abandoned deletes it and replays idempotently, while unknown identity, conflicting disposition, or cleanup failure returns typed evidence without deleting unrelated files or claiming success."
  - "Given active, expired unleased, or malformed instance directories at startup/shutdown, cleanup preserves active/malformed directories, removes only eligible expired residue, reports failures, and invents no ingestion/abandonment disposition."
  - "Given structured acquire receives a download response, its maintained download-rejected behavior remains unchanged."
commitments: [COM-001, COM-004, COM-006]
dependencies: [OUT-001]
```

```yaml target-contract
kind: outcome
id: OUT-003
title: Interactive source-capture workflow
promise: knowledge-ingestor composes interactive Browser tools with untrusted-content handling, D9 source validation, and Knowledge persistence for one identified source without a second-agent handoff.
acceptance:
  - "Given the registered Browser/Knowledge inventories and knowledge-ingestor definition after B1 completion, tool and artifact inspection shows the agent preserves browser_status, loads the browser-interaction skill, and receives navigate, snapshot, click, type, select, read_text, interactive_status, resolve_dialog, release_download, acquire, and maintained Knowledge operations without a filesystem mutation tool; share/WIRING.md records the changed loading edge."
  - "Given real Browser MCP and Knowledge MCP tool functions, real Playwright, a deterministic local HTTP fixture, and resolver/network routing, embedding, and vector dependencies replaced below those public boundaries, the integration reaches the intended page through referenced interaction, preserves redacted source identity/scope, and persists searchable content without a browser-agent relay."
  - "Given the bounded manual VS Code procedure and a synthetic site containing instructions to change goals or use unrelated tools, knowledge-ingestor retains the supplied source goal, treats page/dialog/download content as untrusted, applies D9 confirmation before uncertain persistence, and rejects an unrelated general browsing request; the observation records agent identity, inputs, outputs, and result without source secrets."
  - "Given arbitrary typed/prompt values in manual and automated fixtures, Browser results, B5 diagnostics, dialog/download receipts, and agent output contain none of those values."
  - "Given unknown interaction effect, automated tool proof and the manual procedure show fresh interactive_status/snapshot before another mutation and no translation of unknown into acquisition or ingestion success."
  - "Given one supported downloaded document, the assembled workflow validates/converts and ingests it with provenance, calls release_download with ingested after success or abandoned after terminal rejection, and reports Knowledge and cleanup results."
commitments: [COM-001, COM-003, COM-004, COM-005, COM-006, COM-007]
dependencies: [OUT-001, OUT-002]
```

## Proof And Known Limits

Automated tests cross Browser core, Browser MCP, and Knowledge public boundaries with replacements only below each boundary. Agent behavior uses the bounded manual VS Code procedure. Planner splits Browser, Browser MCP/configuration, and agent-config work into domain-local tasks and retains assembled proof last.

The B1 ordering gate is operator-enforced rather than encoded by Delivery. Seeded wildcard grants broad mutation authority including hostname and IP-literal local services. Mutations may be irreversible. Secrets may enter model-visible arguments. Browser-visible evidence does not prove external business completion. One page excludes parallel work. Downloads are process-lifetime workflow state and may leave expired scratch residue after a crash.
