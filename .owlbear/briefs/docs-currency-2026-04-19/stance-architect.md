# Architectural Stance — Documentation Currency

**Panelist:** Architect
**Brief:** draft-docs-currency-2026-04-19
**Critic cycles:** 5 (see stance-architect-debate.md)
**Confidence:** 0.88

---

## Position Summary

The documentation currency problem is a **scope-definition failure**, not an execution failure. doc-writer does its declared job; its job just excludes 70 of 76 product docs. The fix is structural: an auto-generated doc-index as single source of truth for scope, a rules skill (`r-doc-standards`) as single source of truth for correctness criteria, and a two-layer safety net (per-task doc-writer v2 + periodic doc-audit prompt).

---

## Q1 — doc-writer v2 Scope Declaration

**Position: Index-derived scope with hard exclusions.**

doc-writer's `<boundaries>` section replaces the current 5-path allowlist with: "scope = every file in the doc-index, plus any doc the current task implies should exist but doesn't." The agent file lists hard exclusions only (`.owlbear/` working files — research, decisions, kanban, briefs, scratch).

Why not pattern-allowlist: globs (`share/agents/*.agent.md`, `serve/*/README.md`) are brittle — new doc types require agent-file edits. Why not opt-out blocklist: "everything minus exclusions" is too broad — it would include `.owlbear/research/`, kanban task files, etc. Why not static enumeration: 76 paths in the agent file is unmaintainable.

**The index closes the feedback loop.** When a new doc is created, the index regenerates and doc-writer's scope automatically expands. When a doc is deleted, it disappears from the index and from scope. No human maintenance of scope boundaries.

**Pipeline impact:** Broader scope does NOT mean longer task close. The 90/80 no-op rate holds because doc-writer evaluates *relevance to the current task*, not the entire surface. The `w-doc-update` checklist expands from 5 items to index-aware evaluation, but the assessment heuristic remains: "did this task change something that affects doc X?" Most docs are irrelevant to most tasks.

**New failure mode to gate:** doc-writer could mis-assess relevance (miss a doc that should be updated, or waste time on an irrelevant doc). The doc-audit prompt is the backstop — it catches whatever per-task assessment misses.

---

## Q2 — doc-index Script Architecture

**Position: `.owlbear/scripts/doc-index.py` → `.owlbear/doc-index.yaml`**

### Location

`.owlbear/scripts/doc-index.py`. This is project-ops tooling — it serves the pipeline, not consumers. It belongs alongside existing `.owlbear/hooks/` scripts, not in a `serve/*` package (over-engineering for a single-purpose enumerator) or `scripts/` root (legacy location).

Test in `tests/test_doc_index.py` — the script is permanent infrastructure and must be testable.

### When it runs

**On-demand only.** Two invocation points:

1. **doc-writer session start** — the existing `SessionStart` hook pattern (see `session-context.py` in hooks). doc-writer's hook chain regenerates the index before each session. Cheap operation (filesystem walk + heading extraction).
2. **doc-audit prompt invocation** — the prompt's preamble invokes the script before scanning.

NOT a commit hook. Commit hooks should be fast and side-effect-free. An index that regenerates on every commit adds latency and creates noisy diffs if the index is tracked. The index is ephemeral — regenerated when needed, never hand-edited, never committed.

### Format

**YAML.** Rationale:

