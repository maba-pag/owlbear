---
id: 634
title: Test context condenser (SummarizingCondenser)
status: archived
priority: needed
created: 2026-03-07T05:52:53.7725627+01:00
updated: 2026-03-07T18:08:27.8662405+01:00
started: 2026-03-07T06:07:51.0861003+01:00
completed: 2026-03-07T18:08:27.8662405+01:00
tags:
    - scope:core
    - test
    - agent
class: standard
---

Test-first task for #619. All tests in tests/test_condenser.py using PydanticAI TestModel.

AC:
- [ ] test_noop_below_threshold: __call__ returns original messages unchanged when len(messages) <= max_events
- [ ] test_condenses_above_threshold: when len(messages) > max_events, result = head + summary_request + tail; result length < input length
- [ ] test_keep_first_preserved: first keep_first messages always present in output unchanged (identity check)
- [ ] test_target_size_respected: output length == keep_first + 1 (summary) + tail_size where tail_size = target_size - keep_first - 1
- [ ] test_summary_metadata: the injected ModelRequest has metadata keys 'condensed_at' (ISO timestamp str) and 'forgotten_count' (int > 0)
- [ ] test_summary_content_prefix: the injected UserPromptPart.content starts with '[Condensed Context]\n'
- [ ] test_ends_with_model_request: output always ends with ModelRequest (PydanticAI invariant)
- [ ] test_boundary_alignment_tool_pair: when a ToolCallPart-bearing ModelResponse would be split from its ToolReturnPart-bearing ModelRequest, the boundary adjusts to keep the pair together (both in head or both in tail)
- [ ] test_model_none_uses_test_model: when model=None is passed, constructor stores None (bootstrap supplies the model)
- [ ] test_config_defaults: OwlBearSettings().condenser_enabled is False, .condenser_max_events is 120
- [ ] test_bootstrap_wires_condenser_when_enabled: with condenser_enabled=True, bootstrap passes a SummarizingCondenser in history_processors
- [ ] test_bootstrap_no_condenser_when_disabled: with condenser_enabled=False (default), bootstrap does not pass condenser

depends_on: none (test-first)
