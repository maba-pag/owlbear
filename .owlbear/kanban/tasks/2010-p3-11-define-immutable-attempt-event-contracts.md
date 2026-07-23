---
id: 2010
title: 'P3-11: Define immutable attempt event contracts'
status: collect
priority: high
created: 2026-07-23T14:40:14.905119+02:00
updated: 2026-07-23T15:26:19.965588+02:00
tags:
  - phase-3
  - scope:core
  - runtime
  - attempts
  - contracts
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-003
  - packet:DN-003-PK-004-A
parent: 2003
depends_on:
  - 2002
ac:
  - 'AC-1: Given schema-version-1 mappings for `started`, `released`, `failed`, `crashed`,
    or `succeeded`, the public parser returns a frozen record preserving attempt,
    job, change, delivery-digest, target, actor, process, positive-sequence, timestamp,
    optional-detail, and evidence references.'
  - 'AC-2: Given an unknown field, malformed identity or reference, non-positive sequence,
    unsupported event kind, or missing required reference, the public parser returns
    the stable diagnostic for that class and no record.'
  - 'AC-3: Given an accepted record, public serialization followed by parsing returns
    an equal record, and the supported kind literals remain exactly `started`, `released`,
    `failed`, `crashed`, and `succeeded`.'
proof_bundle: behavioral+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
A public schema-version-1 `AttemptEvent` contract represents immutable started, released, failed, crashed, and succeeded lifecycle evidence with deterministic parsing and serialization.

## Scope
In scope: frozen event model; attempt, job, change, delivery-digest, and target references; actor and process identity; positive sequence; timestamp; optional detail and evidence references; supported-kind literals; parser, serializer, and stable diagnostics.

Out of scope: event persistence, transaction coordination, lifecycle operations, successful completion policy, requests, invalidation, dispatch, MCP, and Cockpit.

## Current Foundation And Ownership
Use the native identity and model conventions delivered through archived task #2002 and current `jobs.py`. This task owns only the attempt event contract. Task #2003 remains the packet aggregate.

## Authority
Resolve behavior from `REQ-008`, `REQ-009`, `IF-003`, design sections 2.2, 2.3, 7.2, 13, and 14, and accepted decisions `DEC-007` and `DEC-009` under `.owlbear/changes/replace-delivery-pipeline/`.

## Proof Guidance
Exercise the public parser and serializer directly with a finite accepted/invalid mapping table. Do not substitute store or lifecycle integration for this boundary.

[[2026-07-23T15:17:53+02:00]]
## Builder Notes
- Change envelope: introduce only the immutable attempt-event contract and its public parse/serialize boundary; exclude storage, transactions, and lifecycle operations.
- Files changed: `serve/kanban/src/owlbear_kanban/attempts.py`, `serve/kanban/src/owlbear_kanban/__init__.py`, and `serve/kanban/tests/test_attempts.py`.
- Change Module Map: no deviation. `attempts.py` is the sibling immutable contract owner; package exports expose the public boundary.
- Proof selected: finite public mapping table covers all five supported kind literals, frozen round trips, and each requested invalid diagnostic class. The focused durable test is justified because this shared public serialization boundary is easy to regress and later storage/lifecycle work depends on it.
- Commands run: `uv run --project /Users/markus/Projects/owlbear-dev pytest serve/kanban/tests/test_attempts.py` (13 passed); `uv run --project /Users/markus/Projects/owlbear-dev ruff check serve/kanban/src/owlbear_kanban/attempts.py serve/kanban/src/owlbear_kanban/__init__.py serve/kanban/tests/test_attempts.py` (all checks passed); scoped `git diff --check` (clean).
- Builder challenger: pass; independently reran the same focused proof and found no completion blocker.
- Follow-up risks: identity semantics beyond required non-empty/reference validation belong to dependent lifecycle and persistence tasks.

