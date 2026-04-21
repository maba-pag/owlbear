# End-User Stance — Documentation Currency Brief

## User Experience Stance

The Brief's design is structurally sound but has five usability gaps that will erode the user experience if shipped as-is. The biggest risk is not the sweep or the audit — it's the **daily per-task impact of doc-writer v2's broadened scope** (Q5). If every task's docs phase suddenly scans 76 files instead of 5, the user learns to ignore doc-writer output. That's the cry-wolf failure mode, and it directly undermines the entire Brief's purpose.

## Usability Reasoning

### Q1 — doc-audit.prompt.md Pacing

**Position: Pre-scan summary is essential. Area-by-area phasing is nice-to-have. "Stop now" is already solved.**

The agent-audit mirror works because its finding queue is naturally bounded — most files pass most dimensions. Doc-audit has a wider rot surface (~76 files, five rot categories confirmed present). A naive one-finding-at-a-time loop could produce 50+ findings before the user sees the shape of the problem.

Required pacing elements:

1. **Pre-scan summary first.** Before any findings loop, doc-audit scans all ~76 files and presents: count of findings per area (root, agents, skills, instructions, prompts, setup, serve) × severity. The user sees "12 high, 8 medium, 22 low across 6 areas" and can make an informed time-commitment decision. This is a 30-second investment that prevents a 2-hour surprise.

2. **Area opt-in/opt-out.** After the pre-scan, the user picks which areas to audit now. "Skip agents, I know those are fine" is a valid choice. The skipped areas remain in the queue for next invocation.

3. **"Stop now" = summarize remaining queue.** This is already in agent-audit's contract ("summarize remaining queue on exit") and should carry over verbatim. No new mechanism needed.

4. **Do NOT add dimension opt-out.** The user doesn't think in audit dimensions (D1–D7). They think in areas ("fix the agent docs"). Dimension filtering adds cognitive load for no practical benefit — the pre-scan summary already lets them control scope via area selection.

### Q2 — Descriptive-Not-Authoritative Diagrams: Reader Signal

**Position: Every diagram needs a visible "Last verified" footer. Date + short commit hash. This is both a reader signal and a machine-checkable anchor for doc-audit.**

A diagram without a freshness signal is worse than no diagram — it creates false confidence. The reader has no way to know if the architecture overview reflects today's code or last quarter's.

Concrete recommendation:
- **In-diagram footer:** `Descriptive — last verified YYYY-MM-DD (abc1234)` placed in a text element at the bottom of every Excalidraw diagram.
- **doc-audit checks this:** Compare the date/commit against recent commits touching the diagram's subject modules. If the code has changed materially since the verification date, flag the diagram as potentially stale.
- **Filename convention adds nothing.** Readers don't infer currency from filenames. Don't bother.
- **Generated-from-template is overengineered** for 7 diagrams. A footer text element is sufficient.

The date+hash combination serves two audiences: humans glance at the date for rough freshness; machines (doc-audit) use the commit hash for precise staleness detection.

### Q3 — Sweep Task Granularity

**Position: One task per area (~8 tasks), with individual tasks for deletion proposals and the SECURITY.md rewrite.**

76 individual file tasks would drown the kanban board. One mega-task would be a multi-week blocker with no progress visibility. Area grouping is the natural granularity because it matches how the user actually works: "today I'll fix the serve READMEs."

Concrete breakdown:
- Root docs (README.md, README-consumer.md, SECURITY.md) — likely 2 tasks: one for READMEs, one for SECURITY.md (which is a full rewrite)
- `serve/*` READMEs — 1 task (includes creating the 7 missing ones)
- `share/agents/` — 1 task
- `share/skills/` — 1 task
- `share/instructions/` + `share/prompts/` — 1 task (small surface, combinable)
- `setup/` + `.github/copilot-instructions.md` — 1 task
- Deletion proposals — 1 task per file proposed for deletion (user-gated, must not be buried inside a fix task)

Total: ~8-10 sweep tasks. Tag all with `docs-sweep` for board filtering. At ~3/week, this fits inside the user's "if it takes a month, so be it" appetite.

### Q4 — Index Visibility and Format

**Position: The index is 95% agent-consumed but must be human-debuggable. Markdown is the right format. Not binary, not SQLite.**

The solo dev will read the index exactly when doc-writer makes a puzzling decision and they need to understand why. That debugging use case is infrequent but high-stakes — if the index is opaque (binary/SQLite), the user can't diagnose doc-writer behavior without additional tooling.

Format recommendation:
- **Markdown** — one file, flat table or heading-per-file structure. Agents parse markdown reliably; humans scan it trivially; git diffs are meaningful.
- **JSON/YAML are acceptable alternatives** but add a parser dependency for human reading (opening raw JSON is less scannable than markdown in a quick VS Code glance).
- **Binary/SQLite is rejected.** The git-diff opacity alone disqualifies it — you can't see what changed in the index after regeneration. The performance argument is irrelevant for ~76 entries.

