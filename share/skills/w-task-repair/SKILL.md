---
name: w-task-repair
description: "Workflow: Repair tasks rejected to shape, applying complete follow-up instructions and escalating material changes to the user"
user-invocable: false
---

# Task Repair

Repair one task or an explicit connected set returned to `shape` by builder, verifier, or collector.
Start from the rejection evidence. Do not rerun full spec shaping when the downstream agent already
supplied a complete, non-material correction.

## Companion Skills

Load these via `read_file` when needed:

| Skill | Load when |
|-------|-----------|
| `h-mcp-kanban` | Claiming, editing, moving, or splitting tasks |
| `w-task-decomposition` | A material or explicitly prescribed split is required |
| `w-spec-shaping` | Repair exposes a material implementation decision |
| `h-ac-quality` | Acceptance criteria need repair |
| `h-codebase-orientation` | Rejection evidence depends on a current-source claim |

## Step 1 - Resolve Ownership And Read The Rejection Chain

Identify whether the selected work is one task or an explicit connected set that cannot be repaired
coherently one task at a time. For a connected set, name the complete task IDs and why joint mutation
is necessary; mere proximity or shared topic is insufficient. Follow `r-pipeline-protocol` to claim
every existing task before the first write. Read each latest `### Required Follow-up` and the agent
section that produced it. Read earlier Shape, Builder, Verify, and Collect Notes only as needed to
understand the current route and avoid reviving superseded instructions.

Treat each failure key in the latest follow-up as the repair identity. Preserve the key while
diagnosing and repairing it; wording changes do not make the defect new. A task cannot leave shape
until Shape Notes name how each current key was resolved or why the corrected route no longer
requires it.

Treat downstream findings as evidence, not infallible authority. Check a narrow source or board fact
when it can cheaply disconfirm the requested repair.

### Repair Closure Gate

Use this gate when a failure key has recurred, passing proof was later rejected, the repair crosses
an assembled boundary, or current source may have drifted from the shaped contract. Ordinary
mechanical reroutes and single-boundary wording fixes do not need the map.

Before editing the task, append a compact Repair Closure Map to the proposed repair evidence:

| Failure Key | Claimed Production Boundary | Current-Source Artifacts | Cheapest Disconfirming Check | Causal Proof Or Negative Control | Executor Availability |
|-------------|-----------------------------|--------------------------|------------------------------|----------------------------------|-----------------------|
| {current key} | {command, workflow, assembled context, or public operation} | {live owners and derived consumers checked} | {source observation or focused probe} | {what must control what; how bypass fails} | {installed executor or observable fail-closed state} |

Rules:

- Read every named live artifact that owns or exposes the claimed boundary; task notes and passing
   component tests are not substitutes for current source.
- State the causal relationship under proof. A scenario that independently scripts an expected
   result and the matching action proves correlation only unless the returned value selects the
   action and a negative control or operation ledger would detect bypass.
- Resolve unavailable tools, agent profiles, mutation owners, and downstream capabilities before
   approval. Use an accepted fail-closed behavior or route the missing premise; do not hide it below
   a replacement or fixture.
- Give the complete map to `shaper-challenger`. A missing or contradicted row blocks routing to
   `build`, even when the repaired AC wording is individually valid.

## Step 2 - Classify The Repair

Classify before changing the board:

| Class | Meaning | Default action |
|-------|---------|----------------|
| Mechanical reroute | Correct work entered the wrong status or missed a required pipeline stage | Apply autonomously |
| Local task repair | Complete instructions correct wording, AC, dependency, proof guidance, or metadata without changing intended behavior or architecture | Apply autonomously |
| Prescribed split | Rejection supplies a complete split whose outcomes and meaning are already determined | Apply autonomously, then audit |
| Material reshape | Repair changes product behavior, scope, architecture, compatibility, security, acceptance meaning, or the task graph beyond complete instructions | Escalate interactively |
| Insufficient rejection | Follow-up is contradictory, incomplete, or cannot identify a valid route | Ask for the missing material decision or record a blocking request |

Task count alone does not make a split or connected repair material. It is material when the shaper
must invent or choose outcomes, boundaries, ownership, or ordering rather than execute complete
instructions.

## Step 3 - Apply Explicit Non-Material Repairs

For a mechanical reroute, local repair, or prescribed split:

1. Apply the smallest board change that satisfies the latest follow-up.
2. Preserve approved intent, unaffected AC, parent links, and dependencies.
3. Do not repeat broad orientation, research, Product Promise review, or decomposition ceremony when
   the rejection does not call those premises into question.
4. Audit every task in the mutation set for resulting status, dependencies, parent links, and
   required next agent.

Do not ask the user to confirm a complete non-material repair. Report what changed in the final
human summary.

## Step 4 - Escalate Material Expansion

If narrow diagnosis exposes a material defect beyond the rejection instructions, stop before task
or OpenSpec mutation. Explain:

- the original rejection and repair it requested;
- the newly discovered problem and evidence;
- why the original repair would knowingly restore an invalid route;
- the recommended architecture, scope, AC, or graph change;
- meaningful alternatives and their consequences.

Use `askQuestions` for the material decision. Load `w-spec-shaping` and use its Material Repair
Re-entry table to resume at the earliest affected review stage without repeating accepted premises.
When the affected work has an OpenSpec planning source, update accepted changes in the owning
artifact, challenge the revised draft graph, and obtain user approval before writes. For a
standalone task, conduct the same focused review against its task authority and approval boundary;
do not require an OpenSpec package merely because the task was rejected.

Strong source evidence is grounds for a recommendation, not authority to make a material decision
silently.

## Step 5 - Record Task History

Append `## Shape Notes` through the task lifecycle operation. Include:

- rejection source and repair classification;
- the Repair Closure Map when the gate was triggered, including the current-source checks and
   challenger disposition for each failure key;
- facts checked and any contradiction resolved;
- exact task, dependency, AC, or status changes;
- each current failure key and the authority, contract, or route change that resolves it;
- user decision and planning-artifact revisions when material escalation occurred;
- resulting route and board audit.

Channel B is mandatory for repaired existing tasks. It is the durable task history, not the
user-facing response format.

## Step 6 - Return A Human Summary

Tell the user what was repaired, why it was autonomous or interactive, and where the task now routes.
For a split, include the resulting tasks and dependency order. Do not reduce the response to an
`APPROVED`, `REFINE`, or `BLOCK` line.
