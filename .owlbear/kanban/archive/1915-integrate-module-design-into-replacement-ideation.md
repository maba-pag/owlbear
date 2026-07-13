---
id: 1915
title: Integrate module design into replacement ideation
status: archived
priority: low
created: 2026-07-12T03:40:28.840846+02:00
updated: 2026-07-14T01:21:35.803957+02:00
tags:
  - scope:agent-config
  - feature
parent:
depends_on: []
ac:
  - 'AC-1: Given an architecture-relevant stance or M3.5 proposal, artifact inspection
    shows the ideation architecture output contract requires structural reasoning
    about module depth, locality, leverage, and the Deletion Test using `h-module-design`.'
  - 'AC-2: Given an approved brownfield `brief.md`, artifact inspection shows the
    mediation contract requires an approach-level module map containing module or
    package responsibility, intended change, interface impact, and unresolved ownership
    questions, while prohibiting unverified source paths and symbols.'
  - 'AC-3: Given the M6 handoff for a brownfield Brief, artifact inspection shows
    the mediation contract assigns source verification through `h-codebase-orientation`
    and concrete Change Module Map creation to Shaper; an exact-reference scan of
    the active shared ecosystem finds no `h-project-orientation` or `r-architecture-standards`
    references.'
blocked: false
block_reason:
claimed_at:
archival_reason: dropped
archival_refs: []
---
## Objective
Carry portable module-design reasoning through the replacement ideation flow: from architecture comparison, into an approved brownfield Brief, and through the explicit shaping handoff.

## Scope
In: the architecture panel output contract, ideation mediation's brownfield Brief contract, and the M6 shaping handoff.

Out: redesigning ideation phases or panel selection; changing Shaper's existing source-verification behavior; modifying historical Briefs; runtime product code; introducing source paths or symbols before shaping verifies them.

## Existing-System Fit
`ideation-architect` already loads `h-module-design`; `h-ideation-panel` owns stance and proposal output contracts; `w-ideation-mediation` owns Brief drafting and the M6 `/shape` handoff. `h-codebase-orientation` and `h-module-design` are the current authorities; `h-project-orientation` and `r-architecture-standards` are retired names.

Proof guidance: inspect the resulting agent/skill contracts, run the focused ideation and authority-wiring static checks, and run an exact-reference scan for retired authority names. No runtime or browser proof is expected.

[[2026-07-13T13:13:20+02:00]]
## Shape Notes

### Verdict
APPROVED as one build-ready agent-ecosystem leaf. The replacement ideation architecture and artifact contract now exist, so the former deferral is resolved.

### Planning Readiness
- Planning source: existing task #1915; no separate Proposal or approved Brief governs this maintenance slice.
- Product outcome and invocation: Phase 2 architecture comparison carries portable module-design reasoning into an approved brownfield `brief.md`, then M6 hands it to `/shape {brief_path}`.
- Existing-system fit: `ideation-architect` already loads `h-module-design`; `h-ideation-panel` owns stance/proposal contracts; `w-ideation-mediation` owns Brief drafting and M6 handoff.
- Normal-path proof: inspect active agent/skill contracts, run focused static ecosystem checks, and scan active shared files for retired authority names. No runtime or browser boundary is claimed.
- Completion/change contract: retain ideation phases, panel selection, Shaper's existing verification behavior, historical Briefs, and runtime code.

### Contract Authorities
| Claim | Authority | Evidence State | Confidence |
|---|---|---|---|
| Module depth, locality, leverage, and Deletion Test vocabulary | `h-module-design` | documented from source | 1.0 |
| Live-source orientation and proof boundary | `h-codebase-orientation` | documented from source | 1.0 |
| Architecture stance/proposal outputs | `ideation-architect` and `h-ideation-panel` | observed in source | 1.0 |
| Brief drafting and M6 shaping handoff | `w-ideation-mediation` and `h-ideation` | observed in source | 1.0 |
| Retired-name prohibition | `tests/test_skill_authority_wiring.py` | observed in checked-in contract | 1.0 |

