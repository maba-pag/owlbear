# Brief: Documentation Currency

**Brief ID:** `docs-currency-2026-04-19`
**Working dir:** `.owlbear/briefs/draft-docs-currency-2026-04-19/`
**Tier:** Deep
**Posture:** Quality over everything. No backwards compatibility. No legacy. Time unbounded.

## 1 · Problem

OwlBear's product documentation has accumulated drift across the repo. Confirmed worst offenders: `SECURITY.md` (entire file references a `src/owlbear/...` tree that no longer exists), both root READMEs (`README.md` claims a `v1/` directory that doesn't exist; `README-consumer.md` diverges from `README.md` on platform/CLI surface), `serve/knowledge/README.md` (stale install paths). 7 of 9 `serve/*` packages have no README at all. Project-level diagrams (kanban, memory layers, MCP topology, pipeline, ideation, Cockpit, project overview) do not exist as authoritative artifacts.

The drift is **not** because `doc-writer` does its job poorly. The landscape scan confirmed the diagnosis: **`doc-writer`'s declared scope is five paths** (`README.md`, `.github/copilot-instructions.md`, `.owlbear/research/*`, `.owlbear/sources/*`, Python docstrings). The agent does that job correctly. The job is too narrow. ~70 of the repo's product docs sit outside its scope and have no per-task gate.

