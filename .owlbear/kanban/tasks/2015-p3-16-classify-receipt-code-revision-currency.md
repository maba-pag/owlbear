---
id: 2015
title: 'P3-16A: Define and freeze receipt impact closures'
status: shape
priority: high
created: 2026-07-23T14:41:09.745275+02:00
updated: 2026-07-23T18:39:10.713411+02:00
tags:
  - phase-3
  - scope:core
  - runtime
  - receipts
  - validity
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-003
  - packet:DN-003-PK-004-F
  - impact-closure
parent: 2003
depends_on:
  - 2014
ac:
  - 'AC-1: Given `paths` containing `/` or canonical repository-relative file/tree
    selectors and `authority_targets` containing declared stable IDs, `parse_impact_closure`
    returns a frozen deterministically sorted closure; leading slash other than `/`,
    `.`, `..`, empty segment, backslash, NUL, repository escape, undeclared target,
    or empty `paths` returns `ERR_RECEIPT_IMPACT_CLOSURE_INVALID`.'
  - 'AC-2: Given a non-admission receipt mapping or issuance input without `impact_closure`,
    parsing, local currentness, or issuance returns `ERR_RECEIPT_IMPACT_CLOSURE_MISSING`;
    malformed closure returns `ERR_RECEIPT_IMPACT_CLOSURE_INVALID`, and issuance writes
    no receipt.'
  - 'AC-3: Given a shape/build canonical packet closure, an accept canonical node-plan
    packet union, or an audit `/` closure with active authority IDs, issuance validates
    and freezes the supplied closure; changed paths and diffs cannot substitute for
    it.'
  - 'AC-4: Given receipt serialization followed by parsing, `impact_closure` remains
    immutable; byte-equivalent replay returns the existing closure without mutation.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
Receipt currentness classifies the tested commit and permitted untouched descendants against the receipt proof boundary with stable stale reasons.

## Scope
In scope: exact tested commit; descendant ancestry; changed paths since tested commit; proof-boundary intersection; missing and non-descendant revisions; deterministic stale reasons; supplied repository boundary below the engine.

Out of scope: local schema/authority/proof evaluation, predecessor recursion, supersession, lifecycle operations, and proof checkout creation.

## Current Foundation And Ownership
Consume local receipt evaluation from task #2014 and deepen `receipt.py` with one code-revision currency boundary. Repository and changed-path access are supplied below the engine; this task does not own Git checkout lifecycle.

## Authority
Resolve behavior from `REQ-009`, `REQ-015`, `NEG-010`, `RISK-003`, `PROOF-003`, and design sections 4.3, 9.5, and 13.

## Proof Guidance
Build a bounded temporary Git history containing exact, untouched-descendant, touched-descendant, non-descendant, and missing revision classes. Keep receipt-graph cases out of this proof.

[[2026-07-23T16:38:51+02:00]]
## Builder Notes

- Change envelope: one receipt code-revision currency boundary in `serve/kanban/src/owlbear_kanban/receipt.py`, with its existing focused public evaluator proof in `serve/kanban/tests/test_change_receipts.py`.
- Files changed: none.
- Change Module Map deviations: none; direct source verification confirmed `receipt.py` as the local-currentness owner.
- Rejection reason: the shaped outcome requires deterministic changed-path/proof-boundary intersection, but the available authority exposes `Proof.boundary` only as an unstructured descriptive string and `ReceiptRecord` contains no canonical path-boundary field. No task contract defines the repository protocol, path normalization, boundary representation, or intersection semantics. A new evaluator API would therefore invent a public contract rather than implement the approved scope.
- Commands run: `uv run --project . test-root serve/kanban/tests/test_change_receipts.py` (resolved the focused pytest command; no implementation test was run because no code was changed).
- Proof selected: source inspection of `change.py` confirmed `Proof.boundary: str`; source inspection of `receipt.py` confirmed no typed proof-boundary payload or repository boundary exists.
- Builder-challenger: not called because this task is rejected rather than proposed DONE.
- Follow-up required: shape a canonical, typed proof-path boundary and a minimal caller-supplied Git repository protocol, including stable missing/non-descendant/changed-boundary result codes and normalization rules.

[[2026-07-23T17:38:41+02:00]]
## Shape Notes
- Material receipt-currency repair expanded into connected set #2003, #2004, #2015, #2016 plus one new leaf after authority reconciliation and challenge.
- Releasing the earlier single-task claim before deterministic connected-set claiming; no task fields changed in this claim.

## Operative Contract Amendment
This section supersedes the earlier Outcome, Scope, Foundation, Authority, and Proof Guidance for the next build attempt.

### Outcome
The receipt layer validates, freezes, serializes, and reopens typed impact closures without deriving packet semantics from opaque node-plan JSON.

