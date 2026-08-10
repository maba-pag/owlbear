# Decisions — Memory MCP Tool UX Refactor

## D1 — 2026-05-03 14:00 — Project Type

**Status quo:** MCP Memory server exists with 5 tools, markdown+frontmatter storage, and multiple consumer skills/agents.
**Decision to make:** Classify project type for ideation depth calibration.

**Options considered:**

- A: net-new — build from scratch
- B: existing-feature/refactor — fix and reshape what exists

**Chosen:** B — existing-feature/refactor. The server is coded, tested, and has documented consumers. The storage restructure (from prior brief) has shipped. This work fixes the tool API surface and aligns architecture.

**Rejected:**

- A because the module exists and has shipped consumers. The problems are interface design and structural conformity, not missing functionality.

**Source inputs:**

- User: proactive audit before rollout; identified broken access control, hidden constraints, architectural non-conformity vs. other serve/ packages.

## D2 — 2026-05-03 14:10 — Investment Tier

**Status quo:** Need to calibrate ideation depth.
**Decision to make:** Investment tier selection.

**Options considered:**

- A: Scratch — internal spike, lightweight
- B: Tool — internal utility, single user
- C: Shared — multi-consumer, team artifact

**Chosen:** C — Shared. The MCP Memory server ships as part of OwlBear to all consumer projects. Quality bar matters — other projects depend on this interface. The current tool surface was agent-designed without deep user review; user now wants to bring critical perspective and shape the definitive solution.

**Rejected:**

- A because this is production infrastructure, not a spike.
- B because the tool surface is consumed across projects via the shared OwlBear system, not just internally.

**Source inputs:**

- User: "this is a shared tool and I value quality over anything in this owlbear project, because any other projects will rely on its services."

## D3 — 2026-05-03 14:10 — Design Lineage

**Status quo:** Current 5-tool surface (store_learning, query_memory, update_entry, delete_entry, approve_entry) exists after storage restructure.
**Decision to make:** Was this a deliberate API design?

**Finding:** No deep user review was done. The user relied on agent output during the storage restructure. The solution works but is not considered high-quality. User is now bringing their critical perspective post-hoc to shape the definitive design.

**Implication for Phase 2:** The current tool surface carries no design debt — it can be freely reshaped. There are no deliberate design decisions to preserve; only the storage layer (markdown+frontmatter) and the lifecycle concept (pending→curated→approved) are prior-brief commitments.

## D4 — 2026-05-03 14:15 — Lifecycle Model

**Status quo:** 3-step lifecycle: pending→curated→approved. User's input proposes various simplifications.
**Decision to make:** Keep, simplify, or make flexible?

**Options considered:**

- A: Keep 3-step (pending→curated→approved) as-is
- B: Collapse to 2-step (pending→approved), remove curator middleman
- C: 3-step with optional skip (allow pending→approved directly)

**Chosen:** A — Keep 3-step. The curator quality gate has value; the problem is how the lifecycle is encoded in the tool surface, not the lifecycle itself.

**Rejected:**

- B because the curation step provides a real quality filter — agent-generated entries benefit from review before user approval.
- C because optional steps add state machine complexity without clear benefit.

## D5 — 2026-05-03 14:15 — General Agent Tool Surface

**Status quo:** General agents see 5 tools. Only 2 have valid use cases.
**Decision to make:** What should the general agent tool surface be?

**Finding:** `update_entry` has no use case for general agents — they can't see pending entries by default (query returns curated+approved), and they shouldn't edit curated/approved content. General agents need exactly: `store_learning` (create entry, always pending) and `query_memory` (read curated+approved entries). All editing, state transitions, and deletion belong to the curator surface.

**Implication for Phase 2:** The tool surface splits into two clean audiences: general agents (2 tools) and curator (N tools TBD). Access control becomes a tool-visibility question (agent `tools:` lists), not a runtime role check.

## D6 — 2026-05-03 14:30 — Architecture Split

