---
id: 1672
title: 'P3-02: Memory accordion detail and state-dependent actions'
status: todo
priority: important
created: 2026-05-18T17:44:11.043517+02:00
updated: 2026-05-19T22:00:22.997123+02:00
tags:
  - phase-3
  - scope:cockpit-web
  - frontend
parent: 1659
depends_on:
  - 1671
ac:
  - 'Row click expands inline PAccordion showing entry content rendered as sanitized
    markdown (rehype-sanitize custom schema allowing: p, br, ul, ol, li, strong, em,
    code, a with href restricted to http/https/mailto protocols; stripped elements:
    script, style, img, iframe; no dangerouslySetInnerHTML) plus all metadata fields
    (id, source_agent, scope_agents, categories, confidence, state, timestamps)'
  - "State-dependent action buttons within accordion: Approve visible for curated
    only (no confirmation needed), Edit visible for pending/curated/approved (inline
    warning for approved entries: 'Editing will require re-approval'), Delete visible
    for all non-deleted states (confirmation dialog with text distinguishing hard-delete
    for pending vs soft-delete for curated/approved)"
  - 'Inline edit form: editable title/categories/confidence/scope_agents/content with
    character counter (max 1024 for content); save sends POST /api/memories/{id}/edit
    with expected_updated_at from loaded entry; silent background refetch after mutation
    success (no loading indicator replaces the visible entry list); nav-rail badge
    shows pending memory entry count when >0 (hidden at zero, aria-label updates with
    count)'
  - "Error UX: 409 OCC conflict shows inline banner within the accordion ('Entry was
    modified — refreshing') and auto-refetches; 404 shows 'Entry no longer exists'
    and removes entry from local list; 422 shows field-level validation messages on
    the edit form parsed from FastAPI structured detail array ({detail: [{loc, msg}]})"
  - "Response-driven local update: on approve/edit success, replace the entry in the
    local entries array from the response payload entry field; on delete success,
    remove entry from local array (pending hard-delete) or update entry state to 'deleted'
    (curated/approved soft-delete) based on prior state; no list-level loading spinner
    during mutations (entries remain visible and interactive); on mutation failure,
    leave local state unchanged and display error per AC4"
  - "State promotion feedback: when the edit response returns state='curated' for
    a previously pending entry (auto-promotion triggered by scope_agents assignment),
    update the state badge immediately and show a brief inline note: 'Promoted to
    curated — scope agents assigned'"
proof_bundle: behavioral
blocked: false
block_reason: 'test-writer crashed twice: agent returned no output on both attempts'
claimed_at: 2026-05-19T22:00:22.997123+02:00
archival_reason:
archival_refs: []
---
Brief: see parent #1659 and `.owlbear/briefs/draft-cockpit-memory-tab/brief.md`

## Scope

Add interactive accordion detail and mutation actions to the Memory tab list.

### In Scope
- PAccordion expand on row click showing full entry detail
- Markdown content rendering with sanitization (rehype-sanitize)
- State-dependent action buttons: Approve, Edit, Delete
- Approve action: POST /api/memories/{id}/approve (curated only)
- Delete action: confirmation dialog, POST /api/memories/{id}/delete
- Edit form: inline within accordion, character counter, save/cancel
- Approved entry edit warning ("will require re-approval")
- Refetch list after every successful mutation
- Nav-rail pending count badge (visible when count > 0)
- OCC conflict handling (409 → user message to refetch)

### Out of Scope
- SSE/live updates (deferred)
- Bulk approve/delete (deferred)
- Memory creation from cockpit (deferred)
- Memory diff view (deferred)

## Technical Context
- Sanitization: rehype-sanitize or equivalent allowlist — strong, em, code, a (href validated)
- No `dangerouslySetInnerHTML`
- No remote image loading (strip img tags)
- PDS components: PAccordion, PButton, PModal (for delete confirmation), PTextarea

[[2026-05-19T20:40:14+02:00]]
## Research

