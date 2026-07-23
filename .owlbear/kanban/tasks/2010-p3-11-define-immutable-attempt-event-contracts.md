---
id: 2010
title: 'P3-11: Define immutable attempt event contracts'
status: verify
priority: high
created: 2026-07-23T14:40:14.905119+02:00
updated: 2026-07-23T15:17:53.950840+02:00
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
