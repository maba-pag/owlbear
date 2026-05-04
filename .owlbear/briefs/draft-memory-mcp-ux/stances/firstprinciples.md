# First-Principles Stance — Memory MCP Tool UX Refactor

## Irreducible Core

The actual need reduces to: **pipeline agents must persist lessons-learned and retrieve relevant ones, without trial-and-error against hidden constraints.** That's it. Everything else in the framing is structure layered on top of that claim.

## Assumptions Challenged

### 1. The 3-step lifecycle is borrowed structure, not an irreducible need

**Claim in framing:** pending→curated→approved is a settled, load-bearing decision.

**Challenge:** This lifecycle is borrowed from multi-reviewer systems (editorial pipelines, content moderation queues) and applied to a single-user setup where exactly one human reviews everything. The three-step model implies a world where the curator and the approver are different actors with different trust levels. In OwlBear, the "curator" is an agent acting on behalf of the single user, and the "approver" is that same user. The real question is: **does the curation step produce measurably better entries than direct user review of pending entries?**

If the curator agent reliably improves entry quality (deduplication, consolidation, rewording), the middle step earns its existence. If the curator is just a gate that rubber-stamps or lightly edits, it's ceremony — a 2-step model (pending→approved) with an optional "curate" action on pending entries would be simpler and equivalent.

The framing locked this as "3-step stays" without evidence that the curation step is load-bearing. That lock deserves pressure.

**Irreducible minimum:** Entries have a "not yet reviewed" state and a "reviewed" state. Whether there's one or two review steps is an optimisation question, not a structural one.

**Confidence:** 0.72 — the curation step *might* earn its keep through deduplication, but that's a feature of the curator agent, not of the state machine.

### 2. The two-package split is conformity tax with no current payer

**Claim in framing:** Memory must split into `serve/memory/` (engine) + `serve/mcp-memory/` (wrapper) to match the other three domains.

**Challenge:** The split exists in kanban, knowledge, and browser because those engines have non-MCP consumers. Kanban's engine is imported by the cockpit backend. Knowledge's engine is imported by the MCP-knowledge server. Browser's engine is imported by the MCP-browser server. In every case, a second consumer justifies the separation.

Memory has **zero non-MCP consumers today**, and the framing identifies none for the future. The cockpit doesn't display memory entries. No other package imports memory models. The only consumer is the MCP server process itself.

Extracting a package to match a pattern, when no consumer exists for the extracted package, is speculative architecture. The conformity argument assumes the pattern has inherent value — but the pattern exists to solve a concrete problem (shared engine code across consumers), and that problem doesn't exist here.

**The genuinely load-bearing argument for extraction is testability** — testing engine logic without MCP context wiring. But the current tests already import `MemoryEngine` and `MemoryEntry` directly from `owlbear_mcp_memory`. The engine is already a clean class with a `Path` constructor. MCP context is only in `tools.py`. Testability is already solved without a package split.

**Irreducible minimum:** Engine code must be importable and testable without MCP. It already is. The split adds a package, a pyproject.toml, CI plumbing, and import path changes across all tests and consumers — for architectural conformity with no functional gain.

**Confidence:** 0.82 — unless a concrete non-MCP consumer is identified, this is premature abstraction.

### 3. Access control via tools: lists is weaker than it appears

**Claim in framing:** Kill `OWLBEAR_MEMORY_CALLER`, use agent-level `tools:` lists in `.agent.md` to control who sees which tools.

**Challenge:** `tools:` lists in `.agent.md` are a **visibility hint**, not an enforcement boundary. Three failure modes:

1. **Subagent escalation.** An agent with a restricted tool list can dispatch a subagent (e.g., General Purpose) that has full tool access. The boundary is trivially circumvented.
2. **Direct MCP calls.** Any process that can reach the MCP server's stdio can call any tool. The tools: list is a VS Code UI filter, not a server-side ACL.
3. **Agent file edits.** The tools: list is a text file. An agent with file-write access can edit its own `.agent.md` to add tools.

