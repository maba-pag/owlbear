# Loop-Breaker Protocol Update — 2-Batch-Cycle Threshold

> **Owning task:** #1408 — B2: Loop-breaker protocol update — 2-batch-cycle threshold
> **Date:** 2026-05-09 **Status:** Complete

## 1. Context and Question

The brief (#1403) specifies changing the loop-breaker from a FAIL-count model to a batch-review-cycle model. With the B1 reviewer rewrite (archived #1407) now shipping batch-all-findings, the loop-breaker terminology needs to reflect the new review model where each cycle collects all findings at once.

**Key discovery:** Commit `96ed7280` (April 29) already changed the numeric threshold from 3 to 2 (was "3rd+ FAIL," now "2nd+ FAIL"). The remaining work is a **terminology update** — replacing "FAIL" counting with "batch review cycle" counting — plus adding the cycle-3 architect escalation from synthesis recommendation #7.

## 2. Sources Studied

| Source | Path | Relevance |
|--------|------|-----------|
| Brief #1403 | `.owlbear/briefs/draft-pipeline-review-rethink/brief.md` (B2 row) | 1.0 — defines the change |
| Synthesis (panel convergence C3) | `.owlbear/briefs/draft-pipeline-review-rethink/synthesis.md` (lines 29-31, 148) | 1.0 — "2 batch cycles, cycle-3 architect escalation" |
| Architect stance Q4 | `.owlbear/briefs/draft-pipeline-review-rethink/stances/architect.md` (lines 91-95) | 0.9 — "start at 2 batch-review cycles" |
| Protocol file | `share/skills/r-pipeline-protocol/SKILL.md` (lines 112-114) | 1.0 — current text |
| Code-review skill | `share/skills/w-code-review/SKILL.md` (line 211) | 1.0 — downstream reference |
| Reviewer agent | `share/agents/reviewer.agent.md` (line 61) | 0.9 — downstream reference |
| Broad-audit prompt | `share/prompts/agent-broad-audit.prompt.md` (line 135) | 0.8 — downstream reference |
| Git history (96ed7280) | Commit diff | 1.0 — proves threshold already changed 3→2 |

## 3. Analysis

### What changed in B1 (already shipped)

The reviewer now uses **batch-all-findings** (no first-failure gating). Each review pass collects every finding before issuing a verdict. This means each "cycle" has higher diagnostic value than the old per-finding gating model.

### Current state vs. target state

| Aspect | Current | Target |
|--------|---------|--------|
| Counting unit | "FAIL" (individual verdict) | "batch review cycle" (full review pass) |
| Threshold | 2nd+ FAIL → backlog | 2nd batch review cycle → backlog |
| Detection | Count `## Review Evidence` sections | Count `## Review Evidence` sections (same mechanism) |
| Cycle-3 escalation | Not defined | Architect AC refinement |

### Files requiring changes

| File | Current text | New text |
|------|-------------|----------|
| `r-pipeline-protocol/SKILL.md` | `< .90, 1st FAIL` / `< .90, 2nd+ FAIL` | `< .90, 1st batch review cycle` / `< .90, 2nd+ batch review cycle` |
| `w-code-review/SKILL.md` | `2nd+ review FAIL on same task` | `2nd+ batch review cycle on same task` |
| `reviewer.agent.md` | `Fail (2nd+)` / `2nd+ review failure` | `Fail (2nd+ cycle)` / `2nd+ batch review cycle` |
| `agent-broad-audit.prompt.md` | `2nd+ FAIL` | `2nd+ batch review cycle` |

### Cycle-3 architect escalation (new)

The synthesis (rec #7) specifies: "with escalation to architect for AC refinement on cycle 3." This adds a new row to the Confidence Thresholds table — if a task reaches a 3rd batch review cycle, it should escalate to the architect to refine AC rather than just looping through backlog again.

## 4. Recommendation (confidence: 0.90)

Create one follow-up task to make the terminology update across all four files and add the cycle-3 escalation row. The change is mechanical — well-defined text replacements plus one new table row.

**Challenge: SKIP — trivial terminology update with no design ambiguity.**

## 5. Follow-up Tasks

One task: update loop-breaker terminology and add cycle-3 escalation across 4 files.
