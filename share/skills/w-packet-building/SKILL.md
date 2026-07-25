---
name: w-packet-building
description: "Workflow: Build one engine-selected implementation packet through scoped commit and inline review"
user-invocable: false
---

# Packet Building

Process one engine-selected `build` job in a single warm shared-worktree session. The builder
implements the complete packet outcome, creates one scoped commit, resolves mandatory independent
review, and returns one structured disposition. The engine remains the authority for selection,
claims, writer coordination, receipts, and downstream work.

This workflow owns implementation inside the selected packet's admitted impact closure. It cannot
edit delivery authority, node plans, jobs, receipts, requests, or another packet's implementation.

## Companion Skills

Load these with `read_file` immediately before the named work:

| Skill | Load when |
|-------|-----------|
| `h-codebase-orientation` | Locating current owners, callers, proof commands, and canonical contracts |
| `h-module-design` | A local implementation choice affects dependency placement or module locality |
| `h-pytest-and-linting` | The packet changes Python or Python proof |
| `h-vitest-and-linting` | The packet changes the Cockpit frontend or frontend proof |
| `r-workspace-governance` | Establishing path custody and creating the scoped commit |

## Authority Boundary

The orchestrator supplies the complete result of one successful public `start_job` call. Treat its
job, attempt, claim, actor, process, candidate revision, change identity, delivery digest, target
node, node-plan digest, packet identity, and timestamps as immutable execution identity. Do not
pick, start, finish, release, or recover work from this workflow.

The builder may:

- query current change, job, receipt, request, activity, and health projections;
- inspect admitted authority, the current target-node plan, repository source, history, and tests;
- edit only packet-owned implementation outputs and proportionate durable proof;
- run focused proof and create one commit from explicit owned paths;
- delegate one mandatory review with system-generated context;
- repair an `implementation-defect` inside the same packet and request fresh review;
- return one structured disposition to the orchestrator.

Only the orchestrator maps a returned disposition to public `finish_build` or `release_job`.

## Step 1 - Rehydrate The Selected Packet

Complete this check before any tracked-file edit, including after resuming a warm session:

1. Require the supplied result to contain a started job and event, with no diagnostic, and require
   the job kind to be `build`.
2. Require the active job claim, attempt, actor, process, and claim timestamp to match the supplied
   execution identity.
3. Call `show_change(change_id)` and require its delivery digest to match the selected job.
4. Call `show_job(change_id, job_id)` and require its target node, packet identity, node-plan digest,
   delivery digest, and active claim identity to match the supplied result.
5. Read the current admitted target node and `plans/<target-node-id>.yaml`. Require exactly one
   packet with the selected packet identity and require the current node-plan digest to match the
   selected job.
6. Call `show_receipt` for the current plan receipt and each required predecessor receipt. Require
   their authority, code revision, and validity to satisfy the selected job's current prerequisites.
7. Inspect the candidate repository revision and focused source named by the packet's impact closure.
   Require all pre-existing changes intersecting that closure to have explicit, unambiguous custody.

Return `BuildBlocked` for stale, malformed, incomplete, or contradictory execution identity,
authority, plan, receipt, repository, or custody evidence. Do not choose the newest-looking artifact,
silently refresh the digest, broaden the packet, or edit before the check passes.

## Step 2 - Fix The Change Envelope

Derive one bounded implementation envelope from the selected packet:

- outcome and admitted obligations advanced;
- required outputs across code, tests, documentation, migration, and generated artifacts;
- canonical impact-closure paths and authority targets;
- consumed and produced interfaces;
- focused proof boundary, commands or observations, allowed lower replacements, and evidence outputs;
- explicit exclusions and packet dependencies.

Use repository evidence to resolve implementation facts inside that envelope. Do not add a product
outcome, public or cross-module interface, migration, compatibility path, security policy, lifecycle
semantic, proof boundary, delivery dependency, or path outside the admitted packet closure.

## Step 3 - Implement And Prove The Outcome

Keep one warm session under the existing engine-owned writer claim. Implement every packet-required
output needed for the outcome, including proportionate tests or generated artifacts when the packet
requires them. Preserve unrelated user changes and do not acquire a second writer claim or dispatch
another job.

Run the smallest proof that exercises the packet's maintained or public boundary. Record commands or
observations, exit status, relevant output, replacements, environment facts that affect the result,
and the exact impact closure exercised. A mock may replace only lower layers allowed by the packet's
proof contract.

If implementation or proof exposes work outside the envelope, stop editing and classify the finding
under Step 6. Do not turn discovered scope into an implicit packet expansion.

## Step 4 - Create One Scoped Commit

Load `r-workspace-governance` and inventory every packet-owned durable path. Use the repository's
scoped commit mechanism with explicit paths; never pass a broad directory or include unrelated,
pre-existing, control-plane, job, receipt, or authority changes. The commit must contain the complete
packet implementation and its admitted durable proof outputs.

After commit, require:

- the commit exists and is a descendant of the selected candidate revision;
- its changed paths equal the reviewed packet-owned path set;
- no tracked packet-owned change remains outside the commit;
- unrelated workspace and index bytes are unchanged;
- recorded proof still identifies the committed implementation.

