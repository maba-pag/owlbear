---
id: 1913
title: Verify continuous codebase orientation without restructuring
status: verify
priority: medium
created: 2026-07-12T03:04:01.048065+02:00
updated: 2026-07-14T01:21:06.658995+02:00
tags:
  - scope:agent-config
  - feature
parent: 1914
depends_on:
  - 1912
ac:
  - 'AC-1: Given the active pipeline configuration, artifact inspection shows `h-codebase-orientation`
    owns `.owlbear/doc-index.md`, `.owlbear/py-index.md`, `.owlbear/ts-index.md`,
    direct-source and exact-search proof boundaries; Shaper workflows load it when
    source grounding is triggered, while Builder and Verifier list it as required
    reading.'
  - 'AC-2: Given brownfield shaping with a Change Module Map, artifact inspection
    shows `w-task-decomposition` creates the source-verified map and `r-pipeline-protocol`,
    Builder, and Verifier carry and check it while treating current source as stronger
    authority.'
  - 'AC-3: The focused orientation and authority regressions exit zero; when green,
    verification records zero product-file changes and does not rename or move skills,
    modify legacy ideation structures, regenerate indexes, or add abstractions.'
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
Rename and promote the orientation handbook, wire it into shaper/builder/verifier, apply deep-module guidance during shaping, add a per-change module map to Shape Notes, and record deferred ideation integration outside the retiring ideation artifacts.

## Scope
In: `share/agents`, `share/skills`, `share/WIRING.md`, generated doc index, durable future-work note.
Out: changes to the current ideation flow and spec-kit.

Proof guidance: run agent ecosystem structural checks and exact-reference scans.

[[2026-07-12T03:57:59+02:00]]
## Builder Notes
- Renamed project orientation from `h-code-orientation` to `h-project-orientation` and wired it into shaper, builder, verifier, w-research, and task decomposition.
- Added deep-module and Change Module Map guidance to shaping/decomposition, including the bounded shortcut rule for brownfield work.
- Updated `README.md`, `serve/tools/README.md`, `.github/copilot-instructions.md`, `share/WIRING.md`, and the orientation handbook.
- Deferred replacement-ideation integration recorded as task #1915 rather than editing retiring ideation/spec-kit artifacts.
- Validation: `validate_agents.py` pass, focused extraction tests 25 pass, `git diff --check` clean, `builder-challenger` pass after shortcut narrowing.
- No implementation code changed; docs/skills/agent guidance only.

[[2026-07-13T03:56:43+02:00]]
## Collect Notes
- Classification: leaf. Task #1913 has no child tasks and its Objective, Scope, and AC describe direct implementation work rather than aggregate intent.
- Leaf verification evidence: missing. The body contains Builder Notes and builder proof, but no `## Verify Notes` or verifier PASS.
- Invariant map coverage: cannot be closed at collect because verifier evidence for the three task AC is absent.
- Dependency gate: dependency #1912 is archived with reason `completed`; no dependency gap remains.
- Residual decisions: no pending request records and no unresolved decision state found.
- Rationale: reject to shape because leaf archival requires verifier PASS/Verify Notes; collector does not re-review implementation or substitute builder evidence for verification.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | shaper via `/shape` | Restore the task to the appropriate pipeline route so verifier PASS and `## Verify Notes` can be produced before collect. | n/a | Task body has Builder Notes dated 2026-07-12 but no Verify Notes. |

[[2026-07-13T13:18:04+02:00]]
## Shape Notes

### Verdict
APPROVED as one build-ready agent-ecosystem leaf. This is a collector-rejected recovery: prior Builder Notes exist, but current source must be reconciled before the normal verifier handoff.

### Planning Readiness
- Planning source: existing task #1913 and aggregate parent #1914.
- Product outcome and invocation: Shaper, Builder, and Verifier load a shared codebase-orientation contract; shaping records a source-verified module map and applies module-design diagnostics; task #1915 preserves replacement-ideation integration as separately routed work.
- Existing-system fit: current checked-in authorities supersede stale historical task literals.
- Normal-path proof: inspect the assembled agent and skill contracts, run the focused authority-wiring regression, and query task #1915 through Kanban.
- Completion and change contract: retain index generation under completed sibling #1912; exclude current ideation/spec-kit implementation from #1913; create no child tasks.

### Contract Authorities
| Claim | Authority | Evidence State | Confidence |
|---|---|---|---|
| Orientation ladder and discovery/proof boundary | `h-codebase-orientation` | observed | 1.0 |
| Required readers | Shaper, Builder, Verifier agent files and `test_skill_authority_wiring.py` | observed | 1.0 |
| Module map and depth lifecycle | `w-task-decomposition`, `h-module-design`, `r-pipeline-protocol` | observed | 1.0 |
| Replacement-ideation future work | Kanban task #1915 | observed after shaping | 1.0 |

