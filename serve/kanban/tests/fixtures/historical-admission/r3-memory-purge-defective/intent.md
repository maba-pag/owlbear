# Replace the OwlBear Delivery Pipeline

> **Change ID:** `r3-memory-purge-defective`
> **Owning intake:** #1968
> **State:** Approved, pending admission
> **Authority:** This file owns product intent. Technical realization belongs in `design.md`; execution ownership belongs in `graph.yaml`; material choices belong in `decisions.yaml`.

## Problem

OwlBear's current idea-to-delivery pipeline repeatedly admits task graphs that look complete but omit known product-path work. Four consecutive OpenSpec changes required late graph expansion or material reshaping after implementation began. The pipeline preserves document structure and local task evidence but does not prove that interfaces, migrations, destructive semantics, proof infrastructure, and normal workflows form one executable product.

The current system also divides authority poorly:

- `/ideate` leaves confirmed intent in chat;
- OpenSpec synthesizes intent, requirements, design, and advisory tasks before independent grounding;
- `/shape` repairs an anchored task suggestion and copies durable claims into task prose;
- builders and verifiers process isolated task IDs;
- collectors reconstruct product coherence after local work has passed; and
- OpenSpec contributes little after its proposal command is removed, while imposing setup, generated-command, schema, vocabulary, and duplicate-authority costs.

This is a control-plane architecture defect. Incremental prompt additions cannot correct it.

## Product Promise

OwlBear will provide one native, resumable path from rough idea to accepted change:

1. A user collaborates with one `/design` session that persists intent, decisions, evidence, architecture, interfaces, migration, risk, proof, and a complete delivery graph as understanding develops.
2. The user is asked one material decision at a time with explicit options, pros, cons, risks, recommendation, and confidence. Repository-answerable facts are researched rather than delegated to the user.
3. Admission certifies a specific semantic revision for layered delivery completeness before any implementation work enters Kanban.
4. Kanban remains OwlBear's implementation control surface. Each admitted delivery node receives one bounded `shape` job; shaping creates the outcome-cohesive build packets needed for that node without changing its admitted delivery obligations.
5. Builders implement one packet in a shared worktree under a global writer lease and resolve mandatory read-only reviewer findings in the same warm session.
6. An independent acceptor proves each delivery node against its authoritative contract, all descendant receipts, and the exact committed revision. A final independent auditor proves the complete user workflow and issues the change receipt.
7. Rejections create typed findings, corrective jobs, invalidated receipts, and superseding receipts. Completed attempts remain immutable history.
8. Cockpit exposes changes, delivery graphs, Kanban jobs, decisions, evidence, invalidation, and acceptance without requiring users to reconstruct truth from Markdown task histories.
9. OpenSpec and the old task-authoritative `shape -> build -> verify -> collect` path are removed in the same atomic cutover. The old stores remain only as an immutable historical snapshot.

## Primary Workflows

### WF-1: Rough idea to admitted change

The user invokes `/ideate` or `/design`. OwlBear creates or resumes a native change, preserves every confirmed decision immediately, delegates research and architecture checks to fresh read-only specialists, presents the complete delivery graph, and admits only the exact revision that passes layered admission and user approval.

### WF-2: Delivery node to shaped packets

Admission creates one `shape` job per delivery node. When its graph dependencies are satisfied, the shaper receives the node contract plus the full admitted graph and creates the complete build-packet DAG for that node. The shaper may refine implementation work but cannot add or weaken a product outcome, interface, migration, risk disposition, or proof boundary without global design re-entry and re-admission.

### WF-3: Packet implementation with warm review

The orchestrator dispatches at most one tracked-file writer at a time. A builder claims a `build` job, implements the complete outcome including proportionate tests, docs, generated artifacts, migration, and proof, commits it, and invokes a system-context read-only reviewer. The builder fixes concrete findings in the same session and produces a receipt only after review passes.

### WF-4: Node acceptance and corrective work

