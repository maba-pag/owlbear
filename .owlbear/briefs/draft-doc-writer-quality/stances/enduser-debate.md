# End-User Debate Log — doc-writer quality

## Round 1

### Draft Position

HTML comment TODO markers are an anti-pattern for user experience. They hide known problems from the primary audience (rendered-markdown readers) while creating a false sense of progress. The decision to use `<!-- TODO(...) -->` optimizes for implementation convenience (no kanban dedup, no board flooding) at the expense of user-visible honesty.

Key claims:
1. Invisible markers serve machines, not humans
2. TODO insertion is verification theater under a new name
3. "Littered with TODOs" interim period harms trust
4. Honest verification matters at point of reading, not point of writing
5. Diagram quality is secondary to prose accuracy for both audiences

Confidence: 0.75

### Critic Challenges (Round 1)

- **Critical:** Position collapses dual-audience system into single rendered-reader model. Agents read raw markdown — HTML comments ARE visible to that audience. Machine-readable debt tracking is part of the operating contract.
- **Moderate:** TODO markers ≠ verification theater. A debt admission is semantically different from a false certification ("Last verified: ..."). The equivalence flattens a real distinction.
- **Moderate:** "Worse than no marker" is asserted, not demonstrated. No marker gives no hook for doc-audit, no source-local context for maintainers, no persistent signal.
- **Moderate:** Recommendation attacks presentation, not the actual failure mode. The root cause is that doc-writer never reads the README. Visible warnings could become a new form of theater (shallow scan → broad caveats).
- **Moderate:** Scale problem underplayed. Corpus is "REALLY bad" — visible warning density could become the dominant reader experience.
- **Minor:** Diagram argument overreaches. Reassigning ownership doesn't prove diagrams are secondary.

Blind spots flagged: warning staleness, severity calibration, source-mode readers, doc-audit follow-through as real bottleneck, locality vs. visibility distinction.

Critic confidence: 0.58. Pressure: medium.

### Position Revisions (Post-Round 1)

1. **Dual audience acknowledged.** Revised to recognize agents as raw-source readers for whom HTML comments are visible. The fix is severity-calibrated, not all-visible.
2. **TODO ≠ theater — conceded.** Dropped the equivalence. Shifted concern to "is invisible honesty sufficient for the reader who encounters wrong information?"
3. **Scale-aware calibration added.** Only high-impact issues (wrong APIs, stale references to removed components) should get visible warnings. Minor issues stay as HTML comments.
4. **Warning lifecycle added.** Visible warnings must be removed by doc-audit when resolving the underlying issue.
5. **Doc-audit discipline identified as real bottleneck.** Marker format matters less if audit doesn't run.

Confidence: 0.80

## Round 2

### Revised Position Summary

Core: honest verification behavior is the primary UX improvement. HTML-comment-only markers underserve human readers. Severity-calibrated approach — visible admonitions for high-impact issues, HTML comments for minor ones — serves both audiences.

### Critic Challenges (Round 2)

- **Critical:** Position still blesses the brief decision while rejecting its locked mechanism. Option C is called correct, but its specific TODO-comment-only mechanism is challenged. This is a direct disagreement with a locked decision — should be stated explicitly.
- **Critical:** "Primary UX win" claim is process-centered, not end-user-centered. Readers don't experience honest reading — they experience corrected prose, visible warnings, or silence. Reader-facing signal remains primary by the panelist's own test.
- **Critical:** Overclaims trust recovery in a broadly broken corpus. Absence of warning is weak evidence in a corpus where everything might be wrong. Brief describes diffuse rot, not isolated defects.
- **Moderate:** Severity calibration depends on reliable classification from an agent that hasn't shown reliable baseline editorial judgment.
- **Moderate:** Scope overstated. "Doc-writer will actually read the docs" sounds corpus-wide, but locked behavior is per-touched-package only.
- **Moderate:** Rendered-reader proportion is asserted, not established.
- **Moderate:** Calibration examples are cleaner than the problem. "Missing coverage" can be action-blocking too — omission severity is contextual.

Blind spots flagged: false negatives (severe issue mislabeled minor → stays invisible), document-level trust (what does an unmarked paragraph mean in a broadly stale file), uneven remediation tempo.

Critic confidence: 0.57. Pressure: high.

### Final Position Revisions (Post-Round 2)

1. **Explicit disagreement with locked decision.** Stated directly that I disagree with the HTML-only TODO marker mechanism.
2. **Reframed from process to reader outcome.** Primary framing is now "what the reader experiences" — inline fixes (good), invisible markers (partial), untouched packages (unchanged).
3. **Trust recovery acknowledged as corpus-dependent.** Per-task gates make docs "less wrong," not "correct." Real trust recovery requires doc-audit completing full sweeps.
4. **Narrowed visible-warning scope to avoid classification problem.** Instead of severity calibration (requires LLM judgment), recommend visible warnings only for mechanically-identifiable removals (symbol no longer exists in codebase). Avoids the false-negative risk from bad classification.
5. **Added doc-audit cadence warning.** Marker system effectiveness depends entirely on audit frequency, which is not locked.

Final confidence: 0.78
