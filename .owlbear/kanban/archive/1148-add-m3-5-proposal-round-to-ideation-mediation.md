---
id: 1148
title: Add M3.5 proposal round to ideation mediation
status: archived
priority: medium
created: 2026-04-27T21:43:30.790296+00:00
updated: 2026-04-28T01:17:33.008180+00:00
tags:
- ideation
- pipeline
- agent
parent:
depends_on:
- 1147
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective

Add a gated "Design It Twice" proposal step to ideation Phase 2. When M3 landscape reveals genuine design ambiguity, domain panelists produce competing complete designs in parallel, enabling comparison-driven decisions before M4.

Inspired by Ousterhout's "Design It Twice", adapted to the existing multi-agent panel architecture.

Split from #1147.

## Acceptance Criteria

- [ ] `w-ideation-mediation` SKILL.md: new Step 1.5 (between current Steps 1 and 2) defining M3.5 gated proposal round
- [ ] M3.5 gate: Mediator evaluates M3 landscape for >=2 viable approaches with no dominant option; if single clear approach, skip M3.5 and proceed to Step 2 unchanged
- [ ] When M3.5 triggers, Step 2 (stance-mode late domain panel + Pragmatist converge) is entirely skipped; M3.5 and Step 2 are mutually exclusive paths to `synthesis.md`
- [ ] When triggered: Mediator dispatches all 4 domain panelists in parallel (overrides problem-signal selection matrix for maximum design diversity), each via PROPOSE-mode prompt (directive passed through runSubagent prompt field, not a separate agent config)
- [ ] `h-ideation-panel` SKILL.md: new "Propose Mode" section under Late Domain Panel that defines panelist behavior: receive M3 landscape synthesis + directive to produce a complete design shaped by domain emphasis (not a domain-only slice)
- [ ] Propose-mode output: `stances/{name}-proposal.md` with required sections: Design Summary, Key Structural Choices, Trade-offs, Domain Rationale, Confidence
- [ ] `h-ideation` SKILL.md: blackboard artifacts section updated with `stances/*-proposal.md` paths
- [ ] After proposals collected: Mediator dispatches Pragmatist `mode=compare` to produce `synthesis.md` containing: (a) diff-oriented comparison matrix showing only divergences between proposals (table columns: Decision Point, architect, data, enduser, security, Tension Level), (b) common ground summary, (c) open questions
- [ ] `h-ideation-panel` Pragmatist Modes section: new `mode=compare` that reads `stances/*-proposal.md` plus `context.md`/`decisions.md`, writes `synthesis.md` per format in preceding AC item
- [ ] Modified Step 3 (M4): Pragmatist comparison feeds user decision turn; user may pick a direction or hybrid elements from multiple proposals
- [ ] Post-hybridization: two sequential `ideation-critic` passes: (1) synthesis critic reads hybridized `synthesis.md` verifying internal consistency of combined elements, (2) result critic reads updated `synthesis.md` + `decisions.md` challenging the final design on its own merits
- [ ] Both critic passes subject to O15 classification per existing Critic Validation rules in `w-ideation-mediation`
- [ ] Verification checklist in `w-ideation-mediation` updated with M3.5 items
- [ ] `ideation-{architect,data,enduser,security}.agent.md`: output restrictions updated to include `stances/{name}-proposal.md`; propose-mode Critic skip documented (per DR 1148-ac-scope-amendment, option A)
- [ ] `ideation-pragmatist.agent.md`: `mode=compare` added to persona and contract sections (per DR 1148-ac-scope-amendment, option A)
- [ ] `.owlbear/briefs/README.md`: blackboard directory structure and Agent Read/Write Matrix updated for `*-proposal.md` artifacts and Pragmatist `mode=compare` path

## Architecture Notes

