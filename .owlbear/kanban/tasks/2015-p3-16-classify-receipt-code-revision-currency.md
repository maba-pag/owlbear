---
id: 2015
title: 'P3-16A: Define and freeze receipt impact closures'
status: build
priority: high
created: 2026-07-23T14:41:09.745275+02:00
updated: 2026-07-23T18:16:46.738798+02:00
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
