---
id: 2092
title: 'P16-06: Align native distribution, generated assets, and documentation'
status: verify
priority: medium
created: 2026-07-27T08:40:04.276149+02:00
updated: 2026-07-27T12:02:38.988783+02:00
tags:
  - phase-16
  - scope:distribution
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - digest:6c95c70c81a1
  - node:DN-012
  - packet:T6
  - module:MOD-006
  - module:MOD-007
  - module:MOD-009
parent: 1989
depends_on:
  - 2090
  - 2091
  - 2088
  - 2089
ac:
  - 'AC-1: Given the built and installed consumer artifact after #2088 through #2091,
    its public inventory contains the required native source, setup, seed, MCP, Cockpit,
    and ecosystem assets and contains no active OpenSpec command, legacy task runtime,
    retired route, retired role, or compatibility artifact.'
  - 'AC-2: Given the maintained setup, consumer, sharing, security, and ecosystem
    documentation and configuration, they describe the native design and delivery
    workflow and identify immutable legacy inventory as history rather than execution
    authority.'
  - 'AC-3: Given a fresh distribution diff against the canonical package and seed
    manifests, each shipped generated path has a current native owner and no unowned
    compatibility path remains.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
The built and installed consumer distribution contains the native control plane, setup, seed, Cockpit, and ecosystem assets while maintained documentation and generated configuration describe no active legacy workflow.

## Scope
In scope: MOD-006, MOD-007, and MOD-009 distribution manifests, generated assets, checked-in consumer configuration, public setup/consumer documentation, and immutable-history references.

Out of scope: implementing snapshot/finalizer/setup behavior, deleting runtime or agent execution paths, assembled cutover behavior, and live-board retirement.

## Authority
DN-012 at delivery digest `6c95c70c81a13ef7a59206ac63bfd9b7338ccb87520d22d90517bf67d50167e9`; REQ-011, REQ-017, IF-013/IF-016 public surfaces, MIG-001 through MIG-004 consumer inventories, RISK-005, and outputs from #2088 through #2091.

Proof guidance: build and install the consumer artifact in a temporary workspace, inspect the resulting artifact/config inventory, and run maintained documentation/config validators; do not add source-string absence tests.

[[2026-07-27T12:02:38+02:00]]
## Builder Notes

DONE. Adopted the complete uncommitted #2092 change envelope from the interrupted builder attempt after inspecting and validating it; unrelated Memory, task-control, and MCP configuration state remains excluded.

- AC-1: removed active `openspec/`, installer/seed compatibility, generated `opsx-*` prompts and skills, retired diagrams, and stale generated/runtime references. `tests/test_native_distribution.py` proves the exact retired-path and shipped native inventories; setup and Cockpit launch regressions pass. The earlier packet proof also passed 264 Cockpit tests and the production Vite build.
- AC-2: aligned maintained setup, consumer, sharing, package, ecosystem, and security-adjacent documentation/configuration with native design and delivery. Published the former OpenSpec tree through `create_legacy_snapshot` at `.owlbear/legacy/openspec-final`; `verify_legacy_snapshot` proves 22 files and four explicit `completed-history` dispositions while active paths remain absent.
- AC-3: exact distribution proof covers sync ownership, prebuilt Cockpit output, retained diagram inventory, MCP inventory, and relative documentation links. The doc-index owner no longer excludes retired command trees.
- Corrected MCP Memory review attribution to `memory-reviewer`; `tests/test_memory_git.py` exercises public `commit_batch` behavior in a real temporary Git repository.
- Focused evidence: 73 unique Python regressions passed across native distribution/setup/launch, customization contracts, Memory review, and doc indexing; Markdownlint passed 39 files; yamllint passed all files; agent and skill validators passed; focused Ruff and format checks passed; diagnostics and both staged/unstaged diff checks are clean. Three pre-existing asyncio deprecation warnings remain.
- Independent builder challenger decision: pass; both prior findings are resolved and no blocking defect remains.
