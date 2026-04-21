# End-User Critic Debate Log

## Cycle 1 — Scope Gating Staleness (Q5)

**Critic challenge:** "Your scope-gating recommendation adds a 'relevant code paths' field to the doc-index. That field is itself a mapping that must be maintained. You're solving staleness by introducing a new thing that can go stale. How is this different from the problem you're trying to fix?"

**Response:** The mapping is derived automatically, not manually maintained. A doc at `serve/kanban/README.md` relates to `serve/kanban/` by path structure — no human annotation needed. Content-derived relationships (e.g., an agent file that mentions "kanban" in its text) are parsed at index-generation time. The index is regeneratable on demand, so the mapping refreshes whenever the script runs.

The asymmetric cost matters: a false positive (checking a doc that didn't need it) costs a no-op check — seconds. A false negative (missing a doc that needed updating) costs accumulated rot — the exact problem we're solving. The automatic derivation should err toward over-inclusion.

**Outcome:** Position refined to emphasize automatic derivation and asymmetric cost. Core recommendation held.

## Cycle 2 — Diagram Date Footer Precision (Q2)

**Critic challenge:** "A date alone is a false signal. The diagram could be verified today, and the code could change an hour later. You're giving readers a false sense of freshness. Worse, a stale diagram with a recent date is more dangerous than one with no date at all."

**Response:** Agreed that date alone is insufficient. Strengthened to date + short commit hash (`abc1234`). The commit hash gives doc-audit a precise anchor: "has the relevant module changed since this commit?" The date gives the human reader a rough signal.

The Critic is right that a recently-dated stale diagram is dangerous — but the alternative (no signal at all) is worse. With no signal, *every* diagram is of unknown freshness. With a date+hash, at least the reader has a basis for judgment, and doc-audit has a machine-checkable anchor.

The "recent date but stale" scenario is caught by doc-audit (the periodic layer), not by the reader's judgment. The footer is a reader convenience; doc-audit is the enforcement mechanism. They work together.

**Outcome:** Position strengthened from date-only to date + commit hash. Acknowledged the Critic's point about false freshness but maintained that imperfect signal > no signal.

## Cycle 3 — Sweep Task Volume (Q3)

**Critic challenge:** "8 area tasks plus deletion proposals could total 10-15 tasks on the board. For a solo dev, that's a significant backlog addition on top of regular work. You're optimizing for progress visibility over board usability — the opposite of what you claim."

**Response:** The user explicitly stated "quality over everything, if it takes a month so be it." 10-15 tasks over a month is ~3-4 per week. The kanban board supports tag-based filtering — tagging all sweep tasks with `docs-sweep` lets the user hide them when working on non-docs tasks and surface them when doing docs work.

The alternative — one mega-task — is worse for the solo dev: it becomes a multi-week untrackable blocker with no sense of progress. The user can't see "I've done 6 of 8 areas" — they just see one task that's been in-progress for three weeks.

The real question is whether 8 is the right number, not whether grouping is right. 8 feels natural because it maps to directory structure (the way the user navigates the repo). If certain areas combine naturally in practice, the planner can merge them.

**Outcome:** Position held. Acknowledged the volume concern but maintained that grouped tasks with tag filtering is better than one mega-task or 76 micro-tasks.

## Cycle 4 — Index Format (Q4)

**Critic challenge:** "You dismiss JSON but agents parse JSON natively. Markdown requires string parsing that could introduce subtle bugs in doc-writer's index consultation. For an agent-consumed artifact, you're optimizing for the wrong audience."

**Response:** Fair point on parsing reliability. However, the workspace already has agents consuming markdown extensively — every agent file, skill file, and instruction file is markdown. The agents' markdown parsing is well-exercised.

The debugging use case is real: when doc-writer makes a surprising decision, the user opens the index to understand why. Markdown is immediately scannable in VS Code's preview pane. JSON requires mental parsing of braces and commas to find the relevant entry.

Updated position: markdown is preferred, JSON is acceptable. Both are viable. Binary/SQLite remains rejected for git-diff opacity. The planner should choose based on what doc-writer's implementation consumes most naturally — if the agent code parses JSON more cleanly, use JSON. This is an implementation detail, not a UX-critical decision.

**Outcome:** Position softened from "markdown is the right format" to "markdown preferred, JSON acceptable." The core constraint (human-debuggable, git-diffable) is what matters, not the specific format.

## Cycle 5 — Consumer Doc-Writer Boundary (Q6)

**Critic challenge:** "You say doc-writer v2 must not edit OwlBear-shipped files in consumer projects. But doc-writer's deny-code-writes hook already prevents editing files outside its scope. Isn't the existing hook sufficient? You might be inventing a problem that the current architecture already solves."

**Response:** The deny-code-writes hook prevents editing *application logic* files (`.py` control flow), not documentation files. Doc-writer is specifically allowed to edit markdown files. In a consumer project, OwlBear's shipped agent files (`share/agents/*.agent.md`) are markdown files that doc-writer is allowed to edit. Nothing in the current hook prevents doc-writer from "improving" `builder.agent.md` in a consumer's workspace.

The index marking ("OwlBear-shipped paths") is the right mechanism, but it needs to be enforced in doc-writer's scope rules, not just exist as metadata. The agent definition must say: "If the index marks a doc as OwlBear-shipped, skip it." Without this explicit rule, doc-writer v2's broader scope makes it MORE likely to touch OwlBear files, not less.

**Outcome:** Position held and strengthened. The Critic's challenge revealed that the existing deny-code-writes hook does NOT cover this case — it's a genuine gap that must be addressed in doc-writer v2's agent definition.

## Summary

Five cycles completed. Three positions refined (Q2 date→date+hash, Q4 markdown-only→markdown-preferred, Q5 emphasized automatic derivation). Two positions held under challenge (Q3 area grouping, Q6 consumer boundary). No positions reversed. The Critic's strongest contribution was on Q6 — forcing explicit analysis of why the existing hook doesn't cover the consumer boundary case.
