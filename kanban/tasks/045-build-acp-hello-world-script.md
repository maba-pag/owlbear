---
id: 45
title: Build ACP hello-world script
status: backlog
priority: needed
created: 2026-03-26T18:55:56.6812494+01:00
updated: 2026-03-26T19:20:11.8173222+01:00
tags:
    - phase-1
    - scope:orchestrator
depends_on:
    - 7
    - 46
class: standard
---

## Objective

Build minimal Python script using agent-client-protocol SDK:

1. Spawn copilot --acp --stdio --allow-all-tools
2. Initialize connection, create session
3. Send a prompt, print streamed response
4. Handle process cleanup

## AC

- [ ] Script runs and gets a response from Copilot CLI
- [ ] Uses official Python SDK (agent-client-protocol)
- [ ] Handles process cleanup on exit
- [ ] Located in packages/orchestrator/examples/

[[2026-03-26]] Thu

## Research

Findings: docs/research/acp-hello-world.md
Originating research: docs/research/acp-protocol.md section 5

Key decisions:

- Use connect_to_agent() (not spawn_agent_process) for non-Python binary
- Spawn: copilot --acp --stdio --allow-all-tools
- Client: stub fs/terminal methods with RequestError.method_not_found
- Cleanup: terminate, wait_for(5s), kill (gemini.py pattern)
- Resolve binary via shutil.which('copilot') for cross-platform
- Target ~50-60 LOC total

Dependencies added: depends_on [7, 46]

- #7: monorepo skeleton (creates packages/orchestrator/examples/)
- #46: add agent-client-protocol to orchestrator deps

Sources: 8 (SDK docs/examples, Copilot CLI ACP docs, mcp-copilot-acp, rest-acp)
Confidence: .90