- Panelist agents already support parallel dispatch (h-ideation-panel "Parallel Batch" pattern): no new invocation mechanism needed
- PROPOSE mode is a behavioral directive via prompt text, not a config change: panelists load h-ideation-panel which defines both stance and propose modes
- `allow-stances-only.py` PreToolUse hook uses stances/ prefix: verify `stances/*-proposal.md` is covered by existing glob
- No new `.agent.md` files required: existing panelists serve both modes
- No Python code changes: all changes are skill/handbook markdown + agent file contract updates + briefs README
- When M3.5 triggers, Step 2 (normal stance-mode panel + Pragmatist converge) is skipped; M3.5 and Step 2 are mutually exclusive paths to `synthesis.md`
- Propose-mode panelists skip embedded Critic loops; adversarial quality covered by dual post-hybridization Critic passes
- M3.5 always dispatches all 4 domain panelists regardless of problem-signal selection matrix; comparison-driven design requires maximum diversity of domain perspectives

## Out of Scope

- Changes to M1-M2 discovery phase
- Changes to early challengers (firstprinciples/outsider/simplifier)
- Making the proposal step mandatory (always gated on ambiguity)
- New panelist `.agent.md` files (existing agents serve both modes)
- Diagram updates (`share/diagrams/ideation.excalidraw`) — follow-up task if needed
- Test fixture updates for the M3.5 path (`tests/test_ideation_overhaul_static.py`, `tests/test_ideation_diagram_1034.py`) — follow-up task if needed

[[2026-04-27]]
## Research
- Research doc: .owlbear/research/1148-m3-5-proposal-round.md
- Sources: 8 studied, 6 high-relevance (≥.85)
- Recommendation: Implementable with scope amendment — add 5 agent file updates to AC (confidence: .72)
- Follow-up tasks created: none (DR gates the amendment)
- Decision requests: 1 created (.owlbear/decisions/pending/1148-ac-scope-amendment.md)

## Challenge Results
- Challenger: block (confidence in original: .34)
- Key challenges: (C1) panelist output restrictions don't include proposal files, (C2) mandatory Critic loops conflict with propose mode, (C3) pragmatist only defines converge/denoise
- Researcher response: accepted C1-C3 — scope amendment required. Revised from T1 to T2. Created blocking DR for AC amendment.

