# End-User Stance — doc-writer quality

## User Experience Position

The primary UX improvement in this brief is not the marker mechanism — it is that task-related doc errors will be fixed inline and that pre-existing issues will be surfaced at all. Today the reader encounters wrong information with no signal that anyone knows it's wrong. After the redesign, task-caused errors get corrected and pre-existing rot gets flagged. That is a real improvement.

However, the locked decision to use HTML-comment-only TODO markers (`<!-- TODO(doc-writer): ... -->`) underserves the human reader. HTML comments are invisible in rendered markdown — GitHub, IDE preview panes, and any documentation site. For the human who reads the doc and encounters a stale API signature or a reference to a removed component, the experience is unchanged: they see wrong information, they have no warning, and they may act on it.

**I disagree with the locked mechanism.** The brief frames HTML comments as "visible to humans reading the doc" (context.md, Locked Outcome #1) — this is only true for humans reading raw `.md` source. That is a subset of the audience, not the audience.

## Usability Reasoning

### What the reader actually experiences

The reader outcome that matters is: **"when I read this doc, can I trust the information, or am I warned where I can't?"**

Under the current design:
- Task-caused issues → fixed inline. Reader experience improves. **Good.**
- Pre-existing issues → HTML comment inserted. Rendered-doc reader sees nothing. Raw-source reader sees the comment. **Partial.**
- Untouched packages → no change until doc-audit runs. **Unchanged.**

The inline fix behavior (Option C) is the correct UX call. Fixing task-caused errors at the point of change means readers of recently-touched docs get better information immediately. This is the primary win.

The TODO marker mechanism is where UX degrades. In a corpus described as "REALLY bad, outdated, and plain wrong," absence of a warning is weak evidence of correctness. The doc-writer will read a README, find multiple pre-existing issues, insert invisible comments, and the rendered doc looks exactly the same as before. The team thinks the problem is tracked; the reader is still misled.

### Why not all-visible warnings?

The Critic correctly challenged my original position that all pre-existing issues should get visible admonitions. In a broadly stale corpus:
- Visible warnings at scale become the dominant reader experience — a wall of ⚠️ markers is its own trust failure
- The doc-writer agent has not demonstrated reliable editorial judgment for severity classification
- False negatives (severe issue classified as minor → stays invisible) create a worse outcome than no classification at all

### What I recommend instead

**Visible warnings for a narrow, mechanically-identifiable class: references to removed or renamed symbols.** The brief already locks structural verification for "removal-focused checks" (decisions.md). When a grep finds a README referencing a symbol that no longer exists in the codebase, that is not an editorial judgment call — it is a mechanical fact. These should get a visible inline note (e.g., `> ⚠️ This section references \`orchestrator\` which has been removed.`). Everything else stays as HTML comments.

This avoids the severity-classification problem (mechanical checks, not LLM judgment) while giving the reader a warning for the highest-confidence class of stale information.

### Warning lifecycle

A visible warning that persists after the underlying issue is fixed becomes a new false statement. The doc-audit must explicitly remove warnings when resolving issues. Both insertion and removal are part of the TODO marker contract.

## Key Trade-offs

| Trade-off | Assessment |
|-----------|------------|
| HTML-only markers hide known issues from rendered-doc readers | Significant for humans. Acceptable for agents (they read raw source). |
| Visible warnings at scale create noise | Real risk. Mitigated by restricting to mechanically-verified removals only. |
| Severity calibration adds LLM judgment complexity | Avoid. Use mechanical checks for visible warnings, not editorial judgment. |
| Docs improve only on touched packages between audits | Acceptable. This is the inherent trade-off of task-scoped gates vs. corpus sweeps. |
| Doc-audit cadence determines whether markers clear | Critical. If audit discipline is weak, markers (visible or hidden) accumulate indefinitely. The brief should specify audit trigger conditions. |

## Warnings

1. **"Visible to humans" claim is wrong.** The locked outcome says TODO markers are "visible to humans reading the doc." This is false for rendered markdown. If the brief proceeds with HTML-only markers, this claim should be corrected to "visible to humans reading raw source and to automation."

2. **Trust cannot be recovered incrementally.** In a corpus where everything might be wrong, fixing one README's task-related issues does not make it trustworthy — the rest of the file may still be stale. Real trust recovery requires doc-audit completing full sweeps. The per-task gate makes docs *less wrong*, not *correct*.

3. **Doc-audit cadence is underspecified.** The brief defines doc-audit scope but not when it runs. If it runs quarterly, HTML TODO markers accumulate for months. If it runs after every 10 tasks, the backlog stays manageable. The user experience of the marker system depends entirely on audit frequency, which is not locked.

4. **Diagram deprioritization is correct.** Moving diagram work to doc-audit is the right UX call. Prose accuracy is higher-priority for both audiences: agents parse prose for API contracts, humans use prose for implementation guidance. Diagrams provide orientation but readers do not rely on them as authoritative. Per-task diagram freshness was verification theater; editorial depth in audit sweeps is better.

## Confidence

**0.78**

Core improvement (honest read + inline fix) is well-founded and will meaningfully improve reader experience. The marker mechanism disagreement is real but constrained — the HTML-only approach is suboptimal for humans but not catastrophic. The visible-warning-for-removals recommendation is narrow and mechanically grounded.
