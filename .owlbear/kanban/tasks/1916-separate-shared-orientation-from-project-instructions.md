---
id: 1916
title: Preserve the project/shared instruction authority boundary
status: verify
priority: medium
created: 2026-07-12T04:09:21.262709+02:00
updated: 2026-07-14T01:21:06.675642+02:00
tags:
  - scope:agent-config
  - docs
parent:
depends_on: []
ac:
  - 'AC-1: Given the current OwlBear workspace, artifact inspection shows `.github/copilot-instructions.md`
    contains repository identity, branch topology, directory structure, Cockpit stack,
    and test-domain mapping, while portable index, `test-root`, Semble, proof-boundary,
    commit, and managed-artifact rules are absent from that file and owned by `h-codebase-orientation`
    or `r-workspace-governance`.'
  - 'AC-2: Given active files under `share/`, an exact-reference scan returns no `h-project-orientation`
    or `r-project-standards` references and shows current orientation or artifact-placement
    consumers naming `h-codebase-orientation` or `r-workspace-governance`.'
  - 'AC-3: Given the focused instruction-authority regression, the test command exits
    zero without requiring renames, file moves, new abstractions, broad documentation
    rewrites, or runtime product-code changes; when the command is already green,
    task implementation changes no product files.'
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
Preserve the working boundary in which `.github/copilot-instructions.md` owns current-repository facts while shared OwlBear skills own portable orientation and workspace-governance behavior.

## Scope
In: reconcile task #1916 against the current `.github/copilot-instructions.md`, `h-codebase-orientation`, `r-workspace-governance`, and their focused authority-boundary proof. Repair only a concrete contradiction found by that proof.

Out: renaming or moving current skills; reorganizing agent, skill, prompt, instruction, or test structures; reintroducing retired `h-project-orientation` or `r-project-standards` names; changing repository-specific branch, directory, Cockpit, or test-domain facts; unrelated cleanup; runtime product code.

Minimum change contract: current working structures are the authority. A green focused proof requires no product-file edit; a failure permits only the smallest local reconciliation needed for AC-1 through AC-3.

Proof guidance: inspect the named authority surfaces, run the focused instruction-boundary regression, and scan active shared ecosystem files for retired authority names.

## Historical Context
Prior Builder and Collect Notes below describe an earlier authority layout. They remain audit history, not current implementation instructions.

[[2026-07-13T23:48:44+02:00]]
## Shape Notes

### Verdict
APPROVED as one preservation-first build leaf. Current source and focused regressions are already green, so compliant implementation verifies the boundary and changes no product files unless a named proof exposes a concrete contradiction.

### Planning Readiness
- Planning source: existing collector-rejected task #1916; no Proposal or approved Brief governs this maintenance slice.
- Product outcome and invocation: OwlBear contributors receive repository facts from `.github/copilot-instructions.md` and portable orientation/governance from shared skills without duplicate or conflicting authority.
- Existing-system fit: current source supersedes historical Builder Notes and retired names.
- Normal-path proof: inspect the assembled instruction and skill artifacts, run `tests/test_skill_extraction.py` and `tests/test_skill_authority_wiring.py`, and scan active `share/` Markdown for retired names.
- Completion/change contract: preserve working structures. A green proof means zero product-file edits. Repair only a concrete contradiction inside the named boundary.

### Contract Authorities
| Claim | Authority | Evidence State | Confidence |
|---|---|---|---|
| Repository facts remain project-local | `.github/copilot-instructions.md` | observed | 1.0 |
| Portable discovery and proof rules remain shared | `h-codebase-orientation` | observed | 1.0 |
| Commit and managed-artifact rules remain shared | `r-workspace-governance` | observed | 1.0 |
| Authority boundary and current names remain protected | `tests/test_skill_extraction.py`, `tests/test_skill_authority_wiring.py` | observed and executed | 1.0 |