- Machine-parseable (doc-writer, doc-audit consume programmatically).
- Human-readable for debugging (unlike JSON's brace noise).
- Supports per-file structured metadata (path, headings list, category tag) without requiring a parser more complex than PyYAML.
- Markdown would require regex parsing to extract structured data — wrong tool.

### Schema (indicative)

```yaml
generated: "2026-04-19T10:00:00Z"
docs:
  - path: "README.md"
    category: "root"
    headings: ["Installation", "Quick Start", "Architecture"]
  - path: "share/agents/builder.agent.md"
    category: "agent"
    headings: ["persona", "critical_rules", "output_format"]
  # ...
```

Categories: `root`, `agent`, `skill`, `instruction`, `prompt`, `setup`, `serve-readme`, `config` (for `.github/copilot-instructions.md`). Category enables doc-audit to apply dimension-appropriate checks.

### Exclusions (hardcoded in script)

Directories excluded from enumeration: `.owlbear/research/`, `.owlbear/decisions/`, `.owlbear/briefs/`, `.owlbear/kanban/`, `.owlbear/scratch/`, `.owlbear/sources/`, `store/`, `tests/`, `node_modules/`, any `dist/` or `build/`.

---

## Q3 — doc-audit.prompt.md Structure

**Position: Mirror agent-audit structure; create `r-doc-standards` skill; no `h-doc-structure` handbook.**

### Mirror fidelity

doc-audit mirrors agent-audit's process architecture exactly:

- Standards-loading preamble (load rules before scanning)
- Two-surface scan (prose docs + diagrams)
- Severity-sorted queue presented to user before findings loop
- One-finding-at-a-time with askQuestions checkpoints
- Finding cards with evidence, options, confidence
- Pause/bail at any point

The structural template works. What changes is the standards loaded and the audit dimensions.

### `r-doc-standards` — YES, create it

**This is non-negotiable.** agent-audit's power comes from citable rules — every finding traces to `h-agent-structure § X` or `r-pipeline-protocol § Y`. Without citable rules, doc-audit findings are subjective opinions. `r-doc-standards` codifies:

- Required sections per doc category (serve README must have: Purpose, Installation, Configuration, API/Usage)
- File-reference validation rule (every path/URL in a doc must resolve)
- Version-residue prohibition (no references to deprecated tech, removed directories, dead URLs)
- Audience markers (dev-only docs marked; synced docs must be consumer-safe)
- Cross-reference integrity (if doc A links to doc B, doc B must link-back or the reference is validated)
- Diagram linkage rule (if a diagram exists for a module, the module's README must link it)

This is a `r-` (rules) skill, not `h-` (handbook) — it contains SHALL/MUST constraints, not how-to procedures.

### `h-doc-structure` — NO, don't create it

A handbook for "how to structure a doc" is over-engineering. Agents know how to write markdown. The rules skill tells them what's required; the existing `h-excalidraw-diagram` tells them how to make diagrams. No third skill needed.

### Audit dimensions (doc-audit analogues of D1–D7)

| Dimension | Name | What it checks |
|-----------|------|---------------|
| D1 | Currency | Doc content matches current code reality (APIs, paths, configs) |
| D2 | Completeness | Required sections present per `r-doc-standards` category rules |
| D3 | Accuracy | Factual claims verified against implementation |
| D4 | Orphan Detection | Docs reference nonexistent files, directories, commands, or concepts |
| D5 | Audience Fitness | Dev-only content not leaking into consumer-synced docs; consumer docs self-sufficient |
| D6 | Cross-reference Integrity | Internal links resolve; external URLs are plausible (not `your-org` placeholders) |
| D7 | Diagram Currency | Diagrams match code; diagrams linked from relevant prose docs |

---

## Q4 — Diagram Authorship Workflow

**Position: `share/diagrams/` for all 7 project diagrams. Versioned in git. Filename is the metadata.**

### Location

`share/diagrams/` — a new directory in the synced surface. All 7 owlbear-dev diagrams live here:

```
share/diagrams/
  project-overview.excalidraw
  pipeline.excalidraw
  kanban.excalidraw
  memory-layers.excalidraw
  mcp-topology.excalidraw
  ideation-panel.excalidraw
  cockpit.excalidraw
```

Why `share/diagrams/` and not co-located with each module:

1. **Sync guarantee.** `share/` syncs to main. Diagrams are product artifacts for consumers.
2. **Single discovery point.** doc-writer and doc-audit enumerate one directory, not hunt across 6+ packages.
3. **Cross-cutting diagrams exist.** `project-overview.excalidraw` and `mcp-topology.excalidraw` don't belong to any single module — they span the system.

Why not `.owlbear/diagrams/`: `.owlbear/` is excluded from main-branch sync. These diagrams are product artifacts consumed downstream.

### Versioning

**Git-tracked.** Excalidraw JSON is text — diffs are readable (element adds/removes/moves). Diagrams change infrequently; commit noise is minimal.

### Linking from prose docs

Each module's README (or relevant doc) includes a relative link: `![Pipeline](../../share/diagrams/pipeline.excalidraw)`. The `r-doc-standards` skill codifies: "if a diagram exists for your area, your README MUST link it."

### How doc-writer knows the mapping

**Filename convention is the mapping.** `kanban.excalidraw` maps to `serve/kanban/`. `cockpit.excalidraw` maps to `serve/cockpit/`. No per-diagram metadata file — the filename IS the identifier, and the doc-index includes diagram entries alongside prose docs (category: `diagram`).

The doc-index enumerates `share/diagrams/*.excalidraw` with the same schema as prose docs (path + category). doc-writer matches diagram filenames to the code area affected by the current task.

### Trigger discipline (restating M2 for clarity)

doc-writer updates diagrams under exactly two conditions:
1. Explicit task requests diagram creation/update (architect/planner authority)
2. Code change affects an area with an existing diagram (doc-writer's per-task assessment)

doc-writer NEVER autonomously decides "this needs a new diagram." Diagram creation authority lives with architect and planner.

---

## Q5 — Deletion Proposal Workflow

**Position: Route through existing DR (decision-request) mechanism via scribe. No new machinery.**

### Per-task flow

```
doc-writer identifies orphaned/superseded doc
  → invokes scribe
    → scribe creates DR in .owlbear/decisions/pending/{task-id}-delete-{slug}.md
      DR body: file path, deletion rationale, evidence (what replaced it / why it's dead)
  → doc-writer notes the pending DR in its Channel B output
  → task advances normally (the deletion is a separate concern)
```

User resolves the DR:
- **Approved:** DR resolution creates a deletion task (or user deletes directly)
- **Redirected:** User decides the doc should be updated, not deleted → remediation task instead
- **Rejected:** Doc is intentionally kept; no action

### Why DRs, not a custom deletion mechanism

The DR mechanism exists precisely for "agent needs human approval for an irreversible action." Deletion is irreversible (even with git, un-deleting a file the user didn't know about is friction). Re-using DRs means:
- No new pipeline concept to learn
- Existing DR resolution flow handles it
- scribe already knows how to create DRs
- Audit trail via `.owlbear/decisions/`

### Sweep-specific optimization

During the initial sweep, multiple orphaned docs may surface. The sweep executor can aggregate proposed deletions into a single DR with a table of files + reasoning, rather than N individual DRs. This is a planner-level decomposition choice, not an architecture change.

---

## Q6 — Sweep Workflow

**Position: Decomposed into normal pipeline tasks. No special skill, no special invocation, no sweep-specific agent.**

### Decomposition shape

The sweep is a sequence of standard kanban tasks, ordered by dependency:

**Phase 0 — Tooling (prerequisite for everything else)**
1. Create `.owlbear/scripts/doc-index.py` + test
2. Create `r-doc-standards` skill
3. Create `doc-audit.prompt.md`

**Phase 1 — Agent redesign**
4. Redesign `doc-writer.agent.md` v2 (scope, boundaries, w-doc-update v2)
5. Update `w-doc-update` skill for expanded checklist
6. Verify doc-writer v2 across behavioral modes (M2 outcome 4)

**Phase 2 — Remediation (parallelizable after Phase 1)**
7. Fix root docs (`SECURITY.md`, `README.md`, `README-consumer.md`)
8. Fix `serve/knowledge/README.md`
9. Create missing `serve/*` READMEs (7 packages — can be one task or split by package)
10. Fix `your-org` placeholder URLs (4 files — one task)

**Phase 3 — Diagrams (parallelizable after Phase 0)**
11–17. One task per diagram (7 tasks). Each is an explicit diagram-creation task with architect/planner authority.

**Phase 4 — Validation**
18. Run doc-audit.prompt.md as acceptance test. Findings become new tasks if any.

### Why not a single sweep task or custom invocation

- A single sweep task is too large for the pipeline's "one logical change per commit" discipline.
- A custom skill/prompt for sweeping duplicates what doc-audit already does (enumerate, assess, remediate).
- Normal pipeline tasks get proper TDD, review, and docs gates. Sweep-specific shortcuts would bypass quality controls.

### The sweep dies after execution

Per M2 outcome 1: "A temporary sweep working-doc lives during the sweep and dies after." The sweep's task decomposition IS the working doc — it lives on the kanban board during execution and archives when done. No permanent sweep artifact beyond the remediated docs and the permanent doc-index.

---

## Key Trade-offs

| Decision | Gained | Given Up |
|----------|--------|----------|
| Index-derived scope | Auto-adapting scope, no manual maintenance | Dependency on index freshness — stale index = stale scope |
| YAML index format | Machine + human readable | YAML parsing dependency (PyYAML) |
| `r-doc-standards` skill | Citable rules for audit, objective findings | Another skill to maintain |
| `share/diagrams/` flat dir | Simple enumeration, sync guarantee | Diagrams not co-located with their modules |
| DR-based deletion | Reuses existing mechanism, audit trail | More heavyweight than inline approval for bulk deletion |
| Decomposed sweep | Quality gates per task, parallelizable phases | More kanban overhead than a single sweep |

---

## Warnings

1. **Index freshness is a single point of failure.** If doc-writer's SessionStart hook fails to regenerate the index, it operates on stale scope. The hook must fail loudly (non-zero exit blocks session) rather than silently using an old index.

2. **`r-doc-standards` scope creep.** The skill must stay terse — SHALL/MUST rules only, no prose guidance, no examples, no rationale. If it grows beyond ~80 lines, it's absorbing content that belongs elsewhere.

3. **Diagram maintenance drag.** 7 diagrams are 7 things that can go stale. The doc-audit D7 dimension catches this, but only on user invocation. There is no automated diagram-staleness detector — it depends on doc-writer's per-task assessment and periodic audit discipline.

4. **Phase 2/3 parallelism requires planner coordination.** Tasks 7–17 can run in parallel after their prerequisites, but the planner must declare dependencies correctly or tasks will collide (e.g., two tasks editing the same README).

5. **w-doc-update v2 complexity budget.** The expanded checklist must not become a 20-item bureaucratic gate. The assessment should remain heuristic ("does this task affect any indexed doc?"), not exhaustive ("check every indexed doc against this task").
