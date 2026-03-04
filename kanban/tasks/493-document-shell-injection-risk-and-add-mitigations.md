---
id: 493
title: Document shell injection risk and add mitigations
status: ideation
priority: important
created: 2026-03-04T07:38:08.5010961+01:00
updated: 2026-03-04T07:38:08.5010961+01:00
tags:
    - audit
    - security
    - tools
class: standard
---

SEC-01: TerminalToolset passes LLM commands to create_subprocess_shell. CommandSafetyGuard regex is bypassable (double spaces, base64, alt tools). Inherent design tension. Document limitation, consider allowlist mode for production, add to approval policy (see SEC-05 task). AC: risk documented, additional mitigations evaluated. See docs/security-audit.md.
