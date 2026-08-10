# Brief: DR Script Replacement

**Type:** existing-feature/refactor | **Tier:** Shared | **Phases:** 3

## Summary

Replace the scribe agent with a deterministic `decisions.py` module in the kanban engine. Expose `create_dr` as an MCP tool. Add Cockpit resolve UI. Delete the scribe agent and all references.

## Problem

The scribe agent is a pure-mechanical LLM intermediary between pipeline agents and the `.owlbear/decisions/` filesystem. It adds cost, latency, and fragility to operations that are fully deterministic (create file, scan dir, classify response, move file, update task). Users currently resolve DRs by editing raw YAML frontmatter — a Cockpit UI would be faster and less error-prone.

## Solution

Engine-native DR lifecycle:
1. Agents call `create_dr` MCP tool (fire-and-forget, task auto-blocked)
2. Users resolve via Cockpit UI (primary) or file-edit fallback
3. `pick_tasks` sweeps resolved DRs as a fail-safe side-effect

## What Gets Deleted

- `share/agents/scribe.agent.md`
- `share/skills/w-decision-routing/SKILL.md`
- Orchestrator "dispatch scribe every cycle" pattern
- All agent/skill references to scribe

---

## Phase 1: Engine + Format + MCP Tool

### New Module: `serve/kanban/src/owlbear_kanban/decisions.py`

Standalone module. No dependency on `engine.py` internals beyond the public `Engine` protocol (block_task, unblock_task, append_body).

#### Simplified File Format

**Pending file** (``.owlbear/decisions/pending/{task_id}-{slug}.md``):

```yaml
---
task_id: "1234"
agent: "builder"
request_type: "decision"
created: "2026-04-30T14:30:00+02:00"
response: "pending"
---

# {Human-readable title derived from slug}

{Agent-provided markdown body: context, options, question}
```

**Resolved file** (moved to `resolved/` after processing):

Same file, with `response` changed from `pending` to one of the closed enum values, and optional user notes appended below a `## Response` heading.

#### Frontmatter Fields (5 total)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| task_id | string | yes | Kanban task ID that gets blocked |
| agent | string | yes | Originating agent name |
| request_type | string | yes | `decision` or `action` |
| created | ISO 8601 datetime+tz | yes | Full timestamp |
| response | closed enum | yes | `pending`, `approved`, `rejected`, `needs-info` |

**Reader contract:** ignore unknown frontmatter keys (forward-compatible with old files that have extra fields like `urgency`, `decision_type`, etc.).

#### Response Enum (Closed)

| Value | Meaning | Resolve Action |
|-------|---------|----------------|
| `pending` | Awaiting user response | Skip (not resolved) |
| `approved` | User approved | Unblock task, append to body, move to resolved/ |
| `rejected` | User rejected | Unblock task, append to body, move to resolved/ |
| `needs-info` | User needs clarification | Keep blocked, append to body, move to resolved/ |
| *unknown* | Unrecognized value | Leave in pending, log warning |

#### Functions

**`create_dr(task_id, agent, request_type, body) → Path`**

