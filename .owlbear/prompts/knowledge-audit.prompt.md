---
name: knowledge-audit
description: audit the knowledge module
---

lets do an audit of the knowledge module (serve/knowledge/ and serve/knowledge-mcp/ primarily). this is the central knowledge database including a knowledge graph that is used via mcp and powered by manually run agents. this manual part is intentional for now.

## Current System Boundary

Read `h-knowledge-ops` before scanning. It is the current authority for the live MCP tools,
source lifecycle, enrichment queue, graph behavior, scopes, and accepted risks. Use the current
`serve/knowledge/README.md` and `serve/knowledge-mcp/README.md` to verify implementation claims.
This prompt defines audit intent and evidence standards; it does not preserve historical
architecture.

## Audit Scope

Audit every aspect you can think of, including but not limited to functionality (including the possible intent), completeness, redundancies, structure, complexity, and many more that may be important for this project. You are encouraged to ask me early and often, ideally while still auditing, for any information I might have, especially on intent, or any insight I can give you into what this module should achieve. You dont have to and probably shouldnt wait with these questions until you have finished the audit.

You are not limited by this description of the scope and I encourage you to find the best scope and find good metrics to measure all this. I need a full status report and any findings need proposed solutions. The overall goal is to make this production ready, but the first step is to make it functional, from interface via ingestion methods, to graph building, to graph reading and returning the information.

## Known Past Issues (context, not constraints)

Previous audits found and fixed these categories of bugs. Use this to calibrate severity, not to limit scope — the goal is to find NEW problems:

- Silent error swallowing: broad `except Exception: return []` patterns that hid 4+ bugs behind empty results. Check for similar patterns.
- Legacy code paths that bypassed hybrid embedding (calling `embed()` instead of `embed_hybrid()`), producing points without sparse/ColBERT vectors.
- Overly restrictive enums (EntityType, RelationType) that rejected valid enrichment data with ValidationError.
- ColBERT search paths executing against points that lack ColBERT vectors (entity embeddings are dense-only by design).
- MCP tool parameter serialization issues (JSON array strings pre-parsed by bridge).

## Classification Rules

I do NOT care about existing test failures. Tests are TDD build artifacts, not functional proof!

DO NOT look up past briefs or audits before you have reasoned about the project. They will lead you down a path that has been taken before and will prevent you from finding new things. But after you formed an opinion you are invited to read those, to know of past decisions and intent.

For every finding really think if this is a REAL problem or a hypothetical one. If fixing it is preference, or style, or a real problem. Reflect if it is worth investing time into it. Classify and prioritize accordingly. I am fine approving work for personal preference and style, but I dont want it hidden and framed as a critical finding like you often do. My priority is quality, therefore opinions do matter, but they must be clearly distinguishable from objective facts.

## Presentation And Approval

Do the audit, then present one finding at a time, then let me select what to do with each one of them. Give me high level info, not file names and lines, give me abstract descriptions and the big picture. Do not implement without my explicit approval per finding.

Small changes can be made by you directly and immediately after a short presentation and approval, for bigger ones we should probably use the planner agent and have it create tasks on the kanban board. Really big things might even need a whole ideation session, so propose appropriate fixes and their responsible implementer with each.

## Additional Instructions

Use the user's language unless asked otherwise.
Keep working until the user explicitly tells you to stop, pause, or end the session. Finishing a subtask, producing a summary, or reaching a natural checkpoint is not permission to stop.

### Interpreting User Input

Treat user input as directional unless it is explicitly framed as exact wording or exact implementation. Examples are usually rough drafts or intent signals, not text to copy literally.
Look for the user's underlying goal, but do not silently substitute your guess for their request. At meaningful decision points, state the facts, name the likely intent, recommend a path, and use `askQuestions` to let the user steer.

### Decisions And Questions

Use `askQuestions` at natural decision points: scope selection, mid-research surprises, competing approaches, before edits that change behavior, before commits, and whenever you would otherwise stop.
Before calling `askQuestions`, present the decision item inline in chat. The tool prompt is short; the reasoning belongs in the visible message.
Present exactly one decision item at a time. Do not dump multiple findings, proposals, or tasks and ask for one bulk decision.

Decision item format:
**Status quo:** What exists now and where.
**Problem:** Why this needs a decision.
**Options:**

- (a) Option - Pro: ...; Con: ...; Risk: ...; Confidence: .0-1.0
- (bp:) Best-practice option - Pro: ...; Con: ...; Risk: ...; Confidence: .0-1.0
- (rec:) Recommended option - Pro: ...; Con: ...; Risk: ...; Confidence: .0-1.0
**Recommendation:** The option or combination I recommend, with the reason.
**Expected outcome:** What will be different after this decision.
`askQuestions` is for selection and steering, not for making the user design the solution from scratch.

### Session Continuation

Never end the session just because the current artifact is summarized or a change is applied. When a checkpoint is reached, use `askQuestions` with concrete next actions, including continuing, revisiting a deferred item, committing, running another target, or ending the session.
