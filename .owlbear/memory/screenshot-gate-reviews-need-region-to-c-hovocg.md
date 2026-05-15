---
id: 87b35435-1f3b-47b9-af0c-2792b2320d37
title: Screenshot gate reviews need region-to-code mapping
categories:
- process
- pitfall
- tool-usage
confidence: 0.88
state: curated
scope_agents:
- reviewer
source_agent: reviewer
created_at: '2026-05-15T09:07:00.528836Z'
updated_at: '2026-05-15T09:11:19.183444Z'
approved_at: null
---

For frontend ACs that require screenshot evidence, map visible screenshot content back to the actual component regions before claiming a region is missing. If implementation defines the region and the screenshot only omits it from frame, route as a builder-owned artifact/proof failure (usually in-progress), not an implementation absence. Pair the artifact review with a note on whether task-local tests only prove file existence/format.
