---
id: 87b35435-1f3b-47b9-af0c-2792b2320d37
title: Screenshot absence is not implementation absence
categories:
- process
- pitfall
- tool-usage
confidence: 0.8
state: curated
scope_agents:
- reviewer
source_agent: reviewer
created_at: '2026-05-15T09:07:00.528836Z'
updated_at: '2026-05-16T03:37:40.003957Z'
approved_at: null
---

For frontend screenshot ACs, do not treat a missing region in the captured frame as missing implementation until you map the screenshot bounds back to the component regions. If the code defines the region but the artifact clips or omits it, request corrected screenshot proof instead of failing the implementation.
