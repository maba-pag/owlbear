---
id: 528
title: Consolidate triple-nested exception swallowing in agent._record_usage
status: backlog
priority: nice-to-have
created: 2026-03-04T07:38:34.6885367+01:00
updated: 2026-03-07T00:19:00.3839584+01:00
started: 2026-03-07T00:16:21.1426018+01:00
tags:
    - audit
    - code-quality
    - scope:core
class: standard
---

F-06: Three successive except Exception blocks for usage retrieval, cost calculation, premium lookup. Configuration bugs invisible. Consolidate to single try/except, log at WARNING not DEBUG. AC: single exception handler, failures visible. See docs/code-quality-audit.md.

## Research (2026-03-07)

Research checklist items 1-3: N/A - trivial consolidation of 3 exception handlers.

### Analysis

The method has 3 try/except Exception blocks:
- **Outer** (L160-210): wraps result.usage(), record creation, tracker.append()
- **Inner-1** (L163-176): wraps calc_estimated_cost() - enrichment
- **Inner-2** (L179-189): wraps get_premium_requests() - enrichment

All three log at DEBUG, making config bugs invisible.

### Partial success behavior

The existing test test_cost_import_error_returns_none explicitly verifies that when cost calc raises, the record is still created with premium_requests=1.0. This is partial-success behavior that matters: core token counts (input_tokens, output_tokens, requests) are the most valuable telemetry and should never be lost because an enrichment lookup (cost table, premium multiplier) failed.

### Options

| Option | Handlers | Partial success | Test impact | Confidence |
|--------|----------|-----------------|-------------|------------|
| A: 3-to-2 (rec) | Outer + 1 inner enrichment block | Core record preserved; if cost fails premium also skipped | Update 1 test | .85 |
| B: 3-to-1 | Single handler | Lost - any enrichment failure kills entire record | Breaks test_cost_import_error_returns_none | .50 |
| C: Log-level only | Keep 3 handlers, DEBUG-to-WARNING | Fully preserved | No test changes | .90 |

### Recommendation (.85)

Option A: Merge inner-1 and inner-2 into a single enrichment try/except. Keep the outer handler for core usage flow. Change all logging from DEBUG to WARNING. This reduces 3-to-2 handlers while preserving the critical invariant that token counts are always recorded.

The original AC says 'single exception handler' but that would break partial-success semantics. Recommend AC refinement: 'at most 2 exception handlers (core + enrichment), failures logged at WARNING.'

### Implementation notes
- Move both lazy imports to top of enrichment block
- Default estimated_cost and premium to None before the block
- Single except Exception that logs at WARNING
- Update test_cost_import_error_returns_none to expect premium=None when cost raises
