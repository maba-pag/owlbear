---
id: 1992
title: 'P1-02: Persist immutable change receipts and diagnose authority health'
status: build
priority: low
created: 2026-07-22T01:58:50.836111+02:00
updated: 2026-07-22T01:58:50.836111+02:00
tags:
  - phase-1
  - scope:core
  - storage
  - health
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-001
  - packet:DN-001-PK-002
parent: 1977
depends_on:
  - 1991
ac:
  - 'AC-1: Given a schema-version-1 receipt mapping whose kind is `admission`, `shape`,
    `build`, `accept`, `audit`, or `supersession` and whose common change/digest identity
    matches a loaded revision, the public receipt store creates `<receipt_id>.yaml`
    once and reads back the common envelope plus kind payload; a second create for
    that receipt ID raises a stable conflict and preserves the original bytes; verify
    through the public store in a temporary workspace.'
  - 'AC-2: Given an absolute, traversing, null-containing, or symlinked receipt path;
    a filename/envelope identity mismatch; an unsupported schema version or kind;
    or malformed YAML, the public receipt store returns a structured diagnostic and
    leaves no outside write or temporary residue; verify with table-driven temporary-workspace
    cases.'
  - 'AC-3: Given a complete package, a partial or malformed authority package, and
    a package with a receipt whose delivery digest differs from the loaded revision,
    the public change-health boundary returns deterministic code, detail, path, and
    target findings plus checked paths without changing file bytes or mtimes; the
    complete package with its matching admission receipt returns zero findings; verify
    through the public health boundary.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Bootstrap Projection Identity
- `change_id`: `replace-delivery-pipeline`
- `delivery_digest`: `9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8`
- `delivery_node_id`: `DN-001`
- `packet_id`: `DN-001-PK-002`

## Outcome
A public receipt store creates and reads schema-version-1 receipt envelopes once under a loaded revision, and read-only change health reports authority and receipt defects without changing tracked bytes.

## Scope
In scope: common receipt identity envelopes for `admission`, `shape`, `build`, `accept`, `audit`, and `supersession` payloads; contained non-symlink receipt paths; exclusive atomic create and read; stable conflict, parse, and path diagnostics; read-only health over authority and receipt files; public exports; durable store, health, and path tests grounded in the committed admission receipt shape.

Out of scope: assembling admission receipts; predecessor, supersession, code-revision, or proof-boundary validity; invalidation; job transitions; repair or quarantine; MCP, HTTP, and UI contracts.

## Authority
Resolve normative behavior from `DN-001`, `RISK-004`, and `PROOF-001` in `.owlbear/changes/replace-delivery-pipeline/graph.yaml`. This bootstrap task cannot add, weaken, or supersede those obligations.

Proof guidance: exercise the public receipt store and change-health boundary with a temporary filesystem replacement only; run focused package pytest and the existing atomic-write and health suites. Durable tests are justified by immutable evidence and path-security/data-loss risk.