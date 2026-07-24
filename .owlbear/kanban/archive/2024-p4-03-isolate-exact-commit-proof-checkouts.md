---
id: 2024
title: 'P4-03: Isolate exact-commit proof checkouts'
status: archived
priority: high
created: 2026-07-24T16:50:58.417043+02:00
updated: 2026-07-24T17:29:31.114843+02:00
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
archival_reason: completed
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

[[2026-07-24T17:24:09+02:00]]
## Builder Notes
- Change envelope: resolve only the verifier's canonical-SHA follow-up within `ProofCheckoutManager` and its existing real-Git proof. No change to checkout containment, cleanup, runtime health, or unrelated delivery behavior.
- Files changed: `serve/kanban/src/owlbear_kanban/proof_checkout.py`; `serve/kanban/tests/test_proof_checkout.py`.
- Change Module Map deviations: none. The repair stays inside the shaped deep checkout owner and its focused proof boundary.
- Implementation: replaced boolean revision existence validation with `_resolve_commit`, which returns `git rev-parse --verify <revision>^{commit}`. The resolved canonical SHA is now the sole value passed to detached `git worktree add`, stored in `ProofCheckout.commit`, and written to the manifest.
- Durable-test justification: added a single real temporary-Git `HEAD` regression because manifest SHA is a security-sensitive external proof fact and symbolic/abbreviated revision handling is otherwise easy to regress without detection.
- Commands run: `uv run pytest serve/kanban/tests/test_proof_checkout.py -q --tb=short` (6 passed); `uv run pytest serve/kanban/tests/test_proof_checkout.py serve/kanban/tests/test_runtime_query.py -q --tb=short` (10 passed); `uv run ruff check serve/kanban/src/owlbear_kanban/proof_checkout.py serve/kanban/tests/test_proof_checkout.py` (all checks passed).
- AC-to-evidence map: AC-1: `test_materialize_uses_exact_commit_read_only_checkout_and_manifest` proves the detached exact checkout, tracked-file read-only policy, and manifest facts; `test_materialize_resolves_symbolic_commit_to_canonical_manifest_sha` proves symbolic `HEAD` records the resolved SHA. AC-2: the existing real-Git invalid-kind, missing-commit, symlinked-root, and unusable-root cases pass. AC-3: the existing idempotent cleanup and public `RuntimeQuery.work_health` orphan case pass in the 10-test focused suite.
- Current failure-key resolution: canonical-SHA manifest recording is fixed by using the `rev-parse` output for worktree creation, returned checkout data, and manifest serialization; the new real-Git `HEAD` test asserts the canonical SHA appears in the manifest.
- Builder-challenger result: pass; bounded two-file diff matches task scope and both focused checks pass.
- Follow-up risks: none for the returned failure key. Future acceptor/auditor lifecycle ownership of cleanup remains outside this task's shaped scope.

[[2026-07-24T17:27:31+02:00]]
## Verify Notes
- Evidence reviewed: task Projection/Outcome/Envelope/AC, both Builder Notes, the returned canonical-SHA diff `79f776531`, `ProofCheckoutManager`, public `RuntimeQuery` health integration, `NativeRuntime` wiring, exports, and focused real-Git tests.
- Named authorities checked: `DN-004`, `IF-005`, `RISK-004`, `PROOF-014`, and accepted `DEC-018`. `DEC-018` requires a disposable read-only checkout under the proof root for the tested exact SHA, normal environment/toolchain, recorded SHA and replacements, and cleanup. The implementation uses the resolved `rev-parse` SHA for detached worktree creation, checkout result, and manifest.
- Change Module Map: no map was supplied. The changed deep checkout owner, existing runtime health facade/wiring, exports, and real-Git proof all match the shaped envelope. No interface or scope deviation found.
- Normal-path boundary exercised: builder evidence uses a real temporary Git repository, actual Git worktree operations, filesystem permissions, YAML manifest serialization, and public `RuntimeQuery.work_health`; no Git/filesystem behavior is replaced above the permitted lower boundary.
- Checks run: verifier `ruff check` over the checkout owner, health integration, runtime wiring, exports, and focused test passed. The focused `pytest` command was externally interrupted twice with exit 130 before output, so it is not claimed as verifier proof. Builder's matching focused real-Git suite passed with 10 tests after the repair.
- Findings and patch: no verifier patch. The prior failure key, canonical-SHA manifest recording, is resolved by `_resolve_commit`; the real-Git symbolic `HEAD` regression asserts resolved SHA output in checkout metadata and manifest.
- AC-to-evidence: AC-1: real-Git materialization checks exact detached HEAD, read-only tracked file, environment/replacement manifest content, plus symbolic `HEAD` canonical SHA. AC-2: real-Git ineligible-kind, missing-commit, symlinked-root, and unusable-root cases check diagnostics and containment. AC-3: a real remaining checkout is visible as `ERR_WORK_PROOF_CHECKOUT_ORPHAN` through public work health; repeated cleanup removes it.
- Prior same-failure-key rejection check: one prior verify rejection identified canonical SHA recording; this repair closes that exact key. No repeated rejection.
- Recalled memory assessed: 6 entries assessed; scope/artifact and active-workspace guidance were applied.
- Verifier-challenger: pass. It confirmed task intent, direct source behavior, scope, and builder real-Git proof support PASS despite verifier terminal interruptions.
- Final route: pass to collect.

[[2026-07-24T17:29:31+02:00]]
## Collect Notes
- Classification: leaf. Task #2024 has no child tasks, carries a `type:build` tag, and contains no aggregate/EPIC intent; its parent relationship does not make this task aggregate.
- Latest verification evidence: newest `## Verify Notes` occurrence records PASS after closing the canonical-SHA manifest follow-up. Focused real-Git proof at commit `79f776531` (the newer verifier note refers to canonical-SHA diff `79f776531`) exercised exact detached HEAD, read-only tracked files, manifest facts, containment diagnostics, idempotent cleanup, and public orphan health. The builder's matching focused suite passed with 10 tests; verifier ruff passed. The verifier's later focused pytest was interrupted externally twice and is not claimed as proof.
- Intent source: task Projection, Outcome, Envelope, and AC-1 through AC-3, governed by DN-004, IF-005, RISK-004, PROOF-014, and accepted DEC-018.
- Invariant map coverage: the verifier maps AC-1 to real-Git materialization, readonly files, manifest and canonical SHA; AC-2 to ineligible, missing, symlinked, and unusable-root diagnostics; AC-3 to public orphan health and repeated cleanup.
- Child coverage: not applicable; `list_tasks(parent=2024)` returned no children.
- Dependency gate: dependency #1979 is archived completed and current `dep_status` is `ok`.
- Residual decisions: `list_requests` returned no pending or resolved structured requests for this task; task is unblocked and the current verifier note names no unresolved follow-up.
- Archive rationale: leaf verification is complete and closure conditions are satisfied; archive as completed.
