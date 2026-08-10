# Brief — Agent & Skill Signal-to-Noise Ratio — Compression Tooling

**Parent:** Task 1293 (neutral-shared-layer ideation spin-off)
**Tier:** Shared
**Type:** existing-feature/refactor

## Problem

80 instruction files in `share/` (35 skills, 26 agents, 7 instructions, 12 prompts) have grown organically. ~1/3 of content is estimated noise — verbose prose wrappers, over-specified interpretations, redundant conditionals, prescriptive templates, cross-reference ceremony, and stale institutional memory. The reviewer agent alone loads 1,113 lines of required reading for its primary workflow.

The existing `agent-audit` prompt finds critical findings every run but can't evaluate signal density at the per-sentence level. Its D6 dimension is surface-level. Two complementary tools are needed: one for big-picture coherence, one for attention-dense per-file compression.

## Solution

Two complementary `.prompt.md` files:

| Tool | Focus | Interaction Model |
|------|-------|-------------------|
| **Broad Audit** (`agent-broad-audit.prompt.md`) | Ecosystem coherence, cross-file patterns, priority triage | Finding-loop (one at a time, approval). End-of-run ranked report. |
| **Deep-Dive** (`agent-deep-audit.prompt.md`) | Per-sentence signal evaluation, full-depth single-target audit | Single proposal per target, section-by-section approval with batch escape hatch. |

**Division of labor:** The broad audit identifies *where* attention is needed (quick SNR indicator alongside its full ecosystem audit). The deep-dive does the *deep work* (everything about one agent/skill cluster, in extreme depth). The user bridges between them manually — the deep-dive receives no audit findings to prevent anchoring bias.

**Shared vocabulary:** Both prompts inline the same 6-category noise taxonomy:

1. Verbose prose wrappers
2. Over-specification
3. Redundant conditionals
4. Prescriptive message templates
5. Cross-reference ceremony
6. Stale institutional memory

## Broad Audit (`agent-broad-audit.prompt.md`)

**Replaces:** the existing `agent-audit.prompt.md`

**Full audit retained:** Schema checks, linked-file validation, `applyTo` correctness, structural compliance, duplication detection, content placement, pipeline integrity, memory governance — all continue as today. Some dimensions may be slightly lighter to rebalance attention toward the strengthened SNR signal.

**D6 (SNR) strengthened:**

- Upgraded from shallow ("is there rationale?") to a quick indicator/finder that scans for noise-taxonomy patterns
- Flags files deserving deep-dive attention — not a full per-sentence drill, but enough to identify where attention should concentrate
- Universal files (`applyTo: **`) explicitly called out as highest-leverage class
- Progressive attention flags emitted during the audit (unranked, non-blocking)

**New deliverable: End-of-run ranked report**

- Produced after completing the full audit pass (all dimensions, not just D6)
- Dual-axis ranking: (1) noise density relative to category peers × (2) context-budget weight (file size + required_reading chain × consumer count)
- Category-grouped (agents ranked against agents, skills against skills, etc.)
- High-budget files with moderate noise outrank low-budget files with high noise
- Serves as prioritized input for deep-dive sessions

**Interaction model:** Finding-loop preserved (one finding at a time, approval cycle). Attention flags and ranked report are supplementary outputs alongside the existing finding flow.

## Deep-Dive (`agent-deep-audit.prompt.md`)

**New prompt.** Takes one agent or one skill and examines it with its full dependency cluster at extreme depth.

**Scope modes:**

- **Agent mode:** Takes one agent → loads the agent file + all skills it references (`required_reading`, frontmatter links). Audits the agent's full instruction surface as a coherent unit.
- **Skill mode:** Takes one skill → loads the skill + identifies all agents that consume it. Audits the skill in the context of its actual consumers.

**Pre-analysis: context loading**

- Maps the full dependency cluster for the target (agent → skills, or skill → consumers)
- For universal skills (`applyTo: **`): pragmatic sampling — load top 3-5 heaviest consumers by required_reading chain, note total consumer count
- Understands the unit as a whole before evaluating any part

