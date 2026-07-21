---
id: 1991
title: 'P1-01: Load canonical native change revisions'
status: build
priority: medium
created: 2026-07-22T01:58:43.460559+02:00
updated: 2026-07-22T01:58:43.460559+02:00
tags:
  - phase-1
  - scope:core
  - authority
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-001
  - packet:DN-001-PK-001
parent: 1977
depends_on: []
ac:
  - 'AC-1: Given a contained `.owlbear/changes/<change_id>` package whose two Markdown
    files decode as UTF-8 and whose schema-version-1 decision and graph documents
    name the requested change, the public `ChangeRevision` loader returns one immutable
    revision with accepted decisions and the ten authored delivery sections addressable
    through stable IDs; verify through the public loader in a temporary workspace.'
  - 'AC-2: Given two packages that differ only by CRLF versus LF, trailing line breaks,
    YAML mapping order, or accepted-decision source order, `delivery-v1` returns the
    same SHA-256 digest; changing a Markdown character, accepted decision record,
    delivery sequence item, or delivery mapping value changes that digest; verify
    through the public digest boundary against canonical JSON vectors.'
  - 'AC-3: Given an absolute, traversing, null-containing, or symlinked change path;
    a missing authority file; BOM or non-UTF-8 Markdown; malformed YAML; a duplicate
    stable ID; or an unresolved graph reference, the public loader returns a structured
    diagnostic and no `ChangeRevision`; verify with table-driven temporary-workspace
    cases.'
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
- `packet_id`: `DN-001-PK-001`

## Outcome
A public immutable `ChangeRevision` boundary joins the four authority files, resolves stable graph identities and references, computes `delivery-v1`, and rejects unsafe, malformed, or partial packages without returning partial authority.

## Scope
In scope: strict boundary models for the four authority files; strict UTF-8 Markdown reads; YAML-to-JSON-mode values; stable ID/reference indexing; the canonical delivery envelope and SHA-256 digest; contained non-symlink package/file reads; structured loader diagnostics; public package exports; durable loader, digest, and path-safety tests.

Out of scope: delivery completeness and admission rules; Kanban jobs; receipt persistence; receipt-chain validity; MCP, HTTP, and UI contracts.

## Authority
Resolve normative behavior from `DN-001`, `IF-001`, `RISK-004`, and `PROOF-001` in `.owlbear/changes/replace-delivery-pipeline/graph.yaml`. This bootstrap task cannot add, weaken, or supersede those obligations.

Proof guidance: exercise the public loader and digest boundary with a temporary filesystem replacement only; run focused package pytest plus package-export and downstream-import scans. Durable tests are justified by the shared identity and path-security boundary.