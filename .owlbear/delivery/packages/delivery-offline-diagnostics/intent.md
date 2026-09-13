# Delivery Offline Diagnostics

> Status: candidate Design authority; formal gates pending
> Programme packet: P05 in `.owlbear/research/change-continuation-delivery-redesign.md`
> Dependencies: reviewed P01 result `4bf2365180c2851723fa09d91fa48a209220eb33`; source-owned bounded discovery task in this Change
> Admission precondition: P01 or an independently verified semantic successor must be accepted into this Change's integration target before admission.

## Problem And Product Promise

Delivery can fail before `PortfolioApplication`, Delivery MCP, or one Change runtime can compose. Existing setup tools do not provide bounded machine-readable diagnosis of malformed local Delivery persistence. Current persisted-Change discovery contains entry errors but reads authority files without explicit size/change fences, so bounded offline diagnosis also needs a source-owner correction that preserves startup classification.

P05 provides one read-only `delivery-diagnose` command that independently inspects a declared local capability set. One malformed entry remains one finding and cannot hide healthy siblings. Reports distinguish inspected, filtered, unavailable, and uninspected capabilities, use bounded safe details and relative paths, and never repair, recover, lock, contact remotes, run hooks, create files, or compose `PortfolioApplication`/`DeliveryRuntime`.

Healthy means no defect in the explicitly inspected set, not universal Delivery health.

## Normal Workflow

1. A maintenance agent invokes `uv run delivery-diagnose [PATH] --format json`; default text remains available for setup investigation.
2. The command derives local Delivery paths without creating them and inspects supported categories independently through bounded source-owned parsers.
3. It returns versioned `healthy | attention | unavailable`, capability coverage/counts, bounded Change summaries/findings, and an explicit no-change statement.
4. Malformed package, Change, state-publication, coordination, report, or transaction entries do not hide siblings.
5. Later repair may consume JSON only after fresh repair authority. P05 exposes no mutation or repair action.

## Scope

### In Scope

- Delivery-core bounded, descriptor-safe contract/frontier/admission reads in persisted discovery, with per-file oversized/observable-change codes and unchanged startup recoverability semantics.
- `delivery-diagnose [PATH] [--change ID] [--format text|json]` in `serve/tools`.
- Startup/host config, Design packages, local Change authority, state-publication, coordination, integrated P01 finalization reports, and documented transaction-marker structural inspection.
- Explicit uninspected rows for revisions, claims, completions, publications, remote/provider state, process liveness, worktree content, online readiness, and repair eligibility.
- Deterministic rendering, bounded counts/details, distinct exits, Setup help, generated Python index, and disposable tests.
- Two sequential native tasks: T3 bounded discovery, then T2 tools command; both independently reviewed at T3.

### Out Of Scope

Repair, migration, replay, locks, process termination, worktree operations, Git/remote/provider operations, MCP startup, claims/completions/publications validation, repair eligibility, and a repair prompt. Existing live records are not test fixtures.

## Preserved Behavior

Existing setup tools, strict semantics, startup/health/report persistence, malformed bytes, Git refs, and user files remain unchanged. Admission-file oversize/observable change remains a recoverable admission partial; contract/frontier equivalents remain startup-fatal as their existing unavailable/invalid classes are today.

## Success

An agent obtains bounded truthful JSON when the application or one local record fails. Reports disclose unsupported categories. The user does not run tests, inspect files, or repair state.

## Technically Done But Wrong

- Admission before P01 integration.
- Generic discovery codes that change startup strictness.
- Unbounded reads duplicated in tools or locking/recovering package/report store readers.
- Hiding non-attributable transaction markers in selected-Change mode.
- Treating filtering as truncation or revisions as filtered.
- Printing values/content/raw errors/absolute paths, following symlinks, or advertising repair.

```yaml target-contract
kind: commitment
id: COM-001
class: dealbreaker
provenance: user-requested recoverable Delivery programme and P05 boundary
statement: Offline diagnosis remains read-only and does not require PortfolioApplication, DeliveryRuntime, MCP availability, remote services, transaction recovery, or writable Delivery state.
```

```yaml target-contract
kind: commitment
id: COM-002
class: protected-request
provenance: P01 diagnostic contract and source-owned persistence readers
statement: Every report distinguishes inspected local facts from filtered, unavailable, and uninspected capabilities without weakening parser or startup semantics, accepting unbounded authority files, or synthesizing authority.
```

