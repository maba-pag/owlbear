# Skill Docs Update — guidance Field and block:user Tag

> **Owning task:** #988 — Update skill docs for guidance field and `block:user` tag
> **Date:** 2026-04-18 **Status:** Complete

## 1. Context and Question

Parent #973 introduces a `guidance` field on MCP tool responses and a `block:user` tag for Cockpit-initiated blocks. Decision D9 mandates three skill doc updates. This research identifies the exact insertion points and content for each file, gated on implementation completion.

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | `.owlbear/briefs/draft-blocked-task-dr-enforcement/decisions.md` (D1–D9) | Internal | .95 — locked design decisions |
| S2 | `share/skills/h-mcp-kanban/SKILL.md` | Internal | .95 — target doc, current state |
| S3 | `share/skills/r-pipeline-protocol/SKILL.md` §5 Escalation | Internal | .95 — target doc, blocking convention |
| S4 | `share/skills/w-decision-routing/SKILL.md` | Internal | .90 — target doc, entry points |
| S5 | `.owlbear/research/block-time-guidance-mcp-973.md` | Internal | .85 — parent task research |
| S6 | Parent #973 body (architect review, Brief) | Internal | .90 — implementation spec |

## 3. Analysis — Insertion Plan per File

### 3.1 `h-mcp-kanban/SKILL.md`

| Location | Change | Rationale |
|----------|--------|-----------|
| After "## Tool Summary" table | Add "## Response: Guidance Field" section | New concept; agents need to understand the field before tool-specific details |

Content to add (draft, finalise after implementation):

- `guidance: list[str]` — advisory messages returned on `KanbanTask` responses.
- First declared field → first in JSON output (Pydantic v2 declaration-order serialization).
- Empty list `[]` when no guidance applies. Non-empty for: block operations (DR-required), forward-skip moves, success outcomes (commit-pushed).
- Guidance is advisory, not enforced. Agents should read and act on guidance messages.
- Reference: agents blocking a task should follow the DR workflow in `w-decision-routing`.

### 3.2 `r-pipeline-protocol/SKILL.md`

| Location | Change | Rationale |
|----------|--------|-----------|
| §5 "Blocking Convention", after existing paragraphs | Add DR-required rule and `block:user` exemption | Strengthens existing convention with explicit rule and exception |

Content to add:

- **Explicit rule:** Every agent-initiated block MUST be paired with a Decision Request (via scribe). The MCP tool response includes guidance reminding agents of this requirement.
- **`block:user` exemption:** Tasks tagged `block:user` were blocked by a human via Cockpit. Agents reading such tasks skip DR creation — the block is user-driven. The tag is auto-managed: Cockpit adds it on block, removes on unblock; MCP block operations remove it (agent re-blocking takes ownership).

### 3.3 `w-decision-routing/SKILL.md`

| Location | Change | Rationale |
|----------|--------|-----------|
| Top of "## When to Create a Decision Request" section | Add one-paragraph entry-point note | Agents arriving via block-guidance need to know they're in the right place |

Content to add:

- **Block-time guidance entry point:** When an MCP tool response includes guidance directing you to create a Decision Request (after blocking a task), follow the `check-or-create` mode below. The guidance message confirms the convention — this workflow is the authoritative procedure.

### 3.4 Dependency Analysis

Task #988 body says "Depends on: all implementation tasks complete" but `depends_on` field is empty. Per architect review, #988 depends on #985, #989, #991 (the three MCP integration tasks). These must complete before #988 so doc content references final field names and message text.

## 4. Recommendation

Proceed with the three-file insertion plan above (confidence: .90). Drafts are ready; final wording requires implementation tasks to land so exact message text and field behavior can be verified.

Challenge: SKIPPED — trivial docs-only task with all decisions locked in Brief.

## 5. Follow-up Tasks

None. #988 is a leaf task — it IS the implementation. Wire `depends_on: [985, 989, 991]` so the pipeline blocks until integration tasks complete.
