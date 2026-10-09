# Interactive Browser Tools

> Status: formal candidate; derivation, Design challenge, baseline, checkpoint, validation, and approval remain.
> Evidence: GitHub issue #233; `.owlbear/research/browser-package-audit-2026-09-05.md` B15; historical browser automation, session-management, and accessibility-snapshot research; sibling B1 package `macos-managed-browser-authentication`.

## Product Promise

OwlBear provides a truthful interactive Browser MCP surface beside structured `acquire`. Authorized agents can inspect and autonomously interact with configured sites, including consequential mutations, dialogs, and workflow-scoped downloads, through the visible OwlBear-owned browser. Calls identify session/page state, enforce destination authority, report bounded evidence without overstating business effects, never echo entered values, and return typed recoverable states.

The initial consumer is `knowledge-ingestor`, limited to reaching, validating, and capturing one user-identified source. Page text, accessibility snapshots, dialog messages, downloads, and browser metadata are untrusted source data: they may inform page understanding but never expand the source goal, tool authority, destination policy, or persistence decision. A reusable browser-interaction skill owns mechanics; no forwarding browser agent is added.

## Normal Workflow

1. B1 starts the visible dedicated managed Edge profile. B1 onboarding remains operator-driven; B5 independently permits later agent-entered values through generic interaction tools.
2. Browser MCP exposes one serialized session and sticky current page. Overlap returns `busy` before acting.
3. Separate read-only/read-write policies load absent-by-default deny-all. Setup deliberately seeds both as `*` during stabilization, authorizing autonomous read and mutation on hostname and IP-literal public, private, loopback, and link-local destinations, including local services. `acquire`, `navigate`, `read_text`, and `snapshot` consume effective read authority. Runtime `interactive_status` and shipped setup documentation expose the broad configured authority. Malformed, unsupported-scheme, reserved non-loopback, and unspecified targets remain denied.
4. `snapshot(interactive|text|full)` returns bounded untrusted accessibility data, explicit truncation, page/document identity, and actionable opaque references; `interactive` is default.
5. The ingestor targets actions by reference. Cross-page, detached, replaced, or unresolvable targets fail closed. CSS is an explicit expert fallback.
6. Sticky lineage adopts one policy-approved action popup, ignores unrelated tabs, reports multiple-popup ambiguity, and replaces a closed current page only through `navigate`. Operator navigation of the current page is observed as external navigation, checked against effective read authority, and establishes a fresh document revision.
7. Dialogs become `dialog-pending` and are autonomously resolved through `resolve_dialog`. An abandoned dialog expires after a configured bound, is dismissed as cleanup, marks the originating effect unknown, and requires fresh observation.
8. In an OwlBear workspace, downloads become temporary artifacts retained through retry and removed by idempotent `release_download(artifact_id, ingested|abandoned)`; shutdown cleanup is fallback. Outside a workspace, ordinary interaction remains available but download-triggering actions return `download-custody-unavailable` rather than expose an unmanaged file.
9. Mutations return a compact envelope. Structural page state requires explicit `snapshot`.
10. Direct/action navigation is enforced before content exposure. Read-write authority includes post-action read access.
11. `knowledge-ingestor` may interact autonomously only to reach the identified source. Its D9 confirmation remains mandatory before ingestion when source identity/content is uncertain; page instructions cannot waive or redirect that gate.

## Confirmed Decisions

