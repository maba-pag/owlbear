---
name: w-orchestration
description: "Workflow: Orchestration — plan, dispatch, and verify agent execution cycles"
user-invocable: false
---

# Orchestration

Dispatch fresh engine plans until no work remains.

## Context Budget

- `rate_limited` starts `False`. After one rate-limit error, use `wave_size=1` for the rest of the session.
- `cycle_count` starts at 1 and increments after each cycle.
- Keep no board state between plans.

## Native Dispatch Contract

For an admitted `change_id`, call `pick_jobs` for the current candidate revision, call `start_job` for
one returned entry, dispatch only its assigned profile, and pattern-match its structured disposition.
The profile-specific success object selects the matching `finish_plan`, `finish_build`,
`finish_accept`, or `finish_audit`;
`RateLimited` selects `release_job`; `Crash` selects strict-expiry `recover_expired_claims`. Then obtain
a fresh plan. Each profile processes exactly one started job and stops. Do not route by prose or
bridge native jobs to task lifecycle state.

For an engine-selected `planner`, dispatch `runSubagent(agentName="planner")` with only the complete
successful `start_job` result serialized as its prompt. Pattern-match one exact disposition:

- `PlannerSuccess`: call `finish_plan` with the unchanged change, job, attempt, claim, actor, and
   process identity from the started job, an orchestrator-owned completion timestamp, and the
   returned `receipt_id`, `code_revision`, `evidence`, `evidence_ids`, `impact_closure`, `node_plan`,
   `build_job_ids`, and `accept_job_id`. Do not inspect, complete, or reconstruct `node_plan`.
- `RequestCreated`: call `release_job` with the unchanged active identity, then obtain a fresh
   `pick_jobs` result. The pending request is an engine dispatch gate.
- `SpecificationReentry`: call `release_job`, halt native mode, and report the returned target,
   finding, and evidence for user-facing `/design` re-entry. Do not edit Specification or legacy task
   state.
- `PlanBlocked`: call `release_job`, halt native mode, and report the returned target and finding.

Malformed planner output is an unstructured return and follows crash recovery. The orchestrator
never creates a planner Decision Request or node plan itself.

For an engine-selected `builder`, dispatch `runSubagent(agentName="builder")` with only the complete
successful `start_job` result serialized as its prompt. Pattern-match one exact disposition:

- `BuilderSuccess`: call `finish_build` with the unchanged change, job, attempt, claim, actor, and
   process identity from the started job, an orchestrator-owned completion timestamp, and the
   returned `receipt_id`, `code_revision`, `evidence`, `evidence_ids`, and `impact_closure`. Do not
   inspect, reconstruct, or supplement those returned fields.
- `SpecificationReentry`: call `release_job` with the unchanged active identity, halt native mode,
   and report the returned finding class, target, finding, and evidence for user-facing `/design`
   re-entry. Do not create a corrective job, request, receipt, or authority edit.
- `CommitFailed`: call `release_job` with the unchanged active identity, halt native mode, and report
   the returned command, error, and changed paths. Do not broaden or retry the commit from the
   orchestrator and do not issue a receipt.
- `BuildBlocked`: call `release_job` with the unchanged active identity, halt native mode, and report
   the returned target and finding. Do not create corrective work or issue a receipt.

Malformed builder output is an unstructured return and follows crash recovery. The orchestrator
never reviews, repairs, commits, classifies findings, or assembles build evidence itself.

For an engine-selected `acceptor`, dispatch `runSubagent(agentName="acceptor")` with only the complete
successful `start_job` result, including the engine checkout, serialized as its prompt. Pattern-match
one exact disposition:

- `AcceptorSuccess`: call `finish_accept` with the unchanged change, job, attempt, claim, actor, and
   process identity from the started job, an orchestrator-owned completion timestamp, and the returned
   `receipt_id`, `code_revision`, `evidence`, `evidence_ids`, `impact_closure`, and
   `reconciliation_plan_job_ids`. Forward every returned field unchanged.
