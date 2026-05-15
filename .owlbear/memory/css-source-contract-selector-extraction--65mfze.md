---
id: 08dc8c5e-d64c-4834-bb96-86d85c193e5d
title: CSS source-contract selector extraction may require column-0 selector lines
categories:
- pitfall
- tool-usage
confidence: 0.86
state: deleted
scope_agents:
- builder
- test-writer
source_agent: builder
created_at: '2026-05-14T03:46:12.874863Z'
updated_at: '2026-05-15T20:45:43.798132Z'
approved_at: null
---

In SidecarCollapse_1549-style tests, extractSelectorBlock() matches selectors only at line start after newline (no leading spaces). Nested selectors inside @media with indentation can false-fail as Missing CSS selector block. Keep tested selector lines unindented or update helper regex to allow leading whitespace.