## Key Findings
1. Prior art validated: Ousterhout "Design It Twice" + mattpocock design-an-interface skill confirm approach
2. Hook compatible: allow-stances-only.py regex covers stances/*-proposal.md
3. Parallel dispatch: existing Parallel Batch pattern supports propose-mode dispatch
4. Agent file conflicts: 3 contract conflicts require minor updates to 4 panelist + 1 pragmatist agent files
5. Step 2 flow: M3.5 replaces Step 2 when triggered (mutually exclusive paths to synthesis.md)
6. Critic loops: recommend skip in propose mode; dual post-hybridization Critic covers adversarial quality

## Decision Resolved

**Decision:** A: Amend AC to include panelist agent file updates

Approved. AC scope amended to include panelist agent file contract harmonization (agent file docs and output restrictions). Changes are surgical and low-risk.

[[2026-04-27]]
[[2026-04-28]]
## Research (validation pass)
- Validation pass: all 8 codebase claims from research doc confirmed against current source
- AC amended per resolved DR 1148-ac-scope-amendment (option A): added 2 AC items for agent file contract harmonization (4 panelist output restrictions + pragmatist mode=compare)
- Architecture notes updated: Step 2 mutual exclusivity, propose-mode Critic skip rationale
- Out-of-scope clarified: "new agent files" not "all agent file changes"
- Sources already logged in .owlbear/sources/overview.md
- No follow-up tasks needed — #1148 is the implementation task with full amended scope (3 skill files + 5 agent files, all markdown)
[[2026-04-27]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One feature: M3.5 proposal round. All changes flow from that single capability. |
| Interface clarity | PASS | After refinement: exact file sections, output format columns, delegation chain, Critic input specs all explicit. |
| Dependency correctness | PASS | No dependencies; split from #1147 which is independent. |
| Module layering | PASS | All changes within ideation subsystem (share/skills, share/agents, .owlbear/briefs). No cross-domain leaks. |
| TDD compliance | PASS | Tagged `agent` — pass-through tag. No testable Python interface; all markdown changes. |
| KISS/YAGNI | PASS | Gated design (skip when single clear approach). No hypothetical extras. |
| Premise challenge | PASS | No existing "Design It Twice" mechanism in the ideation workflow. Genuine gap. |
| Pattern consistency | PASS | Uses existing Parallel Batch dispatch, Pragmatist synthesis modes (new mode follows converge/denoise pattern), Critic O15 validation. |
| Security surface | PASS | No new system boundaries. All internal agent/skill markdown. |
| Single domain | PASS | Entirely within ideation domain. |

### AC Refinements Applied

1. **New AC 3 (Step 2 suppression):** Added explicit mutual exclusivity — "When M3.5 triggers, Step 2 is entirely skipped." Was only in Architecture Notes; needed in AC for verifiability.
2. **Refined AC 4 (roster override):** Changed "4 domain panelists" to "all 4 domain panelists (overrides problem-signal selection matrix)." Resolves authority clash with existing h-ideation-panel selection logic.
3. **Refined AC 8 (delegation chain):** Changed "Mediator builds" to "Mediator dispatches Pragmatist mode=compare to produce synthesis.md containing: (a) divergence matrix, (b) common ground summary, (c) open questions." Resolves comparison-ownership ambiguity.
4. **Refined AC 9 (Pragmatist inputs):** Added "reads stances/*-proposal.md plus context.md/decisions.md" and back-referenced AC 8 format. Eliminates duplicate/conflicting output specs.
5. **Refined AC 11 (Critic inputs):** Added what each pass reads — "(1) reads hybridized synthesis.md" and "(2) reads updated synthesis.md + decisions.md." Pins input boundaries.
6. **New AC 16 (briefs README):** Added `.owlbear/briefs/README.md` update for directory structure and Agent Read/Write Matrix. Prevents adjacent contract drift.
7. **Out of Scope additions:** Diagram and test fixture updates noted as explicit follow-up candidates.

### Challenge Results
- Challenger: reconsider (confidence in original: 0.57)
- Key findings: (1) Step 2 suppression only in architecture notes not AC, (2) roster selection authority clash, (3) comparison artifact ownership ambiguity between Mediator and Pragmatist, (4) dual Critic inputs unspecified, (5) briefs README adjacent contract drift
- Architect response: accepted all 5 findings. Applied 6 AC refinements and 2 out-of-scope clarifications. Post-refinement confidence: .88

### Codebase Verification
- `w-ideation-mediation/SKILL.md`: Steps 1-6 structure confirmed; Step 1.5 insertion point clear between Step 1 (M3 Landscape) and Step 2 (Late Domain Panel)
- `h-ideation-panel/SKILL.md`: Pragmatist Modes section has converge and denoise; mode=compare follows same structural pattern
- `h-ideation/SKILL.md`: Blackboard Artifacts section lists stances/ contents; proposal.md addition is straightforward
- `ideation-{architect,data,enduser,security}.agent.md`: All have "Write only to stances/" rule and output file lists; proposal path addition is surgical
- `ideation-pragmatist.agent.md`: Persona lists 2 modes; mode=compare addition follows existing pattern
- `allow-stances-only.py`: `_STANCES_RE = re.compile(r"(/|^)stances/")` — confirmed covers `stances/*-proposal.md`
- `.owlbear/briefs/README.md`: Directory structure and Agent Read/Write Matrix need proposal artifacts added

### Verdict: APPROVE (after REFINE)
### Action Taken: Refined 5 AC items for precision, added 1 new AC for briefs README, added 2 out-of-scope items. Advanced to todo.
[[2026-04-27]]
## Test-Writer Notes
- Non-implementation task (tagged `agent`) — no tests applicable.
- All AC items are markdown-only: skill files (`w-ideation-mediation`, `h-ideation-panel`, `h-ideation`), agent files (4 panelist + 1 pragmatist), briefs README. No Python interfaces.
- Architecture review explicitly confirmed: "pass-through tag. No testable Python interface; all markdown changes."
- Passing through to builder.

[[2026-04-28]]
## Builder Notes
- Non-implementation task — markdown/agent-contract scope only.
- AC coverage audit completed across required files; all items present.
- Files changed by builder: none.
- Tests: not applicable for this pass-through (`agent` task; no Python interface changes).
- Lint: not applicable for this pass-through.
- Evidence summary: `w-ideation-mediation` contains Step 1.5 gate, Step 2 mutual exclusivity, dual post-hybridization Critic passes, and updated verification checklist; `h-ideation-panel` contains Propose Mode and Pragmatist `mode=compare`; `h-ideation` lists proposal artifacts; all four late-domain panelist agent files include `*-proposal.md` outputs and propose-mode Critic skip; `ideation-pragmatist.agent.md` includes `mode=compare` in persona/contract; `.owlbear/briefs/README.md` updates blackboard structure and Agent Read/Write Matrix for proposal artifacts.

## Post-task Reflection
- No implementation deltas required; task state represented a completed markdown contract rollout.
- Fastest reliable path was direct AC-to-file evidence mapping before deciding pass-through.
- Scope discipline prevented unnecessary churn in already-converged docs/agent contracts.
[[2026-04-28]]
## Review Evidence
### Test Results
- pytest: 30 passed, 0 failed (`tests/test_ideation_overhaul_static.py`)

### Lint
- ruff: clean (`tests/test_ideation_overhaul_static.py`)

### Coverage
- N/A for task-owned surface. Quality-runner reported coverage not meaningful because #1148 changes markdown/agent-contract files only.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
- Latest task authority explicitly scopes M3.5 fixture updates as follow-up work if needed (`.owlbear/kanban/tasks/1148-add-m3-5-proposal-round-to-ideation-mediation.md:68`) and marks this as a tagged `agent` pass-through with no testable Python interface (`.owlbear/kanban/tasks/1148-add-m3-5-proposal-round-to-ideation-mediation.md:117,152-154`).
- `tests/test_ideation_overhaul_static.py` passed 30/30 and provides adjacent regression context, but it does not directly assert the new M3.5/proposal-round contract. I treated that as non-blocking follow-up debt rather than a gate failure because the latest scope authority keeps fixture expansion out of #1148.
- Follow-up created: `#1153 Add static coverage for ideation M3.5 proposal-round contracts` (placeholder only; kanban parser rejected body/status edits in this session).

#### Security Review
- No issues found. Reviewed markdown-only contract surfaces; no secrets, code execution, path handling, or new trust boundaries.

#### Test Integrity
- No weakened or removed `TestFromAC_*` assertions found in the scoped suite.

#### Test Quality
- Existing ideation static suite remains strong for prior ideation-overhaul invariants, but it is not task-owned proof for proposal/compare-path text. Non-blocking for #1148 because tests are explicitly follow-up scope; tracked via #1153.

#### Data Safety
- No issues found. Panelist write scope remains under `stances/`; Pragmatist write scope remains synthesis artifacts.

#### Implementation-Aware Gaps
- No implementation gaps found. Live authority is AC-compliant across the skill files, agent files, and briefs README listed below.

#### Builder Process Quality
| Metric | Value |
|---|---|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- `share/agents/ideation-pragmatist.agent.md:14` still says "You have two modes" while the same file documents `mode=compare` at `:46`, `:94`, and `:123`. Non-blocking wording drift.
- Builder note says "Files changed by builder: none"; review is therefore anchored to current repository state rather than attributable diff evidence.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| Step 1.5 added to mediation | `share/skills/w-ideation-mediation/SKILL.md:81-98` | direct file inspection | PASS |
| M3.5 gate requires `>=2` viable approaches and no dominant option | `share/skills/w-ideation-mediation/SKILL.md:81-84` | direct file inspection | PASS |
| M3.5 and Step 2 are mutually exclusive | `share/skills/w-ideation-mediation/SKILL.md:84,100-101` | direct file inspection | PASS |
| M3.5 dispatches all 4 domain panelists in parallel with PROPOSE prompt directives | `share/skills/w-ideation-mediation/SKILL.md:85-94` | direct file inspection | PASS |
| `h-ideation-panel` defines Propose Mode under Late Domain Panel | `share/skills/h-ideation-panel/SKILL.md:93-114` | direct file inspection | PASS |
| Proposal files require Design Summary / Key Structural Choices / Trade-offs / Domain Rationale / Confidence | `share/skills/h-ideation-panel/SKILL.md:99-106` | direct file inspection | PASS |
| `h-ideation` blackboard artifacts include `stances/*-proposal.md` | `share/skills/h-ideation/SKILL.md:69-93,117-120` | direct file inspection | PASS |
| Mediator dispatches Pragmatist `mode=compare` with divergence matrix, common ground, and open questions | `share/skills/w-ideation-mediation/SKILL.md:95-98`; `share/skills/h-ideation-panel/SKILL.md:173-188`; `share/agents/ideation-pragmatist.agent.md:94-123` | direct file inspection | PASS |
| `h-ideation-panel` defines Pragmatist `mode=compare` read/write contract | `share/skills/h-ideation-panel/SKILL.md:173-188` | direct file inspection | PASS |
| Step 3 supports selecting one proposal or hybrid elements from multiple proposals | `share/skills/w-ideation-mediation/SKILL.md:114-119` | direct file inspection | PASS |
| Two sequential post-hybridization Critic passes are defined | `share/skills/w-ideation-mediation/SKILL.md:124-128` | direct file inspection | PASS |
| Both Critic passes are triaged with O15 | `share/skills/w-ideation-mediation/SKILL.md:124-129` | direct file inspection | PASS |
| Verification checklist includes M3.5 items | `share/skills/w-ideation-mediation/SKILL.md:146,156-161` | direct file inspection | PASS |
| Architect/data/enduser/security agents allow `*-proposal.md` and document PROPOSE-mode Critic skip | `share/agents/ideation-architect.agent.md:31-33,61-71`; `share/agents/ideation-data.agent.md:33-35,63-73`; `share/agents/ideation-enduser.agent.md:31-33,61-71`; `share/agents/ideation-security.agent.md:31-33,61-71` | direct file inspection | PASS |
| Pragmatist agent adds `mode=compare` to persona and contract sections | `share/agents/ideation-pragmatist.agent.md:14-18,46-56,94-123` | direct file inspection | PASS |
| `.owlbear/briefs/README.md` documents proposal artifacts and compare-path synthesis contract | `.owlbear/briefs/README.md:5-31,55-59,69-77` | direct file inspection | PASS |

### Deductions
- `-0.06` missing task-owned static proof for proposal/compare-path text; tracked as follow-up #1153
- `-0.03` minor wording drift in `share/agents/ideation-pragmatist.agent.md`

### Verdict
- PASS -> docs | confidence `0.91`

### Action
- Advanced #1148 to `docs` and released review claim.
[[2026-04-28]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Changed files are all agent-executable (SKILL.md, .agent.md, .owlbear/briefs/README.md) — no IN-scope prose docs reference this surface by name |
| 2 | Module docstrings | No | N/A | No Python modules created or modified |
| 3 | External attribution | Yes | Verified | Sources logged in `.owlbear/sources/overview.md` at lines 11-16 (Ousterhout "Design It Twice" + mattpocock/skills) — confirmed present |
| 4 | Research doc | Yes | Verified | `.owlbear/research/1148-m3-5-proposal-round.md` exists; linked in task body; follow-up #1153 created by reviewer for static coverage |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/ideation.excalidraw` describes `share/skills/h-ideation/**`, `share/skills/w-ideation-mediation/**`, `share/skills/h-ideation-panel/**`, `share/agents/ideation-*.agent.md` — all match changed files. Footer updated: `Last verified: 2026-04-28 (e733deff)` |
| 6 | Explicit diagram creation | No | N/A | Out of scope per task body ("Diagram updates — follow-up task if needed"); no explicit creation request |
| 7 | Deletion detection | No | N/A | No files deleted by this task |

### Scope Classification

| File | Scope | Action |
|------|-------|--------|
| share/skills/w-ideation-mediation/SKILL.md | OUT (agent-executable) | N/A |
| share/skills/h-ideation-panel/SKILL.md | OUT (agent-executable) | N/A |
| share/skills/h-ideation/SKILL.md | OUT (agent-executable) | N/A |
| share/agents/ideation-architect.agent.md | OUT (agent-executable) | N/A |
| share/agents/ideation-data.agent.md | OUT (agent-executable) | N/A |
| share/agents/ideation-enduser.agent.md | OUT (agent-executable) | N/A |
| share/agents/ideation-security.agent.md | OUT (agent-executable) | N/A |
| share/agents/ideation-pragmatist.agent.md | OUT (agent-executable) | N/A |
| .owlbear/briefs/README.md | OUT (not in IN-scope list) | N/A |
| share/diagrams/ideation.excalidraw | IN (diagram) | Footer updated |

### Files Updated
- share/diagrams/ideation.excalidraw (footer: `Last verified: 2026-04-28 (e733deff)`)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/1148-*` files existed)
[[2026-04-28]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Step 1.5 added to mediation | `share/skills/w-ideation-mediation/SKILL.md:81-98` | PASS |
| M3.5 gate >=2 viable, no dominant | `share/skills/w-ideation-mediation/SKILL.md:81-84` | PASS |
| M3.5 and Step 2 mutually exclusive | `share/skills/w-ideation-mediation/SKILL.md:84,100-101` | PASS |
| All 4 panelists dispatched parallel, PROPOSE directive | `share/skills/w-ideation-mediation/SKILL.md:85-94` | PASS |
| h-ideation-panel Propose Mode section | `share/skills/h-ideation-panel/SKILL.md:93-114` | PASS |
| Proposal required sections (5) | `share/skills/h-ideation-panel/SKILL.md:99-106` | PASS |
| h-ideation blackboard lists *-proposal.md | `share/skills/h-ideation/SKILL.md:69-93,117-120` | PASS |
| Pragmatist mode=compare with divergence matrix | `share/skills/w-ideation-mediation/SKILL.md:95-98; share/skills/h-ideation-panel/SKILL.md:173-188; share/agents/ideation-pragmatist.agent.md:94-123` | PASS |
| h-ideation-panel Pragmatist mode=compare contract | `share/skills/h-ideation-panel/SKILL.md:173-188` | PASS |
| Step 3 supports direction choice or hybridization | `share/skills/w-ideation-mediation/SKILL.md:114-119` | PASS |
| Two sequential post-hybridization Critic passes | `share/skills/w-ideation-mediation/SKILL.md:124-128` | PASS |
| Both Critic passes subject to O15 | `share/skills/w-ideation-mediation/SKILL.md:124-129` | PASS |
| Verification checklist updated with M3.5 items | `share/skills/w-ideation-mediation/SKILL.md:146,156-161` | PASS |
| 4 panelist agents: *-proposal.md output + propose-mode Critic skip | `ideation-{architect,data,enduser,security}.agent.md` output restrictions + propose-mode sections | PASS |
| Pragmatist agent mode=compare in persona and contract | `share/agents/ideation-pragmatist.agent.md:14-18,46-56,94-123` | PASS |
| Briefs README updated for proposals and compare path | `.owlbear/briefs/README.md:5-31,55-59,69-77` | PASS |

### Test Results
- pytest: 2739 passed, 117 failed, 4 skipped (0 failures in ideation scope; all 117 in kanban storage/engine and MCP knowledge — pre-existing debt)
- ruff: clean, 0 violations
- Ideation static suite: 30/30 passed (per reviewer evidence; 0 ideation failures in full run)

### Architect Quality: 4/5
AC was well-refined through architecture review (7 refinements, challenger-driven). Specific file paths, output format columns, delegation chain, and Critic input specs all explicit. Minor gap: pragmatist "two modes" wording pre-existed; AC amendment process (via DR) was well-managed.

### Deduction Breakdown
- -0.02: Commit integrity — deliverables bundled with unrelated #1086 in mixed commit `e3f2e9f9`; message doesn't mention #1148
- -0.01: Minor wording drift in `ideation-pragmatist.agent.md:14` ("two modes" while documenting three)

### Confidence: .97
### Action: archive