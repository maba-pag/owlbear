# End-User Stance — Memory MCP Tool UX (Full Design)

## User Experience Stance

The 7-tool design is structurally sound: clean audience separation (2 general, 4 curator, 1 user), consistent naming, required parameters with no hidden defaults. Two critical UX defects remain: the hidden 1KB body limit recreates the brief's original problem, and body-only recall strips interpretability signal agents need to weight knowledge. The design will succeed if these are addressed and the rollout sequences activation correctly.

## Usability Reasoning

### 1. Tool Naming — Approve

`save_memory` and `recall_memory` pass the discoverability test. "save" + "memory" match the highest-probability agent search terms for writing. "recall" is semantically close to "remember" / "retrieve" / "memory" — VS Code's tool_search uses semantic matching, so exact keyword matters less than semantic proximity.

The full set (`save_memory`, `recall_memory`, `list_memories`, `read_memory`, `curate_memory`, `delete_memory`, `approve_memory`) follows a consistent `verb_noun` pattern. Each tool's purpose is legible from its name alone. No agent needs documentation to guess what `delete_memory` does.

**Caveat:** "recall" is not a verb programmers reach for first — "query", "get", "fetch" are more common in code. The strength of `recall_memory` depends on semantic search rather than keyword matching. This is acceptable because MCP tool discovery IS semantic search. But consumer instructions must be updated atomically with the rename — agents whose skills still reference `query_memory` will be confused.

### 2. Hidden 1KB Body Limit — Strong Oppose

D22 deliberately hides the body-size constraint from the tool description, relying on validation errors to educate agents. This recreates the EXACT defect the brief's problem statement identifies:

> "Valid categories, confidence range (0.7–1.0), state transitions, and default query behavior are enforced by Pydantic but not exposed in tool descriptions or JSON Schema. Agents fail on first call with cryptic validation errors."

The rationale — preventing "fill the budget" behavior — is an instruction-level concern. You fix agent verbosity in their pipeline instructions ("be concise, focus on actionable lessons"), not by hiding the constraint from the tool interface. An agent that writes a thoughtful 1.2KB entry and gets rejected learns nothing useful from the failure — it just truncates blindly.

**Position:** State the limit in the tool description. One line: "content: string, max 1000 characters." This costs nothing and eliminates a guaranteed first-call failure mode for agents with thorough lessons to record.

### 3. recall_memory — Conditional Accept (include confidence)

The design intent is sound: general agents consume knowledge, they don't manage it. Stripping IDs, timestamps, scope arrays, and state from the return payload keeps agents focused on the content.

But stripping confidence removes critical interpretability signal. When an agent recalls multiple entries and two contradict, confidence is the ONLY available tiebreaker. Without it, the agent has no basis to prefer one piece of recalled knowledge over another. This isn't "management metadata" — it's a quality-of-information signal for the consumer.

**Minimum viable recall format:**
```
## Entry Title (confidence: 0.85)

Body content here...

## Another Entry (confidence: 0.92)

Body content here...
```

