# M3.5 Proposal Round — Research

> **Owning task:** #1148 — Add M3.5 proposal round to ideation mediation
> **Date:** 2026-04-27 **Status:** Complete

## 1. Context and Question

Can a gated "Design It Twice" proposal step be inserted into Phase 2 mediation using only skill/handbook markdown changes, as the AC claims? What design clarifications and scope amendments are needed?

Split from #1147 by architect review. User-directed feature addition.

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | Ousterhout "A Philosophy of Software Design" Ch.11 — Design It Twice | Book/concept | .90 |
| 2 | mattpocock/skills `design-an-interface` SKILL.md | GitHub skill | .85 |
| 3 | `w-ideation-mediation/SKILL.md` (current) | Codebase | .95 |
| 4 | `h-ideation-panel/SKILL.md` (current) | Codebase | .95 |
| 5 | `h-ideation/SKILL.md` (current) | Codebase | .90 |
| 6 | `ideation-{architect,data,enduser,security}.agent.md` | Codebase | .95 |
| 7 | `ideation-pragmatist.agent.md` | Codebase | .90 |
| 8 | `.owlbear/hooks/allow-stances-only.py` | Codebase | .85 |

## 3. Analysis

### 3.1 Prior Art Validation

Both sources confirm "Design It Twice" is sound and has prior agent implementations:

- **Ousterhout**: Generate ≥2 radically different approaches for any non-trivial design; comparison reveals what matters more than either design alone.
- **mattpocock/skills**: Spawns 3+ sub-agents with different constraint directives in parallel, each producing a complete interface, then compares. Structural match to the AC's parallel propose-mode dispatch.

### 3.2 Architecture Fit — Trade-off Matrix

| Criterion | Assessment | Evidence |
|-----------|-----------|----------|
| Hook compatibility | PASS | `_STANCES_RE = re.compile(r"(/\|^)stances/")` matches `stances/*-proposal.md` |
| Parallel dispatch | PASS | h-ideation-panel "Parallel Batch" pattern already supports 4 panelists in parallel |
| Pragmatist extension | NEEDS WORK | Agent file defines only converge/denoise; mode=compare requires agent file update |
| Panelist output paths | NEEDS WORK | Agent files restrict to `stances/{name}.md` + `stances/{name}-debate.md`; proposal files not listed |
| Critic loop in propose mode | NEEDS WORK | Agent files say "Critic loop is mandatory"; propose mode intent is generative, not adversarial |
| Step 2 flow when M3.5 triggers | AMBIGUOUS | AC doesn't explicitly state whether Step 2 is replaced or supplemented |
| Mediator agent | PASS | Already has `ideation-critic` in agents list for dual Critic passes |

### 3.3 Agent File Contract Conflicts (challenger-identified)

Three conflicts between the AC's "no .agent.md changes" scope and the actual agent contracts:

**C1 — Output file restrictions.** All 4 panelist agent files say: "Your sole output files are `stances/{name}.md` and `stances/{name}-debate.md`." Writing `stances/{name}-proposal.md` violates this contract.

**C2 — Mandatory Critic loop.** All 4 panelist agent files say: "Critic loop is mandatory. Never release an unexamined first draft." Propose mode's generative intent (confirmed by the dual post-hybridization Critic design) implies skipping embedded Critic loops.

**C3 — Pragmatist mode list.** Pragmatist agent file persona and contract define only converge and denoise. mode=compare is undefined.

**Resolution**: The AC's out-of-scope item says "Panelist `.agent.md` changes (mode is prompt-driven)" — the intent is no NEW agent files. Minor updates to EXISTING agent files (output paths, mode list, propose-mode Critic behavior) are necessary and should be added to the AC. The alternative (prompt-override of agent contracts) works in practice but creates architectural debt.

### 3.4 Flow Clarification

When M3.5 triggers, the flow should be:

```
Step 1 (M3) → Step 1.5 (M3.5 gate + parallel propose-mode dispatch)
  → Pragmatist mode=compare → synthesis.md
  → Step 3 (modified M4: comparison-driven decision)
  → Step 4 (dual Critic: synthesis + result)
```

Step 2 (normal stance-mode panel + Pragmatist converge) is skipped when M3.5 fires. The two paths produce the same artifact (`synthesis.md`) with different semantics — stance convergence vs. proposal comparison.

### 3.5 Critic Loop Design

| Option | Pro | Con | Confidence |
|--------|-----|-----|------------|
| A: Skip Critic loop in propose mode | Lower latency (avoid 4×5 calls), cleaner separation (generative vs adversarial) | Proposals may contain unchallenged weaknesses | .75 |
| B: Keep Critic loop in propose mode | Proposals are hardened before comparison | 20 extra Critic calls, redundant with dual post-hybridization Critic | .55 |
| C: Reduced Critic (1 cycle max) | Balance: one quick check without full adversarial loop | Non-standard; adds complexity | .40 |

**Recommendation**: Option A (.75 confidence). The dual post-hybridization Critic pass catches issues at the right abstraction level — after the user has made choices and elements are combined.

## 4. Recommendation

The M3.5 proposal round is architecturally sound and implementable with one scope amendment: **minor updates to existing panelist and pragmatist agent files are required** in addition to the three skill files. No new agent files are needed.

**Amended scope (3 skill files + 5 agent files):**
- `w-ideation-mediation/SKILL.md` — Step 1.5, Step 2 conditional skip, modified Step 3, verification checklist
- `h-ideation-panel/SKILL.md` — Propose Mode section, Pragmatist mode=compare
- `h-ideation/SKILL.md` — Blackboard artifacts (add `*-proposal.md`)
- `ideation-{architect,data,enduser,security}.agent.md` — Add proposal output path, note propose-mode cycle
- `ideation-pragmatist.agent.md` — Add mode=compare to persona and contract

**Confidence**: .72 overall. Core design is solid; main risk is the Step 2 replacement semantics and Critic loop behavior need explicit definition in the skill text.

**Challenge**: reconsider — confidence in original: .34. Challenger identified genuine contract conflicts (C1-C3) that required scope amendment. Researcher accepted C1-C3 and the T2 classification.

## 5. Follow-up Tasks

- #1148 AC amendment: add agent file updates to scope (see Section 3.3)
- Tier: T2 (advisory) — adds new pipeline behavior, but user-directed and architect-reviewed
