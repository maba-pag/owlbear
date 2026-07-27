---
id: 2090
title: 'P16-02: Expose the fail-closed bootstrap finalizer'
status: build
priority: high
created: 2026-07-27T08:39:49.070496+02:00
updated: 2026-07-27T08:39:49.070496+02:00
tags:
  - phase-16
  - scope:core
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - digest:6c95c70c81a1
  - node:DN-012
  - packet:T2
  - module:MOD-001
  - module:MOD-006
  - interface:IF-016
parent: 1989
depends_on:
  - 2087
ac:
  - "AC-1: Given a released terminal board with zero active claims, writers, and pending
    requests; a verified #2087 inventory; expected authority and code revisions; and
    explicit finalization approval, the public finalizer writes an immutable snapshot
    and finalization receipt, removes the supplied active board and sibling carrier,
    verifies their absence, and returns the tracked paths required for the caller's
    commit."
  - 'AC-2: Given missing or stale proof, a nonterminal projection, an active claim,
    writer, or request, a changed source, an existing destination, a hash mismatch,
    or an unsafe path, the finalizer returns a typed failure, preserves a recoverable
    source, and writes no completed finalization receipt.'
  - 'AC-3: Given an interruption during publication or absence verification, recovery
    exposes no partial-success receipt; a replay after correction completes once and
    returns the same committed artifact identities.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
A public fixture-proved finalizer applies the native snapshot contract only after terminal-readiness, currentness, approval, claim, writer, request, and path checks, then publishes immutable finalization evidence and returns the tracked paths for the caller's scoped commit.

## Scope
In scope: reusable MOD-001 finalization transaction, typed request/result/finalization-receipt declarations, and MOD-006 public command/script adapter.

Out of scope: invoking the command against the live self-hosting board, native job dispatch for DN-015, consumer setup, and broad legacy-surface removal.

## Authority
DN-012 at delivery digest `6c95c70c81a13ef7a59206ac63bfd9b7338ccb87520d22d90517bf67d50167e9`; IF-016, MIG-005's consumed handoff contract, DEC-036, RISK-001, KEEP-007, MOD-001 internal ownership, and MOD-006 public interface ownership.

Proof guidance: invoke the public command against temporary populated repositories and exercise the finite approval/currentness/readiness/path/publication/absence matrix; never point it at the live board.