[[2026-07-23T15:22:26+02:00]]
## Verify Notes
- Evidence reviewed: task AC-1 through AC-3; builder notes; the committed task implementation in `serve/kanban/src/owlbear_kanban/attempts.py`; public exports in `serve/kanban/src/owlbear_kanban/__init__.py`; and the focused mapping-table tests in `serve/kanban/tests/test_attempts.py`.
- Named authorities checked: `REQ-008`, `REQ-009`, `IF-003`, design sections 2.2, 2.3, and 7.2, plus accepted `DEC-007` and `DEC-009` in `.owlbear/changes/replace-delivery-pipeline/`. The immutable operational-event model aligns with the work/evidence-plane and purpose-specific-job authorities.
- Change Module Map: no ownership deviation. The contract remains isolated to the intended sibling module and package export surface.
- Normal-path boundary exercised: direct public `parse_attempt_event_mapping` accepted all five kinds; no store, lifecycle, or injected substitute was used.
- Checks run: `uv run --project /Users/markus/Projects/owlbear-dev pytest serve/kanban/tests/test_attempts.py` passed (13 passed); `uv run --project /Users/markus/Projects/owlbear-dev ruff check serve/kanban/src/owlbear_kanban/attempts.py serve/kanban/src/owlbear_kanban/__init__.py serve/kanban/tests/test_attempts.py` passed (all checks passed); `git diff --check` clean.
- Finding: REJECT. AC-3 requires a public serialization boundary followed by public parsing. The package exposes only `parse_attempt_event_mapping`; the round-trip test invokes `AttemptEvent.model_dump(mode="json")` directly. That Pydantic method is not a task-owned public serializer, so the required public serialize-then-parse contract is absent and unproven.
- Required follow-up: add and export the minimal public attempt-event serializer, and update the focused round-trip test to call it before `parse_attempt_event_mapping`. Preserve the existing narrow module ownership and immutable model.
- Patches applied: none; this missing public contract requires builder-owned implementation and proof.
- Prior same-AC rejection check: task history contains only the builder implementation commit; no prior Verify Notes or same-AC rejection exists.
- Verifier-challenger: not called because a PASS verdict is not proposed.
- Final route: REJECT to build.

[[2026-07-23T15:24:29+02:00]]
## Builder Notes
- Change envelope: add only the missing public attempt-event serializer and its package export; update the existing public round-trip proof. Storage, transactions, and lifecycle operations remain excluded.
- Files changed: `serve/kanban/src/owlbear_kanban/attempts.py`, `serve/kanban/src/owlbear_kanban/__init__.py`, and `serve/kanban/tests/test_attempts.py`.
- Change Module Map: no deviation. `attempts.py` remains the immutable event-contract owner; the package root exposes the public boundary.
- Proof selected: the existing finite mapping-table test now calls `serialize_attempt_event_mapping` followed by `parse_attempt_event_mapping` across all five supported kinds. The focused durable test remains justified because this shared public serialization contract is easy to regress and is a dependency for later lifecycle and persistence work.
- Commands run: `uv run --project /Users/markus/Projects/owlbear-dev pytest serve/kanban/tests/test_attempts.py` (13 passed); `uv run --project /Users/markus/Projects/owlbear-dev ruff check serve/kanban/src/owlbear_kanban/attempts.py serve/kanban/src/owlbear_kanban/__init__.py serve/kanban/tests/test_attempts.py` (all checks passed); `uv run --project /Users/markus/Projects/owlbear-dev ruff format --check serve/kanban/src/owlbear_kanban/attempts.py serve/kanban/src/owlbear_kanban/__init__.py serve/kanban/tests/test_attempts.py` (3 files already formatted); scoped `git diff --check` (clean).
- Builder challenger: pass; no concrete blockers. It independently ran the focused test, lint, format, and diff checks and found the change narrow and the durable test justified.
- Follow-up risks: none within this contract scope.

[[2026-07-23T15:26:19+02:00]]
## Verify Notes
- Evidence reviewed: AC-1 through AC-3; both Builder Notes; committed implementation at `b3f3e9b07`; public exports; and the focused mapping-table proof.
- Named authorities checked: `REQ-008`, `REQ-009`, and `IF-003` in `.owlbear/changes/replace-delivery-pipeline/graph.yaml`; design sections 2.2, 2.3, 7.2, 13, and 14; and accepted `DEC-007` and `DEC-009`. The immutable operational-event contract agrees with the work/evidence planes and purpose-specific job model.
- Change Module Map: no deviation. The contract remains isolated to `attempts.py`, its package export surface, and the focused test; storage and lifecycle remain untouched.
- Normal-path boundary exercised: public `serialize_attempt_event_mapping` followed by public `parse_attempt_event_mapping` across exactly `started`, `released`, `failed`, `crashed`, and `succeeded`; no store, lifecycle, or injected substitute was used.
- Checks run: `uv run --project /Users/markus/Projects/owlbear-dev pytest serve/kanban/tests/test_attempts.py` passed (13 passed); Ruff check passed; Ruff format check reported 3 files already formatted; `git diff --check` was clean; VS Code diagnostics found no errors in the three touched files.
- Findings: none. The parser preserves the required immutable record fields and returns stable diagnostics for unknown fields, malformed identities/references, non-positive sequences, unsupported kinds, and a missing required reference. Public serialization now round-trips through the public parser.
- Patches applied: none.
- Prior same-AC rejection check: one earlier AC-3 rejection required the missing public serializer. Builder resolved it in commit `b3f3e9b07`; the focused proof now calls the exported serializer before parsing. No repeated unresolved failure family remains.
- Verifier-challenger: pass. It confirmed AC coverage, public-boundary proof sufficiency, authority alignment, and no scope drift.
- Final route: PASS to collect.
