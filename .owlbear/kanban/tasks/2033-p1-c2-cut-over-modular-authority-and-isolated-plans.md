---
id: 2033
title: 'P1-C2: Cut over modular authority and isolated plans'
status: build
priority: high
created: 2026-07-25T02:46:34.205290+02:00
updated: 2026-07-25T02:46:34.205290+02:00
tags:
  - change:replace-delivery-pipeline
  - node:DN-001
  - node:DN-003
  - corrective
  - scope:core
  - migration
  - storage
  - type:build
  - rigor:thorough
parent: 1968
depends_on:
  - 2032
ac:
  - 'AC1: Given the admitted bootstrap package and embedded node plans, migration
    writes the three `delivery/*.yaml` files and one plan file per populated node;
    public `load_change` returns digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`.'
  - 'AC2: Given `load_change` after migration, `graph.yaml` absence succeeds; restoring
    `graph.yaml` returns `ERR_CHANGE_SCHEMA_INVALID` targeting that file, so no fallback
    or dual authority is accepted.'
  - 'AC3: Given a plan read or node-plan digest request, `ChangeRevision` and receipt
    currentness use `plans/<node-id>.yaml`; a missing plan yields the declared unavailable
    or stale result rather than embedded execution data.'
  - 'AC4: Given a runtime plan-publication participant from #2032, commit changes
    only the target plan and its transaction peers; injected interruption recovers
    prior bytes or the complete new plan, never a partial YAML document.'
  - 'AC5: Source and maintained-fixture inspection finds no active `ExecutionPlan`
    or `node_plans` graph field, `graph.yaml` plan mutation, or dual modular/monolithic
    registration.'
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
Migrate the admitted bootstrap carrier and active consumers to modular authority and isolated plans with no `graph.yaml` fallback.

## Scope
In scope: physical package migration, public `load_change`, `ChangeRevision` plan access, receipt digest/currentness, native plan persistence, and change health.

Out of scope: `shape` to `plan` identity, reconciliation, dispatch, and MCP.

## Authority
Admitted digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; DEC-030; MIG-004; DN-001; IF-001; PROOF-001.

Complexity waiver: five AC share one atomic migrated-package boundary; splitting carrier removal from plan persistence would expose a forbidden dual authority.

Proof guidance: migrate a package copy through the public loader, compare semantic identity, and interrupt isolated plan publication.