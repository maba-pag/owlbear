---
id: 2091
title: 'P16-03: Install a native-only consumer workspace'
status: archived
priority: high
created: 2026-07-27T08:39:56.044193+02:00
updated: 2026-07-27T11:25:30.013799+02:00
tags:
  - phase-16
  - scope:setup
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - digest:6c95c70c81a1
  - node:DN-012
  - packet:T3
  - module:MOD-006
  - interface:IF-013
parent: 1989
depends_on:
  - 2088
  - 2089
ac:
  - 'AC-1: Given a fresh consumer workspace, invoking public setup creates empty native
    change, job, request, receipt, activity, and evidence stores and installs the
    current prompts, agents, skills, MCP configuration, hooks, seed assets, and Cockpit
    bundle without OpenSpec or legacy task-runtime assets.'
  - 'AC-2: Given an existing consumer workspace with user settings and native records,
    rerunning setup merges managed configuration, preserves user-owned values and
    records, and leaves the installed native inventory unchanged in meaning.'
  - 'AC-3: Given the resulting consumer workspace, the maintained native import and
    launch boundary starts without loading an OpenSpec package, a legacy task store,
    or a compatibility reader.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Outcome
Public setup creates or updates a consumer workspace with empty native authority/work stores and the current agent, MCP, Cockpit, hook, and seed ecosystem, without requiring OpenSpec or a compatibility runtime.

## Scope
In scope: setup/init behavior, seed store topology, user-state-preserving merge behavior, package installation boundary, and native launch smoke.

Out of scope: reusable snapshot/finalizer logic, Python/API legacy deletion owned by #2088, agent ecosystem deletion owned by #2089, and live-board retirement.

## Authority
DN-012 at delivery digest `6c95c70c81a13ef7a59206ac63bfd9b7338ccb87520d22d90517bf67d50167e9`; REQ-017, IF-013 installation half, MIG-003, RISK-005, KEEP-007, MOD-006, plus final native inventories from #2088 and #2089.

Proof guidance: exercise public setup against fresh and populated temporary consumer workspaces with the package-install recorder, then run the maintained native import/launch smoke; preserve user-owned files and settings.

[[2026-07-27T11:24:01+02:00]]
Builder completed native-only consumer setup at commit 56e5d3261. Public init creates native authority/work stores, skips OpenSpec installation/output, removes legacy task seed topology, preserves user settings and native records across reruns, and starts Cockpit against the generated NativeWorkspace. Focused proof: 29 setup/import/launch tests passed; Ruff, pre-commit hooks, diagnostics, and independent builder challenge passed.

[[2026-07-27T11:25:20+02:00]]
Verifier accepted exact builder commit 56e5d3261. All packet paths were drift-free, the 29-test setup/import/launch proof passed after commit, commit ancestry was valid, and verifier-challenger returned PASS with no defect in AC coverage, topology, rerun preservation, or scope.

[[2026-07-27T11:25:30+02:00]]
Collected #2091 with builder commit 56e5d3261 and verifier commit 9ac427674. Durable setup regressions cover fresh native installation, package-install absence, exact installed ecosystem inventory, populated rerun preservation, native import inventory, and setup-generated Cockpit launch.
