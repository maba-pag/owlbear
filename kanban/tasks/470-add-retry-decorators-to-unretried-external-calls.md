---
id: 470
title: Add retry decorators to unretried external calls
status: ideation
priority: needed
created: 2026-03-04T07:37:49.872598+01:00
updated: 2026-03-04T07:37:49.872598+01:00
tags:
    - audit
    - resilience
    - scope:core
class: standard
---

R-4: auth/copilot.py (3 HTTP calls), tools/github_api.py (4 endpoints), channels/slack.py (chat_postMessage), memory/knowledge/intake.py (read_url), tools/web_search.py (_web_read) all have zero retry on external calls. Wrap with tenacity retry (transient only, 3 attempts, exp backoff). AC: all external HTTP calls have retry. See docs/resilience-audit.md.