**Core analysis: everything about this unit, in depth**

- **Correctness:** Does the overall flow make sense across the agent + skills? Are instructions coherent and correctly sequenced? Do cross-references resolve?
- **Completeness:** Does the agent have all needed tools, the right model, adequate context? Are skills missing content the agent needs?
- **Naming & structure:** Are section names right? Is content in the right file within the cluster?
- **Value per instruction:** Is each instruction earning its context-window cost? Does it steer behavior the model wouldn't produce alone?
- **Signal-to-noise:** Per-sentence evaluation using the 6-category noise taxonomy. Proposes compression: removal, terse rewrite, or structural reorganization.
- **Cross-file coherence:** Within the cluster — is content duplicated across the agent and its skills? Should it move? Is anything in a skill that belongs in the agent or vice versa?
- Conservative bias: lean toward keeping when uncertain. Procedural sequences and institutional memory get extra protection.

**Output: single proposal per target**

- Structural proposals first (flow fixes, content moves between files in the cluster, completeness additions)
- Compression proposals second (per-section across all files: what to cut/rewrite and why)
- Issues found (broken links, missing tools, wrong model, naming problems, misplaced content)

**Interaction model:**

- Section-by-section approval via `askQuestions` (grouped by file within the cluster)
- Agent proposes changes → user approves, rejects, or modifies
- Batch-approve escape hatch after trust established
- Internally adaptive analysis depth — user always sees the same proposal format

## Acceptance Criteria

**AC1 — Broad audit prompt exists and works**

- `agent-broad-audit.prompt.md` replaces `agent-audit.prompt.md`
- All existing audit dimensions (D1-D5, D7) preserved with finding-loop behavior
- D6 upgraded: scans for noise-taxonomy patterns, emits attention flags, flags universal files
- End-of-run ranked report produced with dual-axis scoring (noise density × context-budget weight)

**AC2 — Deep-dive prompt exists and works**

- `agent-deep-audit.prompt.md` created
- Accepts an agent name or skill name as input
- Loads the full dependency cluster (agent + skills, or skill + consumers)
- Produces a single structured proposal (structural first, compression second, issues third)
- Section-by-section approval via `askQuestions` with batch-approve escape hatch
- 6-category noise taxonomy applied with conservative bias

**AC3 — Shared taxonomy inlined in both prompts**

- Same 6 categories appear in both prompts with matching definitions
- Categories: verbose wrappers, over-specification, redundant conditionals, prescriptive templates, cross-reference ceremony, stale institutional memory

**AC4 — Evaluation (blocked, user-action, last task)**

- Run `agent-deep-audit` on the reviewer agent (192 lines + 1,113 lines required reading)
- Rate proposal quality: measurable token reduction with per-section justification
- Verify no pipeline regression after applying proposals
- This task is blocked from the start and only unblocked after all prompt-building tasks are complete

## Operational Risks

| Risk | Mitigation |
|------|-----------|
| **Taxonomy overlap** — a sentence can exhibit multiple noise patterns | Taxonomy is a recognition vocabulary, not a formal partition. Agent can note multiple patterns. |
| **File-40 fatigue** — deep-dive across many agents/skills may lead to rubber-stamping | Batch-approve escape hatch. The tool is infrastructure for ongoing use, not a sprint commitment. |
| **Silent contract erosion** — stripping instructions that look generic but enforce specific OwlBear behavior | Conservative bias. Interactive approval. Consumer-context loading. Pipeline monitoring. |
| **Prompt bloat** — expressing adaptive strategies may make `agent-deep-audit` itself too long | If prompt exceeds ~300 lines, split into prompt + companion skill for analysis methodology. |

## Out of Scope

- Automated pipeline between broad and deep-dive (user bridges manually)
- Creative-latitude annotations (`[TIGHT]`/`[GUIDE]`) — dropped as counterproductive
- Verification baselines (pre-compression pass-rate recording) — existing monitoring suffices
- Routing changes — routing is correct; the problem is content density in correctly-routed files
- Actually compressing all 80 files — the Brief delivers the *tools*; compression campaigns are separate work
