# Synthesis — Neutral Shared Layer

## Summary

Four late-domain panelists (architect, data, enduser, security) evaluated the refactoring plan for decoupling OwlBear-specific content from `share/`. There is strong convergence on the migration model (D3 = project-neutral shared + local overrides), the critical role of `setup/init.py` scaffolding, and the need for atomic cross-reference migration. The central tension is placeholder notation: the user's original `{variable, e.g. example}` syntax vs. the prose-only approach favored by three of four panelists. A secondary tension exists around implementation scope — whether to pursue the full 10-file sweep or a surgical P1/P2 subset (as early challengers recommended).

---

## Convergences

### C1 — `copilot-instructions.md` is the single project-local authority

All four stances agree: after refactoring, all project-specific path facts live in `.github/copilot-instructions.md` and/or local `.owlbear/` files. Shared skills reference abstract concepts; the project config resolves them. (architect §Rec 2, data §Rec 5, enduser §Position ¶1, security §Rec 1)

### C2 — `setup/init.py` must scaffold the binding layer

All four stances identify this as critical or highest-leverage. Without scaffolding, consumers get no signal that project-local path mapping exists. The enduser stance calls it "the single highest-leverage intervention" (enduser §Rec 4). The architect flags it as a scope risk — it could slip (architect §Confidence). Data and security concur it must be part of the atomic delivery.

### C3 — Shell commands must never contain placeholder syntax

Universal agreement: executable commands, `lint_paths` arrays, tool invocation templates use concrete illustrative paths with an adjacent prose note ("adjust for your layout"). No `{var}` in anything a model might copy-paste into a terminal. (architect §Rec 1, data §Rec 1, enduser §Position — "forces the model into exploration mode", security §Rec 4)

### C4 — Cross-reference chains migrate as atomic units

Data identified specific foreign-key violations (`r-doc-standards` → `doc-audit.prompt.md` → `doc-standards.instructions.md` → `h-agent-structure` stubs table). All stances support atomic migration to prevent dangling pointers. The architect independently arrived at the same conclusion via "atomic implementation" (architect §Rec 3, data §Rec 2).

### C5 — `doc-standards` should be split, not fully moved

The architect explicitly recommends keeping generic quality rules in shared while extracting the OwlBear-specific scope enumeration (architect §Rec 4). Data frames this as "keep the pattern, extract the instance." No dissent from enduser or security.

### C6 — Path-sensitive routing needs logic changes, not just text edits

The enduser and security stances both flag `h-quality-runner` as a structural issue: its path-prefix routing (`serve/cockpit/web/` → Vitest) is not a prose problem but a behavioral coupling that needs project-level configuration (enduser §Rec 6, security §Rec 2, security Risk table row 7).

### C7 — `copilot-instructions.md` content must stay declarative

Security warns against placing behavioral directives there that override shared skill logic — that creates split-brain instruction conflicts (security §Rec 1). The architect's 80% threshold rule (only content benefiting ≥80% of agent interactions) is compatible with this (architect §Rec 5).

### C8 — The refactoring is security-neutral

Security assessed no trust boundary changes, no privilege escalation vectors, and a minor improvement in information exposure. Confidence 0.88. (security §Risk Assessment)

---

## Disagreements

### T1 — Placeholder notation: template `{var, e.g. X}` vs. prose-only

This is the central tension. The user initially requested `{variable, e.g. example}` notation.

| Stance | Position | Rationale |
|--------|----------|-----------|
| **Architect** (0.78) | Templates OK in prose/examples, banned in commands | LLM context window IS the resolution mechanism; `e.g.` provides standalone fallback; templates work in ~8 non-executable contexts |
| **Data** (0.80) | Prefers prose, but templates "viable with risks" | Template syntax already exists in codebase (`w-code-review` lint_paths, prompt variables); risk is not "LLMs can't parse" but "silent degradation when examples drift" |
| **Enduser** (0.68) | **Hard ban** on template syntax | Three specific LLM failure paths: (1) model copies example literally, (2) model preserves curly-brace string in output, (3) model recognizes template but has no resolver. Prose triggers exploration behavior instead. |
| **Security** (0.88) | Prose preferred | "Prose cannot be mistaken for a resolution mechanism" — framed as integrity, not vulnerability |

**Score: 3 prefer prose, 1 allows templates in limited scope.** The architect is the sole template advocate but restricts to non-executable contexts. The enduser provides the strongest empirical argument against (three failure paths), though acknowledges low confidence (0.68) on the empirical claim.

