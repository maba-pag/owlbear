# Decisions — Documentation Currency Brief

**Brief:** draft-docs-currency-2026-04-19
**Date:** 2026-04-19
**Tier:** Deep

## Locked unanimously (panel convergence — no decision needed)

1. Root cause = scope, not execution.
2. Auto-generated doc-index is the central artifact, consumed by `doc-writer` v2 + `doc-audit`.
3. Two-layer safety net: per-task (`doc-writer`) + periodic (`doc-audit`).
4. `doc-audit.prompt.md` mirrors `agent-audit.prompt.md` structurally.
5. `r-doc-standards` skill must exist (citable rules, `r-` not `h-`).
6. User-gated deletion. `doc-writer` never deletes autonomously.
7. Diagrams live in `share/diagrams/`, git-tracked.
8. Sweep is decomposed into normal pipeline tasks (no special workflow).
9. **`doc-writer` v2 keeps the 90/80 no-op rate via per-task relevance gating against the index. Ship gating and broadened scope together — never sequentially.**
10. Pre-scan summary added to `doc-audit` so user knows the time commitment per area before the loop starts.

## Open-question decisions (M4 facilitation)

### OQ1 — Index enumeration

**Decision: exclusion-list hardcoded in the script** (Architect's position).

User accepted the fail-open posture, against Mediator's recommendation of allowlist-with-config. Trade-off: simpler script, requires diligence to add new working dirs to exclusions; `doc-audit` is the safety net for false-includes. Allowlist option remains available as a future change if rot reappears via this vector.

### OQ2 — Index format

**Decision: markdown with strict machine-generated format** (End-User's position; Mediator revised after user pointed out Security's injection argument was misapplied — format does not affect downstream shell-injection risk, which is a code-level bug).

The index has a simple shape (file path + per-file TOC + outbound links). Markdown is parseable via predictable structure (`## <path>`, `- ## <heading>`), gives free VS Code outline view, readable git diffs, and is meta-aligned with the docs corpus it indexes.

### OQ3 — Diagram metadata

**Decision: both — `describes` field in index + auto-maintained `Last verified YYYY-MM-DD (commit-hash)` footer in each diagram.**

Cost is small (1 line per diagram in index + 1 text element). They serve different purposes (mechanical drift detection vs reader trust signal) and are not redundant. The footer is auto-maintained by `doc-writer` whenever it touches a diagram (zero hand maintenance). The `describes` field is set-once-mostly (rarely shifts).

### OQ4 — Index script location

**Decision: `serve/tools/` package, with `doc-index` as the first entry point.**

User rejected single-purpose `serve/docindex/` (overkill) and `.owlbear/scripts/` (doesn't sync to consumers, contradicts outcome 1). User also rejected `setup/` (script is ongoing tool, not setup-time). Final shape: a real `serve/tools/` Python package, follows the `serve/*` pattern, exposes `uv run doc-index`. Future utility scripts land here as new entry points (audit helpers, sweep helpers, migration scripts).

### OQ5 — Deletion mechanism

**Decision: deletion task + external scribe-managed DR (auto-blocked).**

User correctly spotted that the panel's task-vs-DR framing was a false dichotomy. Both serve different purposes: task = work container (pipeline gates, atomic commit, board visibility); DR = approval gate (decision audit trail, user-acceptance integrity). M4 Critic correctly noted that DRs in OwlBear are **external scribe-managed files** in `.owlbear/decisions/pending/`, not inline task payloads — "embedded DR" was Mediator shorthand.

**Concrete plumbing (resolved during M4 sharpening):**

1. `doc-writer` v2 detects a deletion candidate (only within its scope — see scope decision below; agent-executable files are out of scope for deletion proposals entirely).
2. `doc-writer` creates a child kanban task ("delete X") via the `owlbear-kanban` MCP — **a new tool capability `doc-writer` v2 must gain**. The child task is `blocked` with `block_reason: "awaiting deletion DR"`.
3. `doc-writer` invokes `scribe` (already an allowed sub-agent) to write a DR file in `.owlbear/decisions/pending/`. DR contents: file path, content preview, inbound-link list, reasoning.
4. User resolves DR (approve / redirect / reject) → DR file moves to `resolved/` → block lifts on the deletion task.
5. Task flows through normal pipeline: test-writer ensures inbound-link tests; **builder removes file AND repairs/removes inbound links in a single atomic commit** (transactional — Data); reviewer; `doc-writer` updates index.

Original Security recommendation for elevated-authority on agent-executable files is **dropped as obsolete** — those files are now entirely out of `doc-writer`'s deletion-proposal scope (see scope decision). Orphaned agent-executable files are detected by `agent-audit.prompt.md` and routed through `architect`, not `doc-writer`.

### OQ6 — Hook refactor

**Decision: blocking prerequisite — fix the hook before `doc-writer` v2 ships** (Security's position).

`deny-code-writes.py` currently uses an OwlBear-specific directory deny-list, giving zero protection to consumer source code (`src/`, `lib/`, `app/`). Refactor to extension-allowlist: `.md` + `.excalidraw` only for the seeded consumer variant; broader (allowing docstring edits in `.py`) for owlbear-dev. Two hook files. Phase 0 alongside `r-doc-standards` and `serve/tools/` skeleton.

## Phasing (locked, post-M4-Critic)

- **Phase 0 (prerequisite tooling):** `r-doc-standards` skill (must come first — doc-audit needs citable rules) • `serve/tools/` package + `doc-index` script + markdown index format • `deny-code-writes.py` refactor (two variants — strict consumer-seed and broader owlbear-dev) • `doc-audit.prompt.md` skeleton mirroring `agent-audit` with pre-scan summary (depends on `r-doc-standards` existing first).
- **Phase 1 (agent redesign):** `doc-writer` v2 with index-derived scope + per-task relevance gating + diagram authorship capability + new kanban task-creation tool capability + deletion-task workflow via scribe-managed DRs. Verification log across 6 behavioral modes.
- **Phase 2 (sweep + diagrams):** Decomposed remediation tasks per area (granularity per planner's normal task-decomposition rules, not pre-fixed at ~8–10). Each rotten doc fixed, consolidated, or deletion-task-proposed. **Includes the 7 owlbear-dev Excalidraw diagrams** (1 overview + 6 named modules), each with `describes` metadata in the index and auto-maintained footer. **Single `doc-audit` run as the sweep's acceptance gate at the end.** (Phase 2 and original Phase 3 folded; previous separation created an ordering trap because doc-audit would otherwise fail on missing diagrams.)

## Scope contraction (post-M4 user clarification)

`doc-writer`'s **edit + propose-deletion scope** is **descriptive documentation only**, NOT agent-executable behavioral content. Approximately **25 files in scope:**

- 3 root: `README.md`, `README-consumer.md`, `SECURITY.md`
- 9 `serve/*/README.md`: existing 2 (cockpit, knowledge) + 7 missing-but-needed (orchestrator, kanban, browser, mcp-kanban, mcp-knowledge, mcp-memory, mcp-browser)
- 2 `setup/*.md`: setup-guide, sharing-guide
- 4 share-category READMEs: `share/agents/README.md`, `share/skills/README.md`, `share/instructions/README.md`, `share/prompts/README.md` (docs *about* the agent ecosystem categories, not the executables themselves)
- 7 diagrams: `share/diagrams/*.excalidraw`

**OUT of doc-writer scope (agent-executable, owned by architect / agent-audit):**

- `share/agents/*.agent.md` (24 agent definitions)
- `share/skills/*/SKILL.md` (30 skills) — includes `r-` rules, `w-` workflows, **and `h-` handbooks** (defaulted OUT; planner may revisit)
- `share/instructions/*.instructions.md` (6 instruction stubs)
- `share/prompts/*.prompt.md` (7 prompts)
- `share/skills/*/references/*.md` (handbook reference content)
- **`.github/copilot-instructions.md`** (master instruction file for Copilot — behavioral, not descriptive)

The **doc-index still lists all doc-bearing files** (so `doc-audit` can scan the full surface and `doc-writer` can know agent-files exist for prose-reference purposes — e.g., when an agent gains a new behavior, the related share-category README may need a one-line update). But `doc-writer`'s **edit + delete-proposal** scope is the smaller set above.

## Process feedback queued (for after Brief)

- Mediator dumped 6 outcome-sharpenings in a table without per-item context, then asked "accept all 6?". Future: walk through one item (or tightly-coupled small cluster) per turn with the original text quoted, the Critic's actual concern in plain language, and the proposed change visible. Never bulk-ratify analysis the user hasn't actually seen.

## M4 Critic sharpenings (post-decision Critic pass)

### Markdown index grammar (Cluster A)

**Decision: lock the grammar.**

- File headers in the index use the literal file path: `## share/agents/README.md`. Paths can't collide; duplicates impossible at the file-header level.
- Per-file section headings are listed as bullets with heading text **wrapped in backticks** to neutralize markdown special chars: `` - ## `Setup & Installation` ``. Backticks-in-headings (rare) escaped via standard markdown.
- Outbound links per file go in their own sub-section: `### Outbound links`, bulleted list of `[text](target)` pairs as raw markdown (auto-extracted; code blocks excluded per Data's rule).
- Index file starts with: `<!-- AUTO-GENERATED by serve/tools/doc-index. DO NOT EDIT. Regenerated on demand. -->`
- Parser is implemented in `serve/tools/` alongside the generator (single source of truth for read+write).

### `describes` schema (Cluster A)

**Decision: globs only, no abstract concepts.**

- `describes` is **a list of file path globs** — nothing else. Examples: `serve/cockpit/**/*.py`, `share/agents/architect.agent.md`.
- No abstract concepts, no module names, no English descriptions.
- Drift detection is mechanical: `git log` shows commits affecting any matching path since the diagram's last footer date → flag drift.
- For consumer projects: same schema, just consumer paths. Generic.

### Exclusion-list safety window (Cluster B)

**Decision: accept the window, document it.**

User chose simplicity over the safety-check complexity. The Brief and `doc-writer` v2 docs must explicitly document: between exclusion-list updates, a window exists where new working dirs may be auto-included as docs. Mitigation is "run `doc-audit` periodically" + "add new working dirs to the exclusion list when creating them." No code change in `doc-writer`.

### Sweep granularity guidance (Cluster B)

**Decision: light hint to planner.**

The Brief includes a one-line decomposition seam suggestion: *"Suggested decomposition seams: by area (root / serve / share-category READMEs / diagrams), then per-file within each area where size warrants."* Planner applies its own `w-task-decomposition` rules (single-responsibility, ~2hr tasks) for actual breakdown.

### Doc-index lifecycle (Mediator-set defaults; planner may revisit)

- **Committed to git.** Consumers cloning owlbear-main get a baseline index for OwlBear-shipped paths; consumer-side regen extends it against their tree. Index changes appear in git diffs (signal value during review).
- **Regenerated:** on `doc-writer` SessionStart (the agent already has a SessionStart hook); on `doc-audit` invocation (always-fresh for the audit); on demand via `uv run doc-index`.
- **Regen failure behavior:** `doc-writer` logs and continues using the stale index as advisory (not blocking). `doc-audit` fails hard on regen failure (it cannot audit against a missing/broken index).