**Status quo:** All other domains have engine + MCP wrapper two-package pattern. Memory has only `serve/mcp-memory/`.
**Decision to make:** Include extraction in this brief or defer?

**Options considered:**

- A: Include `serve/memory/` extraction in this brief
- B: Defer until a non-MCP consumer exists (backlog with trigger)

**Chosen:** B — Defer. No second consumer exists. The engine is already testable by importing from the MCP package directly. Creating a standalone package adds pyproject.toml, CI plumbing, and import path changes for zero functional gain today.

**Rejected:**

- A because conformity for its own sake adds maintenance cost without unlocking capability. Trigger condition: when a non-MCP consumer (e.g., Cockpit route, CLI tool) needs to import the engine.

**Source inputs:**

- Simplifier (0.90 confidence): "The code is already factored correctly — engine.py, models.py, tools.py. The only consumer is the MCP server itself."
- First-principles (0.82): "The split adds a package, a pyproject.toml, CI plumbing — for architectural conformity with no functional gain."

## D7 — 2026-05-03 14:30 — Lifecycle Challenge Response

**Status quo:** D4 locked 3-step lifecycle. First-principles challenged it as "borrowed from multi-reviewer systems."
**Decision to make:** Re-open or confirm?

**Confirmed:** D4 stands. The 3-step lifecycle is load-bearing infrastructure, not ceremony.

**Why the challenge was wrong:**

- The curator agent runs every 5th orchestration cycle and provides a REAL quality gate: prevents one-offs and low-quality entries from persisting into permanent memory.
- Human review (curated→approved) adds outside knowledge — the user validates content, confidence, and scope with domain expertise that agents lack.
- These are genuinely different actors with different capabilities: agent stores → curator agent reviews quality → human approves with domain knowledge.
- First-principles assumed the curator doesn't measurably improve entries. That assumption is false — the curation step is architecturally required.

## D8 — 2026-05-03 14:30 — Category Enum

**Status quo:** 9 mandatory categories. First-principles called it "premature taxonomy."
**Decision to make:** Keep, make optional, or replace?

**Chosen:** Keep as mandatory. Categories serve dual purpose:

1. **Curation aid:** Categorization helps the curator agent assess and route entries efficiently.
2. **Writing discipline:** Forces the storing agent to reflect on what type of learning it's recording. If an entry mixes categories (e.g., a "pitfall" and a "process"), the agent should split it into two entries — this is a quality signal.

**Rejected:**

- "Make optional" — removes the reflection forcing function.
- "Replace with tags" — too unconstrained; free-form tags don't force taxonomic reflection.
- "Drop entirely" — loses both curation and writing-discipline value.

**Note for Phase 2:** Agent instructions should explicitly guide agents to split entries when they mix categories. The enum set (9 values) can be evaluated for completeness/redundancy during implementation.

## D9 — 2026-05-03 14:30 — Brief Scope

**Status quo:** Simplifier proposed separating consumer migration into P2.
**Decision to make:** Scope of this brief.

**Chosen:** P1 + P2 together — tool UX fix AND consumer updates. Consumer migration is trivial from a task perspective and shouldn't be a separate brief.

**Rejected:**

- P1-only because consumer updates are mechanical and small; separating them adds coordination overhead without benefit.

## D10 — 2026-05-03 14:30 — Access Control Mechanism

**Status quo:** `OWLBEAR_MEMORY_CALLER` per-process env var is broken. `MEMORY_TOOLS_EXCLUDE` is low-value.
**Decision to make:** Replace, fix, or delete?

**Chosen:** Delete both. Access control via agent `tools:` lists in `.agent.md` files — same mechanism all other MCP servers use. This is accident prevention (agents don't see tools they shouldn't call), not true access control — but sufficient for single-user laptop deployment.

**Rejected:**

- Fix the env var (per-request caller identity) — adds complexity for a threat model that doesn't exist.
- Replace with a new mechanism — unnecessary; existing infrastructure handles it.

**Source inputs:**

