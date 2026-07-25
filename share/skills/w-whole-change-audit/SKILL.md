---
name: w-whole-change-audit
description: "Workflow: Whole-change audit — rehydrate and independently audit a full change"
user-invocable: false
---

# Whole-Change Audit

Authenticate and audit an engine-started `audit` job that carries a whole-change proof checkout.
The auditor validates change-wide receipts, the Product Promise, accepted decisions, IF-014,
PROOF-008, migrations and removals, admitted workflows, request state, allowed lower replacements,
and before/after Git state without mutating tracked lifecycle or implementing corrective work.

## Step 1 — Rehydrate the Started Audit Job

Treat the serialized successful `start_job` result as immutable execution authority. Require all of:

1. The result contains an active `audit` job and started event with no diagnostic. Its change,
   job, attempt, claim, actor, process, and candidate revision identities agree.
2. The result contains the engine-created whole-change proof checkout. Its root and commit identify
   the candidate revision; never substitute the shared worktree or create another checkout.
3. `show_change(change_id)` matches the selected delivery digest. Rehydrate the Product Promise,
   accepted exclusions and preserved behavior, every accepted decision, every admitted migration
   and removal or absence obligation, and every admitted normal workflow from that pinned change.
4. `show_job(change_id, job_id)` matches the supplied target, active claim, current plan identity,
   and exact candidate revision for the whole-change audit.
5. `list_jobs` and `show_receipt` establish one current accept receipt for every required delivery
   node at the candidate revision. No stale or superseded receipt may satisfy the set.
6. `list_requests` confirms no unresolved request blocks WF-005. Rehydrate IF-014's read-only final
   verdict contract and failure semantics.
7. Rehydrate PROOF-008's exact boundary, five required scenarios, allowed lower replacements, and
   durable outputs. Every replacement must be explicitly below an admitted workflow boundary.

Return `AuditBlocked` for stale, malformed, incomplete, contradictory, unsafe, or unavailable
execution identity, checkout, authority, plan, receipt, or proof. Do not select, refresh, repair,
release, or finish work.

## Step 2 — Capture Read-Only Baseline

Record before state in the supplied checkout:

- exact checkout root and candidate SHA
- Product Promise and accepted decisions
- accepted-node receipt set, migrations/removals, admitted workflows, and request state
- IF-014 and PROOF-008 contract identities
- list of admitted lower-layer replacements and why they are permitted
- `git rev-parse --verify HEAD`, `git status --porcelain=v1 --untracked-files=no`, and
  `git diff --binary HEAD --`

All commands must run with the engine checkout as the working directory. Temporary diagnostics and
generated artifacts must live under `.owlbear/scratch/` in that checkout and must not stand in for
the production boundary being audited.

## Step 3 — Execute Whole-Change Proof Envelope

Exercise the complete Product Promise and every admitted normal workflow at the supplied SHA.
Compare observed behavior with accepted decisions, migration/removal and absence obligations,
IF-014, PROOF-008, the current accepted-node receipt set, and closure state. Keep command, exit
status, relevant output, environment facts, replacement identities, and before/after tracked-state
snapshots as evidence.

If tracked index or worktree diverges from the supplied candidate SHA at any point, return
`AuditRejected` with `implementation-defect` findings; do not repair or remove tracked changes.

Classify each failed audit claim using the admitted matrix:

| PROOF-008 failure | Finding class | Corrective target |
|-------------------|---------------|-------------------|
| Cross-node integration failure | `implementation-defect` | `whole-change-integration` |
| Implemented migration/removal absence or failure | `implementation-defect` | `whole-change-integration` |
| Stale acceptance receipt | `implementation-defect` | `whole-change-integration` |
| Admitted Product Promise, decision, workflow, or proof omission | `planning-omission` | `admitted-design-authority` |
| Tracked auditor edit | `implementation-defect` | `whole-change-integration` |

An unresolved request blocks WF-005 and returns `AuditBlocked`; it is not a guessed corrective
finding. For every rejection finding, use a valid immutable `Finding` target kind and identity,
name the source attempt/job, concrete detail, and evidence. Build the invalidation only from the
typed route produced for the matrix row; do not invent another route or corrective job.

If execution identity, checkout, or required authority is stale, malformed, incomplete,
contradictory, unsafe, or unavailable before proof can classify an admitted omission, return
`AuditBlocked` with the specific `target` and `finding`.

## Step 4 — Return One Disposition

Return exactly one object. Preserve the supplied execution identity outside the object; the
orchestrator supplies it unchanged to lifecycle operations.

### `AuditorSuccess`

Use only when the whole-change checkout satisfies the Product Promise, accepted decisions, and
durable receipts. Map unchanged to `finish_audit` parameters:

```yaml
kind: AuditorSuccess
receipt_id: <stable audit receipt identity>
code_revision: <exact tested candidate SHA>
evidence: <assembled proof, per-node receipt closures, replacements, and before/after tracked state>
evidence_ids: [<durable evidence identities>]
impact_closure: <admitted change-level impact closure>  # optional
```

These fields map unchanged to the MCP `finish_audit` signature; do not invent or rename fields.

### `AuditRejected`

Use when exact-commit proof, receipt closure, or tracked-state independence fails:

```yaml
kind: AuditRejected
detail: <concise rejection summary>
evidence_ids: [<proof and tracked-state evidence identities>]
findings: [<complete immutable Finding objects>]
invalidation: <one typed invalidation with supersession and exact minimum corrective jobs>
```

These fields map unchanged to MCP `reject_audit` parameters; forward every field unchanged.

### `AuditBlocked`

Use when the selected work cannot be judged without inventing or replacing missing execution or
proof authority. Map to `release_job` with the unchanged active identity:

```yaml
kind: AuditBlocked
target: <job, checkout, authority, plan, receipt, proof, or evidence target>
finding: <specific stale, malformed, incomplete, contradictory, unsafe, or unavailable condition>
```

Return `AuditBlocked` rather than guessing or selecting another artifact. `AuditBlocked` maps to
`release_job` with unchanged identity and halts orchestration for that pair.

## Step 5 — Stop

Stop after one disposition. Do not call lifecycle tools, classify or assemble corrections beyond the
immutable findings, mutate replacements, or perform other lifecycle mutations. The orchestrator
owns lifecycle routing and any subsequent plan decisions.

## Known Pitfalls

- Do not convert missing accepted decisions into guessed findings; block instead.
- Do not construct new evidence identities; reference durable evidence only.
- Tracked edits authored during audit invalidate independence and must produce `AuditRejected`.
- Do not treat a corrective route target such as `admitted-design-authority` as a finding class.
