---
id: 556
title: Fix PydanticAI deprecation warnings in tests
status: backlog
priority: nice-to-have
created: 2026-03-04T07:38:58.5656888+01:00
updated: 2026-03-07T02:18:49.5387298+01:00
started: 2026-03-07T01:05:39.6945136+01:00
tags:
    - audit
    - test
class: standard
---

L3: 77 warnings about model name without provider prefix. Bootstrap tests pass MagicMock as model. Not failures but noisy. Fix model references. AC: zero deprecation warnings in test output. See docs/test-quality-audit.md.

## Research (2026-03-07)

See docs/research/pydanticai-deprecation-warnings.md for full analysis.

**Root cause:** PydanticAI v0.8.1 deprecated bare model names in infer_model(). 77 warnings from 2 categories: 43 bare 'gpt-4o' string (build_toolsets fallback to settings.chat_model) + 34 MagicMock (bootstrap tests pass MagicMock without spec=Model).

**Fix (test-only, zero source changes):**
1. Change MagicMock() to MagicMock(spec=Model) in 17 bootstrap integration tests
2. Pass chat_model='test' to build_toolsets() in ~28 test calls + 1 expansion test
3. Verify with: uv run pytest -W error::DeprecationWarning

Related: #551 (remove hardcoded gpt-4o defaults from source  separate task).