- User (observations): "MEMORY_TOOLS_EXCLUDE is a deletion candidate... Use agent-level tool whitelisting instead of server-level tool blacklisting."
- Both challengers agreed (0.85–0.88 confidence).

## D11 — 2026-05-03 14:45 — Read Path Architecture

**Status quo:** Agents currently read memory from `/memories/repo/*.md` files (loaded as repo memory, dozens of files read individually) or don't read at all.
**Decision to make:** Post-activation, where do agents READ approved memory?

**Options considered:**

- A: MCP `query_memory` is the single read path. One call returns curated+approved entries scoped to the calling agent.
- B: Approved MCP entries propagate into `/memories/repo/*.md` thematic files. Agents continue reading repo memory.
- C: Defer to Phase 2.

**Chosen:** A — MCP as single source. `query_memory(scope_agents=["agent_name"])` becomes the one-call pre-flight. Returns only relevant entries directly into context. Vastly simpler than reading 100+ individual files.

**Rejected:**

- B because it keeps the unscalable file-reading pattern alive. Dozens of entries need individual reads — horrible UX.
- C because the direction is clear from user requirements.

**Source inputs:**

- User: "it only makes sense to have reading all memory items relevant to an agent during preflight (query_memory with agent=agent_name) instead and only have curated or even approved items delivered directly into context with that one call."

## D12 — 2026-05-03 14:45 — VS Code Memory Sunset

**Status quo:** VS Code memory (`/memories/`) is the current primary system. Unmanaged, unscalable (100+ entries, each read individually).
**Decision to make:** Keep, sunset gradually, or big-bang replace?

**Chosen:** Big-bang replacement. When agents get `ob-memory/*` in their tools: arrays, `vscode/memory` is removed simultaneously. No coexistence period. One system, not two competing tools. An agent should never face ambiguity about which memory tool to use.

**Data migration:** Out of scope for this brief. User handles manually. Losing existing entries is acceptable vs. creating tool ambiguity.

**Rejected:**

- Gradual sunset because coexistence creates exactly the confusion this brief aims to eliminate — agents wouldn't know which tool to use.
- Keep both because "two similar tools" is worse than losing some historical data.

## D13 — 2026-05-03 14:45 — Tool Naming (problem framing, not solution)

**Status quo:** `store_learning` is the write tool name. Agents find tools via `tool_search`.
**Problem identified:** An agent who solved a problem and wants to record the lesson would search for "memory", "save", "remember", "record" — not "store" or "learning." The current name fails the discoverability test.

**Decision for Phase 2:** Tool names must match natural agent search behavior. Both the write and read tools need names that surface when agents search for memory-related capabilities.

**Not decided:** The actual new names. Phase 2 evaluates options.

## D14 — 2026-05-04 — Tool Naming (resolution)

**Chosen:** `save_memory` (write), `recall_memory` (read), `list_memories` (curator scan), `read_memory` (curator read), `curate_memory` (curator edit), `delete_memory` (curator delete), `approve_memory` (user approve).

**Rationale:** "save" and "memory" match highest-probability agent search terms. "recall" maps to memory-retrieval mental model. Curator and user tools use action verbs consistent with MCP conventions. Panel convergence (architect + enduser).

## D15 — 2026-05-04 — General Agent Tool Surface (resolution)

**Chosen:** 2 tools: `save_memory` (write) + `recall_memory` (read). No scope parameter on write. `agent` parameter required on read.

**Parameters — save_memory:** title (required), content (required), categories (required, ≥1), confidence (required, 0.7–1.0), source_agent (required, immutable).
**Parameters — recall_memory:** agent (required). ~~`"*"` wildcard~~ superseded by D32 — `"*"` is code-blocked. Curator uses `list_memories` + `read_memory` instead. Recall returns approved entries first (priority), then curated entries up to limit (D37).
**Returns — recall_memory:** Body only (with title as heading). Ultra-minimal. No metadata.

## D16 — 2026-05-04 — Curator Tool Surface

**Chosen:** Option C — 4 MCP tools: `list_memories`, `read_memory`, `curate_memory`, `delete_memory`. All operations through MCP. Entry IDs only (no filenames). No modality split.