**Early challenger signal:** The simplifier noted "removing examples strips concreteness that makes skills usable." First-principles asked whether generic defaults are even coherent. Both suggest the answer may be fewer files touched, not different notation.

### T2 — Implementation scope: full sweep vs. surgical subset

| Stance | Position |
|--------|----------|
| **Architect** | All 10 files + `setup/init.py` + local overrides, atomically |
| **Data** | Full authority migration with post-migration grep validation |
| **Enduser** | Focus on highest-leverage (scaffolding), accept graceful degradation elsewhere |
| **Security** | Audit each path-sensitive file; no position on scope breadth |
| **Simplifier** (early) | P1 = split `owlbear-system.instructions.md` (60% of pain, 30-min edit). P2 = 3 path-heavy skills (25% more). Defer P3 indefinitely. |
| **First-principles** (early) | Triage which files carry universal opinion the model doesn't already have. The "shared" set may be much smaller than `share/`. |

**Tension:** The architect and data stances want completeness to prevent split-brain. The simplifier argues surgical priority delivers most value with minimal risk. These aren't incompatible — the question is whether to ship P1 first or bundle everything.

### T3 — How much goes into `copilot-instructions.md`

| Stance | Position |
|--------|----------|
| **Architect** | 80% threshold: only content benefiting most agent interactions. Architecture overview → `.owlbear/instructions/` instead. |
| **Security** | Keep it declarative (facts/paths). No behavioral overrides. |
| **Enduser** | Scaffold a commented path-mapping section for complex projects. |

No hard disagreement, but the boundaries need an explicit decision: what's "factual enough" for always-loaded context vs. what should be conditional (instruction stub with `applyTo`)?

---

## Recommendation

**Confidence: 0.76**

### On placeholder notation (T1)

Adopt the **prose-first approach with concrete examples in clearly-framed reference blocks**. This is the pragmatic middle ground:

- Inline generic references use conceptual nouns: "your source packages", "your frontend package root"
- Where a concrete example aids comprehension, frame it explicitly: *"Example (OwlBear-dev): `serve/cockpit/web/`"* — this is the data stance's Rec 4 and satisfies the architect's "standalone comprehension" requirement
- No `{variable, e.g. example}` template syntax in shared files
- `copilot-instructions.md` uses concrete paths (it IS the authority)

**Grounding:** Three of four panelists converge on prose. The architect's core concern (skills must be independently readable) is met by the "framed example" pattern without requiring template syntax. The enduser's failure-path analysis is the strongest objection to templates, even at lower confidence.

**Trade-off acknowledged:** This departs from the user's original request for `{variable, e.g. example}` notation. The panel evidence suggests templates create more failure modes than they solve, given VS Code's lack of a resolution mechanism.

### On implementation scope (T2)

Adopt **phased delivery aligned with the simplifier's P1/P2/P3 triage**, but with the architect's atomicity constraint applied within each phase:

- **P1:** Split `owlbear-system.instructions.md` (extract §2-§4 to OwlBear-dev local). Ship with `setup/init.py` scaffolding update. Atomic.
- **P2:** Genericize `r-project-standards`, `h-quality-runner`, `h-agent-structure`. Migrate `r-doc-standards` chain atomically. Ship together.
- **P3:** Remaining cosmetic passes. Defer until friction reports from consumers.

This satisfies data's "no split-brain" concern (each phase is internally complete) while avoiding the all-or-nothing risk the architect acknowledged.

### On `copilot-instructions.md` content (T3)

Apply the architect's 80% rule + security's "declarative only" constraint:

- **In `copilot-instructions.md`:** Directory structure table, primary test paths, package manager mappings, monorepo layout facts
- **In `.owlbear/instructions/`:** Architecture overview, namespace table, package-specific conventions (conditional via `applyTo`)

---

## Open Questions

1. **User decision required — notation.** The panel recommends prose-only, departing from the user's original `{variable, e.g. example}` request. Does the user accept prose-first with framed examples, or insist on template syntax (with the architect's command-exclusion constraint)?

2. **User decision required — phasing.** Ship P1 first (one file split + init.py scaffolding) then P2, or bundle everything as one deliverable?

3. **Canonical vocabulary.** The enduser recommends standardizing 3-5 conceptual nouns across all affected files ("source packages", "frontend package root", "test directories", etc.). Should this vocabulary be defined in a shared file, or is consistency-by-convention sufficient?

4. **Quality-runner routing.** All stances agree this is structural, not textual. Is the routing logic fix in-scope for this refactoring, or is it a separate task?

5. **First-principles triage.** Should P2 include a triage step — auditing which of the 10 files carry opinion the model doesn't already have — potentially shrinking the shared set further?