The framing treats "don't show the tool" as equivalent to "enforce the role." It isn't. What it *actually* provides is: **agents won't accidentally call tools they shouldn't, because the tools aren't in their schema.** That's accident prevention, not access control.

**The real question is: does accident prevention suffice?** For a single-user laptop system with no adversarial actors, it probably does. But the framing should name it honestly: this is "don't put the chainsaw where the toddler plays," not "lock the tool shed."

**Irreducible minimum:** General agents shouldn't see curator tools. Whether that's enforced or just hidden depends on threat model. For single-user OwlBear, hiding is sufficient — but call it hiding, not access control.

**Confidence:** 0.88 — the mechanism works for the actual threat model, but the framing overstates what it provides.

### 4. The 9-category enum is metadata theater

**Claim in framing:** Categories are part of the model; agents must provide them on store.

**Challenge:** Look at what `query_memory` actually does with categories: it's an optional filter that most callers don't use. The default query behavior returns curated+approved entries sorted by confidence — categories are irrelevant to the default path.

Nine categories (knowledge, behaviour, pitfall, process, tool, goal, personality, preference, context) is a taxonomy designed for a corpus that **doesn't exist yet** — the memory store is currently empty. The taxonomy was designed speculatively, not empirically.

The real retrieval question for an agent is: "what did we learn about X?" — which is a text search problem, not a category-filter problem. An agent querying for "pytest pitfalls" would need to know that the category is "pitfall" AND the content mentions pytest. The category adds no retrieval value that a keyword in the title or content doesn't already provide.

Categories impose a classification cost on every `store_learning` call (agents must pick from 9 values they can't see in the schema, which is problem #3 in the framing) and provide almost no retrieval benefit.

**Irreducible minimum:** If categories exist, they should be optional and few (3–4 max, empirically derived from actual entries). Or: drop categories entirely and rely on content search. The current 9-value enum is premature taxonomy.

**Confidence:** 0.78 — categories *could* become useful at scale (hundreds of entries), but the current design pays the cost upfront for a benefit that may never materialise.

### 5. The "agent-hostile interface" problem reduces to schema documentation

**Claim in framing:** Hidden constraints are a design problem requiring tool surface redesign.

**Challenge:** This is the most genuinely irreducible problem in the framing — and it's simpler than presented. The fix is mechanical: put the constraints in the tool descriptions and JSON Schema. Enum values in the schema. Confidence range in the field description. Default query behavior in the tool docstring. State transition rules in update_entry's description.

This doesn't require architectural changes, package splits, or tool surface redesign. It requires better docstrings and schema annotations. The MCP protocol already supports JSON Schema with enums, ranges, and descriptions. The problem is that nobody wrote them.

**Irreducible minimum:** Tool descriptions must contain every constraint an agent needs to succeed on first call. This is a documentation fix, not an architecture fix.

**Confidence:** 0.91 — this is the clearest win in the entire framing.

## Summary: What's Genuinely Irreducible vs. Borrowed

| Claim | Verdict | Simpler Alternative |
|-------|---------|---------------------|
| Agents need to store and retrieve lessons | **Irreducible** | — |
| Tool descriptions must expose all constraints | **Irreducible** | Schema + docstring fix |
| General agents shouldn't see curator tools | **Irreducible** | tools: list hiding (not "access control") |
| 3-step lifecycle | **Borrowed** | 2-state (pending/approved) + optional curation action |
| Two-package engine split | **Borrowed** | Keep inline until a non-MCP consumer exists |
| 9-category taxonomy | **Borrowed** | Optional free-form tags, or drop entirely |
| Runtime role enforcement | **Borrowed** | Unnecessary for single-user; tools: hiding suffices |

## Overall Confidence: 0.80

The framing correctly identifies real pain (hidden constraints, broken access control, over-scoped surface) but prescribes structural remedies (package split, lifecycle formalization, category enums) that exceed the irreducible need. The simplest version of this refactor is: fix the tool descriptions, split the tools: lists, and delete the broken role enforcement. Everything else can wait for evidence.
