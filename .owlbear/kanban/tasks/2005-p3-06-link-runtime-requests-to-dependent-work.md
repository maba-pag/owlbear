---
id: 2005
title: 'P3-06: Link runtime requests to dependent work'
status: collect
priority: medium
created: 2026-07-22T21:59:06.804749+02:00
updated: 2026-07-24T14:19:01.582931+02:00
tags:
  - phase-3
  - scope:core
  - runtime
  - requests
  - decisions
  - actions
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-003
  - packet:DN-003-PK-006
parent: 1979
depends_on:
  - 2002
  - 2003
ac:
  - 'AC-1: Given decision or action input, request creation requires change/digest
    plus optional graph-target and job references; decision options preserve label,
    pros, cons, risks, recommendation, confidence, and rationale, while action requests
    preserve exact returned evidence and resume condition; unresolved references create
    no request or job link.'
  - 'AC-2: Given a pending request, only its linked jobs report request-blocked while
    unrelated jobs retain prior readiness; exact create replay and concurrent resolve
    produce one request identity and one immutable resolution without partial job
    links.'
  - 'AC-3: Given a local resolution, the transaction unblocks only the linked dependent
    slice and returns its invalidation intent; given a material authority resolution,
    it leaves linked jobs blocked or stale and returns design re-entry against the
    current change revision without mutating authority.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Bootstrap Projection Identity
- `change_id`: `replace-delivery-pipeline`
- `delivery_digest`: `9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8`
- `delivery_node_id`: `DN-003`
- `packet_id`: `DN-003-PK-006`

## Outcome
Structured decision and action requests attach to one change revision and optional graph target or job; pending requests block only linked work, and resolution either resumes that slice or records material design re-entry.

## Scope
In scope: native request and option/action contracts; pending/resolved immutable storage; create/list/show/resolve operations; job block references; local versus material resolution disposition; transaction and replay behavior.

Out of scope: designer `askQuestions`, authority mutation, MCP and Cockpit request APIs, corrective job generation, broad invalidation closure, and legacy task-scoped request changes.

## Current Foundation And Ownership
Build a native request owner over the transaction and job-lifecycle boundaries from preceding packets. Legacy `request_models.py` and current request routes remain bootstrap-carrier code until DN-009/DN-012.

## Authority
Resolve behavior from `REQ-015`, `REQ-016`, `KEEP-006`, `IF-003`, `PROOF-003`, and design section 11. Material authority changes return a typed design re-entry disposition rather than editing authority inside the runtime.

Proof guidance: exercise public native request operations over temporary change/work roots, including linked versus unrelated jobs, exact replay, concurrent resolution, local resume, and material re-entry.

[[2026-07-23T11:29:26+02:00]]
## Shape Notes
- Repair classification: connected dependency-closure audit; no operative contract change required.
- Dependency closure: #2005 introduces its own native request contracts/storage and consumes the transaction kernel and job/claim foundation from #2002/#2003. AC-2 and AC-3 already require atomic request identity/resolution with linked job references, no partial links, and scoped invalidation intent. No sibling or descendant producer is required.
- Ownership boundary: request activity remains request/job-link mutation in this task; broad invalidation closure and corrective jobs remain #2006. Material authority resolution still returns design re-entry without mutating authority.
- Board audit: remains `build`, parent #1979, dependencies #2002 and #2003, and is correctly dependency-blocked.

[[2026-07-24T14:01:06+02:00]]
## Builder Notes
- Added `NativeRequestRuntime` with strict revision-scoped decision/action request, option, resolution, local resume, and material design-reentry contracts.
- AC-1: creation validates current change/digest, graph target, and every linked job before mutation; decision options retain pros, cons, risks, recommendation, confidence, and rationale; actions retain exact evidence and resume condition.
- AC-2: create and resolve compose immutable request/resolution records with OCC-guarded linked job replacements under `RuntimeTransaction`; exact replay returns stored identity/outcome, interrupted operations recover, and concurrent exact resolve yields one immutable resolution. Only linked jobs receive request blocks.
- AC-3: local resolution removes only the resolved request ID from linked jobs and returns `RequestResumeIntent`; material resolution leaves links blocked and returns `DesignReentryDisposition` against the current change revision without authority mutation.
- Proof: `uv run pytest -n 0 serve/kanban/tests/test_runtime_requests.py -q` reported 2 passed. `uv run ruff check` passed and `uv run ruff format --check` reported both owned files formatted. Dedicated-module import smoke passed. Builder challenger decision: pass.
- Adjacent integration: request tests plus native runtime produced 22 passes and one unrelated concurrent #2004 fixture failure where strict `FinishJobRequest` tuple fields received lists; no #2004 files were modified or adopted.

[[2026-07-24T14:19:01+02:00]]
## Verify Notes
- Reviewed builder commit `ed57a2430` and the complete task-owned implementation in `runtime_requests.py` plus public focused proof in `test_runtime_requests.py`; no verifier product patch was needed.
- Named authorities checked: task AC-1 through AC-3; admitted `REQ-015`, `REQ-016`, `KEEP-006`, `IF-003`, `PROOF-003`; and design section 11. The implementation preserves revision/job-scoped requests, structured decision/action payloads, crash-safe transaction behavior, local dependent-slice resume, and typed material design re-entry without authority mutation.
- Module and interface scope: builder added one native request owner and one owning behavioral test inside `serve/kanban`; no MCP, Cockpit, legacy request route, broad invalidation, or corrective-job surface changed. This matches the shaped ownership boundary with no deviation.
- AC-1 evidence: public creation proof validates revision, digest, graph target, and linked jobs before mutation; an unresolved job reference creates neither request nor link; decision tradeoffs, recommendation, confidence, and rationale plus exact action evidence and resume condition survive storage.
- AC-2 evidence: exact create replay returns one stored identity; only the linked job receives the request block; interrupted multi-participant publication recovers; concurrent exact resolution returns one immutable result; changed resolution replay conflicts.
- AC-3 evidence: local resolution removes only the resolved request ID from linked jobs and returns `RequestResumeIntent`; material resolution keeps linked jobs blocked and returns `DesignReentryDisposition` tied to the current revision digest.
- Checks: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run python -m pytest -p xdist.plugin -o addopts='' serve/kanban/tests/test_runtime_requests.py -q` reported 2 passed. The isolated plugin run emitted three expected unknown-config warnings for omitted unrelated plugins. `uv run lint serve/kanban/src/owlbear_kanban/runtime_requests.py serve/kanban/tests/test_runtime_requests.py` passed. VS Code diagnostics reported no errors, and `git diff --check` was clean.
- Runner note: the configured pytest command twice exited 130 before output; the approved no-output retry rule led to the isolated xdist-hook run above, which reached and passed the focused behavior suite.
- No resolved structured requests, current follow-up, earlier Verify Notes, or prior same-failure-key rejection existed for this task.
- Verifier challenger decision: pass; no task-intent, proof-sufficiency, scope-drift, or unresolved-AC finding.
- Final route: PASS to collect.
