---
id: 1914
title: Close continuous orientation without disturbing current planning 
  structures
status: shape
priority: medium
created: 2026-07-12T03:04:06.678099+02:00
updated: 2026-07-14T08:13:02.935623+02:00
tags:
  - scope:tools
  - scope:agent-config
  - feature
parent:
depends_on:
  - 1912
  - 1913
  - 1916
ac:
  - 'AC-1: A Kanban audit shows task #1912 archived as completed, tasks #1913 and
    #1916 with verifier PASS evidence, and task #1915 archived as dropped under the
    user-approved deprecation decision.'
  - 'AC-2: Artifact inspection and focused regression evidence at aggregate collection
    show `h-codebase-orientation`, Change Module Map carry-through, the project/shared
    authority boundary, and the active `/ideate` followed by `/opsx:propose` and `/shape`
    path remain present without retired authority names.'
  - 'AC-3: Aggregate diff and proof audit shows no rename or move of current skills,
    no edits to remaining legacy ideation structures, and no product-file change introduced
    solely to close this graph.'
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Problem
Close the continuous orientation work against the current, working planning structures without reviving superseded rename or legacy-ideation instructions.

## Decisions
- Preserve separate advisory artifacts: `.owlbear/doc-index.md`, `.owlbear/py-index.md`, and `.owlbear/ts-index.md`; task #1912 already delivered the source indexes.
- Keep `h-codebase-orientation` as the portable orientation authority. Shaper workflows load it when source grounding is needed; Builder and Verifier use it as required reading.
- Preserve source-verified Change Module Maps through shaping, build, and verify while treating current source as stronger authority.
- Treat `/ideate` using `w-idea-refinement`, followed by `/opsx:propose` and later `/shape`, as the active successor path.
- Drop task #1915 because it adds work to the user-deprecated multi-agent ideation flow. Remaining legacy surfaces are reachable but must not be deleted, renamed, rewired, or otherwise changed by this graph.
- Preserve the project/shared authority boundary verified by task #1916.

Proof guidance: inspect the active artifacts and task histories, scan for retired authority names, and use the focused idea-refinement, skill-authority, and skill-extraction regressions. Aggregate closure must not require product-file changes.

[[2026-07-14T01:21:06+02:00]]
## Shape Notes

### Source And Repair
- Source: connected reshape of tasks #1913 through #1916 after planning and orientation structures changed.
- Classification: user-approved aggregate graph reshape.
- No OpenSpec package governs this maintenance graph.

### User Decisions
- Preserve current orientation, module-map, and project/shared authority structures.
- Treat `/ideate` using `w-idea-refinement`, followed by `/opsx:propose` and `/shape`, as the active successor path.
- Drop #1915 as an obsolete enhancement to the user-deprecated multi-agent ideation flow, while leaving its remaining source surfaces untouched.
- No rename, move, legacy cleanup, broad rewrite, new abstraction, index regeneration, or product-file change is authorized.

### Change Module Map
| Module | Responsibility | Change | Owner |
|---|---|---|---|
| `h-codebase-orientation` | orientation and proof boundary | read-only verification | #1913 |
| `w-task-decomposition`, `r-pipeline-protocol`, Builder, Verifier | Change Module Map lifecycle | read-only verification | #1913 |
| `.github/copilot-instructions.md`, `r-workspace-governance` | project/shared authority boundary | read-only verification | #1916 |
| `ideate.prompt.md`, `w-idea-refinement`, `WIRING.md` | active planning successor | read-only aggregate audit | #1914 |
| legacy ideation surfaces | deprecated flow still reachable | no change | #1915 dropped |

### Product Invariant Map
| Invariant | Owner | Boundary | Proof |
|---|---|---|---|
| Source-grounded orientation and agent loading | #1913 | active contracts | inspection and focused regression |
| Map creation and carry-through with current source stronger | #1913 | shaping and pipeline contracts | inspection and focused regression |
| Repository facts local; portable rules shared | #1916 | project instruction and shared skills | exact scan and focused regression |
| Active successor untouched; no new legacy-flow work | #1914 | prompt, wiring, and board | inspection plus #1915 archival audit |

### Final Graph
- #1912 remains archived `completed` and parented to #1914.
- #1913 routes to `verify`, parent #1914, depending on #1912.
- #1916 routes to `verify` with no dependencies.
- #1915 archives `dropped` and is not a dependency because dropped dependencies block aggregate dispatch.
- #1914 routes to `collect` depending on #1912, #1913, and #1916.

### Evidence And Challenge
- Focused regressions: 12 passed.
- Retired-name scan under `share/`: no matches.
- Shaper challenger initially rejected the unsupported source-deprecation inference; after the user supplied product authority and legacy reachability was preserved as a fact, the corrected graph passed.
- Pre-route board audit matched titles, parent links, dependencies, and claims.

[[2026-07-14T08:13:02+02:00]]
## Collect Notes

- Classification: aggregate. Parent intent comes from `## Problem`, `## Decisions`, and the shaper-created `## Shape Notes`, including the Change Module Map, Product Invariant Map, final graph, and explicit aggregate AC.
- Invariant map coverage: #1912 covers the advisory source indexes; #1913 records verifier PASS for orientation ownership and Change Module Map carry-through; #1915 is archived `dropped` under the user-approved legacy-ideation decision; #1916 is intended to cover the project/shared authority boundary but has no recorded verifier evidence.
- Child coverage: `list_tasks(parent=1914)` returned no active tasks because relevant children are archived. Direct live ID lookup shows #1912 archived `completed` with `parent: 1914`, #1913 archived `completed` with `parent: 1914`, #1915 archived `dropped`, and #1916 archived `completed` with no parent link. No pending request records exist for #1914 or #1912 through #1916.
- Parent dependency gate: #1914 depends on #1912, #1913, and #1916; all three are archived `completed`. #1913 reports `dep_status: ok` for its dependency on #1912. #1915 is correctly excluded from the parent dependency list because it is archived `dropped`.
- Child completion evidence: #1912 has Verify Notes and Collect Notes with public CLI proof, 76 focused tests, ruff proof, verifier-challenger PASS, and completed archival. #1913 has final Verify Notes and Collect Notes with 22 authority tests, 4 idea-refinement tests, agent validation, clean diff check, verifier-challenger PASS, and completed archival. #1915 is archived `dropped` as explicitly authorized. #1916 is archived `completed`, but `show_task(section="Verify Notes")` and `show_task(section="Collect Notes")` both return empty bodies; its full record contains no recoverable verifier PASS evidence.
- SHA-linked aggregate proof: not run because aggregate AC-1 is already unsatisfied by missing upstream verifier evidence for #1916. A new aggregate regression at HEAD cannot substitute for the required child Verify Notes.
- Residual decisions: no pending Decision or Action Requests and no block state remain. The unresolved closure gap is evidentiary, not a user decision.
- Reject rationale: aggregate AC-1 explicitly requires #1916 verifier PASS evidence. Archived-completed metadata alone does not satisfy that condition, and collector must not re-review or reconstruct leaf verification.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | shaper via `/shape` | Repair the graph so #1916 has authoritative verifier PASS/Verify Notes and a valid leaf closure history, then return #1914 to collect with SHA-linked aggregate normal-path proof tied to the tested commit. | n/a | #1916 is archived `completed`, but both requested evidence sections are empty; #1914 AC-1 requires verifier PASS evidence. |
