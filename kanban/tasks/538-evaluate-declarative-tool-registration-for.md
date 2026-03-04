---
id: 538
title: Evaluate declarative tool registration for toolsets
status: ideation
priority: nice-to-have
created: 2026-03-04T07:38:43.2377201+01:00
updated: 2026-03-04T07:38:43.2377201+01:00
tags:
    - audit
    - yagni
    - tools
class: standard
---

YAGNI-01: All 14 toolsets follow same ceremony: __init__ -> super().__init__() -> _register_tools() -> N x add_function(). Consider @tool decorator or tools: ClassVar pattern for auto-registration. Borderline YAGNI since PydanticAI doesnt offer declarative API. AC: decision documented, implemented if beneficial. See docs/software-design-audit.md.