### Change Module Map
| Module | Current Responsibility | Planned Change | Interface Impact | Owning Task |
|---|---|---|---|---|
| `share/agents/ideation-architect.agent.md` | Architecture panel behavior and output contract | require named portable diagnostics where needed | changed agent contract | #1915 |
| `share/skills/h-ideation-panel/SKILL.md` | Stance/proposal protocol | carry structural reasoning into architecture outputs where needed | changed artifact contract | #1915 |
| `share/skills/w-ideation-mediation/SKILL.md` | Brief drafting and M6 handoff | require brownfield approach map and source-verification handoff | changed workflow contract | #1915 |
| `tests/` focused ecosystem contracts | Static authority and ideation regression checks | update only when durable protection is justified | maintained proof surface | #1915 |

No new module, adapter, or seam is planned. Existing owners provide the best locality and pass the Deletion Test.

### Product Invariant Map
| Product Invariant | Owning Task | Normal-Path Boundary | Proof / Allowed Replacement |
|---|---|---|---|
| Architecture comparison applies depth, locality, leverage, and Deletion Test reasoning | #1915 | stance/proposal output contract | artifact inspection; no replacement |
| Approved brownfield Brief carries an approach-level map without fabricated source details | #1915 | mediation Brief contract | artifact inspection; no replacement |
| M6 assigns live-source verification and concrete Change Module Map creation to Shaper | #1915 | mediation handoff plus shared-reference scan | focused static checks; no replacement |

### Scope And AC Changes
- Removed the obsolete future-replacement prerequisite and retired names `h-project-orientation` and `r-architecture-standards`.
- Replaced prose AC with AC-1 through AC-3 covering architecture output, approved brownfield Brief, and M6 handoff.
- In scope: agent/skill contracts. Out of scope: workflow redesign, runtime code, historical Brief migration, and pre-shaping source literals.
- Complexity: 3 AC, one static/artifact proof mode, one agent-contract failure domain; no decomposition needed.
- Dependencies: none. This is a direct leaf, not an aggregate parent.

### Challenger
`shaper-challenger` decision: pass. It confirmed readiness, current authority names, one owner and normal-path proof per invariant, full coverage of the three-part Product Promise, and no boundary-bypassing proof.

### Evidence
- Direct reads of the named source authorities and focused static tests.
- Kanban projection validated the claimed leaf, AC, and empty dependency set before challenge.
- `uv run --project . indexes .` was interrupted with exit code 130 and produced no usable proof. Direct source remained authoritative; no generated-index delta is claimed as part of shaping.


## Current Repair Authority
The user confirms the multi-agent ideation flow targeted by this task is deprecated. Its active successor is `/ideate` using `w-idea-refinement`, followed by `/opsx:propose` and later `/shape`. Legacy prompts, agents, skills, tests, diagrams, and documentation remain reachable in source but are outside this graph: do not delete, rename, rewire, or otherwise modify them. This task adds no replacement implementation work because architecture and concrete source/module mapping remain owned downstream by `h-module-design`, `w-spec-shaping`, and `w-task-decomposition`.

[[2026-07-14T01:21:31+02:00]]
## Shape Notes

### Source And Repair
- Source: connected reshape of tasks #1913 through #1916.
- Classification: user-approved drop after a material status-quo change.

### User Decision
- The multi-agent ideation flow targeted by this task is deprecated.
- Its successor is `/ideate` using `w-idea-refinement`, followed by `/opsx:propose` and later `/shape`.
- Remaining legacy prompts, agents, skills, tests, diagrams, and documentation are still reachable in source but are explicitly outside this graph. They must not be deleted, renamed, rewired, or otherwise changed here.

### Planning And Module Impact
- No OpenSpec artifact governs this maintenance task.
- No implementation module is changed.
- Architecture and concrete source/module mapping remain owned downstream by `h-module-design`, `w-spec-shaping`, and `w-task-decomposition`; the generic idea-refinement successor intentionally does not inherit architecture-panel behavior.

### Task And Route Changes
- Historical Brief, panel, and M6 acceptance criteria are superseded by the user's deprecation decision.
- No replacement implementation task is created.
- Archive reason is `dropped`; task #1914 audits this outcome without depending on the dropped task.

### Evidence And Audit
- Active successor verified in `ideate.prompt.md`, `w-idea-refinement`, and `WIRING.md`.
- Legacy reachability was verified and is not misrepresented as source absence.
- Focused successor and authority regressions: 12 passed.
- Shaper challenger: pass after the user decision was recorded as product authority.
