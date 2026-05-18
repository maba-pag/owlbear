---
id: 1672
title: 'P3-02: Memory accordion detail and state-dependent actions'
status: research
priority: important
created: 2026-05-18T17:44:11.043517+02:00
updated: 2026-05-18T18:24:23.615705+02:00
tags:
  - phase-3
  - scope:cockpit-web
  - frontend
parent: 1659
depends_on:
  - 1671
ac:
  - 'Row click expands inline PAccordion showing entry content rendered as sanitized
    markdown (rehype-sanitize allowlist: strong, em, code, a with href validation;
    no dangerouslySetInnerHTML, no remote images) plus all metadata fields (id, source_agent,
    scope_agents, categories, confidence, state, timestamps)'
  - "State-dependent action buttons within accordion: Approve visible for curated
    (no confirmation), Edit visible for pending/curated/approved (inline warning for
    approved: 'will require re-approval'), Delete visible for all non-deleted (confirmation
    dialog distinguishing hard-delete for pending vs soft-delete for curated/approved)"
  - 'Inline edit form: editable title/categories/confidence/scope_agents/content with
    character counter (max 1024); save sends POST /api/memories/{id}/edit with expected_updated_at
    from loaded entry; list refetches on mutation success; nav-rail badge shows pending
    entry count when >0'
  - 'Error UX: 409 OCC conflict shows inline toast/banner ("Entry was modified — refreshing")
    and auto-refetches; 404 shows "Entry no longer exists" and removes from list;
    422 shows field-level validation messages on the edit form'
  - 'Optimistic update: successful mutations update local state immediately from the
    response payload (no loading spinner on the list); failed mutations revert and
    show the error'
  - 'State promotion feedback: when editing a pending entry causes auto-promotion
    to curated (scope_agents added), the state badge updates immediately and a brief
    inline note explains the promotion ("Promoted to curated — scope agents assigned")'
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
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