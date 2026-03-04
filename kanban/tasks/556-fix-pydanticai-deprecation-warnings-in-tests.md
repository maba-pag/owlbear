---
id: 556
title: Fix PydanticAI deprecation warnings in tests
status: ideation
priority: nice-to-have
created: 2026-03-04T07:38:58.5656888+01:00
updated: 2026-03-04T07:38:58.5656888+01:00
tags:
    - audit
    - test
class: standard
---

L3: 77 warnings about model name without provider prefix. Bootstrap tests pass MagicMock as model. Not failures but noisy. Fix model references. AC: zero deprecation warnings in test output. See docs/test-quality-audit.md.