**Rejected:**
- A (3 tools, read from disk): Two handle types (IDs + filenames). Modality split between MCP and file tools.
- B (2 tools, edit from disk): No state machine enforcement on edits. Auto-downgrade impossible.
- D (1 tool): No enforcement at all.

**Panel:** Architect preferred A (0.78). Data (0.75), enduser (0.78), security preferred C. User chose C.

## D17 — 2026-05-04 — User Approval Tool

**Chosen:** `approve_memory` — user-only, via guided prompt (memory-review.prompt.md). User never calls MCP directly. Agent walks user through curated entries for approval.

## D18 — 2026-05-04 — Scope Assignment Model

**Chosen:** Curator-only. Storing agents do not set scope. Three-state semantics: `[]` = unscoped (awaiting curator), `["*"]` = universal (visible to all), `[names]` = targeted. Scope validation gate: `pending→curated` rejects if `scope_agents` is still `[]`.

**Rejected:** `intended_for` non-binding hint from storing agent (user: "omit").

## D19 — 2026-05-04 — Deletion Model

**Chosen:** State-dependent. `pending` entries: hard-delete from disk (never committed, no trace). `curated`/`approved` entries: soft-delete (mark state=deleted, file retained).

## D20 — 2026-05-04 — Auto-Downgrade

**Chosen:** Code-enforced. Any field change on an `approved` entry automatically downgrades state to `curated`. Returns guidance hint: "Entry was previously approved. Present to user for re-approval." No agent input to set state — auto-state logic handles it.

## D21 — 2026-05-04 — Schema Fields

**Added:** `approved_at` (set on approve, cleared on downgrade). `source_agent` (required, immutable, set at creation).
**Dropped:** `modified_by` (impractical — no identity mechanism post-D10; state transitions encode who acted).

## D22 — 2026-05-04 — Body Limit

**Chosen:** 1KB character limit on content field (excluding frontmatter). NOT stated in tool description — only in validation error message. Prevents "fill the budget" agent behavior.

## D23 — 2026-05-04 — Confidence Range

**Chosen:** 0.7–1.0. Required, no default. 1.0 is valid for heavily-confirmed entries.

## D24 — 2026-05-04 — Category Names

**Chosen:** Rename 3 ambiguous: `tool` → `tool-usage`, `knowledge` → `domain-knowledge`, `context` → `env-context`. Other 6 unchanged: behaviour, pitfall, process, goal, personality, preference.

**Rationale:** Zero entries exist — zero migration cost. The 3 renamed terms are genuinely ambiguous ("tool" and "context" are overloaded in AI; "knowledge" too generic).

## D25 — 2026-05-04 — Git Commits

**Chosen:** Curator batch-commits. Pending entries remain uncommitted until curation. Hard-deleted nonsense never enters git history. Curation produces one batch commit per run.

## D26 — 2026-05-04 — Cutover Gate

**Chosen:** No formal gate. User controls big-bang timing (copy dev→main). The system is dormant; no production data to protect.

## D27 — 2026-05-04 — Recall Payload

**Chosen:** Body only (with title as heading). No structured metadata (no id, categories, confidence, state, timestamps). Agents get the knowledge, not memory management metadata.

## D28 — 2026-05-04 — Per-Agent Confidence

**Rejected:** Binary scope (in/out per agent) instead. No per-agent confidence scores. Mixes entry quality with agent relevance, creates O(agents × entries) complexity, violates YAGNI. Panel consensus (architect + data).

## D29 — 2026-05-04 — curate_memory Auto-State Logic

**Chosen:** `curate_memory` always results in `curated` state. pending→curated (auto-promote), curated→curated (stays), approved→curated (auto-downgrade). Agent never sets state — auto-state logic in code.

## D30 — 2026-05-04 — curate_memory Editing Pattern

**Chosen:** Full body replacement. Entries are ≤1KB. Curator reads via `read_memory`, constructs improved body in context, submits full replacement via `curate_memory(entry_id, content="new body")`. Partial-update: only provided fields get updated; `None` = no change.

