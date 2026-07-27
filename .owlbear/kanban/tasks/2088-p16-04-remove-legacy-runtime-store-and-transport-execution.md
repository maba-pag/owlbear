---
id: 2088
title: 'P16-04: Remove legacy runtime, store, and transport execution'
status: build
priority: high
created: 2026-07-27T08:39:27.780712+02:00
updated: 2026-07-27T08:39:27.780712+02:00
tags:
  - phase-16
  - scope:core
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - digest:6c95c70c81a1
  - node:DN-012
  - packet:T4
  - module:MOD-001
  - module:MOD-002
  - module:MOD-004
  - module:MOD-007
parent: 1989
depends_on: []
ac:
  - 'AC-1: Given the shipped Python import inventory, MCP tool inventory, and FastAPI
    route inventory, native change, graph, job, request, evidence, health, history,
    and legacy-inventory read contracts remain callable through their public boundaries.'
  - 'AC-2: Given a lookup or call for legacy task CRUD, arbitrary movement, old lifecycle
    statuses, OpenSpec runtime loading, compatibility translation, or retired task/decision
    routes, the public boundary exposes no registered callable and HTTP surfaces return
    the maintained not-found response.'
  - 'AC-3: Given the native health scanner and mapped package checks after removal,
    they complete without dangling legacy registrations, imports, schemas, or store
    readers.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
Shipped Python, MCP, and FastAPI surfaces expose native change/job contracts without an executable legacy task or OpenSpec runtime path.

## Scope
In scope: MOD-001, MOD-002, MOD-004, and MOD-007 legacy readers, task CRUD/lifecycle registrations, old status/schema imports, compatibility translation, and retired HTTP routes.

Out of scope: agent/prompt/skill retirement, consumer installation, documentation, immutable historical inventory, and live-board deletion.

## Authority
DN-012 at delivery digest `6c95c70c81a13ef7a59206ac63bfd9b7338ccb87520d22d90517bf67d50167e9`; REQ-011, NEG-004, MIG-001 through MIG-004 consumer inventories, RISK-005, and completed native IF-001 through IF-004, IF-010, and IF-011.

Proof guidance: run focused native import, MCP contract, FastAPI contract, and health checks plus a bounded downstream-impact scan; remove stale tests that preserve retired execution behavior.