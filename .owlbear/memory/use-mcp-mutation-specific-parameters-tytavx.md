---
id: 7bd3dbe1-b960-4cfa-b99f-44560336ae79
title: Use MCP mutation-specific parameters
categories:
- pitfall
- tool-usage
- domain-knowledge
confidence: 0.82
state: deleted
scope_agents:
- builder
- reviewer
- planner
- architect
source_agent: copilot
created_at: '2026-05-17T01:34:50.764246Z'
updated_at: '2026-05-17T03:34:23.973915Z'
approved_at: null
---

For OwlBear Kanban MCP mutations, use the operation-specific tool and parameters: move status with `move_task`, change tags with `add_tag`/`remove_tag`, and avoid invalid nullable task YAML such as `blocked: null`. Do not assume `edit_task` accepts every task field.
