---
id: 1510
title: 'Cockpit: Sync PDS local assets in public/ with npm package version'
status: research
priority: important
created: 2026-05-12T09:09:32.883043+00:00
updated: 2026-05-12T09:09:45.945618+00:00
tags:
  - cockpit
  - frontend
  - bug
parent: 1495
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Problem\n\nThe PDS npm package is at v4.1.0 but `public/porsche-design-system/components/` contains v4.0.0 core chunk. Additionally `public/porsche-design-system/icons/` has only 1 icon file when more are needed (e.g. `close.eec3c5d.svg` is missing). This causes:\n\n1. **404s** for the core chunk (version mismatch between loader and local assets)\n2. **CDN CSP violations** for icon assets that fall back to CDN fetch when not found locally\n\n## Acceptance Criteria\n\n- [ ] Research how PDS assets are structured in `node_modules/@porsche-design-system/` and what files must be copied to `public/`\n- [ ] Identify the complete set of required icon SVGs beyond what is currently present\n- [ ] Determine whether a build script (npm `postinstall` or Vite plugin) or manual copy is the right approach\n- [ ] Produce follow-up kanban tasks for implementation (asset sync script/plugin + verification)