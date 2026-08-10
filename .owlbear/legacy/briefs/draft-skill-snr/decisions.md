# Decisions — Agent & Skill Signal-to-Noise Ratio

## Project Type

- **Chosen:** existing-feature/refactor
- **Rationale:** The 80 files exist and ship today. This is an audit and possible reduction/restructure, not a greenfield design.

## Investment Tier

- **Chosen:** Shared
- **Rationale:** Files serve multiple consumers (pipeline agents, consumer projects). Outcomes shape the product's instruction surface. Full panel + research bridge warranted.
- **Rejected:** Tool — files are multi-consumer, not internal-only utility.
- **Rejected:** Production — not external-facing; durability of the compression decisions can be revisited.

## Approach — Version C (locked)

- **Chosen:** Two complementary prompts (broad audit improvement + new deep-dive prompt)
- **Rationale:** The existing agent-audit finds critical findings every run but can't go deep enough. Wherever it does dig, there are new findings at all criticality levels. A single tool can't cover both ecosystem coherence AND per-sentence compression at quality.
- **Rejected:** Direct task without prompt (simplifier) — the problem repeats across 80 files; methodology must be reusable from the start.
- **Rejected:** Ablation-first (first-principles) — these are complex workflow/handbook skills, not "coding style" reminders. Removing one breaks the agent chain entirely, not subtly. Ablation is incoherent for this domain.
- **Rejected:** Routing changes — routing is fine. The right files reach the right agents. The problem is content density in correctly-routed files.

## Early Challenge Assessment

- **Simplifier:** Useful pressure on scope sequencing, but wrong about "just do it directly." The problem is structural repetition across 80 files — methodology IS the deliverable.
- **First-principles:** Good challenge on verification rigor, but fundamentally misread the domain by treating complex workflow procedures as simple style reminders. Ablation suggestion reveals the stance didn't read the actual files.

## D5 — 2026-05-04 — Tool Boundary Refinement

**Decision to make:** How do the broad audit and deep-dive divide responsibility for SNR evaluation?

**Chosen:** Complementary focus — broad audit strengthened at what it does best (abstract, overarching, ecosystem-level). Its SNR dimension becomes a quick indicator/finder that flags files deserving attention but doesn't drill into per-sentence analysis. Deep-dive does the opposite: quick context glance, then deep nitty-gritty compression. Deep-dive is allowed to cross-check other files ("lift the head up occasionally").

**Source inputs:**

- User: "strengthen the broad audit prompt in the aspects it can do well... but also the depth shouldn't be completely lost, but be more of an indicator and quick finder"
- User: "deep drill prompt should do the exact opposite: take a quick glance at the context, then dive deep... but also be allowed to cross check with other files, lift the head up occasionally"

## D6 — 2026-05-04 — Dropped Questions

**Dropped:** Creative latitude encoding ([TIGHT]/[GUIDE] annotations)

- Rationale: Not productive, only destructive. Would lead to critic suppression. If something deserves rethinking, it deserves rethinking — don't preemptively mark it immune.

**Dropped:** Verification baseline (record pipeline pass rates before compression)

- Rationale: Measurement for the sake of measuring. Existing monitoring covers regression detection.

**Settled:** Trivial-knowledge scope

- Deep-dive agent judges whether the model would already know something; proposes removal to user via askQuestions. Interactive loop provides sufficient control.

## D7 — 2026-05-04 — Design Spine (locked)

**Decision to make:** What design spine do the two prompts share?

**Chosen:** Panel recommendation accepted as-is (confidence 0.78):

1. Single proposal per file (user-facing) + internally adaptive analysis
2. Section-based approval with batch-approve escape hatch
3. 6-category noise taxonomy (5 original + stale institutional memory)
4. Consumer-context resolution mandatory before classification
5. End-of-run ranking with unranked attention flags during audit
6. User-bridged routing (no automated context passing between tools)
7. Category-grouped ranking, not global (peer-relative scoring)
8. Universal files (`applyTo: **`) as highest-leverage class

**Rejected:** None — panel convergence was strong.

**Residual risks deferred to implementation:** Prompt bloat expressing adaptive strategy, end-of-run delay tolerance, funnel false-positive rate, context window pressure for heavy agents.

**Source inputs:**

- Panel: architect, enduser, data (3 stances + pragmatist convergence)
- User: accepted as-is

## D8 — 2026-05-04 — Critic Validation Refinements

**Decision to make:** How to address two material findings from the dual Critic pass?

**Chosen — M1 (consumer-context bounds):** Pragmatic loading cap for universal files. Load top 3-5 heaviest consumers by required_reading chain, note total consumer count, classify with that sample. Prompt acknowledges sampling explicitly.

**Chosen — M2 (dual-axis ranking):** Ranking incorporates two axes: (1) noise density relative to category peers, and (2) context-budget weight (file size + required_reading chain × consumer count). High-budget files with moderate noise outrank low-budget files with high noise.

**Operational risks (noted for Brief):**

- Taxonomy overlap — recognition vocabulary, not formal partition; agent can note multiple patterns per sentence
- File-40 fatigue — batch-approve escape hatch + "use over time" infrastructure bounds this
- Silent contract erosion — interactive approval + conservative bias + consumer-context + monitoring bounds this

**Source inputs:**

- Critic pass 1 (synthesis): 8 challenges, 5 blind spots → 1 material, 7 minor, 1 nonsense (O15 applied)
- Critic pass 2 (design merit): 6 challenges, 3 blind spots → 1 material, 4 minor (O15 applied)
- User: accepted both resolutions, note risks in Brief