If the scoped commit cannot be created or verified, return `CommitFailed`. Do not review uncommitted
work, issue finish fields, retry with a broad commit, or absorb unrelated paths.

## Step 5 - Generate Mandatory Review Context

Construct reviewer context from current artifacts after the commit. Include all of:

| Field | Required content |
|-------|------------------|
| execution | Change, delivery digest, node, packet, node-plan digest, job, attempt, and claim identities |
| authority | Admitted node, obligations, interfaces, risks, workflow, proof, and packet acceptance scenarios |
| envelope | Required outputs, exclusions, dependencies, and exact impact closure |
| change | Base and committed revision, complete diff, and canonical changed paths |
| proof | Commands or observations, results, replacements, environment facts, and evidence identities |
| custody | Scoped commit result and preservation of unrelated workspace and index state |
| prior findings | Typed findings and resolutions from earlier review rounds in this attempt |

Invoke a fresh read-only build reviewer against this generated context. The reviewer must inspect the
committed diff and source-ground every pass or finding against packet authority. It cannot edit,
commit, choose product direction, request generic extra tests, or invoke lifecycle operations.

Missing, malformed, contradictory, or non-source-grounded review context or output returns
`BuildBlocked`. Builder self-review and a reviewer pass against an older commit do not satisfy the
gate.

## Step 6 - Resolve The Review Disposition

Classify every finding with exactly one canonical class:

| Finding class | Builder disposition |
|---------------|---------------------|
| `implementation-defect` | Repair only inside the current packet, rerun affected proof, create a scoped repair commit, regenerate all review context, and require a fresh reviewer pass. |
| `unforeseeable-discovery` | Return `SpecificationReentry` with the exact class, target, finding, and evidence. |
| `planning-omission` | Return `SpecificationReentry` with the exact class, target, finding, and evidence. |
| `scope-change` | Return `SpecificationReentry` with the exact class, target, finding, and evidence. |

An `implementation-defect` repair remains in the same warm claimed attempt. Its repair commit must be
inside the original impact closure, and the final review context must expose the original finding,
resolution, complete cumulative diff, current proof, and new commit identity. No receipt fields may
be returned before the fresh pass.

If a purported local repair changes packet boundaries, admitted authority, or the proof contract,
reclassify it to the applicable non-local finding. Never weaken acceptance, hide a finding, or reuse
an earlier pass.

## Step 7 - Return One Structured Disposition

Return exactly one of these objects to the orchestrator. Do not wrap it in prose.

### `BuilderSuccess`

Use only after the current committed packet has a fresh review pass:

```yaml
kind: BuilderSuccess
receipt_id: <new stable build receipt identity>
code_revision: <reviewed scoped commit SHA>
evidence: <packet proof, reviewer findings and resolutions, and commit evidence accepted by finish_build>
evidence_ids: [<durable evidence identities>]
impact_closure: <reviewed canonical paths and admitted authority targets>
```

These keys match the builder-owned inputs of public `finish_build`. The orchestrator supplies the
unchanged change, job, attempt, claim, actor, process, and completion-time identity from dispatch.

### `SpecificationReentry`

```yaml
kind: SpecificationReentry
finding_class: <unforeseeable-discovery | planning-omission | scope-change>
target: <authority, packet, proof, or code target>
finding: <specific contradiction or unadmitted work>
evidence: <source-grounded reason the current packet cannot own it>
```

### `CommitFailed`

```yaml
kind: CommitFailed
command: <scoped commit operation that failed>
error: <bounded failure detail>
changed_paths: [<packet-owned paths left uncommitted or unverifiable>]
```

### `BuildBlocked`

```yaml
kind: BuildBlocked
target: <job, authority, plan, receipt, repository, review, or evidence target>
finding: <specific stale, malformed, incomplete, contradictory, or ambiguous condition>
```

Only `BuilderSuccess` contains `finish_build` fields. Every other disposition leaves the active
identity unchanged for the orchestrator's identity-preserving `release_job`, native-mode halt, and
user-facing report.

## Step 8 - Stop After The Disposition

Discard packet-local working state after returning. Do not pick, start, release, finish, or continue
into another job. A later invocation must receive a new successful public `start_job` result and
repeat complete rehydration before editing.

## Known Pitfalls

- **Self-selection:** only the orchestrator may pick and start a build job.
- **Digest refresh by assumption:** stale packet or node-plan identity blocks edits; it is not a hint to use another digest.
- **Artifact-specific progress:** code, proof, docs, migration, and generated outputs complete one packet outcome, not separate workflow stages.
- **Review before commit:** the reviewer evaluates the exact commit proposed for the build receipt.
- **Reviewer repair:** the reviewer reports findings; only the claimed builder may edit or commit.
- **Warm scope expansion:** only `implementation-defect` remains local, and only inside the original packet closure.
- **Direct lifecycle mutation:** return one disposition; never call `finish_build`, `release_job`, `start_job`, or `pick_jobs`.
