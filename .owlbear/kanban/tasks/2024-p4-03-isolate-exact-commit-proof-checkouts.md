---
id: 2024
title: 'P4-03: Isolate exact-commit proof checkouts'
status: build
priority: high
created: 2026-07-24T16:50:58.417043+02:00
updated: 2026-07-24T17:06:43.051954+02:00
tags:
  - phase-4
  - scope:core
  - runtime
  - proof-checkout
  - containment
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-004
  - packet:DN-004-PK-003
parent: 1980
depends_on:
  - 1979
ac:
  - 'AC-1: Given an eligible `accept | audit` job and resolvable commit, `ProofCheckoutManager.materialize`
    returns a contained job-specific checkout at that commit; tracked files reject
    writes and its manifest records job, target, commit, environment facts, and declared
    replacements.'
  - 'AC-2: Given traversal identity, a symlinked proof path, missing commit, or failed
    Git setup, materialization returns `ERR_PROOF_PATH_UNSAFE | ERR_PROOF_COMMIT_MISSING
    | ERR_PROOF_SETUP_FAILED` and leaves no usable checkout outside the proof root.'
  - 'AC-3: Cleanup of a materialized checkout is idempotent. A contained checkout
    left after interrupted cleanup appears as `ERR_WORK_PROOF_CHECKOUT_ORPHAN` in
    bounded work health, and orphan cleanup removes it without changing unrelated
    paths.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8`; `DN-004-PK-003`. Resolve normative behavior from `DN-004`, `IF-005`, `RISK-004`, `PROOF-014`, and accepted `DEC-018`; this record is not specification authority.

## Outcome
Add a deep `ProofCheckoutManager` that owns contained exact-commit materialization, read-only tracked files, environment/replacement manifests, idempotent cleanup, and bounded orphan health/cleanup.

## Envelope
In: new `serve/kanban/src/owlbear_kanban/proof_checkout.py`, work-health integration, exports, focused temporary-repository tests. Out: acceptor/auditor behavior, dispatch waves, MCP, Cockpit, and cutover removal.

Proof guidance: real temporary Git repository; replace no Git or filesystem behavior. Prove exact HEAD, containment/no-follow policy, read-only tracked files, cleanup, and orphan health.

[[2026-07-24T17:04:29+02:00]]
## Builder Notes
- Change envelope: implement only the deep proof-checkout owner, bounded work-health integration, public exports, and real temporary-Git proof. No acceptor, auditor, dispatch, MCP, Cockpit, or cutover changes.
- Files changed: `serve/kanban/src/owlbear_kanban/proof_checkout.py`; `serve/kanban/src/owlbear_kanban/runtime_query.py`; `serve/kanban/src/owlbear_kanban/native_runtime.py`; `serve/kanban/src/owlbear_kanban/__init__.py`; `serve/kanban/tests/test_proof_checkout.py`.
- Change Module Map deviations: no shaped map was supplied. Source confirmed the requested new owner and adjacent `RuntimeQuery`/`NativeRuntime` health boundary; no deviation.
- Implementation: `ProofCheckoutManager` creates detached exact-commit worktrees only for accept/audit jobs below a resolved non-symlink proof root, makes tracked regular files non-writable, persists a job/target/commit/environment/replacements manifest, returns stable path/missing-commit/setup diagnostics, and performs idempotent contained cleanup. Runtime health reports remaining roots as `ERR_WORK_PROOF_CHECKOUT_ORPHAN` through the public facade.
- Durable-test justification: retained real temporary-repository tests because exact revision, no-follow containment, read-only files, and orphan cleanup are shared security-sensitive behavior that is difficult to detect manually and likely to regress.
- Commands run: `uv run ruff check serve/kanban/src/owlbear_kanban/proof_checkout.py serve/kanban/src/owlbear_kanban/runtime_query.py serve/kanban/src/owlbear_kanban/native_runtime.py serve/kanban/src/owlbear_kanban/__init__.py serve/kanban/tests/test_proof_checkout.py` (all checks passed); `uv run pytest serve/kanban/tests/test_runtime_query.py serve/kanban/tests/test_proof_checkout.py -q --tb=short` (9 passed).
- AC evidence: AC-1 is exercised by the real Git materialization test: contained job path, exact detached HEAD, read-only tracked file, and manifest facts. AC-2 is exercised by invalid job, missing commit, symlinked root, and unusable-root cases, each leaving no external checkout. AC-3 is exercised via public bounded `RuntimeQuery.work_health`, then repeated cleanup of the same job root with no remaining health paths.
- Current failure-key resolutions: none returned from verify.
- Builder challenger: pass; no concrete blockers.
- Follow-up risks: proof roots are intentionally reported as orphans until the future acceptor/auditor lifecycle invokes cleanup; this task does not own those integrations.

[[2026-07-24T17:06:43+02:00]]
## Verify Notes
- Evidence reviewed: Builder Notes, committed task diff `32eb50638`, `ProofCheckoutManager`, `RuntimeQuery` health integration, exports, and `test_proof_checkout.py`.
- Named authorities checked: `REQ-014`, `IF-005`, `RISK-004`, `PROOF-014`, and accepted `DEC-018` in `.owlbear/changes/replace-delivery-pipeline`. They require a contained disposable read-only checkout of the exact tested commit, manifest facts including SHA/replacements/environment, no-follow containment, cleanup, and orphan health.
- Change Module Map: no supplied map; actual changed modules match the shaped envelope: deep checkout owner, existing runtime health facade, public exports, and focused real-Git proof. No architecture deviation found.
- Normal-path boundary: the focused test creates a real temporary Git repository and uses the actual `git worktree`, filesystem permissions, YAML manifest, and public `RuntimeQuery.work_health`; no Git or filesystem behavior is replaced.
- Checks run: from repository root, `uv run pytest serve/kanban/tests/test_proof_checkout.py serve/kanban/tests/test_runtime_query.py -q --tb=short` passed with 9 tests. `uv run ruff check` across the four touched source modules and proof-checkout test passed. An initial package-CWD test run exposed an existing fixture path assumption; the root-CWD rerun is the valid evidence.
- Findings: `ProofCheckoutManager.materialize` verifies a revision but passes the original supplied `commit` text to `git worktree add` and the manifest. A symbolic or abbreviated revision can therefore be recorded as non-canonical, contradicting `DEC-018`'s tested-SHA requirement despite the checkout resolving correctly.
- Required Follow-up: Resolve the input revision with `git rev-parse --verify <commit>^{commit}`; use the canonical returned SHA for the worktree, `ProofCheckout.commit`, and manifest; add a focused real-Git regression using a non-SHA revision and asserting the manifest contains the resolved SHA.
- Prior same-failure-key rejection check: no earlier Verify Notes or failure key exists for canonical-SHA manifest recording.
- Verifier-challenger: fail. It independently identified the canonical-SHA manifest defect and recommended the same focused repair.
- Final route: reject to build; the required implementation and durable regression assertion exceed the verifier's one-owner/no-durable-test patch-pass budget.