The index lives in `.owlbear/` (dev-only, doesn't sync to main). This is correct — the index is project-specific and regeneratable. **But the generator script must live in a synced path** (see Q6).

### Q5 — doc-writer v2 Broadened Scope: Per-Task UX Impact

**Position: This is the highest UX risk in the entire Brief. Without scope gating, doc-writer v2 will degrade the daily development experience.**

The math: doc-writer v1 checks 5 paths → ~90% no-op rate. Doc-writer v2 checks ~76 paths. If the relevance check is naive (scan all 76 for every task), the per-task docs phase gets slower, noisier, and less trustworthy. The user will either:
- Wait longer for docs phase to complete (time cost)
- See more false-positive "this doc might need updating" findings (attention cost)
- Learn to skim/ignore doc-writer output (trust cost — the cry-wolf failure mode)

**Required mitigation: index-driven scope gating.**

The doc-index must include a "relevant code paths" field per doc entry, derived automatically from file paths and content references (not manually maintained). Doc-writer v2 consults the index, intersects with the task's changed files, and checks only the overlapping docs.

Example: A task that modifies `serve/kanban/src/` triggers doc-writer to check:
- `serve/kanban/README.md` (path-derived)
- Agent files that reference kanban in their content (content-derived)
- Root README if it has a kanban section (content-derived)
- NOT `share/skills/h-excalidraw-diagram/SKILL.md` (no overlap)

This preserves the 90/80 no-op pattern for most tasks while ensuring doc-writer v2 actually catches relevant drift. Without this gating, the broadened scope is a net negative for user experience.

**Secondary mitigation:** doc-writer v2's Channel B output should clearly state which docs it checked and why (index-driven reasoning), so the user can verify the scope was appropriate. Transparency builds trust.

### Q6 — Consumer Experience Post-Brief

**Position: Three things must be true for consumers, and one has an architectural gap.**

What consumers pulling main see differently (good):
1. Fixed root docs — README, SECURITY, copilot-instructions — direct improvement.
2. Updated agent/skill/instruction/prompt files — direct improvement.
3. Excalidraw diagrams (if `.excalidraw` files are in synced paths) — direct improvement.

**Architectural gap: the index generator script.**

The generated index lives in `.owlbear/` (project-local, not synced). That's correct — each project has its own doc surface. But the script that generates the index must ship to main so consumers can regenerate it for their own tree. Currently `.owlbear/` content doesn't sync. The generator script needs to live in `setup/` or `serve/` — a synced directory.

**Consumer doc-writer boundary:** Doc-writer v2 in a consumer project must not edit OwlBear-shipped files. The index's "OwlBear-shipped paths are marked" (M2 outcome 1) is the mechanism — but doc-writer v2's scope rules must explicitly state: *"Edit only project-owned docs. OwlBear-shipped docs are read-only references."* If this boundary isn't explicit, a consumer's doc-writer will try to "fix" OwlBear's agent files and fail against the deny-code-writes hook, producing confusing error output.

**README rename:** `README-consumer.md` → `README.md` happens at sync. This is already handled by the sync workflow. No new UX concern — but the sweep must ensure both files are consistent in content before sync, since they diverge today.

## Key Trade-offs

| Decision | Trade-off | Recommendation |
|----------|-----------|----------------|
| Pre-scan summary in doc-audit | Adds one step before findings loop; delays first finding by ~30s | Worth it — prevents 2-hour surprise |
| Area grouping for sweep tasks | Less granular progress tracking per file | Worth it — board usability > file-level tracking |
| Markdown index format | Less structured than JSON for agent parsing | Worth it — human debuggability outweighs marginal parsing efficiency for 76 entries |
| Index-driven scope gating in doc-writer v2 | Adds index dependency to every docs phase | Essential — without it, broadened scope is a net UX negative |
| In-diagram verification footer | Adds maintenance obligation per diagram | Worth it — false confidence from undated diagrams is worse than the footer cost |

## Warnings

1. **Highest risk: doc-writer v2 without scope gating (Q5).** If the index-driven filtering isn't implemented before broadening doc-writer's scope, the per-task experience degrades. Ship gating and broadened scope together, not sequentially.

2. **Consumer boundary omission (Q6).** If doc-writer v2's scope rules don't explicitly exclude OwlBear-shipped paths in consumer projects, consumers will hit confusing errors on every task's docs phase. This must be in the agent definition, not assumed.

3. **Index generator script placement (Q6).** If the generator script lives in `.owlbear/`, consumers can't regenerate the index. It must ship in a synced path.

4. **doc-audit session length (Q1).** Even with the pre-scan summary and area opt-in, a full audit of all 76 files is a multi-hour session. The cadence guidance should set realistic expectations: "quarterly full audit, monthly spot-check of high-churn areas."

## Confidence

**0.85** — High confidence on the per-task UX risk (Q5) and consumer boundary gap (Q6) as genuine problems. Moderate uncertainty on whether the pre-scan summary (Q1) is implementable cheaply in a prompt-only context (no persistent state between invocations). The diagram footer recommendation (Q2) is straightforward but the specific format (date + commit hash) may need iteration based on Excalidraw's text element constraints.