Categories are borderline useful for consumption but not critical. State is correctly excluded (all recalled entries are curated or approved — the agent doesn't need to know which). IDs are correctly excluded. Entry count at the end ("— 4 entries recalled —") would help agents know the scope of what they received.

### 4. Wildcard and Tool Registration Isolation — Oppose Current Design

Two separate isolation concerns:

**Primary (registration-level):** The rollout plan says "all pipeline agents get `ob-memory/*`." If this means the `/*` wildcard in tools: arrays, ALL 7 tools become visible to ALL agents — collapsing the general/curator separation entirely. The rollout MUST use explicit tool names: `ob-memory/save_memory, ob-memory/recall_memory` for general agents, the full set for the curator.

**Secondary (parameter-level):** `recall_memory(agent="*")` returns all entries regardless of scope. This is documented only in curator instructions but works for any caller. An undocumented-but-functional feature is the worst UX state: it's either a bug (should be code-blocked) or a feature (should be documented). For a tool where access control is "agents don't see tools they shouldn't call" — having a scope-bypass parameter on the ONE tool all agents DO see is a design contradiction.

**Position:** Block `"*"` at the code level for callers without curator tools, OR accept it as a documented feature and trust the `tools:` list isolation. Do not leave it undocumented-but-functional.

### 5. Auto-Downgrade on Any Edit — Accept for v1

D20/D29 reverses the current "approved = immutable" contract to "approved entries are editable but auto-downgrade to curated." This is a significant semantic change (current tests enforce immutability), but the NEW behavior is better UX for the curator:

- Old behavior: curator can't fix a typo without deleting and recreating the entry.
- New behavior: curator edits freely, system enforces re-approval automatically.

The guidance hint ("Entry was previously approved. Present to user for re-approval.") makes the consequence visible. The loss of `approved_at` on downgrade (D21) is acceptable — the timestamp represents the CURRENT approval, not a historical record.

**Future concern:** If the curator frequently fixes trivial typos and each one requires user re-approval, the friction will accumulate. Monitor for this pattern post-launch. A potential v2 addition: `curate_memory(..., admin_edit=true)` that preserves state for non-substantive changes. Not needed at launch.

### 6. Parameter Discoverability — Strong Approve (expanded condition)

All parameters on `save_memory` are required with no hidden defaults. This eliminates the "what do I put here?" ambiguity that plagues the current tool surface. Specifically:

- `categories`: must be an enum in JSON Schema (agents see valid values without documentation lookup)
- `confidence`: must have `minimum: 0.7, maximum: 1.0` in schema
- `source_agent`: clear from name that the agent provides its own identifier

**Expanded condition:** JSON Schema correctness is necessary but not sufficient for first-call success. Seven consumer artifacts (r-pipeline-protocol, h-mcp-memory, h-memory-structure, w-mem-curation, memory-curator.agent.md, tests, and the review prompt) must be updated ATOMICALLY with the tool changes. An agent whose pipeline instructions still say `store_learning(title, content, scope_agents)` will fail regardless of schema quality. The consumer update is part of the UX surface.

### 7. Guidance Hints — Strong Approve (expanded set)

D20 defines one hint. Every mutating operation should return an actionable guidance string:

| Operation | Hint |
|-----------|------|
| `save_memory` | "Entry saved as pending. Awaiting curator review." |
| `curate_memory` (pending→curated) | "Entry promoted to curated. Scope: {agents}." |
| `curate_memory` (approved→curated) | "Entry downgraded from approved. Present to user for re-approval." |
| `curate_memory` (curated→curated) | "Entry updated. State unchanged." |
| `delete_memory` (pending) | "Entry permanently deleted (never committed to git)." |
| `delete_memory` (curated/approved) | "Entry soft-deleted. File retained for audit." |
| `approve_memory` | "Entry approved. Now visible to scoped agents via recall." |

This pattern (return a human-readable hint after mutation) already works in the kanban MCP. It eliminates the "did my action succeed and what happened?" uncertainty.

### 8. Activation Sequencing — Critical Dependency

The system is dormant. The transition from dormant to active is itself a UX event that can fail. If general agents start calling `save_memory` before the curator is wired and functional, pending entries accumulate with no review path — creating a backlog that overwhelms the curator on first run.

**Required sequence:**
1. Wire curator agent with all 4 curator tools + verify end-to-end curation workflow
2. Create `memory-review.prompt.md` and verify user approval flow
3. Wire general agents with `save_memory` + `recall_memory`
4. Update consumer instructions/skills atomically

Step 3 MUST NOT precede step 1. Agents producing entries before a curator exists creates immediate quality debt.

---

## Key Trade-offs

| Dimension | Design gains | Design costs |
|-----------|-------------|--------------|
| Audience separation | Agents can't accidentally manage memory | Curator wiring is a deployment prerequisite |
| Body-only recall | Clean consumption UX, no metadata noise | Agents can't flag stale entries, no confidence signal (defect) |
| Required params, no defaults | Guaranteed schema correctness on success | Higher friction on first call (5 required fields) |
| Hidden 1KB limit | Prevents "fill the budget" gaming | Failed first calls for detailed entries (defect) |
| Auto-downgrade | Curator can edit freely | Re-approval friction for trivial fixes |
| Guidance hints | Immediate operational feedback | Server must maintain hint strings |

## Warnings

1. **The hidden 1KB limit and body-only recall are the two UX defects in an otherwise strong design.** Both are user-chosen deliberate decisions. But they repeat the pattern this brief was created to fix: hiding information from tool consumers. The mediator should weigh whether "preventing gaming" outweighs "first-call failure."

2. **Tool registration isolation is load-bearing.** If the rollout uses `ob-memory/*` instead of explicit tool names, the entire general/curator separation collapses. This is not a tool-UX decision — it's a deployment decision that the tool-UX assumes.

3. **Consumer instruction drift is a first-call failure vector.** Seven artifacts reference the old tool surface. If they're not updated atomically, agents will attempt `store_learning(scope_agents=[...])` and fail despite perfect schema on the new tools.

4. **The curator agent doesn't exist in its required form yet.** Current memory-curator lacks MCP tools and operates via filesystem tooling. The design assumes a curator that must be built before general agent activation.

## Confidence

**0.80**

The structural design (7 tools, audience split, auto-state, guidance hints) is excellent — clean, principled, and learnable. Two specific UX defects (hidden limit, missing confidence in recall) prevent a higher score. Both are fixable without architectural change. Activation sequencing is a real deployment risk but not a design flaw.
