# End-User Debate Log

## Cycle 1

### Draft Position

1. **Deep-dive model:** Section-by-section with diff context (B+C hybrid). H2/H3 boundaries as review units. Before/after with 2-3 lines surrounding context. Files <100 lines get optional full-file view; files >200 lines force section-by-section.
2. **Cognitive load:** Temporal separation — findings during, ranked artifact only at end.
3. **Session continuity:** Pass broad-audit findings as "priming context" to deep-dive. Deep-dive may disagree.
4. **Granularity:** One proposal per logical section (H2 boundary). 5-12 decisions per file.

### Critic Challenges (Cycle 1)

| # | Severity | Challenge | Impact on Position |
|---|----------|-----------|-------------------|
| 1 | Critical | H2 boundaries as review units bakes in structural defects — the files grew organically, structure itself is suspect | Must allow structural proposals before/alongside compression |
| 2 | Critical | One-section-at-a-time with 2-3 lines context is too local for edits that are moves/merges across sections or files | Need mechanism for cross-section/cross-file proposals |
| 3 | Moderate | Line-count thresholds (100/200) are arbitrary — section size variance matters more | Drop arbitrary thresholds, use semantic boundaries |
| 4 | Moderate | Temporal separation = delayed cognitive load, not reduced. If ranking arrives after full finding stream, indicator comes too late | Consider progressive element |
| 5 | Critical | Passing audit findings forward creates anchoring regardless of "provisional" framing. Deep-dive should form independent view | Reframe or remove context passing |
| 6 | Moderate | 5-12 approvals × 80 files = 400-960 decisions total. Unaddressed throughput problem | Need escape hatches and funnel acknowledgment |

### Position Updates After Cycle 1

- Added two-pass model: structural proposals first, then compression
- Revised to progressive ranking (building during audit)
- Reframed context passing as "observations not conclusions"
- Added escape hatches for throughput

## Cycle 2

### Revised Position

1. **Deep-dive model:** Two-pass (structural batch → compression section-by-section). Sub-chunks for >80 line sections. Full-file option for <80 line files.
2. **Cognitive load:** Progressive ranking (available every 5-10 files), final artifact at end.
3. **Session continuity:** Audit findings as "prior observations" — provisional, deep-dive may disagree without justification.
4. **Granularity:** Section-based with "approve remaining" and "show all" escape hatches. Funnel narrows 80 → 15-25 → 3-5 per session.

### Critic Challenges (Cycle 2)

| # | Severity | Challenge | Impact on Position |
|---|----------|-----------|-------------------|
| 1 | Moderate | Two-pass model creates unstable review unit + context switching. Now have 4 modes (structural batch, section, sub-chunk, full-file) — too complex | Collapse to single proposal document |
| 2 | Moderate | "Approve remaining" assumes risk homogeneity across unseen sections — contradicts the finding that individual files contain mixed risk levels | Gate behind summary of what remains |
| 3 | Critical | Progressive ranking on incomplete cohort produces meaningless relative scores. Ranking shown at file 5/80 is noise | Concede: ranking is end-of-run only |
| 4 | Critical | "Observations not conclusions" relabeling doesn't neutralize anchoring. Priming frame is still injected before deep-dive forms own view | Remove automatic context passing entirely |
| 5 | — (blind spot) | No treatment of how rankings change after structural cross-file moves | Acknowledged; this is broad-audit's responsibility to handle |
| 6 | — (blind spot) | 80-line threshold is arbitrary, defended by length not signal density | Drop numeric threshold, use "short enough to review holistically" as user judgment |

### Final Position Updates

- Collapsed two-pass into single proposal document with two labeled regions (structure first, compression second)
- Conceded progressive ranking — end-of-run only; running "attention flags" (unranked) as compromise
- Removed automatic context passing — deep-dive is sovereign, user bridges manually
- "Approve remaining" requires one-line-per-section summary of what's left
- Dropped arbitrary line thresholds; <80 line full-file mode is user's choice not rule

## Resolution

Position hardened after two Critic cycles. Key concessions: progressive ranking dropped (relative scoring needs complete data), automatic context passing dropped (anchoring is real regardless of framing), multi-mode review collapsed to single document. Confidence: 0.72.
