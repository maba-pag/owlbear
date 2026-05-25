---
id: 1853
title: 'P1-03: Engine API — resolve_request with conditional unblock'
status: todo
priority: needed
created: 2026-05-24T20:58:16.414102+02:00
updated: 2026-05-25T05:58:45.394071+02:00
tags:
  - phase-1
  - scope:kanban
  - api
parent: 1850
depends_on:
  - 1852
ac:
  - resolve_request(request_id, selected_option_id, free_text) populates 
    resolution fields (selected_option_id and free_text from args; resolved_at =
    current tz-aware ISO 8601); writes updated file to 
    decisions/resolved/{request_id}.md; deletes 
    decisions/pending/{request_id}.md; returns RequestRecord with 
    resolution.selected_option_id, resolution.free_text, and 
    resolution.resolved_at populated.
  - resolve_request raises NotFoundError(code="ERR_NOT_FOUND") when request_id 
    has no file in decisions/pending/; raises 
    ValidationError(code="ERR_ALREADY_RESOLVED") when the file exists only in 
    decisions/resolved/.
  - 'resolve_request validates selected_option_id: for decisions, non-None value must
    match an existing option_id (ValidationError otherwise); for actions, must be
    None (ValidationError otherwise). At least one of selected_option_id or free_text
    must be non-None (ValidationError when both None).'
  - 'resolve_request appends write-back to task body via edit_task append_body in
    four variants: (1) decision+option: "## DR: {title}\n- **Selected:** {label}";
    (2) decision+option+text: adds "\n- **Notes:** {free_text}"; (3) decision+text
    only: "## DR: {title}\n- **Answer:** {free_text}"; (4) action: "## AR: {title}\n-
    **Outcome:** {free_text}".'
  - resolve_request unblocks the task (edit_task blocked=False) only when zero 
    other structured request files (UUID4-named .md with matching task_id) 
    remain in decisions/pending/; leaves task blocked when sibling structured 
    requests still pending.
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1850 and `.owlbear/briefs/draft-decision-request-data-model/brief.md`

## Scope

**In scope:**
- `resolve_request` engine function
- Resolution validation (option_id cross-check)
- `resolved_at` timestamp insertion
- Atomic move from pending/ to resolved/
- Write-back summary append to task body (3 format variants)
- Conditional unblock logic (sibling pending check)

**Out of scope:**
- List/filter (P1-04)
- Sweep (P1-04)
- MCP/Cockpit layers

## Test scope
`serve/kanban/tests/`

[[2026-05-25T05:58:45+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single resolve operation with documented side effects (move, write-back, unblock) |
| Interface clarity | PASS | After refinement: inputs, outputs, error paths, validation rules all specified |
| Dependency correctness | PASS | #1852 archived/completed; create_request and get_request exist in engine.py |
| Module layering | PASS | kanban engine internal; no upward imports |
| TDD compliance | PASS | Test scope: serve/kanban/tests/ |
| KISS/YAGNI | PASS | Only resolve; list/sweep deferred to P1-04 per Brief sequence |
| Premise challenge | PASS | Brief-driven; replaces unstructured DR resolution system |
| Pattern consistency | PASS | Follows existing engine patterns (ValidationError/NotFoundError, edit_task, file I/O) |
| Security surface | PASS | request_id used for file lookup; validate_path_containment pattern already established in get_request |
| Single domain | PASS | kanban only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| resolve_request file read | File deleted between check and read | OSError | Propagates as NotFoundError | Clean failure |
| resolve_request write resolved | Disk full / permissions | OSError | Propagates | Resolution fails cleanly (pending file untouched) |
| resolve_request delete pending | Permission denied after resolved write | OSError | File exists in both dirs briefly | Idempotent on retry |
| resolve_request append_body | Task file not found / concurrent edit | FileNotFoundError | Should propagate (resolution is still valid) | Write-back missed but request resolved |
| resolve_request unblock | edit_task fails | Exception | Should propagate | Task stays blocked; request resolved |

### Design Notes
- File move is write-resolved-then-delete-pending (not atomic rename) because content changes (resolved_at added to frontmatter).
- If append_body or unblock fails AFTER file move, the resolution is still valid — these are secondary side effects. Builder should NOT rollback the file move on task-body failure.
- Timestamp: tz-aware ISO 8601 (matching create_request's created_at convention), not forced UTC.
- Error taxonomy: ERR_ALREADY_RESOLVED as ValidationError (invalid input at engine level) rather than ConcurrencyError (which the Cockpit layer may remap for its own contract in P1-06).
- Legacy coexistence: AC5 explicitly scopes sibling check to structured requests (UUID4-named files) only. Legacy DRs use {task_id}-{slug}.md naming. During Phase 1, if a task has both legacy DR and structured request, resolve_request won't count legacy files. This is acceptable because: (a) Phase 2 removes legacy system, (b) same task unlikely to have both types simultaneously since both systems block on creation.

### Challenge Results
- Challenger: reconsider (confidence 0.63)
- Findings: (1) task artifact mismatch — accepted, fixed by editing AC; (2) B3 \"all\" quantifier — accepted, replaced with explicit field list; (3) error taxonomy ERR_ALREADY_RESOLVED — rebutted: ValidationError is correct at engine level (invalid input, not concurrent race); (4) legacy coexistence — accepted in part, scoped AC5 to structured files with design note; (5) failure semantics — accepted, documented ordering and no-rollback-after-move design; (6) format determinism for multiline inputs — rebutted: title/label are already length-constrained by RequestOption model (max 120 chars), and free_text is caller-provided arbitrary content that append_body handles natively.
- Architect response: Accepted findings 1,2,4,5; rebutted 3,6. Refined AC from 4 to 5 lines.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Test-writer: PROCEED

### Verdict: APPROVE (after REFINE)
### Action Taken: Refined AC from 4 to 5 lines addressing return type, error paths, validation completeness, B3 quantifier, timestamp convention, and legacy coexistence scope. Advanced to todo.
