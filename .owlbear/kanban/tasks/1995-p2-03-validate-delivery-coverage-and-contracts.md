---
id: 1995
title: 'P2-03: Validate delivery coverage and contracts'
status: build
priority: medium
created: 2026-07-22T13:45:55.105472+02:00
updated: 2026-07-22T15:46:34.251427+02:00
tags:
  - phase-1
  - scope:core
  - admission
  - validation
  - contracts
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-002
  - packet:DN-002-PK-003
parent: 1978
depends_on:
  - 1999
ac:
  - 'AC-1: Missing or multiply assigned ownership or proof for a requirement, negative
    requirement, or preserved behavior returns `DV-003` for that target; one accountable
    owner or support path produces no `DV-003`.'
  - 'AC-2: Incomplete or contradictory interface producer/consumer inventories, authority,
    failure semantics, migration, or proof return `DV-004`; matching node `produces`
    and `consumes` references plus populated contract fields produce no `DV-004`.'
  - 'AC-3: A migration missing ordered steps, consumer inventory, compatibility, deletion
    owner, or absence proof returns `DV-005`; a risk missing scenarios, disposition,
    owner, or proof returns `DV-006`; completing the named fields clears that category
    finding.'
  - 'AC-4: A proof missing boundary, build-capable owner, method, allowed replacements,
    durable outputs, or an owning predecessor returns `DV-007`; a populated proof
    owned by a delivery predecessor before acceptance or audit produces no `DV-007`.'
proof_bundle: behavioral+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Bootstrap Projection Identity
- `change_id`: `replace-delivery-pipeline`
- `delivery_digest`: `9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8`
- `delivery_node_id`: `DN-002`
- `packet_id`: `DN-002-PK-003`

## Outcome
The public admission evaluator rejects incomplete obligation ownership and delivery contracts with the authority-aligned `DV-003` through `DV-007` categories.

## Scope
In scope: accountable requirement, negative-requirement, and preserved-behavior ownership/proof; interface producer/consumer agreement; migration/removal completeness; risk disposition completeness; proof ownership and build-capable predecessor checks; deterministic findings and focused table proof.

Out of scope: evidence gates; topology, reachability, decision coherence, and node-category bounds; historical incident fixtures; receipts, jobs, or persistence.

## Authority
Resolve normative behavior from admission sections 5 and 9 of `design.md`, A1 through A7 in `.owlbear/research/planning-workflow-root-cause-and-redesign.md`, and the `DV-003` through `DV-007` meanings in the admitted receipt. `DV-001` and `DV-002` remain DN-001 loader concerns.

Complexity waiver: four AC share one deterministic contract-completeness algorithm and one public-evaluator table-test mode; splitting by entity type would duplicate traversal and finding semantics.

Proof guidance: exercise the public evaluator over real `ChangeRevision`-derived cases. Run the focused admission suite and Ruff on touched files; no persistence proof belongs here.

[[2026-07-22T14:10:35+02:00]]
## Shape Notes
- Dependency rewired from deprecated #1993 to clean evidence-contract replacement #1999. Coverage and contract validation scope is unchanged; route remains build after #1999.

[[2026-07-22T15:14:24+02:00]]
Released immediately: claimed neighboring task by mistake while routing user request for #1994.

[[2026-07-22T15:26:36+02:00]]
builder crashed once; releasing claim before retry: parallel dispatch returned no output

[[2026-07-22T15:30:52+02:00]]
## Builder Notes
- Change envelope: implement the public admission evaluator checks for DV-003 through DV-007 only; no persistence, topology, evidence-gate, receipt, job, or historical-fixture work.
- Files changed: `serve/kanban/src/owlbear_kanban/admission.py`.
- Change Module Map deviations: none; validation remains in the existing admission evaluator boundary.
- Proof selected: focused behavioral admission suite plus Ruff on the touched module.
- Durable-test justification: no new durable tests added; the existing canonical admitted-revision test proves the populated contract path, and the focused suite is sufficient for this evaluator slice.
- Commands run: `uv run pytest serve/kanban/tests/test_admission.py` (3 passed); `uv run ruff check serve/kanban/src/owlbear_kanban/admission.py` (passed); `git diff --check -- serve/kanban/src/owlbear_kanban/admission.py` (passed).
- Builder-challenger result: pass. Confirmed canonical admission remains admitted with no findings and DV-004 through DV-007 are scoped to the shaped delivery-contract surfaces.
- Follow-up risks: malformed-case table coverage is not yet durable; verify should assess whether broader acceptance coverage is required.