Compounding factor: there is no periodic backstop. Whatever per-task `doc-writer` misses (or never sees, because it isn't in scope) accumulates indefinitely. As OwlBear has crossed a complexity threshold (Cockpit, MCP servers, ideation panel, ~24 agents, ~30 skills) and approaches downstream consumption by potentially hundreds of consumer projects, doc rot has flipped from tolerable to a quality blocker that compounds at the consumer boundary.

(Pleasant find from M3: zero Pydantic AI / v1 leakage in product docs; that material is properly quarantined in `.owlbear/research/`. Initial concern was overblown — but every other rot category is real.)

## 2 · Outcomes (Acceptance Criteria)

When this work is done, all of the following are observably true:

1. **Auto-generated doc index exists.** A Python script in `serve/tools/` (`uv run doc-index`) enumerates every doc-bearing markdown file (path-exclusions hardcoded in script: `.owlbear/scratch/`, `.owlbear/research/`, `.owlbear/kanban/`, etc.) and writes a strict-format markdown index at `.owlbear/doc-index.md`. Each entry: file path header + per-file TOC (section headings, backtick-wrapped) + outbound links sub-section. Auto-generated header marks the file as DO-NOT-EDIT. The index is **best-effort fresh, not always-fresh** — mechanically regenerated from filesystem state on every `doc-audit` invocation (hard requirement; audit fails on regen failure) and on `doc-writer` SessionStart (advisory; doc-writer continues with stale index on regen failure). The exclusion-list is fail-open: new working dirs may be auto-included as docs until added to the exclusions; mitigation is periodic `doc-audit` runs. Index is committed to git. In consuming projects, OwlBear-shipped paths are marked. **A temporary sweep working-doc** (cleanup checklist) lives during the sweep and dies after; issues found become kanban tasks immediately.
2. **All known-rotten docs remediated.** `SECURITY.md` rewritten to reflect actual codebase. Both READMEs corrected and reconciled. `serve/knowledge/README.md` install paths fixed. The 7 missing `serve/*/README.md` files authored. Placeholder `your-org` URLs replaced. Zero v1/Pydantic AI residue in product docs (already verified mostly clean).
3. **Seven owlbear-dev Excalidraw diagrams exist.** 1 project-overview + 6 named module diagrams: kanban, memory layers (global / local / VS Code built-in), MCP topology, pipeline (research → done), ideation panel, Cockpit. Each in `share/diagrams/`, git-tracked. Each diagram has a `describes` field in the doc-index (list of file path globs only — no abstract concepts) and an auto-maintained footer text element: `Last verified: YYYY-MM-DD (commit-hash)`. **Diagrams are descriptive, not authoritative** — authority lives with `architect` and AC. If a diagram disagrees with reality, the diagram is wrong, never the code.
4. **`doc-writer` v2 is defined and verified across behavioral modes.** Definition: scope (~25 descriptive doc files; agent-executable files OUT — see §3), triggers, deletion-task-creation capability, scribe-DR invocation, index consultation, diagram authorship rules — all written into `doc-writer.agent.md`. Verification: agent runs across **exactly 6 named test cases**, one per behavioral mode, each with a **stated expected outcome**:
   - **No-op:** task changes only test files; expected: `doc-writer` writes `## Docs Gate` with all checks N/A and advances to `done`.
   - **Prose update:** task changes a CLI command; expected: `doc-writer` updates `README.md` (or relevant in-scope doc) and commits.
   - **Diagram maintenance during code change:** task touches a file matching an existing diagram's `describes` glob; expected: `doc-writer` updates the matching diagram + footer (date + commit hash).
   - **Explicit diagram-creation task:** task body explicitly requests a new diagram; expected: `doc-writer` creates the .excalidraw + index entry + footer.
   - **Deletion proposal:** task removes a feature with a now-orphaned doc; expected: `doc-writer` creates a child kanban task + scribe-DR; current task advances without deleting.
   - **Ambiguous (misclassification check):** task touches an agent-executable file (OUT of scope); expected: `doc-writer` correctly identifies the file as OUT, no edit, no false-positive remediation.

   Verification log records (per case): task-id, mode, observed behavior, expected outcome, pass/fail, notes. Pass criteria: 6/6 expected outcomes met. Log is permanent (committed to repo as `serve/tools/tests/doc_writer_v2_verification.md` or similar planner-decided path).
5. **`doc-audit.prompt.md` exists and works.** Mirrors `agent-audit.prompt.md` structurally (Scan → severity queue → one-finding-at-a-time loop with `askQuestions` → fix → rescan → verification). Loads `r-doc-standards` first. **Pre-scan summary** before the findings loop shows finding counts per area so the user knows the time commitment. Hard cap of 3 re-scan cycles per file (Security). User invokes; gets drift report; remediation tasks land on the kanban board.
6. **Consumer can use OwlBear correctly from the docs** — validated **opportunistically in the field** (user runs owlbear-main from a separate project on another machine, feeds gaps back as kanban tasks). Not an exit-gate for this Brief.
7. **Two-layer doc-currency safety net is in place.** **Layer 1 (per-task):** No task reaches `done` without `doc-writer` v2 having explicitly run on it (no-op or update). The pipeline gate already exists; this Brief tightens what `doc-writer` does within that gate. **Layer 2 (periodic):** `doc-audit.prompt.md` runs on user invocation, surfaces drift across the whole repo, emits remediation tasks. Catches everything Layer 1 misses (bypassed phases, slow drift, evolving doc needs).

## 3 · Scope: What `doc-writer` v2 owns

`doc-writer`'s **edit + propose-deletion scope** is **descriptive documentation only**. Agent-executable behavioral content (agents, rules/workflow skills, instructions, prompts) is **out of scope** — those are owned by `architect` / `agent-audit` and edited by their respective authors.

**IN scope (~25 files):**

- 3 root: `README.md`, `README-consumer.md`, `SECURITY.md`
- 9 `serve/*/README.md`: existing 2 (cockpit, knowledge) + 7 missing (orchestrator, kanban, browser, mcp-kanban, mcp-knowledge, mcp-memory, mcp-browser)
- 2 `setup/*.md`: setup-guide, sharing-guide
- 4 share-category READMEs: `share/agents/README.md`, `share/skills/README.md`, `share/instructions/README.md`, `share/prompts/README.md`
- 7 diagrams: `share/diagrams/*.excalidraw`

**OUT of scope (agent-executable):**

- `share/agents/*.agent.md` (24)
- `share/skills/*/SKILL.md` (30) — including `h-` handbooks (defaulted OUT; planner may revisit)
- `share/instructions/*.instructions.md` (6)
- `share/prompts/*.prompt.md` (7)
- `share/skills/*/references/*.md`
- `.github/copilot-instructions.md`

The doc-index lists ALL doc-bearing files (so `doc-audit` scans everything and `doc-writer` is aware of out-of-scope files for prose-reference reasons). But `doc-writer`'s **edit + delete-proposal** scope is the IN list above.

**Routing rule for `doc-audit` findings:**

- Findings on **IN-scope files** → remediation tasks default to `doc-writer` (or appropriate phase-2 task during sweep).
- Findings on **OUT-of-scope files** (non-orphan drift in agents/skills/instructions/prompts — e.g., a skill description that contradicts current behavior) → remediation tasks route to **`architect`** (or the agent/skill's original author). `doc-audit` flags the drift; it does not have authority to fix it directly.
- **Orphaned OUT-of-scope files** (a skill that describes a workflow no longer in use) → `agent-audit.prompt.md` is the proper detector; if `doc-audit` finds one incidentally, it routes to `architect` for ecosystem-level decision.

This ensures `doc-audit` can scan the full surface honestly without dragging out-of-scope work into `doc-writer`'s lap.

## 4 · Approach

### 4.1 · Per-task layer: `doc-writer` v2

- **Scope:** the IN list in §3, mediated by the doc-index.
- **Per-task relevance gating:** `doc-writer` doesn't check all ~25 docs every task. It uses the index + the task's changed-files set to identify which docs *could* be affected. 90% of tasks should still be no-op; the broader scope serves the 10% that legitimately touch docs.
- **Diagram authorship:** doc-writer can author/maintain Excalidraw diagrams under exactly two trigger conditions: (a) a task explicitly asks for diagram creation/update (architect or planner decides; builder never authors diagrams), or (b) the agent must update an existing diagram because relevant code changed (detected via `describes` glob + git log). The agent never autonomously decides "this needs a diagram."
- **Deletion proposal workflow:** doc-writer detects a deletion candidate → creates a child kanban task ("delete X") via the `owlbear-kanban` MCP (NEW tool capability for v2) → invokes `scribe` to write a DR file in `.owlbear/decisions/pending/` (file path + content preview + inbound-link list + reasoning) → child task is `blocked` on DR resolution → user resolves → block lifts → task flows through pipeline: **test-writer authors inbound-link tests** (verifying that deleted file's references are repaired/removed) → **builder removes file AND repairs/removes inbound links in a single atomic commit** (transactional) → reviewer → doc-writer updates index.
- **Index updates:** when doc-writer edits any file, it triggers index regeneration (or relies on next SessionStart). Index lifecycle: regenerated on doc-writer SessionStart, on doc-audit invocation, on demand via `uv run doc-index`. Regen failure → doc-writer logs and continues using stale index as advisory; doc-audit fails hard.

### 4.2 · Periodic layer: `doc-audit.prompt.md`

User-invocable interactive `.prompt.md`. Mirrors `agent-audit.prompt.md` structurally — same Scan → severity queue → Finding-loop → Verify shape, same `askQuestions` checkpoints, same one-finding-at-a-time discipline.

**Adaptations for docs:**

- Loads `r-doc-standards` (NEW skill — see §4.4) as the citable rule source.
- Audit dimensions adapted from agent-audit's D1–D7: e.g., D1 Structural (required sections per doc type), D2 Duplication, D3 Placement, D4 Accuracy (claims-vs-implementation, code-path references resolve), D5 Coverage Integrity (every shipped package has a README; every CLI command documented; every link resolves), D6 Currency/Staleness, D7 Cross-reference Integrity. Final dimension list belongs to planner + the `r-doc-standards` author.
- **Pre-scan summary** before the findings loop: "Found N total findings across these areas — [breakdown]. Estimated time at ~2min per finding: ~X minutes. Continue / select areas / stop." Closes the time-commitment-uncertainty problem End-User raised.
- **Hard cap of 3 re-scan cycles per file** to prevent infinite loops (Security).
- Emits remediation kanban tasks on user approval; does not modify files autonomously without per-finding approval.

### 4.3 · Doc-index artifact

- **Location:** `.owlbear/doc-index.md`
- **Generator:** `serve/tools/` package, exposed as `uv run doc-index` (first entry point in a new utility-tools package — future scripts land there too).
- **Format:** strict-grammar markdown (see §4.5).
- **Generation strategy:** filesystem walk with hardcoded exclusion list in the script (fail-open accepted; doc-audit catches false-includes; safety window documented). Scope can be revisited if rot accumulates via this vector.
- **Lifecycle:** committed to git; regenerated on doc-writer SessionStart, doc-audit invocation, and on demand.
- **In consumer projects:** OwlBear-shipped paths are marked; consumer regenerates against their own tree post-clone.

### 4.4 · `r-doc-standards` skill (NEW)

A new `r-` (rules) prefixed skill, citable by `doc-audit` for every finding. Specifies: required sections per doc type (README structure, SECURITY structure, package README structure, share-category README structure), placement rules (what belongs where), cross-reference rules (link integrity), audience-fitness rules. Is **non-negotiable** — without it, `doc-audit` findings are subjective opinions. No `h-doc-structure` handbook (over-engineering at this stage).

### 4.5 · Index markdown grammar (locked)

- File headers use literal file path: `## share/agents/README.md`. Paths can't collide.
- Per-file headings as bullets with text wrapped in backticks: `` - ## `Setup & Installation` ``.
- Outbound links per file in a sub-section `### Outbound links` with `[text](target)` pairs (auto-extracted; code blocks excluded).
- File starts with: `<!-- AUTO-GENERATED by serve/tools/doc-index. DO NOT EDIT. Regenerated on demand. -->`
- Parser implemented in `serve/tools/` alongside the generator.

### 4.6 · `describes` schema for diagrams (locked)

A list of file path globs only. No abstract concepts, no module names, no English. Drift detection is mechanical: `git log` against any matching path since the diagram's footer date → flag drift.

### 4.7 · Hook refactor: `deny-code-writes.py`

Refactor from OwlBear-specific directory deny-list to **extension-based allowlist**. **Two variants:**

- **Strict consumer-seed variant:** `.md` + `.excalidraw` only. No Python writes, no other extensions. Ships in `seed/` for new consumer workspaces.
- **Owlbear-dev variant:** broader — allows docstring edits in `.py` (since `doc-writer` here also maintains module docstrings).

This is a **blocking prerequisite** for `doc-writer` v2: the current hook gives zero protection to consumer source code in `src/`, `lib/`, `app/`. With v2's broader scope, that risk amplifies.

## 5 · Constraints & Non-negotiables

- **No backwards compatibility, no legacy.** Break to improve.
- **Quality over speed.** Time is unbounded.
- **Generic vs owlbear-dev separation:** `doc-writer` v2 is a generic agent shipped to consumers. The 7 named diagrams are owlbear-dev-specific deliverables. Keep the line clean.
- **Authority lives with `architect`/AC**, not with `doc-writer`. Diagrams are descriptive, never authoritative.
- **`doc-writer` never autonomously creates diagrams** (only on explicit task or maintaining existing on code change).
- **`doc-writer` never deletes autonomously** — always proposes via child task + scribe DR.
- **Index must be auto-generated**, never hand-maintained.
- **Agent-executable files (agents, skills, instructions, prompts, copilot-instructions) are OUT of `doc-writer`'s edit/delete scope.** Orphaned agent files route through `agent-audit` + `architect`.

## 6 · Phasing

Suggested decomposition seams; planner applies its own `w-task-decomposition` rules for actual breakdown.

### Phase dependency graph (explicit)

```
Phase 0 (prerequisite tooling)
  ├─ r-doc-standards skill          ───────┐
  ├─ serve/tools/ + doc-index       ───────┤
  ├─ deny-code-writes.py refactor   ───────┤
  └─ doc-audit.prompt.md skeleton   ◄───depends on r-doc-standards
                                          │
Phase 1 (agent redesign)                   ▼
  └─ doc-writer v2  ◄──── depends on ALL of Phase 0
     (broadened scope + relevance gating SHIP TOGETHER — never sequentially)
                  │
Phase 2 (sweep + diagrams)                 ▼
  ├─ area sweep tasks       ◄── depends on doc-writer v2 (to actually do work)
  ├─ 7 diagram tasks        ◄── depends on doc-writer v2 (diagram authorship)
  └─ doc-audit gate run     ◄── depends on all sweep + diagram tasks complete
```

### Phase 0 — prerequisite tooling
  - `r-doc-standards` skill (must come first — `doc-audit` skeleton needs citable rules)
  - `serve/tools/` package + `doc-index` script + markdown index format
  - `deny-code-writes.py` refactor (two variants: `.owlbear/hooks/deny-code-writes.py` for owlbear-dev with broader allowlist; `seed/.owlbear/hooks/deny-code-writes.py` for consumer-seed with strict `.md`+`.excalidraw` only)
  - `doc-audit.prompt.md` skeleton mirroring `agent-audit` with pre-scan summary (depends on `r-doc-standards`)
  - **Within-Phase parallelizable** EXCEPT `doc-audit.prompt.md` waits for `r-doc-standards`.

### Phase 1 — agent redesign
  - `doc-writer` v2: index-derived scope + per-task relevance gating + diagram authorship + new task-creation tool capability + deletion-task workflow via scribe-managed DRs
  - **Hard rule (locked decision):** Broadened scope and relevance gating ship in the SAME task or task pair, never sequentially. Without gating, broader scope is a net UX loss (cry-wolf failure mode).
  - Verification log across 6 named behavioral modes (see Outcome 4)
  - **Depends on:** all of Phase 0 complete.

### Phase 2 — sweep + diagrams (folded; previous separation created an ordering trap)
  - Decomposed remediation tasks per area (root / serve / share-category READMEs / diagrams), then per-file as size warrants. Granularity per planner's `w-task-decomposition` rules.
  - Each rotten doc fixed, consolidated, or deletion-task-proposed (deletion tasks follow the workflow in §4.1).
  - Includes the 7 owlbear-dev Excalidraw diagrams (1 overview + 6 named modules) with `describes` metadata + footer.
  - Single `doc-audit` run as the sweep's acceptance gate at the end.
  - **Depends on:** Phase 1 complete (doc-writer v2 must exist to do the work; doc-audit must exist to gate).

## 7 · Validation Posture

No formal cold-clone or end-to-end consumer test. User self-validates via real downstream use (running owlbear-main from another project on another machine); broken docs become bug-tasks, not blockers for this Brief.

## 7a · Risks the planner should know about

- **Board-volume during sweep.** Decomposed sweep tasks (one per area, possibly per-file within) PLUS deletion child tasks (one per proposed deletion + one DR per task) can produce many concurrent kanban entries. Expected order: tens, possibly low-hundreds. Mitigation: tag tasks consistently (`docs-sweep`, `docs-deletion`, `phase-2`) so the Cockpit can filter; consider `priority: someday` for non-critical deletion proposals to keep the active queue clean.
- **Time-in-docs-status per task increases.** Even with relevance-gating preserving the 90/80 no-op rate, broadening scope means the 10% non-no-op tasks now have more potential touchpoints. Per-task latency in `docs` phase will increase. Acceptable per posture ("quality over speed"), but visible.
- **Committed-index churn = review noise.** The doc-index is committed and regenerated on `doc-writer` SessionStart and every `doc-audit` invocation. Code-only PRs may show index diffs. Mitigation options (planner's call): (a) commit index only when a doc actually changed (skip identical regens), (b) auto-commit index changes via a separate "docs:" commit by doc-writer, (c) accept the noise as a feature (visible scope changes).
- **Hook refactor blast radius.** Flipping from directory deny-list to extension allowlist may surface tasks that previously slipped through (e.g., a task that incidentally tried to write to `.json` config files). Expected to be small but worth a watch during Phase 0 rollout.

## 8 · Open items deferred to planner

- Final list of `doc-audit` audit dimensions (initial draft in §4.2; concrete shape belongs to the `r-doc-standards` author + planner).
- Exact granularity of Phase 2 tasks (planner's `w-task-decomposition` call).
- Boundary cases for doc-writer scope: handbook skills (`h-*`), skill reference files. Defaulted OUT; planner may revisit if scope holes emerge.
- Whether the doc-index should also enumerate inbound links (currently only outbound, with inbound computed by reversal at audit time).
- Whether the index regeneration on `doc-writer` SessionStart can be conditional (skip if recent enough) — performance optimization, not blocker.

## 9 · Process feedback queued for after Brief

Mediator dumped 6 outcome-sharpenings in a table without per-item context, then asked "accept all 6?". Future protocol: walk through one item (or a tightly-coupled small cluster) per turn, with the original text quoted, the Critic's actual concern in plain language, and the proposed change visible. Never bulk-ratify analysis the user hasn't actually seen.

## 10 · Linkages

- **Replaces or substantially revises:**
  - `share/agents/doc-writer.agent.md`
  - `share/skills/w-doc-update/SKILL.md`
  - `.owlbear/hooks/deny-code-writes.py` (live owlbear-dev variant — broader allowlist)
  - `seed/.owlbear/hooks/deny-code-writes.py` (consumer-seed variant — strict `.md`+`.excalidraw` only)
  - `setup/init.py` may need a small update if hook copy logic changes
- **Creates:**
  - `share/skills/r-doc-standards/SKILL.md`
  - `share/prompts/doc-audit.prompt.md`
  - `serve/tools/` package (with `pyproject.toml`, `src/`, `tests/`); first entry point `doc-index`
  - `share/diagrams/` directory + 7 `.excalidraw` files (1 overview + 6 module diagrams)
  - `.owlbear/doc-index.md` (auto-generated; committed)
  - Verification log file (location: planner-decided, e.g., `serve/tools/tests/doc_writer_v2_verification.md`)
  - Temporary **sweep working-doc** (cleanup checklist; ephemeral — deleted at sweep end). Suggested location during sweep: `.owlbear/scratch/docs-sweep-checklist.md`.
- **Sweeps:** all files listed in §3 IN scope (~25)
- **Reference (do NOT modify; mirror or cite only):**
  - `share/prompts/agent-audit.prompt.md` (mirror template for `doc-audit`)
  - `share/skills/h-agent-structure/SKILL.md` (structural conventions)
  - `share/skills/h-excalidraw-diagram/SKILL.md` (diagram authoring)
