# Delivery Pipeline Implementation Plan

> **Owning task:** #1968 - Replace the OwlBear delivery pipeline
> **Date:** 2026-08-02
> **Question:** Which dependency-ordered implementation tasks can replace the delivery pipeline without dual-writing stores or exposing a partial cutover?
> **Authority:** S1-S6 policies and `delivery-pipeline-target-architecture.md`
> **Status:** Candidate for mandatory pre-coding challenge.

## 1. Delivery Rule

Tasks T1-T8 build target behavior in an isolated bootstrap worktree while current exports remain the
executor. T6 does not register `/work`; T8 replacements are not installed until T9. T9 performs the
receipt-gated switch and removal; T10 proves a fresh canary. No task dual-writes stores or migrates jobs.

Each task has one domain owner and one focused review claim. Repairs remain in-task; a false task
boundary returns to this plan; a protected consequence returns to Design.

## 2. Tasks

### T1 - Semantic authority and work-item projection

**Domain:** `serve/kanban`. **Files:** Target authority/projection modules and
`serve/kanban/tests/test_work_items.py`. **Behavior:** Model immutable commitment, outcome, supersession, plan-scope, target evidence input,
design-reentry briefing, semantic update, and completion summary. Derive stage, attention, readiness,
and progress from authority plus the evidence contract later written by T2.

**Acceptance:**

- AC1.1: Given an outcome superseded by two replacement outcomes, the public projection retains the
  old outcome ID as history and links both replacements; `uv run pytest serve/kanban/tests/test_work_items.py -q --tb=short` verifies the returned records.
- AC1.2: Given pending current-digest request evidence for one outcome, the projection reports user
  attention for that outcome and leaves an independent outcome ready; the focused test verifies both states.
- AC1.3: Given solution authority with no composition claim, reviewed build evidence closes the work
  item as Completed; given an accepted plan receipt with a composition claim, the projection reports Assembly.
- AC1.4: Given a C4 solution revision and completion receipts, semantic-update and completion-summary
  queries return rationale, satisfied commitments, accepted deviations, and known limits without creating a request.
- AC1.5: Given a Design return, authority persists failed claim, affected commitments, evidence,
  blocked dependency slice, continuing work, and resume condition; projection returns that briefing unchanged.

### T2 - Target execution and correction kernel

**Domain:** `serve/kanban`; **depends on:** T1. **Files:** Dormant target job/runtime modules and
`serve/kanban/tests/test_target_runtime.py`; reuse existing evidence stores. **Behavior:** Implement plan/build/assembly jobs, nested reviewer evidence, task-scoped requests,
typed return levels, repair continuity, restart, arbiter termination, expiry recovery, and guarded
known-dead recovery. Exclude Priority, Cancel, Release, accept jobs, and audit jobs.

**Acceptance:**

- AC2.1: Given a claimed build and acceptable reviewer evidence at its candidate commit, target
  completion publishes one build receipt and marks its task reviewed; the focused runtime test inspects both artifacts.
- AC2.2: Given repair disposition, the runtime retains reviewer identity; given restart disposition,
  it closes the attempt and requires a different reviewer on the next attempt.
- AC2.3: Given unresolved owner-reviewer disagreement after one evidence response, the runtime accepts
  one arbiter disposition and rejects another review cycle for that attempt.
- AC2.4: Given a request on outcome A, readiness blocks A and its semantic dependents while leaving
  independent outcome B dispatchable; the focused test queries the resulting frontier.
- AC2.5: Public target models reject obsolete job kinds and controls; model-validation tests verify
  `accept`, `audit`, `priority`, `cancelled`, and release mutation payloads fail parsing.

### T3 - Per-change workspaces and portfolio dispatch

**Domain:** `serve/kanban`; **depends on:** T2. **Files:** `change_workspace.py`, target coordination,
and `serve/kanban/tests/test_change_workspace.py`. **Behavior:** Manage one warm writable worktree and writer per change, a cross-chat capacity ledger,
immutable rejected-attempt refs, restart from last reviewed commit, non-rewriting integration, and
target-head CAS.

**Acceptance:**