### Change Module Map
| Module | Current Responsibility | Planned Change | Interface Impact | Owning Task |
|---|---|---|---|---|
| `.github/copilot-instructions.md` | current-repository identity, topology, stack, commands, and test mapping | read-only unless focused proof fails | none expected | #1916 |
| `h-codebase-orientation` | portable orientation and proof boundary | read-only unless focused proof fails | none expected | #1916 |
| `r-workspace-governance` | portable commit and managed-artifact rules | read-only unless focused proof fails | none expected | #1916 |
| Focused authority tests | durable boundary proof | execute; change only for a source-backed contract correction | none expected | #1916 |

Existing owners maximize locality. No rename, move, new module, adapter, seam, or broad rewrite is planned.

### Product Invariant Map
| Product Invariant | Owning Task | Normal-Path Boundary | Proof / Allowed Replacement |
|---|---|---|---|
| Repository facts remain local | #1916 | project instruction artifact | inspection plus focused regression; no replacement |
| Portable orientation and governance remain shared | #1916 | shared skill artifacts and active consumers | focused regression plus exact scan; no replacement |
| Green current structures remain unchanged | #1916 | builder product diff after proof | zero product-file delta; no replacement |

### Scope And AC Changes
- Renamed the task around preservation rather than migration.
- Replaced retired `h-project-orientation` and `r-project-standards` literals with current authorities.
- Added explicit exclusions for renames, moves, reorganizations, new abstractions, broad documentation rewrites, unrelated cleanup, project-fact changes, and runtime code.
- Rewrote AC-1 through AC-3 as artifact, exact-scan, command, and product-diff outcomes.
- Complexity: 3 AC, one static/artifact proof mode, one authority-boundary failure domain; no decomposition or dependencies.
- Tasks #1913 and #1915 are already in `build`; parent #1914 is already in `collect`. They were inspected as context and left untouched under the one-task-per-invocation rule.

### Evidence And Challenger
- `uv run pytest -n 0 tests/test_skill_extraction.py -q`: 4 passed in 0.02s.
- `uv run pytest -n 0 tests/test_skill_authority_wiring.py -q`: 3 passed in 0.03s.
- Exact active-share scan for `h-project-orientation` and `r-project-standards`: no matches.
- Combined preliminary command exited 130 without output and is not evidence.
- Shaper-challenger: pass. It independently confirmed readiness, current authorities, invariant ownership, real artifact-boundary proof, full Product Promise coverage, and the zero-product-edit route.
- Recalled memory was useful, but assessment could not be recorded: `recall_memory` returns body-only blocks while `assess_memories` requires entry IDs.


## Current Repair Authority
This preservation-first contract remains current. The connected reshape adds no implementation scope: verify the project/shared authority boundary and record zero product-file changes when the focused proof is green.

[[2026-07-14T01:21:06+02:00]]
## Shape Notes

### Source And Repair
- Source: connected reshape of tasks #1913 through #1916.
- Classification: preservation-first verification route; existing task contract remains current.

### User Decision And Authorities
- Preserve the boundary where `.github/copilot-instructions.md` owns repository facts and shared `h-codebase-orientation` plus `r-workspace-governance` own portable behavior.
- Current working structures are stronger authority than historical migration notes.
- Green proof authorizes zero product-file changes; only a concrete named-boundary contradiction may be repaired.

### Change Module Map
| Module | Responsibility | Planned Change | Impact |
|---|---|---|---|
| `.github/copilot-instructions.md` | repository-local facts | read-only verification | none |
| `h-codebase-orientation` | portable orientation rules | read-only verification | none |
| `r-workspace-governance` | portable artifact and commit rules | read-only verification | none |

### Product Invariants
- Repository identity, topology, stack, and test mapping remain project-local.
- Portable orientation and governance remain shared.
- Current names and structures remain unchanged when proof is green.

### Task And Route Changes
- No AC, dependency, parent, or implementation-scope expansion was needed.
- Routed directly to `verify` with the zero-change contract intact.

### Evidence And Audit
- Focused idea-refinement, skill-authority, and skill-extraction regressions: 12 passed.
- Exact scan found no retired authority names under `share/`.
- Shaper challenger: pass.
- Board audit confirmed no dependencies and preserved tags.