- `AcceptanceRejected`: call `reject_accept` with the unchanged active identity, an orchestrator-owned
   rejection timestamp, and the returned `detail`, `evidence_ids`, `findings`, and `invalidation`.
   Forward every returned field unchanged.
- `AcceptanceBlocked`: call `release_job` with only the unchanged active identity and an
   orchestrator-owned release timestamp, halt native mode, and report the returned target and finding.

Malformed acceptor output is an unstructured return and follows crash recovery. The orchestrator
never executes acceptance proof, classifies findings, plans corrective routes, assembles evidence,
alters replacements, or supplements a disposition.

For an engine-selected `auditor`, dispatch `runSubagent(agentName="auditor")` with only the complete
successful `start_job` result, including the engine checkout, serialized as its prompt. Pattern-match
one exact disposition:

- `AuditorSuccess`: call `finish_audit` with the unchanged change, job, attempt, claim, actor, and
   process identity from the started job, an orchestrator-owned completion timestamp, and the returned
   `receipt_id`, `code_revision`, `evidence`, `evidence_ids`, and optional `impact_closure`. Forward
   every returned field unchanged.
- `AuditRejected`: call `reject_audit` with the unchanged active identity, an orchestrator-owned
   rejection timestamp, and the returned `detail`, `evidence_ids`, `findings`, and `invalidation`.
   Forward every returned field unchanged.
- `AuditBlocked`: call `release_job` with only the unchanged active identity and an
   orchestrator-owned release timestamp, halt native mode, and report the returned `target` and
   `finding`.

Malformed auditor output is an unstructured return and follows crash recovery. The orchestrator
never executes audit proof, classifies findings, assembles evidence, plans corrections, alters
replacements, or supplements a disposition. It preserves the returned fields verbatim.

Before `start_job`, resolve the selected profile against the installed subagent allowlist. If it is unavailable,
report the profile and halt without claiming or running the job. Role bodies remain in their owning
agent and workflow files.

For `accept` and `audit`, `start_job` returns the engine-owned exact-commit checkout context. The orchestrator
does not materialize or clean it independently; finish, release, and recovery own checkout cleanup.

## Step 1 — Housekeeping

Every 10th cycle (`cycle_count % 10 == 0`), dispatch:

```
runSubagent(agentName="memory-curator", prompt="Curate: Periodic curation", description="Curation")
```

Curator failure does not stop dispatch.

## Step 2 — Plan

Call `pick_jobs` for the admitted change and candidate revision, using `wave_size=1` after a rate limit.

If no entries are returned, report completion and stop.

## Step 3 — Dispatch

Dispatch waves in returned order without re-bucketing. Start and dispatch each returned job once. A
structured result never authorizes the next job; only a fresh `pick_jobs` plan does.

### Dispatch Mechanics

Use `runSubagent(agentName=profile, prompt=serialized_start_result, description=description)`. The
prompt contains only the complete successful `start_job` result; the description is display-only.

**Error handling:** Classify agent returns top-to-bottom. First match wins.

1. **Unstructured return contains `rate-limited | rate_limited | rate limits`:** set
   `rate_limited=True`, retry the same pair once, and keep later plans sequential.
2. **Crash or unstructured return:** call `release_job` with the unchanged active identity and an
   orchestrator-owned timestamp, then retry once from a fresh plan. A second crash halts orchestration.

## Step 4 — Loop

After all waves, increment `cycle_count` and re-plan. Normal completion requires empty waves; user
intervention or a halting error above may stop earlier.

## Output Format

During execution:

```
Cycle 1 (Plan): Running pick_jobs(change_id=replace-cache)...
Cycle 1 (Wave 1/2): job 103 (builder)
Cycle 1 (Done): 3/4 succeeded, 1 crashed (job 112)
```

At end of session:

```
Session complete:
  Completed: #101, #103, #105
  Failed: #112 (crashed twice)
  Cycles: 2
```
