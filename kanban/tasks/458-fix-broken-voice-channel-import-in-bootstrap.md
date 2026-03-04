---
id: 458
title: Fix broken voice channel import in bootstrap
status: ideation
priority: critical
created: 2026-03-04T07:37:38.3966046+01:00
updated: 2026-03-04T07:37:38.3966046+01:00
tags:
    - audit
    - bugfix
    - scope:core
class: standard
---

ARC-02/F-04(Config)/INT-01: create_channel() imports from owlbear.channels.voice but VoiceChannel lives at owlbear.voice.channel. ModuleNotFoundError at runtime. Fix import to correct path. Also decide whether to relocate VoiceChannel to channels/ (see ARC-03). AC: voice channel starts without ImportError. See docs/architecture-audit.md, docs/config-dependency-audit.md, docs/integration-audit.md.
