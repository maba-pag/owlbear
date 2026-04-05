# Error and Rescue Map Template for Arch-Review

> **Owning task:** #785 — Add Error and Rescue Map template to arch-review skill
> **Date:** 2026-03-13 **Status:** Complete

## 1. Context and Question

OwlBear's architect agent reviews tasks at the backlog → todo gate. The arch-review skill Step 3 checks security surface (new system boundaries) but has no structured template for mapping codepaths to failure modes. The question: what template format best fits our existing architecture review workflow?

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| gstack plan-eng-review SKILL.md | <https://github.com/garrytan/gstack/blob/main/plan-eng-review/SKILL.md> | .90 | "Failure modes" required output: per-codepath failure scenario + test coverage + error handling + user impact. Architecture review step: "describe one realistic production failure scenario" |
| FMEA (MIL-STD-1629A / Wikipedia) | <https://en.wikipedia.org/wiki/Failure_mode_and_effects_analysis> | .75 | Industry standard: Item → Failure Mode → Cause → Effect → Severity → Probability → Detection → Risk. Software FMEA: existence, controls count, detectability |

## 3. Analysis

### Template Comparison

| Criterion | gstack's approach (.85) | Full FMEA (.50) | Hybrid (.80) |
|-----------|------------------------|------------------|--------------|
| Columns | Codepath, failure, test?, handled?, user impact | 15 columns (Item, Mode, Cause, Local/System Effect, P, S, D, RPN, Mitigation…) | Codepath, Failure Mode, Exception, Handled?, Test?, User Impact |
| Complexity | Low — 5 columns, prose-friendly | High — requires P×S×D scoring, ordinal scales | Medium — 6 columns, no scoring needed |
| KISS fit | Excellent | Overkill for architecture review | Good |
| Gaps caught | Silent failures, untested paths | Everything (but at high cost) | Silent failures + exception mapping |
| Agent effort | ~2 min per codepath | ~10 min per codepath | ~3 min per codepath |
| Existing fit | Matches arch-review's prose style | Would need new scoring rubric | Extends current security surface check |

### Key Differences from gstack

1. **gstack embeds failure analysis in a plan-review skill** (human-interactive, with AskUserQuestion). OwlBear's architect operates autonomously — the template must be self-contained, not interactive.
2. **gstack requires one failure scenario per codepath.** Sufficient for planning; OwlBear's architect should flag codepaths with no failure analysis rather than mandate exhaustive coverage (YAGNI).
3. **gstack mixes failure modes into a "Required outputs" blob.** OwlBear should make it a discrete checklist step in Step 3 for clear audit trail.

### Integration Points

- **arch-review SKILL.md Step 3** — new sub-step 10 after "Security surface" (item 8) and "Single domain" (item 9). Natural extension of the security/boundary analysis.
- **architect.agent.md self-critique** — add one checkbox: "Failure mode map completed for new codepaths."
- **No .py changes** — this is purely agent configuration.

## 4. Recommendation (.80 confidence)

**Adopt a hybrid template** — gstack's simplicity + FMEA's explicit exception/handling columns. Six columns, no scoring rubric, no probability calculations. The architect fills it for each new codepath in the task under review.

Template:

```
| Codepath | Failure Mode | Exception Type | Handled? | Tested? | User Impact |
|----------|-------------|----------------|----------|---------|-------------|
| {method/function} | {what can go wrong} | {exception class or N/A} | Yes/No | Yes/No | {clear error / silent / degraded} |
```

**Critical gap rule** (from gstack): If any row has Handled=No AND Tested=No AND User Impact=silent → flag as **critical gap**, block the task.

Risk: Low. Adding a sub-step to Step 3 and one checklist item is minimal change. The architect can skip the table for trivial tasks (rename, config tweak) with `N/A — no new codepaths`.

## 5. Follow-up Tasks

Task #785 itself is the implementation task (already at ideation). No additional tasks needed — the AC is already well-defined. The researcher's role is to validate the approach and refine the template.

Refined AC for #785 based on research:

- arch-review SKILL.md Step 3 gets item 10: "Failure Mode Map" with the 6-column template
- Critical gap rule: Handled=No + Tested=No + silent → block
- Trivial-task escape: `N/A — no new codepaths`
- architect.agent.md self-critique: one new checkbox
