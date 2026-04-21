# Context

## Initial Request (raw, M0)

User feels the project documentation is significantly out of date. Two-sided framing:

- **Dev-oriented docs** (this project itself) and **consumer-oriented docs** (for projects consuming OwlBear's services) are both stale.
- Some docs still reference v1 (Pydantic AI–based architecture) — but the project has fully migrated to v2 (VS Code Copilot–only, with GH Copilot CLI as a future-oriented option). Pydantic AI is gone.
- Staleness exists in both root-level files and subdirectories.

User's hypothesis on root cause:
1. **Symptom**: Docs are out of date → need a sweep to bring them current.
2. **Cause**: The `doc-writer` agent may not be focused on the right things, allowing drift to accumulate.

User wants both addressed: (1) get docs current, (2) fix the process so docs stay current.

## M1 Probes — Findings

**Worst offenders called out by name:**

- `SECURITY.md` — "completely old, has nothing to do with the current state AT ALL"
- Both root `README.md` files (dev README and consumer README)

User has not yet looked beyond root level — these are the surface signals.

**Audience priority: Dev-oriented first.**

User chose dev-oriented (architecture, agent/skill internals, `serve/*` READMEs) as the more painful audience right now. Notable inversion from the framing in the initial request — the daily friction of working on OwlBear itself outweighs consumer-adoption friction.

**Kinds of rot — all five present:**

- Outright wrong (dead tech: Pydantic AI, v1 patterns)
- Stale-but-not-wrong (older shape of live things)
- Missing (Cockpit, MCP servers, ideation panel underdocumented)
- Duplicated/contradictory
- Orphaned (docs for things that no longer exist)

User's characterization: "really a little of everything. in most cases one kind per file."

**On `doc-writer`:**

User owns this honestly: the agent was likely underspecified at creation; he didn't verify it was doing what he intended. Worked fine until now because docs weren't critical — but the project has crossed a complexity threshold where they are. The fix is redesign, not blame.

**Sweep shape — systematic + permanent index:**

Full-repo audit, NOT just status-tagging. The inventory must include:

- Every doc, with status (current / stale / outright-wrong / orphaned / missing-but-needed).
- A TOC with cross-references — surfaces duplicates and intentional cross-links.
- Possibly retained **permanently** as a living artifact and explicit input to `doc-writer`. Strong design seed: an authoritative doc-map closes much of the scope-ambiguity gap that lets `doc-writer` drift.

**Process appetite — open, defer to panel.**

User does not want to pre-constrain the redesign. Panel deliberation is invited to recommend mechanism (sharper agent definition, doc-auditor, pipeline gates, doc-impact tagging, ownership map, or combinations).

**Constraints / posture:**

- **Quality over everything.** "If it takes a month, so be it. This has to be perfect."
- **No backwards compatibility, no legacy.** Break to improve.
- **Downstream blast radius is the multiplier**: this project is consumed by dozens, potentially hundreds, of complex downstream projects. Doc rot here propagates as adoption friction and misuse everywhere.

## M1 Problem Statement (committed, post-Critic, post-user-correction)

OwlBear's documentation has accumulated drift across the repo. Visible canaries are at root (`SECURITY.md`, both `README.md` files); a presumed-extensive long tail exists in subdirectories (`serve/*` READMEs, agent/skill docs, setup guides). Rot includes outright-wrong (lingering Pydantic AI / v1 residue), stale-but-not-wrong, missing (Cockpit, MCP servers, ideation panel, **and project diagrams that don't exist at all**), contradictory, and orphaned.

**The per-task phase model is correct.** `doc-writer` running at task close, touching only docs the current task affects, with a 90/80 no-op rate, is the right operational shape. The agent is just underspecified for what it should actually cover.

The problem is two-bodied:

**Body A — One-shot sweep.** Full-repo audit and remediation. Produce a doc inventory (TOC + cross-references + per-doc status) that persists as a permanent input artifact for `doc-writer`. Sweep includes authoring missing diagrams, not only fixing prose.

**Body B — Process redesign, two layers:**

- **Per-task layer:** Redesign `doc-writer` scope. Explicit additions: (a) Excalidraw diagram authorship and maintenance (project-level abstract + per-module detail; flow-oriented and user-oriented examples include "how kanban works," "memory system layers — global, local, VS Code built-in"); (b) inventory-aware (knows what exists, where, who owns what); (c) user-gated deletion (proposes a blocked deletion task with reasoning, user approves/redirects).
- **Periodic layer:** Introduce `doc-audit.prompt.md`, mirroring `agent-audit.prompt.md` — a user-invoked, repo-wide drift detector that emits remediation tasks. This is the backstop for whatever per-task `doc-writer` misses. (This absorbs the "docs as property" and "second-order rot" concerns from Critic, but lands them at the prompt layer rather than as a paradigm change.)