When all required packet receipts exist, an independent `accept` job executes the admitted node proof at an exact clean commit. The acceptor may create ephemeral diagnostic setup but cannot edit tracked files. Failure emits structured findings and minimum corrective `shape` or `build` jobs; prior attempts remain visible and invalid receipts cannot satisfy dependencies.

### WF-5: Whole-change audit and closure

After every delivery node has a valid acceptance receipt, an independent `audit` job executes all admitted normal workflows at an exact clean commit, checks requirement and decision fidelity, and either issues the final change receipt or creates typed corrective work. Successful audit closes and archives the native change mechanically.

## Success Conditions

- Each active product promise, negative requirement, preserved behavior, design obligation, changed interface, migration/removal step, material risk, and normal workflow has an admitted owner and executable proof path.
- Kanban jobs contain operational state and references; they do not become a competing specification authority.
- Every status names an agent transformation: `shape`, `build`, `accept`, or `audit`. Dependency blocking, readiness, claims, staleness, cancellation, and failed attempts are properties or dispositions.
- No tracked-file writer overlaps another writer. Acceptance and audit operate on clean committed revisions.
- The four historical defective plans are rejected before implementation; corrected equivalents are admitted and can complete through the new board.
- A material change to intent, design, interfaces, migration, risk, or proof invalidates affected downstream receipts and jobs deterministically.
- Late graph expansion caused by obligations knowable at admission reaches zero across three representative changes after cutover.
- The old pipeline and OpenSpec integration have no executable, generated, setup, or routing surface after cutover.

## Boundaries

### In Scope

- Native change authority and semantic revision model
- Layered admission and stable diagnostics
- Complete delivery graph and per-node packet shaping
- Graph-aware Kanban jobs, leases, requests, attempts, findings, evidence, receipts, invalidation, dispatch, and health
- Shared-worktree writer serialization and exact-commit proof
- New designer, shaper, builder, reviewer, acceptor, auditor, and orchestrator contracts
- Cockpit change and graph experience
- MCP/API contracts and setup/distribution changes
- Historical snapshot and active-work disposition inventory
- Four incident replays plus generic validator and end-to-end tests
- Atomic removal of OpenSpec and the old pipeline

### Out of Scope

- Backward-compatible execution of old tasks or OpenSpec changes
- Automatic semantic migration of unfinished work
- A general-purpose specification framework
- One status per artifact type such as research, tests, or documentation
- Parallel tracked-file writers or worktree/branch-per-job execution
- Guaranteed elimination of implementation defects or verifier findings
- Mandatory durable tests for every packet or acceptance criterion

## Preserved Strengths

The cutover must retain: one-question product clarification; Product Promise and preserved remainder; technically-done-but-wrong outcomes; explicit user decisions; repository and contract grounding; adaptive architecture review; outcome-cohesive decomposition; boundary-valid acceptance; fresh adversarial challenge; decision/action requests; independent product acceptance; append-only activity history; proportional proof; Kanban visibility; and focused agent contexts.

## Technically Done but Wrong

- A new graph file exists, but delivery nodes omit producer-consumer edges and the system repeats node-complete/edge-incomplete planning.
- The board has new columns, but some columns mean passive queue state rather than an agent transformation.
- Builders still receive copied task prose that can drift from the admitted graph.
- Packet checks pass, but no build-owned mechanism exercises the assembled delivery node or whole user workflow.
- The acceptor or auditor writes missing harnesses or product code and then approves its own work.
- A design revision occurs after admission, but old jobs or receipts can still close the change.
- Every code, test, documentation, and migration file becomes a separate job, multiplying agent starts and deferring integration.
- The old pipeline remains available as a quick lane or compatibility mode and becomes the path of least resistance.

## Non-goals

- Preserve current commands, agents, task file schema, statuses, APIs, frontend layout, or setup behavior for compatibility.
- Minimize implementation effort at the expense of the target architecture.
- Keep the pipeline operational during implementation of this redesign.
- Translate old runtime state into new authority automatically.