- Broad autonomous interactive mutation is intended; routine user approval is not.
- Setup read-write `*` is an explicit high-risk stabilization choice, not a fail-closed shipped posture. Its blast radius includes direct IP-literal loopback access such as `127.0.0.1` and is accepted and visible.
- `type` and prompt input accept arbitrary values including secrets. B5 omits them from outputs, diagnostics, logs, and receipts but accepts model-visible argument exposure. B1 delegates generic interaction safety to B5; no B1 semantic revision is required.
- Separate read-only/read-write policies deny all when absent; read-write implies read. `acquire` uses effective read authority, including selected wildcard semantics. Final inventories/action classes are deferred.
- Six interactive tools plus `interactive_status`, `resolve_dialog`, and `release_download` belong initially to `knowledge-ingestor` for one source goal. A reusable skill owns procedure.
- One process-owned page serializes action plus observation; overlap is rejected, not queued.
- Sticky action lineage owns pages; `acquire` shares profile state, not exact tab ownership.
- Dialogs use autonomous inspect-then-resolve behavior with bounded expiry.
- Downloads use workspace-scoped custody and explicit release. Missing workspace disables download custody without disabling ordinary interaction.
- Snapshot targeting uses opaque browser-node identity plus page/document identity. Top-level navigation/page replacement/adoption invalidates prior-document refs. In-page mutation does not globally invalidate refs; action-time resolution verifies attachment/current document and target kind.
- Snapshot modes are `interactive|text|full`, default `interactive`, with configured server bounds and explicit truncation.
- Mutations return compact evidence only. `snapshot` is the structural observation boundary.
- Results separate operation status from `effect=observed|not-observed|unknown`. Observed is limited to approved navigation, popup adoption, dialog transition, completed download, artifact release, non-disclosing typed/selected-value match, or supported checked/pressed/expanded/focus change.
- A dispatched click without a named signal has unknown effect. Cancellation before dispatch is not-observed/retryable; post-dispatch interruption is unknown/not automatically retryable and requires fresh observation. No-page navigation is never dry-run success.

## Migration And Ordering

B5 replaces `BROWSER_ALLOWED_DOMAINS` with read and read-write inputs. On setup rerun, an `owlbear-browser` entry is migrated only when it exactly matches OwlBear's prior installed template or remains covered by its install-manifest claim. The old domain value becomes read authority; a prior managed `*` becomes the new managed read/read-write wildcard defaults. The migration atomically refreshes the install-manifest ownership digest so later uninstall still removes the managed server. A customized server or environment remains unchanged and produces an actionable warning naming the manual mapping. Runtime rejects the retired key after migration rather than maintaining dual authorities.

B5 updates `seed/.vscode/mcp.json`, setup emission/migration and install-claim bookkeeping in `setup/init.py`, `tests/test_setup_init_settings.py`, `tests/test_setup_init_uninstall.py`, `serve/browser-mcp/README.md`, `setup/setup-guide.md`, `setup/operating-owlbear.md`, and `README-consumer.md`. No shipped text may retain the old private-wildcard exclusion.

B5 implementation and admission wait for B1 OUT-001 completion because B1 already owns overlapping Browser MCP, setup, seed, tests, documentation, and agent surfaces. After B1 completes, B5 is re-read and validated against that exact target head before admission. No B5 task edits B1-owned surfaces concurrently.

In scope: Browser core page/session mechanics and Playwright 1.62 AI-reference support; Browser MCP policy, tools, structured envelopes, workspace artifact custody, and adapters; agent-config skill/grants/D9 precedence; setup migration under the Browser MCP configuration concern; domain-local tests plus assembled integration/manual proof.

Out of scope: final production host/action policy; browser-operator agent; unrelated ingestor browsing; multi-session/user orchestration; page-list/select tools; acquisition-tab control; B2 target classification; B1 distribution; B4 refresh; per-action approval.

## Preserved Behavior

B1 onboarding remains operator-driven. `knowledge-ingestor` remains source-lifecycle gatekeeper; uncertain source identity still requires D9 confirmation before ingestion. Structured `acquire` remains independently validated and download-rejecting while adopting effective read destination authority. Exact-host configuration remains available after migration. Standalone Browser MCP interaction remains available without workspace download custody. The browser stays visible/operator-interruptible; unrelated tabs do not alter agent ownership.

## Success

