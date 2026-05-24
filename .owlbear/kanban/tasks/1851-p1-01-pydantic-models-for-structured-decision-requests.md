---
id: 1851
title: 'P1-01: Pydantic models for structured decision requests'
status: todo
priority: needed
created: 2026-05-24T20:57:55.018006+02:00
updated: 2026-05-24T22:01:46.524378+02:00
tags:
  - phase-1
  - scope:kanban
  - model
parent: 1850
depends_on: []
ac:
  - RequestOption model validates option_id matching 
    ^[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$, label max 120 chars, confidence in [0.0, 
    1.0], rationale max 500 chars; invalid inputs raise ValidationError.
  - DecisionRequest model with kind='decision' requires options with 2-10 items 
    and rejects fewer than 2 or more than 10; ActionRequest model with 
    kind='action' rejects non-empty options; all four models (RequestOption, 
    Resolution, DecisionRequest, ActionRequest) use extra='forbid' and reject 
    unknown fields with ValidationError.
  - 'At-most-one recommended=true constraint: model raises ValidationError when two
    or more options have recommended=true.'
  - "Resolution model has three optional fields: selected_option_id (str|None), free_text
    (str|None), and resolved_at (str|None); all default to None; extra='forbid' rejects
    any additional fields."
  - 'DecisionRequest and ActionRequest share required fields: task_id (int), request_id
    (UUID4-format string), title (str, max 120 chars), summary (str), agent (str),
    created_at (ISO 8601 datetime string); and optional resolution (Resolution, defaults
    to all-None); non-UUID4 request_id, title exceeding 120 chars, or malformed created_at
    raises ValidationError.'
  - A discriminated union type Request (Annotated union on kind field) resolves 
    kind='decision' to DecisionRequest and kind='action' to ActionRequest; 
    invalid kind values raise ValidationError.
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
- `RequestOption`, `Resolution`, `DecisionRequest`, `ActionRequest` Pydantic models
- Kind-discriminated union type for request creation
- Field constraints per Brief data model table
- `extra="forbid"` on models
- `resolution` block with nullable fields (present but null in pending files)

**Out of scope:**
- File I/O, engine API functions (P1-02)
- MCP or Cockpit layers
- Storage format writing (handled by engine)

## Test scope
`serve/kanban/tests/`

[[2026-05-24T22:01:46+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Models only — no I/O, no engine logic |
| Interface clarity | PASS | AC defines all fields, types, constraints, and error paths |
| Dependency correctness | PASS | No dependencies; foundation task |
| Module layering | PASS | kanban package internal; no upward imports |
| TDD compliance | PASS | Test scope: serve/kanban/tests/ |
| KISS/YAGNI | PASS | Minimal model definitions per Brief spec |
| Premise challenge | PASS | Brief-driven; replaces unstructured prose DR system |
| Pattern consistency | PASS | Follows existing ConfigDict(extra=\"forbid\") on domain sub-models (PathsConfig, PipelineConfig, etc.) |
| Security surface | PASS | Pure in-memory validation, no system boundaries |
| Single domain | PASS | kanban domain only |

### AC Refinement Applied
- resolved_at fix: Moved from \"excluded from model\" to optional field in Resolution (str|None, default None). Required for parsing resolved files with extra=\"forbid\".
- created_at format: Added ISO 8601 format validation constraint (new model, no legacy precision concern).
- extra=\"forbid\" observable: Added explicit \"reject unknown fields with ValidationError\" failure path.
- Scope leakage removed: Eliminated serialization language from AC4 (belongs in P1-02).
- Field coverage added (AC5): Required fields with constraints for DecisionRequest/ActionRequest.
- Union type added (AC6): Discriminated union behavior is testable.

### Challenge Results
- Challenger: reconsider (confidence 0.33)
- Findings: (1) resolved_at schema contradiction, (2) created_at under-spec, (3) serialization scope leakage, (4) AC overload, (5) evidence mismatch
- Architect response: accepted findings 1-3, revised AC accordingly. Finding 4 (minor overload) accepted as risk but AC lines remain independently testable. Finding 5 (evidence mismatch) resolved by writing refined AC to task before approval.
- Challenger alternative angle on extra=\"allow\" for top-level objects: rebutted — Brief explicitly mandates extra=\"forbid\" as architectural invariant for the new DR system.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Test-writer: PROCEED

### Verdict: APPROVE (after REFINE)
### Action Taken: Refined AC from 4 to 6 lines addressing challenger findings, advanced to todo.
