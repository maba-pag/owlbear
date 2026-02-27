---
id: 98
title: Test Edge Stable --load-extension sideloading flag
status: todo
priority: low
created: 2026-02-27T03:15:10.3521445+01:00
updated: 2026-02-27T03:47:13.5237302+01:00
started: 2026-02-27T03:32:44.4664477+01:00
tags:
    - phase-6
    - browser
    - research
class: standard
---

Research spike: test whether --load-extension and --disable-extensions-except flags work on current Edge Stable (Windows). Playwright docs claim Chrome/Edge removed these flags, but this may have changed.

See docs/cdp-tab-groups-research.md section 3.3 for context.

## Scope
- Manual testing only — no production code changes
- Results documented in research doc update
- This is a SPIKE: deliverable is knowledge, not code

## Approach
1. Create a minimal MV3 hello-world extension (manifest.json + background.js)
2. Launch Edge Stable with --load-extension pointing to it
3. Verify if extension loads (check chrome://extensions)
4. If blocked, repeat on Edge Dev and/or Canary channels

AC:
- [ ] Minimal MV3 test extension created in docs/scratch/ (ephemeral, deleted after spike)
- [ ] Edge Stable tested with --load-extension flag — result documented (works / blocked / error message)
- [ ] If blocked on Stable: Edge Dev or Canary tested as fallback
- [ ] If policy-based sideloading exists, document the mechanism
- [ ] docs/cdp-tab-groups-research.md updated with findings (new subsection under 3.3)
- [ ] Findings summarized as go/no-go for future extension-based tab grouping