### Change Module Map
| Module | Current Responsibility | Planned Change | Interface Impact | Owning Task |
|---|---|---|---|---|
| `h-codebase-orientation` | orientation ladder and proof boundary | verify or repair locally | shared skill contract | #1913 |
| `w-task-decomposition` and `h-module-design` | source map and module diagnostics | verify or repair locally | shaping workflow contract | #1913 |
| `r-pipeline-protocol` | map carry-through | verify or repair locally | pipeline contract | #1913 |
| Shaper, Builder, Verifier agent files and `share/WIRING.md` | authority loading and role wiring | verify or repair locally | agent contract | #1913 |
| Kanban #1915 | current future-work record | read-only query; separately owned implementation | task contract | #1913 |

Existing owners provide locality; no new module, adapter, or seam is planned.

### Product Invariant Map
| Product Invariant | Owning Task | Normal-Path Boundary | Proof / Allowed Replacement |
|---|---|---|---|
| Shared orientation ladder separates discovery from proof | #1913 | handbook plus required readers | artifact inspection and focused static regression; no replacement |
| Source-verified map and module diagnostics carry through the pipeline | #1913 | decomposition, protocol, and agent contracts | artifact inspection and focused static regression; no replacement |
| Current durable replacement-ideation record exists | #1913 | Kanban #1915 | MCP query; no replacement |

### Scope And AC Changes
- Replaced retired `h-project-orientation` and `r-architecture-standards` assumptions with current `h-codebase-orientation` and `h-module-design` authorities.
- Renamed the task to match the current orientation authority.
- Rewrote AC-1 through AC-3 as artifact or Kanban-query outcomes.
- #1915 was separately shaped to `build`; its current-authority contract resolves the earlier blocker.
- Complexity: 3 AC, one static/artifact proof mode, one agent-contract failure domain; no decomposition needed.
- Dependencies: #1912 is archived completed. Parent #1914 remains in `collect` and depends on #1912 and #1913.

### Evidence And Challenger
- `uv run pytest -n 0 tests/test_skill_authority_wiring.py -q`: 3 passed in 0.04s.
- Default parallel pytest and index refresh attempts were interrupted with exit 130 and are not evidence.
- Final `shaper-challenger`: pass. It confirmed readiness, canonical authority coverage, invariant ownership, full Product Promise coverage across #1912 and #1913, and the `build` recovery route.


## Current Repair Authority
This task now verifies the working orientation contracts without implementation changes. Current source supersedes the historical rename and migration instructions below. In scope: `h-codebase-orientation`, Shaper's on-demand source grounding, Builder and Verifier required reading, and continuous Change Module Map carry-through. Out of scope: skill renames or moves, legacy ideation changes, index regeneration, product code, new abstractions, and documentation cleanup.

Proof guidance: inspect the named artifacts, scan for retired authority names, and run the focused idea-refinement, skill-authority, and skill-extraction regressions. A green proof requires zero product-file changes.

[[2026-07-14T01:21:06+02:00]]
## Shape Notes

### Source And Repair
- Source: connected reshape of tasks #1913 through #1916 after current structures superseded historical implementation assumptions.
- Classification: material preservation-first reshape approved by the user.
- Current authority: `h-codebase-orientation`, `w-task-decomposition`, `r-pipeline-protocol`, and the active Builder and Verifier contracts.

### User Decisions And Readiness
- Preserve current working structures and avoid renames, moves, legacy-ideation edits, index regeneration, new abstractions, and product changes when focused proof is green.
- Remove the stale task #1915 build-ready assertion from AC.
- Normal proof is artifact inspection, exact retired-name scan, and the focused idea-refinement, skill-authority, and skill-extraction regressions.

### Change Module Map
| Module | Responsibility | Planned Change | Impact |
|---|---|---|---|
| `h-codebase-orientation` | portable orientation and proof boundary | read-only verification | none |
| `w-task-decomposition`, `r-pipeline-protocol` | map creation and carry-through | read-only verification | none |
| Builder and Verifier agents | regular orientation consumers | read-only verification | none |

### Product Invariants
- Orientation uses the three advisory indexes, direct source, exact search, and a discovery-versus-proof boundary.
- Shaper grounds source on demand; Builder and Verifier load orientation regularly.
- Change Module Maps remain source-verified and current source remains stronger authority.

### Task And Route Changes
- Renamed to verification-first wording and replaced AC-1 through AC-3 with current contracts.
- Parent remains #1914; completed dependency #1912 remains.
- Routed directly to `verify`; no implementation work is authorized.

### Evidence And Audit
- Focused regressions: 12 passed.
- Retired-name scan under `share/`: no matches.
- Shaper challenger: pass after correction of the active planning-path premise.
- Board audit before routing confirmed parent #1914 and dependency #1912.
