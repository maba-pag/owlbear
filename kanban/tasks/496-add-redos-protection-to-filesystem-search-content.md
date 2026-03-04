---
id: 496
title: Add ReDoS protection to filesystem search content regex
status: ideation
priority: important
created: 2026-03-04T07:38:10.724342+01:00
updated: 2026-03-04T07:38:10.724342+01:00
tags:
    - audit
    - security
    - tools
class: standard
---

SEC-09: content_regex from LLM compiled via re.compile with no complexity guards. Catastrophic backtracking possible with patterns like (a+)+b. Wrap in try/except re.error, reject nested quantifiers, or use regex lib with timeout. AC: malformed/evil regex handled gracefully. See docs/security-audit.md.
