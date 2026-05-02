# First-Principles Stance — Memory Module

## Irreducible Claim

The only thing that matters is: **an agent, at the moment it begins a task, has access to the specific prior lessons that would prevent it from repeating a known mistake on that task.**

Everything else — storage format, MCP servers, curation workflows, promotion layers, approval states, confidence scores — is mechanism. The question is whether the mechanism is necessary for the claim.

## Assumptions Challenged

### 1. "Agents repeat mistakes because memories are low-signal"

**Status: Unearned.**

The framing asserts a causal chain: too many memories → important ones drowned → agents repeat mistakes. But there is a simpler, competing hypothesis that the blackboard itself names in Assumption #1:

**Agents repeat mistakes because `get_knowledge` has never worked.** The mcp-memory server has a transport bug exposing 0 tools. That means the "Primary" leg of Knowledge Pre-flight (`r-pipeline-protocol` §Knowledge Pre-flight) has been silently failing since deployment. The protocol says "graceful degradation — proceed normally" on failure. So agents have been proceeding normally — without any curated knowledge — every single time.

You cannot diagnose a signal-to-noise problem in a channel that has never transmitted. The entire "quality gating" premise rests on an assumption about what happens when agents DO read memories. We have no data on that because they never have (via MCP). The file-based fallback (`/memories/repo/*.md`) does get loaded into context, but those ~11 curated files are already hand-curated by the user — they ARE the quality-gated layer.

**Irreducible test:** Fix the transport bug. Measure whether agents with working `get_knowledge` still repeat mistakes. If yes, the problem is elsewhere. If no, you already have the solution and need zero new infrastructure.

### 2. "Quality gating requires a promotion layer"

**Status: Cargo cult.**

The existing `/memories/repo/*.md` files are:
- Committable and in git ✓
- Human-curated (by definition — a human writes them) ✓
- Agent-role-scoped (filenames like `builder-pitfalls.md`, `reviewer-coverage.md`) ✓
- Already loaded into agent context at startup ✓

This IS a quality-gated promotion layer. It's just manual and file-based. The framing treats "promotion layer" as requiring infrastructure (SQLite, MCP, approval workflows, confidence scores), but the repo-memory files already satisfy the irreducible requirement.

What's missing from these files is not quality gating — it's **automated triage of the inbox**. The `/memories/repo/inbox/` pattern (agent writes bullets → human curates into topic files) is a functioning promotion pipeline. It's manual. The question is whether automating that triage justifies a full MCP server, or whether a simpler mechanism (a curation prompt, a periodic script, a curator agent that reads inbox and rewrites topic files) would suffice.

### 3. "The module needs to be a separate MCP server"

**Status: Unjustified if coexistence model holds.**

The context.md says: "if custom system COEXISTS → merge into knowledge-mcp is viable." But even that understates the reduction. If VS Code memory stays as raw capture, and `/memories/repo/*.md` stays as the curated output, then the only missing piece is **automated inbox triage**. That's a batch job, not a server. It doesn't need to be online. It doesn't need MCP tool exposure. It could be:

- A prompt file (`/memory-curate.prompt.md`) that an agent runs periodically
- A Python script that reads inbox markdown and proposes merges into topic files
- The existing `w-mem-curation` workflow skill, invoked on a cadence

Five MCP tools, SQLite, approval state machines, migration CLI — all for a problem that might be solvable with a scheduled file operation.

### 4. "Fewer memories = better performance"

**Status: Wrong framing.**

The problem isn't volume. The agent context window is loaded with `/memories/repo/*.md` at startup — that's ~25KB across 11 files. That's tiny relative to context limits. Adding 5x more curated entries wouldn't degrade performance.

The actual constraint is **relevance**: does the agent see the right lesson for the current task? The current system has no task-type routing — a builder gets reviewer lessons, a reviewer gets excalidraw patterns. The fix for this is filtering at read time (agent-scoped queries), not filtering at write time (quality gates on entry creation).

The mcp-memory module's `get_knowledge(agent_id=..., min_confidence=0.7)` was designed to solve exactly this — agent-scoped, confidence-filtered retrieval. But it never worked. The file-based system loads everything. The gap is **read-time filtering**, not write-time gating.

### 5. "VS Code memory can't be eliminated"

**Status: True but misleading.**

VS Code memory can't be eliminated because it's used for context compaction — an internal VS Code mechanism. But this is a red herring for the design question. The compaction use is invisible and automatic. It doesn't interact with the curated-knowledge problem at all. Framing the design around "coexistence with VS Code memory" creates false constraints. VS Code memory is orthogonal; design the curation system as if it doesn't exist.

## Restatement of the Problem

Strip away the inherited structure:

1. Agents need task-relevant prior lessons at startup. **(Core requirement.)**
2. Raw lessons accumulate faster than they're curated. **(Operational reality.)**
3. The MCP-based retrieval path has never worked. **(Bug, not architecture gap.)**
4. The file-based path works but loads everything without filtering. **(Read-time problem.)**
5. Inbox-to-topic-file promotion is manual. **(Curation cadence problem.)**

The "quality-gated promotion layer" framing collapses to: **fix the retrieval bug, automate the inbox triage, and add agent-scoped filtering at read time.**

## Zero-Infrastructure Scenario

What if you built nothing new?

1. Fix `mcp-memory` transport bug (it's already coded and tested — this is a config/registration fix).
2. Run `w-mem-curation` on a cadence (weekly?) to triage inbox → topic files.
3. Agents use `get_knowledge(agent_id=...)` for filtered retrieval.

What breaks: nothing new. You get the system you already designed and built, actually working. The only open question is whether the existing mcp-memory design (SQLite, approval states) is the right implementation for what reduces to "filtered read of curated markdown entries."

## What Would Actually Break Without Custom Infrastructure

- **No agent-scoped filtering:** Agents see all lessons, not just their own. Solvable by naming convention (`builder-*.md`) and instruction changes.
- **No confidence scoring:** All curated entries treated equally. Acceptable if human curation provides implicit quality ranking.
- **No programmatic query:** Can't search memories by keyword/category. Acceptable at current scale (~50-100 curated entries).

None of these are critical at current scale. They become relevant at ~500+ curated entries with multiple specialized agent roles.

## Confidence

**0.82** — High confidence that the problem is misframed as an infrastructure gap when it's primarily (a) a bug making existing infrastructure non-functional, and (b) a curation cadence problem. Deducted for the possibility that at larger scale, structured query and confidence scoring provide genuine value that file-based approaches can't match.

## Strongest Challenge

The entire ideation may be solving a problem that doesn't exist yet. Fix the bug. Run the curator. Measure. Then decide if you need more.
