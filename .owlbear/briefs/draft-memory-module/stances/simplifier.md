# Simplifier Stance — Memory Module

## Verdict

The problem is real but the framing inflates it. "Quality-gated promotion layer" is an architecture answer to what is primarily a **curation-frequency and instruction-quality problem**. The existing `mcp-memory` module is a sunk cost with zero production hours — don't let its existence anchor the solution space upward.

## Cut 1: The `/memories/repo/*.md` Files ARE the Promotion Layer

You already have committable, git-native, agent-readable curated knowledge files. They work today. Agents partially read them. The problem isn't "no promotion target exists" — it's "nobody maintains it systematically." A broken custom MCP server with SQLite is not a better promotion target than markdown files that already ship in the repo and already get loaded into agent context.

**Pressure:** Before evaluating any infrastructure, answer: what happens if you just curate `/memories/repo/` better? If the answer is "the problem mostly goes away," you don't need a module.

## Cut 2: The `mcp-memory` Module Has Zero Proven Value

It has never served a single tool call in production. The transport bug means no agent has ever used it. All claimed benefits (quality gating, approval workflow, structured query) are theoretical. The Brief frames this as "keep/restructure/cut" as if it's a running system being evaluated — it's not. It's dead code with a test suite. Treat it as dead code.

**Pressure:** Reframe from "should we fix the existing module" to "if we were starting fresh today, would we build this?" If the answer is no, cut it. If the answer is "maybe something simpler," you just proved the current design is over-scoped.

## Cut 3: Instructions-First Before Infrastructure

The cheapest intervention is updating agent instructions and the `w-mem-curation` workflow:

- "Write to `/memories/repo/` only for patterns confirmed across 3+ tasks"
- "Include confidence score and recurrence count in every entry"
- "Curator runs weekly, prunes entries below threshold"

This is testable in days, costs nothing, and directly addresses "agents produce uncurated entries." If it doesn't work, you've learned something real. If it does work, you've solved the problem without a module.

**Pressure:** The Brief skips this option entirely. Why? If it was tried and failed, that evidence should be in the context. If it wasn't tried, it should be tried before building anything.

## Cut 4: Coexistence Model Adds Complexity It Claims to Solve

Two memory systems = two sets of agent instructions, two mental models, two maintenance surfaces. The framing acknowledges this tension but doesn't resolve it. The simplest coexistence model is: VS Code memory for ephemeral/compaction (already non-negotiable), `/memories/repo/` for curated institutional knowledge (already exists). No third system needed.

Adding an MCP server as a promotion target only makes sense if you need structured query over curated knowledge. But the knowledge MCP already exists. If you need queryable promoted memories, ingest them into `mcp-knowledge` — don't maintain a separate server.

## Cut 5: "Direction Only" Scope Is Fine, but the Option Space Is Too Wide

Four options (keep/restructure/merge/cut) across two coexistence models with conditional merge logic is a lot of decision surface for what should be a binary: **"Do we need custom infrastructure, or do better curation of existing files suffice?"** Answer that first. Everything else flows from it.

## Decomposition Recommendation

Split this into two sequential questions, not one Brief:

| Phase | Question | Deliverable |
|-------|----------|-------------|
| P1 | Does improving instructions + curation workflow on `/memories/repo/` reduce mistake repetition measurably? | 2-week trial with before/after signal quality metric |
| P2 (conditional) | If P1 is insufficient, what is the minimal infrastructure addition? | Scoped Brief — likely "add memory entries to knowledge-mcp" not "fix mcp-memory" |

P2 only fires if P1 fails. This eliminates 80% of the decision surface.

## Confidence

**0.82** — High confidence that the infrastructure framing is premature. Moderate uncertainty about whether instruction-only fixes are *sufficient*, but that uncertainty is exactly why P1 should be a trial, not a Brief.