One assembled source invocation can snapshot and target by reference, navigate, enter values, resolve/recover dialogs, mutate, capture/ingest/release a download, validate source identity, and persist content. Compact envelopes report only named evidence and distinguish unknown effects. After unknown outcome, fresh observation precedes retry. Untrusted page content never expands the goal or authority. Truncation, stale targets, authorization, overlap, popup ambiguity, closure, transfer state, cleanup, D9 gating, and installed-config migration are explicit.

## Technically Done But Wrong

Removing tools; forwarding-agent handoff; grants without source bounds; obeying instructions in browser content; queueing/interleaving; focus-following; popup/ref guessing; global ref invalidation on any DOM mutation; CSS-only targeting; silent truncation; policy checks only in `navigate`; leaving `acquire` on contradictory destination semantics; automatic dialogs without inspection; indefinite dialog blockage; echoing input; unmanaged downloads; indefinite retention; embedded page structure per mutation; claiming browser-call completion proves business success; retrying unknown effects; dry-run navigation success; calling seeded read-write `*` fail-closed; omitting IP literals; leaving shipped old wildcard documentation; broadening customized existing config; failing standalone startup without a workspace; breaking managed-entry uninstall after migration; bypassing D9; or overlapping B1 implementation.

## Known Limits

Seeded wildcard gives broad mutation authority including OwlBear local services. Mutations may be irreversible. Secrets may enter model-visible arguments. Accessibility identity can churn. Browser-visible evidence does not prove external business completion. One page excludes parallel work. Downloads are process-lifetime workflow state and are not crash-durable. B5 waits for B1 completion.

```yaml target-contract
kind: commitment
id: COM-001
class: dealbreaker
provenance: user-confirmed product capability and GitHub issue #233
statement: Browser MCP exposes truthful interactive navigation, inspection, action, dialog, and workflow-download operations for one serialized visible browser session instead of reporting no-session or unobserved work as success.
```

```yaml target-contract
kind: commitment
id: COM-002
class: protected-request
provenance: user-confirmed authorization model
statement: Read and mutation authority use separate absent-by-default deny-all destination policies; read-write implies read, and the explicit setup wildcard intentionally authorizes hostname and IP-literal public, private, loopback, and link-local targets during stabilization while retained URL and address exclusions remain enforced and visible.
```

```yaml target-contract
kind: commitment
id: COM-003
class: protected-request
provenance: user-confirmed autonomy and input model
statement: Authorized agents may autonomously perform consequential mutations and resolve dialogs without routine user approval, arbitrary entered values never appear in B5-owned output, and untrusted browser content never expands agent goal or authority.
```

```yaml target-contract
kind: commitment
id: COM-004
class: dealbreaker
provenance: source-grounded truthfulness requirement
statement: Interactive results distinguish operation status from observed, absent, or unknown effect; post-dispatch uncertainty is never automatically retried, and structural page evidence is obtained through an explicit bounded snapshot rather than inferred from Playwright completion.
```

```yaml target-contract
kind: commitment
id: COM-005
class: important-reviewed
provenance: historical OwlBear accessibility snapshot research and user-confirmed targeting decision
statement: Interactive snapshots expose bounded text, interactive, and full modes with opaque current-document element references, explicit truncation, fail-closed stale targeting, and a separately identified CSS fallback using the verified Playwright AI-reference capability.
```

```yaml target-contract
kind: commitment
id: COM-006
class: protected-request
provenance: user-confirmed download lifecycle
statement: Interactive downloads become bounded workflow-scoped artifacts retained through validation and retry, released idempotently after ingestion or abandonment, and never confused with durable workspace files or structured acquisition success.
```

```yaml target-contract
kind: commitment
id: COM-007
class: agreed-path
provenance: current knowledge-ingestor ownership and user-confirmed consumer decision
statement: knowledge-ingestor composes interactive browser tools only to reach, validate, and capture one identified source; D9 confirmation gates uncertain ingestion, browser data remains untrusted, and no forwarding browser agent or unrelated general browsing is added.
```