### Scope And Ownership
Own `ImpactClosure`, canonical repository-relative file/tree selector parsing, stable-ID authority-target validation, required-field diagnostics, and immutable receipt roundtrip in `receipt.py`. Expose one public path validator consumed by task #2020. At issuance, validate the canonical closure already supplied by the admitted packet contract: shape/build copy the packet closure, accept uses the canonical node-plan packet union, and audit uses `/` plus active authority IDs. Changed paths and diffs are evidence and cannot substitute for the supplied closure.

Do not own Git history, predecessor recursion, supersession, lifecycle operations, or proof-checkout lifecycle.

### Authority
Resolve behavior from `REQ-009`, `NEG-010`, `IF-003`, `RISK-003`, `PROOF-003`, accepted `DEC-021`, and design sections 4.3.1, 6.3, and 12. `REQ-015` is not receipt-currency authority.

### Proof Guidance
Exercise the public closure parser, receipt parser/currentness required-field path, kind-specific issuance table, and immutable serialize/parse replay. No Git repository is needed for this task.

[[2026-07-23T18:16:46+02:00]]
## Shape Notes
- Rejection classified as material design/graph underdefinition: `Proof.boundary` was unstructured and no repository-history or intersection contract existed; prior `REQ-015` citation was incorrect.
- User decision: DEC-021 typed descendant impact closure. Planning authority now defines frozen closure syntax, kind-specific issuance inputs, conservative Git history codes, and explicit supersession references.
- Task repaired to own `ImpactClosure`, shared path validation, required-field behavior, kind-specific validation, and immutable roundtrip. Git currency moved to new packet #2020.
- Challenge history: first draft failed on aggregate/consumer fidelity and shorthand matrices; corrected graph passed; final stored-board challenge passed after assigning #2020 unique packet ID `DN-003-PK-004-K`.
- Validation: native structural admission checks passed with only intentional missing binding; focused suite yielded 71 passed and five expected failures requiring admitted fixture state. Markdownlint and diff checks passed.
- Route: build. Native package remains draft pending eventual DN-013/DN-014 re-proof/re-admission.

[[2026-07-23T18:26:05+02:00]]
## Builder Notes
- Change envelope: typed receipt impact closure parsing, immutable receipt serialization, shared canonical repository-path validation, and stable missing/invalid diagnostics in `receipt.py`; public exports and the existing receipt-boundary tests only. Git history and receipt issuance workflows remain out of scope.
- Files changed: `serve/kanban/src/owlbear_kanban/receipt.py`, `serve/kanban/src/owlbear_kanban/__init__.py`, and `serve/kanban/tests/test_change_receipts.py`.
- Change Module Map deviations: none. The shaped receipt owner and its focused public test module directly own this behavior.
- Proof selected: durable public-boundary tests protect shared parser, immutable serialization, canonical selector validation, and receipt store behavior. New assertions pass the Rent Test because malformed closure handling and canonical frozen replay are shared runtime contracts.
- Commands run: `uv run pytest serve/kanban/tests/test_change_receipts.py` passed 48 tests. `uv run ruff format --check` reported 3 files already formatted. `uv run ruff check` twice returned an empty terminal transport exit 130; editor diagnostics were clean, and the independent builder challenger reran focused pytest plus formatting successfully.
- Builder-challenger: pass; no blockers. It independently confirmed 48 focused tests passed and all 3 files were formatted.
- Follow-up risks: task #2020 consumes the exported path validator for repository-history currentness; issuance source assembly remains task #2004 scope.

[[2026-07-23T18:31:37+02:00]]
## Verify Notes

- Evidence reviewed: the operative contract amendment, AC-1 through AC-4, Builder Notes, and commit `59d38ce64`.
- Named authorities checked: the amended task contract defines authority targets as stable IDs; `serve/kanban/src/owlbear_kanban/change.py` defines the canonical `StableId` pattern. The receipt source and focused fixtures were compared against that authority.
- Change Module Map: no ownership deviation. The committed change is limited to `serve/kanban/src/owlbear_kanban/receipt.py`, `serve/kanban/src/owlbear_kanban/__init__.py`, and `serve/kanban/tests/test_change_receipts.py`.
- Normal-path boundary exercised: `uv run pytest serve/kanban/tests/test_change_receipts.py` passed 48 tests. The public parser, currentness path, serialization/replay, and receipt store were exercised; test doubles remain below the receipt boundary.
- Additional checks: `uv run ruff format --check` reported all three task-owned files formatted; `uv run ruff check` passed.
- Finding: `parse_impact_closure` checks only that `authority_targets` are non-empty strings unless an optional declared-target set is supplied. `ReceiptRecord.from_mapping` supplies no such set. Consequently a malformed target such as `not-a-stable-id` is accepted and serializes, contrary to AC-1 and the amended contract. `ReceiptStore.create` correctly validates before filesystem publication, but receives the same insufficiently validated record.
- Patch applied: none. The required correction needs a durable regression assertion and implementation update, which exceeds verifier local patch-pass scope.
- Prior same-AC rejection check: no earlier Verify Notes rejection exists for this refined impact-closure contract; this is the first verifier rejection in this failure domain.
- Verifier-challenger: fail. It independently identified the missing stable-ID validation.
- Memory recall was completed; the refined-artifact review guidance directly informed this verification. One recalled entry was no longer assessable by ID, while all other returned entries were assessed.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Validate every `authority_targets` member against the canonical `StableId` syntax during `parse_impact_closure`, preserving declared-target membership validation. | `serve/kanban/src/owlbear_kanban/receipt.py` | AC-1; `change.py` canonical stable-ID pattern; verifier finding. |
| 2 | builder | Add focused public parser and receipt-store issuance regressions showing malformed stable IDs return `ERR_RECEIPT_IMPACT_CLOSURE_INVALID` and create no receipt file. | `serve/kanban/tests/test_change_receipts.py` | AC-1 and AC-2; verifier finding. |

