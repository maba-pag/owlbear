# Decisions — Neutral Shared Layer

## D1 — 2026-05-02 — Project Type

**Status quo:** User describes refactoring existing shared content.
**Decision to make:** Net-new, existing-feature/refactor, or uncertain?

**Chosen:** existing-feature/refactor

The shared infrastructure exists and works. The goal is to decouple OwlBear-specific content from the generic framework so non-OwlBear consumers get clean, project-neutral tooling.

## D2 — 2026-05-02 — Investment Tier

**Decision to make:** How deep should ideation go?

**Options considered:**

- Scratch: too shallow — multi-consumer impact
- Tool: single-user scope doesn't fit — two consumers
- Shared: multi-consumer, full panel, research bridge required
- Production: overkill — not external-facing, both consumers controlled by user

**Chosen:** Shared

**Rationale:** Two consumers, wrong abstraction boundaries compound. Full panel and research bridge warranted, but no Critic-at-every-moment overhead needed.

## D3 — 2026-05-02 — Override Mechanism

**Status quo:** VS Code has no skill priority/shadowing between configured paths.
**Decision to make:** How do consumers get project-specific content?

**Options considered:**

- A: Shadow with local copy (`.owlbear/skills/` overrides `share/skills/`)
- B: Make shared files generic; project specifics in `copilot-instructions.md` + local `.owlbear/` additions
- C: Template variables in skills that resolve per-project

**Rejected:**

- A because VS Code has no priority mechanism — two versions = undefined behavior
- C because no variable resolution mechanism exists in VS Code skill files

**Chosen:** B — shared files are project-neutral defaults. Project-specific details live in project-scoped `copilot-instructions.md` and/or local `.owlbear/{agents,skills,instructions,prompts}/` that add (not shadow) content.

**Implication:** Skills must be written so they work without project-specific overlay. OwlBear-specifics that used to be inline become either (a) removed from shared and added to OwlBear-dev's own `copilot-instructions.md`, or (b) moved to a local `.owlbear/` skill/instruction that only OwlBear-dev has.

## D4 — 2026-05-02 — Legacy Cleanup Scope

**Note:** User flagged potential dead code: `owlbear-project.json`, `serve/orchestrator/` module. These are in-scope for investigation but not the primary goal of this work.

## D5 — 2026-05-02 — Placeholder Notation

**Decision to make:** How to represent genericized path references in shared skills.

**Options considered:**

- A: Template syntax `{var, e.g. X}` — compact, self-documenting, but 3 LLM failure paths (literal copy, preserved-as-string, no resolver)
- B: Prose + framed examples — inline generic nouns with explicit "Example (OwlBear-dev): `path`" blocks
- C: Pure prose, no examples — cleanest but strips concreteness

**Rejected:** A (failure paths outweigh compactness), C (under-specified)

**Chosen:** B — Prose-first with framed example blocks. Generic nouns inline ("your source packages"), with explicit examples where concreteness aids comprehension. Shell commands always use concrete paths + adjacent prose note.

**Rationale:** 3 of 4 late-domain panelists converge on prose. VS Code has no resolver, so template notation creates a promise nobody keeps. Framed examples preserve the concreteness the user wanted.

## D6 — 2026-05-02 — Implementation Scope

**Decision to make:** Ship all changes atomically or in phases?

**Options considered:**

- Full atomic sweep — all 10 files + scaffolding in one delivery
- Phased P1→P2→P3 — each phase internally atomic, shipped separately

**Rejected:** Atomic full sweep (large PR, all-or-nothing risk)

**Chosen:** Phased P1→P2→P3

- **P1:** `owlbear-system.instructions.md` split + `setup/init.py` scaffolding (~60% of pain)
- **P2:** Path-heavy skills (r-project-standards, h-quality-runner, h-pytest-and-linting, h-vitest-and-linting, w-code-review) + r-doc-standards chain migration
- **P3:** Cosmetic "OwlBear" renames. Defer until friction reports.

**Rationale:** Ships value fast. Each phase internally atomic (no split-brain). P3 explicitly deferred — cosmetic issues don't cause consumer confusion.

## D7 — 2026-05-02 — Content Placement

**Decision to make:** What extracted OwlBear-dev content goes where?

**Chosen:** 80% rule + applyTo scoping

- **`copilot-instructions.md`:** Directory structure table, primary test paths — needed for most interactions (always-loaded, declarative only)
- **`.owlbear/instructions/`:** Architecture overview, namespace table, domain taxonomy — conditional via `applyTo: "serve/**"` (only relevant when editing source packages)

## D8 — 2026-05-02 — Example Placement in Shared Skills

**Decision to make:** Should shared skills contain labeled OwlBear-dev examples, or should all concrete examples live only in project-local config?

**Options considered:**

- B1: Keep framed examples in shared files — labeled "Example (OwlBear-dev): `path`" gives agents concrete patterns even without overlay
- B2: Remove all project-specific examples from shared — purist "no OwlBear refs"

**Rejected:** B2 (makes shared skills too abstract; agents lose concrete pattern without overlay)

**Chosen:** B1 — Shared skills may contain labeled examples explicitly attributed to a specific project. The label makes them clearly non-normative for other consumers.

**Rationale:** Pragmatic trade-off — labeled examples are better than unlabeled hardcoding AND better than pure abstraction. Agents in non-OwlBear projects will see the label and explore their own filesystem rather than adopting the example.

## D9 — 2026-05-02 — Critic Validation Outcomes

**Material findings accepted:**
1. P1 scope expanded: include reference-update files (README.md, WIRING.md, h-agent-structure, h-memory-structure)
2. Brief defines graceful-degradation contract: shared skills work generically without overlay, precisely with it
3. P2 quality-runner scope: routing prose must reference project config, not just genericize paths
4. Brief includes existing-consumer migration section (manual copilot-instructions.md update)

**Minor findings acknowledged, no design change:** declarative boundary is pragmatic; r-doc-standards split depth is implementation detail; P1 priority justified by trigger frequency; trigger breadth as usage proxy.