- AC3.1: Given ready jobs for changes A and B with capacity two, portfolio dispatch grants one writer
  to each; a second writer for A returns a coordination conflict.
- AC3.2: Given a rejected head, restart creates an immutable attempt ref and recreates A at its recorded last reviewed commit; a Git integration test compares refs and SHAs.
- AC3.3: Given two change branches, integration uses merge commits without rebase, squash, or cherry-pick and retains reviewed task SHAs as ancestors.
- AC3.4: Given an integration conflict, the manager emits a finding and no Assembly job; after accepted
  change-level plan authority, portfolio dispatch returns the Assembly job.
- AC3.5: Given a consumer repository whose integration branch is not `dev`, workspace creation and
  target CAS use the configured branch; the test inspects refs and the resulting target head.

### T4 - MCP target contracts

**Domain:** `serve/mcp-kanban`; **depends on:** T3. **Files:** Dormant target server/models,
`serve/mcp-kanban/README.md`, and `serve/mcp-kanban/tests/test_target_server.py`. **Behavior:** Expose portfolio/work-item queries, semantic updates, completion summaries,
plan/build/assembly lifecycle, typed correction, and interrupted-task recovery.

**Acceptance:**

- AC4.1: The assembled FastMCP server lists target query and lifecycle operations and omits Priority,
  Cancel, Release, accept-completion, and audit-completion operations; package tests inspect registered tools.
- AC4.2: Given two loaded changes, the portfolio query returns work items from both with stable cursor pagination.
- AC4.3: Given a target diagnostic, the MCP response preserves its code, detail, current authority identity, and retry safety.

### T5 - Cockpit backend projection

**Domain:** `serve/cockpit` Python; **depends on:** T4. **Files:** Unregistered target router/models and
`tests/test_cockpit_work_items.py`. **Behavior:** Assemble a target test application serving portfolio, detail, updates, completion,
trace, scoped requests, persisted design briefing, and guarded recovery without changing the current app.

**Acceptance:**

- AC5.1: `GET /api/work-items` without a change selector returns mixed-change cards and attention counts; the route test crosses the assembled FastAPI application.
- AC5.2: `GET /api/work-items/{id}` returns commitments, acceptance, task progress, correction history,
  semantic updates, and trace links while excluding job IDs from the card projection.
- AC5.3: Opening resume-design returns the persisted briefing but leaves the work item in Design until revised authority is admitted.

### T6 - Cockpit portfolio and detail UI

**Domain:** `serve/cockpit/web`; **depends on:** T5. **Files:** Dormant Work page/hooks/components,
`src/__tests__/WorkPortfolio.test.tsx`, and `e2e/work-portfolio.spec.ts`; do not change `src/routes.ts` until T9.

**Acceptance:**

- AC6.1: Opening target `/work` without `?change=` renders Design, Planning, Implementation, and
  conditional Assembly columns without injecting a change selector into the URL.
- AC6.2: Selecting a card reveals semantic detail and scoped request actions; technical trace appears only after its explicit control is activated.
- AC6.3: A 120-card fixture supports change and attention filters while preserving card identity and shown count; Vitest verifies filtering and selection behavior.
- AC6.4: Playwright at 1440x900 and 390x844 reports no horizontal document overflow, overlapping cards,
  clipped controls, or inaccessible card actions and captures PDS-rendered screenshots.
- AC6.5: The Work flow exposes Specification and Requests inside detail and Activity/Evidence inside trace without requiring separate primary-page navigation.
- AC6.6: The target React surface contains no Priority, Cancel, Release claim, accept-job, or audit-job control; Vitest queries the rendered commands.

### T7 - Receipt-gated cutover service

**Domain:** `serve/kanban`; **depends on:** T1, T2, T3. **Files:** Target cutover service beside
snapshot/finalization and `serve/kanban/tests/test_target_cutover.py`; expose a service API, not a console command.

**Acceptance:**

- AC7.1: Given an unclassified C1-C3 commitment, current-digest request, claim, writer, stale authority,
  or stale code revision, readiness fails before target-store mutation and names the blocking identity.
