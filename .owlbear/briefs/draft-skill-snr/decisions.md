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