## D31 — 2026-05-04 — Auto-Downgrade Approach

**Chosen:** Unconditional. Any `curate_memory` call on an approved entry triggers downgrade to curated. No equality comparison, no normalization logic.

**Rejected:** Normalized comparison (compare {title,content,categories,confidence,scope_agents} after normalization, identical = no-op). Too complex — YAML+markdown normalization is a bug factory for marginal benefit. Spurious re-approval on no-op is cheap.

## D32 — 2026-05-04 — Wildcard Blocking

**Chosen:** Code-block. Reject `"*"` in `recall_memory` validation. The curator has dedicated unscoped tools (`list_memories` + `read_memory`) and doesn't need a scope-bypass on the general agent read tool.

**Rejected:** Document-only (allow `"*"` but document as curator-only). Hidden backdoor. Architect + security consensus against.

## D33 — 2026-05-04 — Soft-Delete Retention

**Chosen:** Soft-deleted entries persist on disk indefinitely. Cleanup happens only during prompted curation workflow when user explicitly instructs deletion. No automated GC, no separate feature needed.

## D34 — 2026-05-04 — Per-Tool Registration

**Chosen:** All agent `.agent.md` files must use explicit tool names (e.g., `ob-memory/save_memory`), NOT wildcards (`ob-memory/*`). Wildcards collapse audience separation. Panel consensus (4/4).

## D35 — 2026-05-04 — Activation Sequencing

**Chosen:** Curator first → verify lifecycle → pilot agents → full rollout. Don't wire `save_memory` before the curator can process pending entries. Prevents pending pile-up.

## D36 — 2026-05-04 — Scope Gate Specification

**Chosen:** `scope_agents` is conditional-required. Required for `pending→curated` transition (atomic rejection if missing). Optional for edits to already-curated entries. Error message teaches: "Provide scope_agents to promote this entry."

## D37 — 2026-05-04 — Recall State Filter and Ordering

**Chosen:** Priority-ordered response. Approved entries returned first, then curated entries fill remaining slots up to limit. Implies a limit parameter on `recall_memory`.

**Rejected:** "approved only" (cold-start problem, blocks knowledge flow until first user approval batch) and "curated+approved flat" (no prioritization of user-approved content).

## D38 — 2026-05-04 — Git Commit Behavior for Review Workflow

**Chosen:** Batch commit at the end of the memory review prompt workflow session. Individual `approve_memory` and `delete_memory` calls during review do NOT commit individually — one commit at session end. Consistent with curator batch-commit pattern (D25).

**Note:** `save_memory` still leaves files uncommitted (D25). Curator batch-commits during curation runs. Review prompt batch-commits at session end. Two batch-commit points: curation and review.

## D39 — 2026-05-04 — Seed Data / Bootstrap Strategy

**Chosen:** Start fresh. Clean slate. Existing `/memories/repo/` entries stay as historical reference. Pipeline generates native MCP entries organically.

**Rejected:** Migrate existing entries (format mismatch — plain markdown with no frontmatter schema; automated conversion would produce low-quality entries requiring full curator review anyway).

## D40 — 2026-05-04 — recall_memory Agent Parameter Validation

**Chosen:** Free string. Only `"*"` is code-blocked. No agent registry or known-agent validation. Consistent with self-declared identity model (D21).

## D41 — 2026-05-04 — recall_memory Default Limit

**Chosen:** Default 20. Balances context window budget with sufficient recall coverage.

## D42 — 2026-05-04 — Curator Tool Scope

**Chosen:** Curator gets only the 4 curator tools (`list_memories`, `read_memory`, `curate_memory`, `delete_memory`). Does not get general agent tools (`save_memory`, `recall_memory`). Curator is strictly management — doesn't create entries or use the general recall path.

**Rejected:** Curator gets all 6 tools (4 curator + 2 general). Unnecessary — curator doesn't need to save entries or recall from its own scope.
