---
id: 527
title: Restrict os.startfile to safe file types in CLI channel
status: ideation
priority: nice-to-have
created: 2026-03-04T07:38:34.010185+01:00
updated: 2026-03-04T07:38:34.010185+01:00
tags:
    - audit
    - security
    - scope:cli
class: standard
---

SEC-16: send_file() calls os.startfile(path) on Windows. If LLM controls path, could open executables or macro documents. Restrict to known-safe types (images, text) or require confirmation. AC: only safe file types opened automatically. See docs/security-audit.md.