**Audience clarification (important reframing):** owlbear-dev *consumes* owlbear-main as a service supplier — this very chat's instructions come from main, not dev. The "consumer audience" and "dev-internal audience" are ~95% the same docs. There is only a small dev-only carve-out: anything not synced to main per `.github/copilot-instructions.md` (e.g., `.owlbear/`, `tests/`, `store/`, `seed/` partly). Audience asymmetry is therefore minimal — design for one audience with a small carve-out, not two parallel systems.

**Retained from Critic:**

- **Deletion is in scope, but user-gated.** Doc-writer never deletes autonomously; proposes a blocked deletion task with reasoning.
- **Operational consumer success conditions still need definition** in M2, but they map to "owlbear-dev (and any future consumer) can correctly use OwlBear from its docs."

**Posture:** Quality over everything. No backwards compatibility. No legacy. Time is unbounded.

## M2 Outcomes (committed)

When this work is done, all seven of the following are observably true:

1. **Auto-generated doc index exists in `.owlbear/`.** A Python script enumerates every doc markdown file (path-exclusions: `scratch/`, `research/`, `kanban/`, etc. — only actual doc markdown) and writes an index containing **file path + per-file TOC (section headings)**. No content summary; no source-file frontmatter requirement — filename + TOC is sufficient when files are well-named with descriptive headings. Index format is implementation detail (md / yaml / json — planner's call). Index is regeneratable on demand; cannot disagree with reality. Consumed by `doc-writer` agent and `doc-audit` prompt. In consuming projects, OwlBear-shipped paths are marked. **A temporary sweep working-doc** (cleanup checklist) lives during the sweep and dies after; issues found become kanban tasks immediately, not tracked status fields.
2. **All known-rotten docs are remediated.** `SECURITY.md`, both `README.md`s, and every doc the sweep flagged — fixed, consolidated, or deleted (user-approved). Zero Pydantic AI / v1 residue.
3a. **Seven Excalidraw diagrams exist for owlbear-dev (this Brief delivers them).** 1 project-overview + 6 named module diagrams (kanban, memory layers — global/local/VS Code built-in, MCP topology, pipeline, ideation panel, Cockpit). Produced as kanban tasks during/after the sweep. **owlbear-dev-specific deliverable** — consumer projects make their own diagram decisions for their own code.
3b. **`doc-writer` v2 has the generic capability to author and maintain Excalidraw diagrams.** The agent does so under exactly two trigger conditions: (a) a task explicitly asks for diagram creation/update (architect or planner decides; builder never authors diagrams), or (b) the agent must update an existing diagram because relevant code changed. **The agent never autonomously decides 'this needs a diagram.'** Diagrams remain **descriptive, not authoritative** — authority lives with `architect` and AC; `doc-writer` translates authority into prose and diagrams. A diagram must accurately reflect current system state (so `doc-audit` can flag drift); if a diagram disagrees with reality, the diagram is wrong, never the code.
4. **`doc-writer` v2 is defined and verified across behavioral modes.** Definition: scope, triggers, deletion-gating, and index consultation are written into `doc-writer.agent.md`. Verification: agent runs across ~6 test cases covering each behavioral mode at least once — no-op, prose update, diagram maintenance during code changes, explicit diagram-creation task, deletion proposal, ambiguous/misclassification (real recent tasks where they fit, constructed otherwise). A short verification log records each run and the conclusion.
5. **`doc-audit.prompt.md` exists and works.** Mirrors `agent-audit.prompt.md`. User invokes it, gets a drift report, remediation tasks land on the board. Cadence guidance documented.
6. **A consumer (owlbear-dev or a fresh consumer project) can use OwlBear correctly from the docs.** Validated **opportunistically in the field** — user will run owlbear-main from a separate project on another machine and feed any gaps back as kanban tasks. NOT an exit-gate condition for this work.
7. **Two-layer doc-currency safety net is in place.** **Layer 1 (per-task):** No task reaches `done` without `doc-writer` having explicitly run on it (no-op or update). The pipeline gate already exists; this work tightens what `doc-writer` does within that gate. **Layer 2 (periodic):** `doc-audit.prompt.md` runs on user invocation, surfaces drift across the whole repo, and emits remediation tasks. Catches everything Layer 1 misses (bypassed phases, slow drift, evolving doc needs).

## M2 Validation Posture

No formal cold-clone or end-to-end consumer test. User self-validates via real downstream use; broken docs become bug-tasks, not blockers for this Brief.

## M3 Landscape (committed)

**Doc surface scale:** ~76 product docs total — 3 root (`README.md`, `README-consumer.md`, `SECURITY.md`) + 2 `serve/*` READMEs (cockpit, knowledge) + 24 `share/agents/*.agent.md` + 30 `share/skills/*/SKILL.md` + 7 `share/instructions/*.instructions.md` + 7 `share/prompts/*.prompt.md` + 2 `setup/*.md` + `.github/copilot-instructions.md`. Plus ~650 `.owlbear/` working files (research/decisions/briefs/kanban) — out of scope as product docs.

**v1/Pydantic AI worry: overblown.** Zero pydantic-ai / pydantic_ai matches in the product doc surface. All v1 material is properly quarantined inside `.owlbear/research/`. Logfire mention in `h-pytest-and-linting` is a legitimate Windows-workaround note, not rot. The user's initial concern about v1 leakage doesn't reflect what's actually in the docs today — but the *other* rot categories are very real.

**Worst rot, confirmed and bounded:**

- `SECURITY.md` — entire file references a `src/owlbear/...` tree that no longer exists; cites `docs/security-audit.md` (no `docs/` dir). Structurally orphaned end-to-end.
- `README.md` — claims a `v1/` directory that doesn't exist.
- `serve/knowledge/README.md` — install paths use `packages/knowledge` (current location: `serve/knowledge/`).
- `README.md` vs `README-consumer.md` — divergent surface (POSIX vs Windows, different CLI coverage). Not synchronized.
- Placeholder `your-org` GitHub URL in 4 files.

**Coverage gap (missing-but-needed pattern):** 7 of 9 `serve/*` packages have no README — `orchestrator`, `kanban`, `browser`, `mcp-kanban`, `mcp-knowledge`, `mcp-memory`, `mcp-browser`.

**The big diagnostic finding:** `doc-writer`'s declared scope is literally five paths: `README.md`, `.github/copilot-instructions.md`, `.owlbear/research/*`, `.owlbear/sources/*`, and Python docstrings. The repo has ~76 product docs. The agent's scope **excludes ~70 of them** — every `serve/*/README.md`, every agent, every skill, every instruction, every prompt, every setup guide, `SECURITY.md`, `README-consumer.md`. No diagram authorship. No deletion of stale files (only scratch cleanup). No doc-index awareness. No doc-audit coupling.

> The rot isn't `doc-writer` doing its job poorly — its job is defined to exclude almost the entire doc surface.

**Current `doc-writer` shape (concrete):**

- Per-task reactive only; runs only on tasks in `docs` status.
- 5-item checklist (behavior/API → copilot-instructions, module docstrings, attribution → `.owlbear/sources/`, CLI changes → README.md, research-doc presence/linkage).
- Output: Channel A verdict + appended `## Docs Gate` section to task body + optional commit.
- Allowed sub-agent: `scribe` only.
- Hooks: `deny-code-writes.py` PreToolUse — enforces no-logic-edit boundary.
- "No busywork" rule built-in; 90/80 no-op pattern is already supported.

**`agent-audit.prompt.md` as mirror reference:**

- User-invocable interactive `.prompt.md`; no tool allowlist; one-finding-at-a-time with `askQuestions` checkpoints; explicit pause/bail allowed.
- Loads 4 standards skills first (`h-agent-structure`, `h-memory-structure`, `r-pipeline-protocol`, `r-project-standards`); every finding must cite one.
- 7 audit dimensions (D1–D7): Structural, Duplication, Content Placement, Quality, Pipeline Integrity, SNR, Memory Governance — each with positive + negative-space probes.
- Process: Scan → severity queue → Finding loop (cards with options + confidence) → fix → rescan → Verification (pipeline trace, spot-checks, coverage).
- **Structural gap for mirror:** there is no `r-doc-standards` or `h-doc-structure` skill yet for `doc-audit` to cite. Mirror would either need to author one, or have `doc-audit` cite `w-doc-update` items as rules.

## Tier

**Deep tier confirmed.** Cross-cutting (per-task agent + new prompt + sweep + inventory artifact + diagram authorship), high downstream impact, no-compromise quality posture. Stopping rules will come at M2 (outcomes) and M4 (decisions) — not "do everything," but "make the right hard decisions."
