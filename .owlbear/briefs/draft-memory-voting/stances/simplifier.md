# Simplifier Stance

## Preserved Expectation

Agents can signal which memories were useful; that signal improves recall ordering over time and helps humans curate.

## Scope Inflation Identified

### 1. Cold-start protection is premature mechanism design

Cold-start protection is only necessary if vote-based ordering *replaces* confidence. If votes are a secondary signal layered onto the existing confidence sort, new entries surface naturally via their confidence score until they accumulate votes. The cold-start problem is self-created by the ordering-switch design.

**Cut:** Drop the cold-start mechanism. Keep confidence as primary sort; use votes as tiebreaker/boost. The problem disappears.

### 2. Hybrid promotion/deletion queue is scope creep

The stated problem is "agents can't signal usefulness." The vote field alone gives humans the deletion/promotion signal they need — they look at the numbers. A separate system-marks-for-deletion workflow with confirmation UI is a second feature dressed as part of the first.

**Cut:** Defer the automated mark-for-deletion/promotion system. Vote data is visible in the existing curation workflow. Humans already curate manually.

### 3. Bias resilience is speculative engineering

Designing against "context-dependent voting bias" before observing actual voting patterns is building armor against an imagined enemy. A global score pooled across agents already dilutes individual-task noise. If bias proves real after deployment, the mitigation can be designed with real data.

**Cut:** Drop bias-resilience constraints from V1. Observe. Revisit if voting data shows pathological patterns.

## Recommended Decomposition

| Phase | Delivers | Complexity |
|-------|----------|------------|
| **P1** | `usefulness` field + `vote` MCP tool + vote counts visible in recall results | Low — one field, one tool, display-only |
| **P2** (only if P1 data warrants) | Adjust recall ordering to weight votes | Medium — requires threshold tuning |
| **P3** (only if curation pain persists) | Automated promotion/deletion suggestions | Medium — requires UI + confirmation flow |

## What Remains After First Useful Step (P1)

- Agents vote at end-of-task (lightweight tool — preserved)
- Humans see vote signal during curation (visibility — preserved)
- Recall ordering unchanged until real vote data justifies the change (no risk of regression)
- Self-improving recall is *enabled* but not *activated* — activation is a separate, informed decision

## Confidence: 0.85
