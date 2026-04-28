# M3.5 Proposal-Round Static Test Coverage — Research

> **Owning task:** #1153 — Add static coverage for ideation M3.5 proposal-round contracts
> **Date:** 2026-04-28 **Status:** Complete

## 1. Context and Question

Task #1148 added M3.5 proposal-round contracts across 8 files (3 skills, 4 panelist agents, 1 pragmatist agent). The existing `test_ideation_overhaul_static.py` covers Phase 1 contracts (early challenge lane, critic exclusion) and golden scenarios but has **zero coverage** for M3.5 proposal-round contracts. What contract surfaces need static tests?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| 1 | `h-ideation-panel/SKILL.md` — Propose Mode + mode=compare sections | .95 |
| 2 | `w-ideation-mediation/SKILL.md` — Step 1.5 + verification checklist | .95 |
| 3 | `h-ideation/SKILL.md` — blackboard artifact list | .85 |
| 4 | `ideation-{architect,data,enduser,security}.agent.md` — PROPOSE mode | .90 |
| 5 | `ideation-pragmatist.agent.md` — mode=compare | .90 |
| 6 | `.owlbear/briefs/README.md` — proposal file listing | .85 |
| 7 | `tests/test_ideation_overhaul_static.py` (current, 447 lines) | .95 |
| 8 | `.owlbear/research/1148-m3-5-proposal-round.md` — original research | .80 |

## 3. Analysis

### 3.1 Contract Surface Inventory

Seven contract surfaces across 8 files, all implemented by #1148, none tested:

| # | File | Contract | Testable Needles |
|---|------|----------|------------------|
| C1 | `h-ideation-panel/SKILL.md` | Propose Mode section | `### Propose Mode (M3.5 Path)`, `stances/{name}-proposal.md`, 5 required sections |
| C2 | `h-ideation-panel/SKILL.md` | Critic skip in propose | `In propose mode, panelists skip the embedded Critic loop` |
| C3 | `h-ideation-panel/SKILL.md` | Pragmatist mode=compare | `### mode=compare`, `divergence-only comparison matrix`, `common ground summary`, `open questions` |
| C4 | `w-ideation-mediation/SKILL.md` | Step 1.5 gate | `## Step 1.5`, `at least two viable approaches and no dominant option` |
| C5 | `w-ideation-mediation/SKILL.md` | Mutual exclusivity | `M3.5 and Step 2 are mutually exclusive` |
| C6 | Agent files ×4 | PROPOSE mode contract | `PROPOSE mode`, `stances/{name}-proposal.md`, Critic skip |
| C7 | `ideation-pragmatist.agent.md` | mode=compare | `mode=compare`, `stances/*-proposal.md` |

### 3.2 Implementation Approach — Trade-offs

| Approach | Pro | Con | Confidence |
|----------|-----|-----|------------|
| A: One new test class in existing file | Follows existing pattern, single location | File grows to ~550 lines | .85 |
| B: Separate test file | Isolation, cleaner git blame | Fragments coverage, duplicates helpers | .40 |
| C: Parametrize panelist agents | DRY for C6 (4 agents same contract) | Slightly harder to read | .75 |

**Recommendation**: A + C combined (.85). Add one `TestFromAC_ProposalRoundContracts` class to the existing file, using `pytest.mark.parametrize` for the 4-panelist agent check. Matches the existing `TestFromAC_*` naming pattern.

### 3.3 Proposed Test Methods

| Test | Contracts Covered |
|------|-------------------|
| `test_panel_handbook_has_propose_mode_section` | C1 |
| `test_propose_mode_requires_five_proposal_sections` | C1 (required sections) |
| `test_propose_mode_skips_critic_loop` | C2 |
| `test_pragmatist_has_compare_mode` | C3 |
| `test_compare_mode_defines_output_structure` | C3 (matrix, common ground, open Qs) |
| `test_mediation_has_m35_gate` | C4 |
| `test_m35_and_step2_mutually_exclusive` | C5 |
| `test_panelist_agents_support_propose_mode[name]` | C6 (parametrized ×4) |
| `test_pragmatist_agent_has_compare_mode` | C7 |
| `test_blackboard_documents_proposal_artifacts` | h-ideation + briefs README |

~10 test methods, ~100 lines of code.

## 4. Recommendation

Add a single `TestFromAC_ProposalRoundContracts` class to `test_ideation_overhaul_static.py` covering all 7 contract surfaces. Implementation is straightforward string-presence assertions following the established pattern. No golden scenario fixtures needed — the contracts are in the skill/agent files themselves.

**Confidence**: .88. All contract text is already in the files. Risk is only needle string fragility if someone rewords a sentence.

**Challenge**: Skipped — this is info-only/trivial research (no architectural recommendation, no new capability). The "recommendation" is purely about test class placement (T1 autonomous).

## 5. Follow-up Tasks

- One implementation task: add the test class (target: `backlog` → `todo`)
- Tier: T1 — adding test coverage for already-implemented contracts, no architecture change