```yaml target-contract
kind: commitment
id: COM-003
class: important-reviewed
provenance: current discovery, package, coordination, report, and tools boundaries
statement: One malformed, oversized, or observably changed entry is contained to a bounded finding while healthy sibling packages and Changes remain visible.
```

```yaml target-contract
kind: commitment
id: COM-004
class: protected-request
provenance: privacy and workspace-containment requirements
statement: Output is bounded and deterministic, uses repository-relative paths, omits raw contents and sensitive environment/provider data, and never follows symlinks outside the workspace.
```

```yaml target-contract
kind: commitment
id: COM-005
class: agreed-path
provenance: P05 handoff and current package architecture
statement: After P01 integration, implementation first deepens Delivery persisted discovery with bounded read-only file handling, then adds a consumer-visible tools command without dependency changes or a competing state machine.
```

```yaml target-contract
kind: outcome
id: OUT-001
title: Bounded offline Delivery diagnosis
promise: An agent can inspect supported local Delivery persistence and receive truthful bounded findings even when application composition or one Change record fails.
acceptance:
  - "AC-001: Given supported inspected local config, packages, Changes, state-publication, coordination, and finalization reports, `uv run delivery-diagnose <path> --format json` emits schema version 1, deterministic order, explicit coverage rows, and status healthy when the inspected set has no finding."
  - "AC-002: Given malformed frontier bytes beside a healthy Change, output contains frontier-invalid for that Change and still reports its sibling; no bytes or state change."
  - "AC-003: Given `--change missing-change`, output contains change-not-found, status attention, and exit 1 rather than empty healthy output."
  - "AC-004: Given a missing workspace or unsafe Delivery root, output is one schema-valid unavailable report with workspace-unavailable or delivery-root-unsafe and exit 3; malformed arguments exit 2 without a report."
  - "AC-005: Given malformed/mismatched package or coordination files, findings use bounded registered codes and relative paths; siblings remain represented and raw content/errors are absent."
  - "AC-006: Given P01 integrated and malformed report/pointer beside pending runtime, legacy package, or report transactions, output reports bounded invalid/pending findings without package/report store reads, recovery, locks, Git, network, or provider operations."
  - "AC-007: Capability rows expose workspace, local-config, host-config, design-packages, local-changes, state-publication, coordination, finalization-reports, and transaction-markers as inspected/unavailable/filtered; change-revisions, claims, completions, publications, remote/provider state, process-liveness, worktree-content, online-readiness, and repair-eligibility are uninspected."
  - "AC-008: Text output names status, Change when known, code, bounded summary, and `Read-only diagnosis; no changes made.` without advertising repair."
  - "AC-009: Cap-driven omission sets truncated and preserves observed_count, reported_count, and total finding_count; deliberate sibling filtering does not set truncated."
  - "AC-010: Before/after fixture snapshots match byte-for-byte and no lock, temp file, transaction, Git ref, process, network call, or hook is created."
  - "AC-011: `doctor` and `target-branch` remain unchanged; `uv run help setup` lists consumer-visible `delivery-diagnose`."
  - "AC-012: Text and JSON render one report and emit the standard footer on stderr; unsupported format is rejected before inspection."
  - "AC-013: An oversized contract, frontier, or admission file produces its source-owned per-file too-large code without unbounded read; an observable identity, size, or modification-time change during read produces its per-file changed-during-read code, discards parsed validity, and leaves siblings visible."
  - "AC-014: A report containing an unavailable capability and an attention finding has overall unavailable status and exit 3; precedence is unavailable over attention over healthy."
  - "AC-015: Safe absent Delivery/category roots are inspected with zero counts; missing config is attention, not unavailable, while missing workspace remains unavailable."
  - "AC-016: Given `--change selected`, selected package, authority, state-publication, coordination, and report facts remain inspected while sibling entries are omitted; never-enumerated revisions remain uninspected; non-attributable runtime transaction markers remain represented; capability filtered means it contains only omitted attributable siblings."
  - "AC-017: Given oversized or observably changed admission evidence, startup retains recoverable admission-partial behavior; equivalent contract/frontier failures retain existing fatal startup classification."
commitments: [COM-001, COM-002, COM-003, COM-004, COM-005]
dependencies: []
```
