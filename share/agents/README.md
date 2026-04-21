# agents/

28 agent definitions (`.agent.md` files) in the default VS Code discovery location.

| Tier | Count | Agents |
|------|-------|--------|
| T1 — Orchestrator | 4 | orchestrator, ideator, ideation-discoverer, ideation-mediator |
| T2 — Pipeline | 7 | researcher, architect, test-writer, builder, reviewer, doc-writer, auditor |
| T3 — Support | 4 | scribe, planner, test-curator, memory-curator |
| T4 — Tools | 13 | challenger, code-reader, fix-attempt, quality-runner, ideation-architect, ideation-critic, ideation-data, ideation-enduser, ideation-firstprinciples, ideation-outsider, ideation-pragmatist, ideation-security, ideation-simplifier |

`ideator` is now a thin compatibility router. New ideation work starts in `ideation-discoverer`; post-discovery continuation starts in `ideation-mediator`.

See `h-agent-structure` for structural standards and tier definitions.