- AC7.2: Given injected interruption at snapshot, initialization, adapter staging, smoke verification,
  or receipt publication, absent receipt causes restoration of source paths and previous target refs.
- AC7.3: Given a published receipt, target mutation accepts reintroduced authority and refuses current-schema job files as active work while retaining snapshot queries.
- AC7.4: Given a consumer pre-cutover store without a receipt, target mutation returns a fail-closed
  diagnostic naming snapshot and classification as required actions.

### T8 - Workflow adoption

**Domain:** agent-config; **depends on:** T2, T3. **Files:** Prepare replacements for `share/skills/`,
`share/agents/`, `share/instructions/owlbear-system.instructions.md`, `share/WIRING.md`,
`.github/copilot-instructions.md`, ecosystem tests, and write-guard tests in the isolated worktree;
T9 installs them with target tool registration.

**Acceptance:**

- AC8.1: Orchestration instructions dispatch target plan/build/assembly jobs, enforce one review per
  distinct claim, and route correction through the four return levels; ecosystem validation inspects referenced operations.
- AC8.2: Builder instructions use the assigned change worktree, retain the same reviewer for repair,
  and return typed restart or earlier-authority dispositions without editing plan authority.
- AC8.3: Workflow references contain no current accept/audit job completion, Priority, Cancel, Release claim, shared writable worktree, or assumed `dev` integration target.

### T9 - Activation and obsolete-surface removal

**Activation wave:** domain-scoped commits; **depends on:** T4, T5, T6, T7, T8

T9K switches Kanban exports and removes current execution surfaces/tests. T9M switches FastMCP tools,
README, surface/complete/acceptance/builder/planner interaction tests. T9C registers target
routes and retires current control/integration tests. T9W registers `/work`, removes `/`, `/delivery`,
`/requests`, `/activity`, `/evidence`, and retires old React tests. T9A installs T8. T9S registers
the direct-run `setup/finalize.py` service, updates `setup/init.py`, `README.md`, `setup/setup-guide.md`,
consumer templates, scaffold tests, `test_bootstrap_finalizer_command.py`, and `test_finalization.py`.

**Acceptance:**

- AC9.1: After activation, Python, FastMCP, FastAPI, React, and agent-config public surfaces omit the
  obsolete job kinds and controls; domain contract tests and `rg` removal gates verify named paths.
- AC9.2: `TestClient(app)` returns HTTP 404 for removed API controls; Playwright navigation to removed
  primary paths redirects to `/work` and renders the portfolio instead of an obsolete page.
- AC9.3: A fresh `setup/init.py` workspace creates target stores; a pre-cutover consumer store remains
  mutation-blocked until direct invocation of `setup/finalize.py` publishes its receipt.
- AC9.4: Kanban, MCP Kanban, Cockpit Python, Cockpit web build/E2E, setup, and ecosystem regression
  scopes pass before the finalizer publishes the activation receipt.

### T10 - Fresh-canary self-hosting proof

**Domain:** system verification; **depends on:** T9

Create one small canary change through target Design, Planning, Implementation, optional Assembly,
integration, completion summary, and historical evidence lookup. Preserve its receipts and command
outputs as cutover evidence; do not reintroduce this completed bootstrap change as canary work.

**Acceptance:**

- AC10.1: The canary produces admitted authority, plan receipt, reviewed build receipt, integration
  receipt, and completion summary; a target query reads one bootstrap receipt from the immutable snapshot.
- AC10.2: Stored canary commands show target-only pick/start/finish operations and no current job operation.

## 3. Validation Order

1. Focused package tests after each task.
2. `uv run lint <changed Python and Markdown paths>` for Python/agent tasks.
3. `npm test -- <focused files>` and `npm run build` for Cockpit web tasks.
4. Domain suites from `.github/copilot-instructions.md` before activation.
5. Mandatory independent intent-to-task challenge before T1; independent exact-commit review after each task.

## 4. Limits

Task planning may split a task when source ownership or proof cannot remain one domain. It may not add
compatibility, job stages, review quotas, user checkpoints, or per-task writable worktrees without
returning to the accepted architecture.