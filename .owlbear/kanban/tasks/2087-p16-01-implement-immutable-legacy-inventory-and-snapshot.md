---
id: 2087
title: 'P16-01: Implement immutable legacy inventory and snapshot'
status: build
priority: high
created: 2026-07-27T08:39:20.202385+02:00
updated: 2026-07-27T08:39:20.202385+02:00
tags:
  - phase-16
  - scope:core
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - digest:6c95c70c81a1
  - node:DN-012
  - packet:T1
  - module:MOD-001
parent: 1989
depends_on: []
ac:
  - 'AC-1: Given a stable populated legacy root, a new contained destination, and
    a disposition map covering each active item with `reintroduce-native`, `completed-history`,
    `dropped`, or `superseded`, the native snapshot boundary publishes one immutable
    manifest whose per-record hashes and counts match the source and retains the source
    until verification succeeds.'
  - 'AC-2: Given a missing or unsupported disposition, an existing destination, an
    unsafe or symlinked path, or a source mutation during capture, the snapshot boundary
    returns a typed failure, leaves the source byte-identical, and publishes no completed
    snapshot.'
  - 'AC-3: Given an interrupted publication or a count/hash mismatch, recovery exposes
    no completed snapshot; after the cause is corrected, rerunning the same boundary
    produces one verified snapshot without overwriting a prior destination.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
A reusable native snapshot boundary inventories legacy authority and runtime records, requires one explicit disposition per active item, and publishes a hash-verified immutable manifest without risking source history.

## Scope
In scope: typed manifest/disposition contracts, contained filesystem traversal, no-overwrite publication, source-stability checks, count/hash verification, and deterministic interruption recovery in the native core.

Out of scope: the public bootstrap finalizer, consumer setup, shipped legacy-surface removal, and mutation of the live self-hosting board.

## Authority
DN-012 at delivery digest `6c95c70c81a13ef7a59206ac63bfd9b7338ccb87520d22d90517bf67d50167e9`; IF-013, MIG-001, RISK-001, NEG-004, KEEP-007, and MOD-001. MOD-001 owns reusable snapshot logic; MOD-006 owns the later public setup/cutover adapter.

Proof guidance: run focused native-core behavior checks over temporary populated legacy roots, including publication interruption and source-change recovery; retain durable coverage for the destructive hash/inventory boundary.