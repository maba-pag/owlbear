---
id: 2093
title: 'P16-07: Prove atomic cutover and consumer setup'
status: collect
priority: high
created: 2026-07-27T08:40:26.563879+02:00
updated: 2026-07-27T12:34:55.571724+02:00
tags:
  - phase-16
  - scope:test
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - digest:6c95c70c81a1
  - node:DN-012
  - packet:T7
  - module:MOD-008
  - proof:PROOF-009
parent: 1989
depends_on:
  - 2087
  - 2090
  - 2091
  - 2088
  - 2089
  - 2092
ac:
  - 'AC-1: Given a populated legacy repository with complete dispositions and a fresh
    consumer repository, invoking public cutover and setup produces matching manifest
    hashes and counts, clean native stores, a successful native launch, and no executable
    old runtime surface.'
  - 'AC-2: Given an existing destination, a missing disposition, a source mutation,
    or an induced publication interruption, the assembled boundary publishes no completed
    receipt, does not overwrite history, leaves a recoverable source, and succeeds
    after the cause is corrected.'
  - 'AC-3: Given a successful fixture cutover, the proof output records the invoked
    command, expected authority and code revisions, manifest and hash identities,
    finalization receipt, and returned commit paths required by DN-015 while demonstrating
    that the live self-hosting board was not an input.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
PROOF-009 exercises public setup and the public cutover command against populated legacy and fresh consumer repositories, proving atomic fixture cutover, recovery, native launch, old-surface absence, and the evidence handoff required by terminal DN-015.

## Scope
In scope: durable assembled setup, snapshot, absence, and distribution scenarios over temporary repositories at the public command boundaries.

Out of scope: historical/generic complete-system proof owned by DN-013, real self-hosting board mutation, DN-015 dispatch, and PROOF-016 exact-commit acceptance.

## Authority
DN-012 at delivery digest `6c95c70c81a13ef7a59206ac63bfd9b7338ccb87520d22d90517bf67d50167e9`; PROOF-009, IF-013, IF-016, REQ-011/REQ-012/REQ-017, MIG-001 through MIG-004, RISK-001/RISK-005, DEC-036, and outputs from #2087 through #2092.

Proof guidance: invoke public setup and cutover commands without replacing those boundaries; temporary repositories and the package-install recorder are permitted below them. Record command, revisions, manifests, hashes, receipt, and returned commit-path evidence; never target the live board.

[[2026-07-27T12:32:20+02:00]]
## Builder Notes

DONE. Adopted and completed the interrupted #2093 change envelope without touching the live self-hosting carrier or unrelated dirty state.

### Changed Files
- `serve/cockpit/web/e2e/support/seed-native-proof-stack.py`
- `serve/cockpit/web/e2e/native-proof-assembled.spec.ts`
- `tests/test_bootstrap_finalizer_command.py`
- `tests/test_native_cutover.py`
- `serve/kanban/src/owlbear_kanban/workspace.py`
- `serve/kanban/tests/test_workspace.py`

### AC Evidence
- AC-1: The assembled fixture invokes public `setup/finalize.py` and `setup/init.py`, verifies the immutable `kanban-final` manifest/counts/hashes, checks clean native stores and explicit old-surface absence, launches the real Cockpit process, and completes serial desktop/mobile journeys. The 65-test focused regression and two Playwright journeys passed.
- AC-2: Public-command tests cover existing destination, missing disposition, corrected source mutation replay, and induced publication interruption replay. They prove no completed receipt/overwrite on failure, recoverable source, and success after correction.
- AC-3: `.owlbear/proof-009.json` records both commands, expected delivery/code revisions, source and manifest hashes, finalization receipt, returned commit paths, fixture/live source identities, and an explicit DN-015 handoff. A fail-closed guard and assertions prove the temporary fixture carrier is not the live `.owlbear/kanban` input.

### Validation
- Focused Python regression: 65 passed; four pre-existing Starlette deprecation warnings.
- Dedicated assembled Playwright project: 2 passed serially across desktop and mobile.
- Cockpit CSS/HTML lint, TypeScript build, and Vite production build passed.
- Ruff check/format, VS Code diagnostics, and Git diff integrity checks passed.
- Builder challenger initially failed the implicit AC-3 evidence; explicit handoff/live-input/absent-surface evidence was added, focused and full checks reran, and the required challenger retry passed. Challenger independently reran 14 finalizer/cutover/workspace tests successfully.
- All 20 recalled builder memories were assessed for task #2093.

[[2026-07-27T12:34:55+02:00]]
## Verify Notes

PASS. Independently verified builder commit `7c6ac26def71ba737d9c4db0b03232ec6e583224` against all three ACs and the DEC-036 temporary-carrier boundary.

### Independent Evidence
- AC-1: Public finalizer/setup, native distribution/launch, workspace, and Cockpit integration suite passed; the dedicated real Cockpit desktop/mobile Playwright project passed both journeys serially. Assertions cover matching manifest count/hashes/receipt, clean native stores, and explicit absence of old executable surfaces.
- AC-2: Public-command scenarios prove missing disposition, existing destination, source mutation, and induced publication interruption fail closed without a completed receipt or overwrite, then replay successfully after correction.
- AC-3: The generated proof records exact commands, authority/code revisions, source/manifest hashes, finalization receipt, returned paths, and DN-015 handoff. Source confinement and explicit guard/assertions prove the live self-hosting board was not input.

### Checks
- Focused Python verification: 65 passed; four pre-existing Starlette deprecation warnings.
- Real assembled browser verification: 2 passed across desktop and mobile.
- Commit audit: exactly six declared code/proof files plus the #2093 task record; diff integrity clean.
- Verifier challenger: pass with no unresolved finding.
- All 20 recalled verifier memories assessed.