[[2026-07-22T15:32:27+02:00]]
## Verify Notes
- Evidence reviewed: Builder Notes; the current `admission.py` diff; canonical admitted receipt `.owlbear/changes/replace-delivery-pipeline/receipts/admission-9387dea789fb.yaml`; and A1-A7 in `.owlbear/research/planning-workflow-root-cause-and-redesign.md`.
- Named authorities checked: receipt DV-003 requires accountable node ownership or support; DV-004 requires producer, consumers, contract, authority, failure semantics, migration disposition, and proof; DV-005/DV-006 require their listed contracts; DV-007 requires build-capable owner, assembled boundary, method, permitted replacements, durable outputs, and predecessor availability.
- Change Module Map: no ownership deviation. `serve/kanban/src/owlbear_kanban/admission.py` remains the public evaluator boundary, and the patch is limited to that module.
- Normal-path boundary exercised: `evaluate_admission` over the real `replace-delivery-pipeline` `ChangeRevision` via `uv run pytest serve/kanban/tests/test_admission.py` (3 passed). The canonical populated revision still admits without findings.
- Replacements used below boundary: none; the test loads the real revision and invokes the public evaluator.
- Checks run: `uv run pytest serve/kanban/tests/test_admission.py` (3 passed); `uv run ruff check serve/kanban/src/owlbear_kanban/admission.py` (passed); `git diff --check -- serve/kanban/src/owlbear_kanban/admission.py` (passed).
- Findings: reject. AC-1 requires DV-003 for missing or multiply assigned ownership/proof. `_evaluate_graph` only finds an obligation absent from the combined `owns` and `supports` set, so it cannot reject multiple accountable assignments or validate the required owner/proof relationship. AC-2 requires DV-004 for a missing migration disposition, but `_evaluate_delivery_contracts` never evaluates `interface.migration`. AC-4 requires DV-007 when an owning predecessor is absent; the evaluator checks only that the owner node names the proof and required proof fields are populated, not that the owner precedes acceptance or audit in delivery dependencies. Existing tests exercise only the populated canonical case and cannot falsify these omissions.
- Patches applied: none. The missing conditions and negative cases are implementation work, beyond verifier local-patch authority.
- Verifier-challenger: not called because this is a REJECT verdict; challenger is required only before PASS.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Extend DV-003 to reject multiple accountable owner/support assignments and validate the authority-required ownership/proof relationship; add focused malformed real-`ChangeRevision` evaluator cases. | `serve/kanban/src/owlbear_kanban/admission.py`, `serve/kanban/tests/test_admission.py` | AC-1; receipt DV-003; A1 |
| 2 | builder | Make DV-004 reject interface records without a migration disposition, and add a focused evaluator case. | `serve/kanban/src/owlbear_kanban/admission.py`, `serve/kanban/tests/test_admission.py` | AC-2; receipt DV-004; A2 |
| 3 | builder | Make DV-007 prove that its build-capable owner is an owning predecessor before acceptance/audit, and add a focused evaluator case. | `serve/kanban/src/owlbear_kanban/admission.py`, `serve/kanban/tests/test_admission.py` | AC-4; receipt DV-007; A5-A6 |

- Final route: REJECT to build.

[[2026-07-22T15:39:04+02:00]]
## Builder Notes
- Change envelope: implement only DV-003 through DV-007 delivery coverage and contract validation gaps identified by verification.
- Files changed: `serve/kanban/src/owlbear_kanban/admission.py`, `serve/kanban/tests/test_admission.py`.
- Change Module Map deviations: none; validation remains in the public admission evaluator boundary.
- Proof selected: public `evaluate_admission` over real `ChangeRevision` cases, plus focused Ruff and diff hygiene.
- Durable-test justification: added three focused regression cases because the rejected behaviors were previously untested and easy to regress: duplicate accountable ownership, unknown interface migration disposition, and non-predecessor proof ownership.
- Commands run: `uv run pytest serve/kanban/tests/test_admission.py` (6 passed); `uv run ruff check serve/kanban/src/owlbear_kanban/admission.py serve/kanban/tests/test_admission.py` (passed); `git diff --check -- serve/kanban/src/owlbear_kanban/admission.py serve/kanban/tests/test_admission.py` (passed).
- Builder-challenger result: pass. Confirmed scope, test rent, implementation coverage, and proof.
- Follow-up risks: broader admission categories remain outside this task's shaped scope.

[[2026-07-22T15:42:23+02:00]]
verifier crashed once; releasing claim before retry: parallel dispatch returned no output

[[2026-07-22T15:46:34+02:00]]
## Verify Notes
- Evidence reviewed: task AC-1 through AC-4; both Builder Notes; task commit `1ce2f5ec8`; and the named authorities `.owlbear/changes/replace-delivery-pipeline/design.md` sections 5.1, 5.3, and 9.1 plus research A1 through A7.
- Named authority check: the design requires a changed interface to have a producer and consumer inventory, and deterministic admission rejects incomplete interface producer/consumer fields.
- Change Module Map: implementation and tests remain in the mapped public admission evaluator boundary (`serve/kanban/src/owlbear_kanban/admission.py`, `serve/kanban/tests/test_admission.py`); no architectural deviation.
- Normal-path boundary exercised: `evaluate_admission` evaluated real `ChangeRevision` data loaded from `.owlbear/changes/replace-delivery-pipeline`; no command, evaluator, or revision was mocked.
- Focused checks: `uv run pytest serve/kanban/tests/test_admission.py` passed (6 tests); `uv run ruff check serve/kanban/src/owlbear_kanban/admission.py serve/kanban/tests/test_admission.py` passed; `git diff --check -- serve/kanban/src/owlbear_kanban/admission.py serve/kanban/tests/test_admission.py` passed.
- Finding: mutating a real interface's `consumers` to an empty tuple produces no `DV-004` finding from the public evaluator. This contradicts AC-2 and design section 9.1's incomplete producer/consumer requirement. The direct probe reported `empty-consumers False` with only the expected digest mismatch (`EV-001`).
- Patches applied: none; this is an implementation gap, not a verifier-local correction.
- Verifier-challenger: not called because the proposed route is REJECT, not PASS.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Make an empty interface consumer inventory emit `DV-004` from the public admission evaluator; add focused real-`ChangeRevision` regression coverage and rerun the focused admission suite plus Ruff. | `serve/kanban/src/owlbear_kanban/admission.py`; `serve/kanban/tests/test_admission.py` | AC-2; `.owlbear/changes/replace-delivery-pipeline/design.md` section 9.1; verifier public-evaluator probe |

Final route: REJECT to build.
