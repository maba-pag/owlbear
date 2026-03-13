---
id: 760
title: Add cookie-persistence profiles to BrowserManager
status: backlog
priority: someday
created: 2026-03-12T12:45:27.2480844+01:00
updated: 2026-03-12T12:45:27.2480844+01:00
tags:
    - browser
    - phase-4
class: standard
---

Pattern: save/restore cookies per named profile (~1KB each vs 100MB Chrome profiles). Inspired by botasaurus tiny_profile (see docs/research/botasaurus.md S4.6). AC:
- [ ] BrowserConfig gains optional profile_name field
- [ ] On context close, cookies saved to profiles/{name}.json
- [ ] On context open, cookies restored if profile exists
- [ ] Profile storage path configurable
