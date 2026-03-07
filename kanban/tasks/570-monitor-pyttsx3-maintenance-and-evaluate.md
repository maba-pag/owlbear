---
id: 570
title: Monitor pyttsx3 maintenance and evaluate alternatives
status: backlog
priority: someday
created: 2026-03-04T07:39:12.4680984+01:00
updated: 2026-03-07T04:35:05.8762972+01:00
started: 2026-03-07T04:34:56.9983949+01:00
tags:
    - audit
    - config
    - deps
class: standard
---

F-10: pyttsx3 maintenance risk. RESEARCH COMPLETE (2026-03-07).

Key finding: pyttsx3 is NOT dormant. Released v2.92-2.99 between Sep 2024 and Jul 2025.
Risk downgraded from Medium to Low. Config-dependency-audit updated.

Decision: Keep pyttsx3. When voice features are actively developed, consider adding edge-tts as optional online-quality fallback.

See docs/pyttsx3-tts-alternatives-research.md for full analysis.

AC: decision documented.
