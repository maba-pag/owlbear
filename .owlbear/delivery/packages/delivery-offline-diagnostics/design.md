# Delivery Offline Diagnostics Design

> Status: candidate architecture; formal gates pending
> Packet: P05, separate from `delivery-action-readiness`
> P01 dependency: TASK-001 result `4bf2365180c2851723fa09d91fa48a209220eb33`
> Admission gate: P01 or verified successor must be in the integration target. It was not an ancestor of local `dev` on 2026-09-13; refresh before checkpoint/admission.

## Ownership And Tasks

One Change, two sequential tasks:

1. **T3 Delivery bounded discovery:** source-owned bounded reads and unchanged startup classification.
2. **T2 tools command:** offline report/CLI using reviewed parsers; independent T3 review.

Current discovery reads authority unboundedly, so tools cannot honestly own that fix. Existing owners remain setup doctor, target configuration, Delivery discovery/models, and integrated P01 reports. All locking/recovering store readers, including `DesignPackageStore.read_verified/list_verified`, `FinalizationReportStore.read`, and `RuntimeTransaction.recover*`, are forbidden; package/report inspection parses bounded raw bytes through public models.

Before checkpoint/admission require P01 integrated, confirm report contracts, rerun target baselines, and stay Draft otherwise.

## Task 1: Bounded Persisted Discovery

Deepen `delivery_contract_discovery` without changing its public role:

- 1 MiB per authority file;
- descriptor no-follow regular-file read bounded to limit+1;
- best-effort observable identity/size/mtime checks before/after;
- per-file codes CONTRACT_TOO_LARGE, FRONTIER_TOO_LARGE, ADMISSION_TOO_LARGE, CONTRACT_CHANGED_DURING_READ, FRONTIER_CHANGED_DURING_READ, ADMISSION_CHANGED_DURING_READ;
- contract/frontier codes remain startup-fatal; admission codes enter both `_ADMISSION_ONLY_ERRORS` and loader `_RECOVERABLE_ADMISSION_ERRORS` and remain recoverable partials;
- changed/oversized evidence contributes no trusted validity while siblings continue;
- no locks, writes, recovery, Git, network, or raw errors.

Maintained surfaces: discovery module, loader classification, and focused discovery/startup tests for all codes. Same-inode/same-size writes invisible to observed metadata are outside the best-effort detector; diagnosis is not a lease.

## Task 2: Tools Command

Add `owlbear_tools.delivery_diagnostics` with strict models, contained scanners, `diagnose_delivery(root, change_id=None)`, renderers, CLI, script entry, consumer-visible Setup help, tests, and generated py-index. No dependency/lock change.

## Report Contract

```text
DeliveryOfflineReport
  schema_version: 1
  status: healthy | attention | unavailable
  workspace: "."
  selected_change_id: string | null
  capabilities: tuple[OfflineCapability, ...]
  changes: tuple[OfflineChangeSummary, ...]
  findings: tuple[OfflineFinding, ...]
  finding_count: integer >= len(findings)
  truncated: boolean

OfflineCapability
  name: workspace | local-config | host-config | design-packages |
        local-changes | change-revisions | state-publication | coordination |
        finalization-reports | transaction-markers | claims | completions |
        publications | remote-state | provider-state | process-liveness |
        worktree-content | online-readiness | repair-eligibility
  state: inspected | unavailable | filtered | uninspected
  observed_count: integer >= 0 | null
  reported_count: integer >= 0 | null
  detail: bounded template | null

OfflineFinding
  source: exactly one OfflineCapability name
  code: registered lowercase-hyphenated code
  severity: attention | unavailable
  change_id: string | null
  path: relative POSIX path | null
  detail: bounded fixed template
```

Change summary holds package, local authority, DeliveryChangeStage/null, state-publication, coordination, and finalization-report states. Status precedence unavailable > attention > healthy. Safe absent roots inspected zero. Observed/reported/finding counts expose cap loss; cap-driven omission alone sets truncated. Filtering is carried by capability state/counts and never sets truncated.

JSON is stable plus newline; text derives from it; standard footer goes to stderr. Exit 0/1/3 for healthy/attention/unavailable; argparse 2 gives no report.

## Roots And Bounds

Closed roots:

- packages: `.storage.lock`, legacy transactions, Change directories;
- package Change: exactly authority.json, design.md, intent.md, manifest.json;
- runtime: `.storage.lock`, changes, claims, completions, coordination, optional finalization-reports, host.json, optional host.local.json, publications, transactions;
- coordination: exactly changes/; records at runtime/coordination/changes/<id>.json;
- Change: contract/frontier/admission, optional state-publication/revisions; revisions tolerated, never descended, uninspected;
- report Change: `.storage.lock`, current.json, reports, transactions.

Limits: 256 entries/category, 512 emitted findings, 1 MiB tools-read files, 16 KiB reports, 240 detail, 512 path. No symlink following; only relative output. Expected locks/uninspected roots are not findings.

## Inspection

1. Workspace missing => unavailable report; safe absent category roots => inspected zero.
2. Startup config: bounded schema-version pre-read then strict DeliveryStartupConfig; values hidden, no Git.
3. Host config: public baseline model; optional private override twin with drift test; values hidden.
4. Packages: bounded raw manifest/hash validation; no store. Empty authority valid.
5. Local Changes: safe enumeration plus bounded discovery. Stage/admission only from validated evidence. Revisions uninspected.
6. State publication: optional strict=False DeliveryPendingStatePublication; invalid/pending/ack only.
7. Coordination: exact `runtime/coordination/changes/*.json`, public model, filename match, no liveness inference.
8. Reports after P01: public FinalizationReport and private pointer shape/fixture contract only; no store/cross-history semantics.
9. Transactions: runtime/transactions, packages/transactions legacy, report transactions. Marker filenames only, no parse/replay.
10. Uninspected rows always visible.

With `--change`, shared config remains inspected. Selected package/authority/state-publication/coordination/report entries remain inspected. Sibling attributable entries are omitted; if only siblings exist, capability is filtered with null counts. Revisions/claims/completions/publications remain uninspected. Runtime transaction markers attributable by filename to selected Change are shown; non-attributable markers are always shown because safe attribution is impossible; attributable sibling markers may be omitted. Transaction capability stays inspected. Missing selected ID yields change-not-found.

## Verification And Surfaces

Tests fail if subprocess/network/locks/application/runtime/store/recovery paths are called and compare fixture bytes/types/links. Cover all ACs, expected roots, best-effort changed-read behavior, per-file startup classification, config/host drift, package/report/coordination identity, state-publication, three transaction roots, selected filtering/non-attributable markers, footer/help, doctor/target preservation, package boundary, index, lock freshness.

Task 1 T3 surfaces: `delivery_contract_discovery.py`, `delivery_application_loader.py`, focused Delivery tests.

Task 2 T2 surfaces: delivery_diagnostics.py/tests, tools pyproject, commands.py/tests, generated `.owlbear/py-index.md`. No others discretionary.

Importable Delivery required; broken Python install is P20. Point-in-time, not lease. No repair recommendation. Healthy never proves uninspected categories.

## Formal Gates

Derive/challenge now. Before checkpoint/admission: require P01 integrated, rerun target baselines including P01 tests, checkpoint, rederive identical authority, present limits, obtain approval. Task 1 T3 and Task 2 T2 both independent T3 review. Start no other packet.