Key findings documented in `.owlbear/research/memory-accordion-detail-actions.md`:

1. **PAccordion per entry** with conditional detail rendering (only render ReactMarkdown when open) — eliminates DOM weight concern
2. **Custom restrictive sanitize schema** (strong/em/code/a only; no img; href validated to http/https/mailto)
3. **Mutation asymmetry**: approve/edit return entry envelope → replace in array; delete returns `{success: true}` → remove/mark locally
4. **Structured 422 parsing**: New `parseValidationErrors()` helper needed (FastAPI returns `{detail: [{loc, msg}]}`) — current `getResponseErrorMessage` only reads string detail
5. **Nav badge state lifting**: Restore regressed decisions badge (commit a507483d was overwritten by path-normalization refactor); add `usePendingMemoryCount()` to CockpitProvider
6. **AC3+AC5 reconciliation**: Update local state from response payload immediately, then silent background refetch for consistency
7. **Edit form safety**: PAccordion `update` event fires only on summary click — form field clicks in content area do not collapse

Challenge: proceed (confidence 0.78). No additional follow-up tasks — task is well-scoped for TDD.

[[2026-05-19T20:50:25+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | All items contribute to one capability: interactive detail + mutations for memory entries |
| Interface clarity | PASS (after refinement) | Refined AC1 allowlist, AC3 silent-refetch, AC5 response-driven semantics, AC4 structured 422 |
| Dependency correctness | PASS | #1671 archived (completed); no missing deps |
| Module layering | PASS | Frontend-only extension of existing MemoryTab; no upward imports |
| TDD compliance | PASS | Proof bundle behavioral; test-writer will proceed |
| KISS/YAGNI | PASS | Scope matches parent Brief; no hypothetical features |
| Premise challenge | PASS | Custom UI feature for custom app; no existing capability covers this |
| Pattern consistency | PASS | Uses established PDS components (PAccordion, PModal, PButton); ReactMarkdown+rehypeSanitize pattern from TaskFieldsEditor; CockpitProvider state-lifting from usePendingDRs |
| Security surface | PASS | Custom restrictive sanitize schema; no dangerouslySetInnerHTML; href protocol validation; img stripped |
| Single domain | PASS | All in scope:cockpit-web frontend |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| approve/edit mutation | 409 OCC conflict | HTTP 409 | Yes (AC4) | Inline banner + auto-refetch |
| approve/edit mutation | 404 not found | HTTP 404 | Yes (AC4) | Entry removed from list |
| edit mutation | 422 validation | HTTP 422 | Yes (AC4) | Field-level messages on form |
| delete mutation | 409/404 | HTTP 409/404 | Yes (AC4) | Same as above |
| markdown render | Malformed content | N/A | Yes | ReactMarkdown renders gracefully |

### Design Diverge
- Trigger: skipped — research doc already evaluated 3 approaches (PAccordion vs details vs modal); PAccordion is the clear winner per AC and PDS convention.

### Challenge Results
- Challenger: reconsider (confidence 0.61)
- Findings: (1) AC1 allowlist missing structural tags; (2) AC3/AC5 refetch-spinner conflict; (3) AC5 optimistic-vs-response-driven misnomer; (4) delete semantics underspecified
- Architect response: ACCEPTED all four findings. Refined AC1 (added p/br/ul/ol/li, explicit strip list), AC3 (silent refetch clarification), AC5 (renamed to response-driven, explicit delete handling), AC4 (inline-within-accordion scope, structured 422 detail). Challenger's nav-badge a11y point addressed in AC3 (aria-label updates with count).

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE (after REFINE)
### Action Taken: Refined 4 of 6 AC lines for precision (allowlist completeness, refetch semantics, delete handling, error scope). Advanced to todo.

[[2026-05-19T21:02:55+02:00]]
test-writer crashed once; releasing claim before retry: agent completed with no output

[[2026-05-19T21:05:50+02:00]]
test-writer crashed twice: agent returned no output on both attempts
