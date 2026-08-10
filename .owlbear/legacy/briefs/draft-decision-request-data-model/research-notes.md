# Research Notes — Decision Request Data Model

## Verified Findings

### Current Storage Format

- YAML frontmatter with 5-7 fields: `task_id`, `agent`, `request_type`, `created` (date-only), `response`, optional `resolved`/`resolved_by`
- Filename convention: `{task_id}-{slugified-request-type}.md` with collision suffix `-2`, `-3`
- Directories: `decisions/pending/` and `decisions/resolved/`
- Body: unstructured markdown prose — no enforced shape

### Current Engine (`decisions.py`)

- `create_dr()`: atomic file creation via `O_EXCL`, blocks task with `blocked=True, block_reason="DR pending"`, returns path
- `resolve_pending_drs()`: sweeps pending dir, moves resolved files, appends `canonical_summary()` to task body, unblocks task for approved/rejected
- `parse_dr()`: returns `(meta_dict, body_str)` — callers work with raw dicts, no Pydantic model
- ID generation: filename stem IS the ID (e.g., `1558-decision`)
- Collision handling: suffix numbering in filename

### Current MCP Layer

- Single tool: `create_dr(task_id, agent, request_type, body)`
- Validation: `request_type ∈ {decision, action}` only
- No read/resolve tools — resolution happens exclusively through Cockpit API
- Returns `{created: true, path: "decisions/pending/{id}.md"}`

### Current Cockpit API

- `GET /api/decisions/pending` — lists all pending DRs with title extracted from body
- `POST /api/decisions/{id}/resolve` — resolves with `response ∈ {approved, needs-info, rejected}` + optional `notes`
- Resolution flow: rewrite frontmatter → append Response section to body → append summary to task → unblock → move to resolved/
- Error handling: ConcurrencyError for stale, HTTP 404 for missing, HTTP 422 for malformed
- Title extraction: first heading or first sentence of body, regex-cleaned, max 88 chars

### Current Frontend

- `DecisionsPage.tsx` — full-page sorted list, extracts options/context/recommendation from structured markdown patterns
- `ResolveModal.tsx` — radio buttons for approved/needs-info/rejected + notes textarea
- `usePendingDRs` hook — polls every 60s, also refreshes on SSE `decisions-changed`
- Type: `PendingDR {id, task_id, agent, request_type, created, title, body, body_preview}`

### ID Generation Precedent (Memory Engine)

- Memory entries use `str(uuid4())` — plain UUID4 string
- No prefix, no timestamp embedding, no human-readable component

### Resolution Sweep Pattern

- `resolve_pending_drs()` is a batch sweep — not event-driven
- Cockpit's `POST /resolve` endpoint does inline resolution (rewrite + move + unblock in one request)
- Two resolution paths exist: sweep-based (engine) and inline (Cockpit API)

## Candidate Implications

### Model Design

- The new model likely needs: `request_id` (UUID4), `task_id`, `kind` (decision|action), `title`, `summary`, `options[]` (optional, for decisions), `created_at` (ISO 8601 with timezone), `agent`, `resolution{}` — as structured YAML frontmatter.
- `options[].option_id` + `label` + `recommended` + `confidence` + `rationale` — structured per D3 decisions.
- Resolution payload: `status`, `selected_option_id` (nullable), `free_text` (nullable), `resolved_by`, `resolved_at` — all in frontmatter.
- Body markdown remains for extended context that doesn't fit structured fields.

### Engine API

- Core operations: `create_request()`, `resolve_request()`, `list_requests()`, `get_request()` — three main + one convenience.
- Pydantic models for validation (currently the engine uses raw dicts — this is a quality uplift).
- The sweep pattern (`resolve_pending_drs`) may become obsolete if all resolution goes through the Cockpit API or a new MCP `resolve_request` tool. But it's also the "manual edit" escape hatch.

### MCP Interface

- Replace `create_dr` with `create_request` — richer structured input (title, summary, options, kind).
- Add `list_requests` and `show_request` for agents to consume resolved answers.
- Consider `resolve_request` MCP tool — allows agent-to-agent resolution without Cockpit.

### Cockpit API

- `PendingDRItem` model expands with structured fields (kind, options, summary, resolution).
- `ResolveRequest` model needs to support option selection, free text, and action result responses — not just approve/reject/needs-info.
- Title extraction logic becomes trivial (read `title` field directly).

### Frontend

- `ResolveModal` transforms from radio-buttons-only to adapted controls: option cards when options exist, free-text when appropriate, done/blocked for actions.
- `DecisionsPage` renders structured data directly instead of extracting from body.
- Type definitions expand significantly.

### Filename vs UUID

- Current: filename = ID. New: UUID4 = ID, filename = `{request_id}.md` or `{task_id}-{request_id_short}.md`.
- If filename = full UUID, human readability in `ls` is worse but lookup is trivial.
- If filename = `{task_id}-{slug}.md` (current pattern) with UUID inside frontmatter, the ID is not filesystem-addressable without scanning.
- Simplest: filename = `{request_id}.md` where request_id is UUID4. Engine provides lookup.

## Open Research Questions

1. **Sweep vs. inline resolution:** Should `resolve_pending_drs()` (batch sweep) be kept as a compatibility path for manual file edits, or fully replaced by inline resolution via API/MCP? The sweep enables "edit the file in vim and it resolves on next tick" which aligns with clone=install philosophy.

2. **Action request resolution states:** For `kind=action`, what are the valid resolution states? Candidates: done-success, done-failed, rejected, unable-to-execute. What structured fields should the resolution carry for actions vs decisions?

3. **MCP resolve tool:** Should agents be able to resolve requests (e.g., agent-to-agent handoff), or is resolution always a human action? If agents can resolve, the system becomes a general inter-agent communication mechanism.

4. **Engine model location:** Should the Pydantic models live in `owlbear_kanban.decisions` (current module) or a new module? The current module is ~210 lines. Adding models, validation, and new operations could make it large.

5. **Cockpit error envelope:** The decisions route currently uses FastAPI's `{detail: "..."}` format, not the domain `{code, message}` envelope used elsewhere. Should the new routes align with the domain envelope?

6. **SSE event granularity:** Currently one event type `decisions-changed`. With structured data, should there be `decision-created`, `decision-resolved` events for finer-grained UI updates?

7. **Option ID stability:** If agents provide `option_id` values, what format/validation should apply? Slug-safe strings? UUIDs? The input doc uses human-readable slugs like `mcp-tools`, `hybrid`.
