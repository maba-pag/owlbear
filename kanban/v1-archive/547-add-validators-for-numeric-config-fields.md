---
id: 547
title: Add validators for numeric config fields
status: archived
priority: nice-to-have
created: 2026-03-04T07:38:50.6863315+01:00
updated: 2026-03-22T19:17:40.7477841+01:00
started: 2026-03-07T00:49:53.9397044+01:00
completed: 2026-03-22T19:17:40.7477841+01:00
tags:
    - audit
    - config
blocked: true
block_reason: 'Superseded by archived #840; src/owlbear/config.py and tests/test_config.py already implement the numeric validator contract'
class: standard
---

F-14: temporal_decay_rate, temporal_recency_weight, embedding_idle_timeout, approval_timeout have no validators. Negative or zero values cause subtle bugs. See docs/config-dependency-audit.md.

## Research (N/A - trivial Pydantic field validators)

1. **Theoretical validity** - N/A, trivial change. Standard Pydantic v2 field constraints.
2. **Prior art** - N/A, Pydantic v2 Field(gt=0, ge=0, le=1) is the documented approach.
3. **Technical feasibility** - N/A, Pydantic already imported and used in config.py.
4. **Architecture fit** - N/A, purely additive constraints on existing fields.
5. **Implementation approach** - Add Field() numeric constraints:

| Field | Constraint | Rationale |
|---|---|---|
| temporal_decay_rate | ge=0, le=1 | Formula (1-rate*(1-imp))^hours -- rate>1 makes base negative; <0 grows exponentially |
| temporal_recency_weight | ge=0, le=1 | Weight in score+weight*recency -- negative inverts; >1 overwhelms similarity |
| embedding_idle_timeout | ge=0 | 0 disables timer (code guards <=0); negative semantically wrong |
| approval_timeout | gt=0 | Fed to asyncio.wait_for -- negative raises ValueError; zero instant timeout |

Use Field(gt=0) / Field(ge=0, le=1) directly on definitions -- more concise than @field_validator, equally clear errors.

AC: invalid values rejected at config load (Pydantic ValidationError on constraint violation).

[[2026-03-21]] Sat 03:54
## Architecture Review
**Verdict:** BLOCK

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| temporal_decay_rate ge=0, le=1 | Already implemented in src/owlbear/config.py with ge=0.0, le=1.0 and covered by TestFromAC_TemporalDecayRateValidator in tests/test_config.py. | Mark superseded by #840 |
| temporal_recency_weight ge=0, le=1 | Already implemented in src/owlbear/config.py with ge=0.0, le=1.0 and covered by TestFromAC_TemporalRecencyWeightValidator in tests/test_config.py. | Mark superseded by #840 |
| embedding_idle_timeout ge=0 | Already implemented in src/owlbear/config.py and covered by TestFromAC_EmbeddingIdleTimeoutValidator in tests/test_config.py. | Mark superseded by #840 |
| approval_timeout gt=0 | Already implemented in src/owlbear/config.py with gt=0.0 and covered by TestFromAC_ApprovalTimeoutValidator in tests/test_config.py. | Mark superseded by #840 |
| Invalid values rejected at config load (ValidationError) | Already satisfied by tests/test_config.py and archived task #840 review evidence; moving #547 to todo would duplicate completed work. | Block as stale duplicate |

### Architecture Notes
- Verified current source already contains the four Field constraints in src/owlbear/config.py.
- Verified tests/test_config.py contains the exact validator coverage for all four fields, including default acceptance and invalid-value rejection.
- Verified archived task #840 is explicitly the preceding test task for #547 and already records RED, GREEN, and review evidence for this work.
- The research note in #547 is stale relative to the current workspace state. Approving this task to todo would create duplicate implementation work for an already-shipped contract.
- Single domain remains config, but #547 is no longer an executable builder handoff.

### Changes Made
- Claimed #547 as architect-gpt54-547
- Appended this architecture review
- Moved #547 from backlog to ideation with an explicit stale-duplicate block reason

### Dependencies
- Verified: #840 archived as the completed RED/GREEN path for this contract
- Verified current workspace evidence in src/owlbear/config.py and tests/test_config.py
- No new TDD or builder follow-up is required from #547