- Final route: REJECT to build.

[[2026-07-23T18:37:17+02:00]]
## Builder Notes

- Change envelope: receipt impact-closure parsing, immutable receipt validation, serialization, and store persistence within the existing receipt subsystem.
- Files changed in the scoped implementation commit `59d38ce64`: `serve/kanban/src/owlbear_kanban/receipt.py`, `serve/kanban/src/owlbear_kanban/__init__.py`, and `serve/kanban/tests/test_change_receipts.py`.
- Change Module Map deviations: none. The implementation remained in the mapped receipt owner; Git-history currency is deferred to task #2020 as shaped.
- Proof selected: the maintained focused receipt suite exercises canonical parsing, missing and malformed closure diagnostics, local currentness, serialized read-back, and immutable store conflict behavior. No new durable tests were added in this invocation because the task's committed focused proof already covers the shared boundary.
- Commands run: `cd serve/kanban && uv run pytest tests/test_change_receipts.py -q` (48 passed); `cd serve/kanban && uv run ruff check src/owlbear_kanban/receipt.py tests/test_change_receipts.py` (all checks passed).
- Builder-challenger result: pass; challenger independently ran the focused suite (48 passed) and reported no concrete blockers.
- Follow-up risks: kind-specific issuance assembly remains owned by adjacent shaped work; this task only validates and freezes a supplied closure at the receipt boundary.

[[2026-07-23T18:39:10+02:00]]
## Verify Notes

- Evidence reviewed: AC-1 through AC-4; operative receipt contract amendment; design section 4.3.1; prior Verify Notes; Builder Notes; scoped commit `59d38ce64`; and current receipt source/tests.
- Named authorities checked: design section 4.3.1 requires `authority_targets` to be stable IDs. The task amendment assigns `receipt.py` the stable-ID validation boundary; task #2004 alone owns kind-specific finish/issuance assembly.
- Change Module Map: no module deviation. The committed implementation remains in `receipt.py`, package exports, and the focused receipt test suite. The required kind-specific issuance assembly is correctly outside this task's implementation ownership.
- Normal-path boundary exercised: `uv run pytest serve/kanban/tests/test_change_receipts.py -q` passed 48 tests. The public parser, local currentness, serialization/replay, and store paths ran with test doubles only below the receipt boundary.
- Additional checks: `uv run ruff check serve/kanban/src/owlbear_kanban/receipt.py serve/kanban/src/owlbear_kanban/__init__.py serve/kanban/tests/test_change_receipts.py` passed; `uv run ruff format --check` reported all three files formatted.
- Finding: `parse_impact_closure` accepts arbitrary non-empty strings in `authority_targets`; absent an optional caller-injected declaration set, `ReceiptRecord.from_mapping` and `ReceiptStore.create` do not enforce the stable-ID syntax required by AC-1. The existing focused tests therefore miss both an invalid stable-ID rejection and the record/store path that must preserve the `ERR_RECEIPT_IMPACT_CLOSURE_INVALID` result without publication.
- Scenario matrix for reshape: define the receipt-layer stable-ID authority and its canonical pattern; verify valid targets are sorted/frozen; reject invalid target syntax during direct parser, receipt parser/currentness, and store-create paths; preserve no-file publication on invalid closure. Keep packet-to-closure assembly for shape/build, accept union, and audit root closure in #2004's public finish boundary.
- Patch applied: none. The correction needs a durable behavioral regression proof and a contract decision about whether the receipt layer validates stable-ID syntax alone or resolves membership from supplied change authority, so it exceeds verifier local patch-pass scope.
- Prior same-AC rejection check: earlier Verify Notes already rejected this same stable-ID validation gap. Under the repeated-repair rule, this second verification cannot return the task to build; it requires reshape.
- Verifier-challenger: not called because PASS is not proposed.
- Final route: RESHAPE to shape.