1. Generate slug from first ~40 chars of body (slugified)
2. Write file to `pending/{task_id}-{slug}.md` using `open(path, 'x')` (O_EXCL for atomic creation)
3. Block the task via engine (set block reason to generic "DR pending")
4. If blocking fails (task doesn't exist, already archived, etc.), delete the file and raise
5. Return the created file path

**`resolve_pending_drs(engine) → list[ResolvedDR]`**

1. Glob `pending/*.md`
2. For each file: read frontmatter, check `response` field
3. If `response` is `pending` → skip
4. If `response` is unknown value → log warning, skip
5. If `response` is a valid terminal value:
   - Append `## DR Resolved: {slug}\n\n**Response:** {response}\n\n{user notes from ## Response section, if any}` to task body
   - Unblock task (if response is `approved` or `rejected`; `needs-info` keeps block)
   - Move file to `resolved/`
6. Fail-safe: catch all exceptions per-file, log, continue. Never stall the caller.

### MCP Tool: `create_dr`

Added to `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` using the standard `@mcp.tool()` pattern.

**Parameters:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| task_id | string | yes | Task to block |
| agent | string | yes | Calling agent name |
| request_type | string | yes | `decision` or `action` |
| body | string | yes | Markdown body (context, options, question) |

**Response:** `{created: true, path: "relative/path/to/file.md"}`

**Error cases:** task not found → error response. File collision → append counter suffix.

### pick_tasks Integration

At the top of `pick_tasks` (before task selection logic), call `resolve_pending_drs(engine)`. Wrapped in try/except — resolve failures must never stall task dispatch.

### Guidance Text Update

In `serve/mcp-kanban/src/owlbear_mcp_kanban/guidance.py`, change:
```
"⚠️ ACTION REQUIRED: Create a Decision Request for this block via the scribe agent"
```
to:
```
"⚠️ ACTION REQUIRED: Create a Decision Request via the create_dr tool"
```

---

## Phase 2: Agent/Skill Reference Updates

### New Skill: `share/skills/h-decision-requests/SKILL.md`

Short handbook skill (target: ~50 lines) that tells agents:
- When to create a DR (blocked on user decision, need clarification, scope question)
- How: call `create_dr(task_id, agent, request_type, body)`
- Body format: provide context, list options if applicable, state the question clearly
- Fire-and-forget: task is auto-blocked, no follow-up needed
- Resolution comes via user responding (Cockpit or file-edit), picked up on next `pick_tasks`

### Agent Files to Update

All agents that currently reference scribe or `w-decision-routing`:
- `share/agents/researcher.agent.md`
- `share/agents/test-writer.agent.md`
- `share/agents/builder.agent.md`
- `share/agents/doc-writer.agent.md`
- `share/agents/reviewer.agent.md`
- `share/agents/auditor.agent.md`
- `share/agents/orchestrator.agent.md`

Change: remove scribe from `agents:` list, replace DR instructions with reference to `h-decision-requests` skill.

### Skills/Instructions to Update

- `share/skills/r-pipeline-protocol/SKILL.md` — replace all scribe references with `create_dr` tool usage
- `share/instructions/pipeline-agents.instructions.md` — if it references scribe
- `share/skills/w-orchestration/SKILL.md` — remove "dispatch scribe" from cycle

### Docs to Update

- `.owlbear/decisions/README.md` — rewrite for new format, remove scribe references, document Cockpit as primary resolve path and file-edit as fallback

### Deletions

- `share/agents/scribe.agent.md`
- `share/skills/w-decision-routing/SKILL.md`

---

## Phase 3: Cockpit DR UI

### Backend API

Two new endpoints in `serve/cockpit/src/owlbear_cockpit/routes/`:

**`GET /api/decisions/pending`**

Returns list of pending DRs with frontmatter fields + truncated body preview. Used by status bar indicator and popover list.

```json
{
  "count": 2,
  "items": [
    {
      "id": "1234-scope-question",
      "task_id": "1234",
      "agent": "builder",
      "request_type": "decision",
      "created": "2026-04-30T14:30:00+02:00",
      "title": "Scope question",
      "body_preview": "First 200 chars..."
    }
  ]
}
```

**`POST /api/decisions/{id}/resolve`**

Resolves a pending DR. Body:

```json
{
  "response": "approved",
  "notes": "Optional user notes markdown"
}
```

Action: update the file's `response` frontmatter, append `## Response\n\n{notes}` to body, save. Resolution (unblock + move + task body append) happens on next `pick_tasks` sweep.

### Frontend Components

**Status bar indicator:**
- Always-visible in Shell status bar (alongside existing HealthBadge)
- Shows count of pending DRs
- Single attention color when count > 0, dormant when 0
- Click opens popover list
- Polling interval: implementation decides (60s is fine)

**Popover list:**
- Shows all pending DRs: title, agent, task_id, age
- Click on item opens resolve modal

**Resolve modal:**
- Shows full DR body (rendered markdown)
- Response selector: approved / rejected / needs-info
- Optional notes textarea
- Submit calls `POST /api/decisions/{id}/resolve`

### Pattern Alignment

- Follows existing HealthBadge pattern for status bar integration
- Uses existing DI pattern (`get_engine`) for backend
- Polling uses same hook pattern as `useBoard.ts`

---

## Acceptance Criteria

### P1
- [ ] `decisions.py` module exists with `create_dr` and `resolve_pending_drs` functions
- [ ] `create_dr` MCP tool callable by agents, creates file, blocks task
- [ ] File created with simplified 5-field frontmatter
- [ ] `pick_tasks` resolves pending DRs with non-pending response values
- [ ] Unknown response values logged and left pending
- [ ] Resolve appends decision summary to task body
- [ ] Resolve unblocks task (for approved/rejected) or keeps blocked (needs-info)
- [ ] Resolve failures don't stall `pick_tasks`
- [ ] Guidance text updated to reference `create_dr` tool
- [ ] `create_dr` rolls back file if task blocking fails

### P2
- [ ] `scribe.agent.md` deleted
- [ ] `w-decision-routing/SKILL.md` deleted
- [ ] New `h-decision-requests/SKILL.md` exists (~50 lines)
- [ ] All 7 agent files updated (scribe removed, new skill referenced)
- [ ] `r-pipeline-protocol` updated (scribe → create_dr)
- [ ] `w-orchestration` updated (no scribe dispatch)
- [ ] `.owlbear/decisions/README.md` rewritten

### P3
- [ ] `GET /api/decisions/pending` returns pending DRs
- [ ] `POST /api/decisions/{id}/resolve` updates file
- [ ] Status bar indicator visible, shows count, dormant at zero
- [ ] Popover list shows pending DRs
- [ ] Resolve modal allows response selection + notes
- [ ] Existing resolved files (37) remain readable (reader ignores unknown keys)

---

## Migration

- **Existing 37 resolved files:** Leave as-is. Reader ignores unknown keys. No reformatting needed.
- **Pending dir:** Currently empty. No migration needed.
- **Old format files created after P1 ships:** Not possible — only the engine creates files after P1.
- **`.owlbear/decisions/README.md`:** Rewritten in P2 to document new format and workflow.

## Non-Goals

- No `query_drs` MCP tool (agents read files if needed)
- No `resolve_drs` MCP tool (handled by pick_tasks)
- No concurrency mitigation (acceptable risk)
- No draft/stale-state protection in Cockpit
- No DR creation from Cockpit (agent-only)
- No semantic duplicate detection
