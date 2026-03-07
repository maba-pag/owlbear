---
id: 547
title: Add validators for numeric config fields
status: backlog
priority: nice-to-have
created: 2026-03-04T07:38:50.6863315+01:00
updated: 2026-03-07T00:54:58.7115615+01:00
started: 2026-03-07T00:49:53.9397044+01:00
tags:
    - audit
    - config
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
