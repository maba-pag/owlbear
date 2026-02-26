# Sources

External repos and resources studied during OwlBear development.

## Agent Pattern Research (Task #22)

| Repo | URL | License | What we studied |
|------|-----|---------|-----------------|
| OpenClaw | <https://github.com/openclaw/openclaw> | MIT | Agent loop, ChannelPlugin adapter, JSONL sessions, hook system, heartbeat, auth rotation, build pipeline |
| Nanobot | <https://github.com/HKUDS/nanobot> | MIT | MessageBus, Tool ABC, LiteLLM provider, progressive skill loading, two-layer memory, subagent spawning |
| claude-code-hooks-mastery | <https://github.com/disler/claude-code-hooks-mastery> | MIT | Claude Code hooks (13 event types), builder/validator team pattern, meta-agent factory, TTS integration, safety guards |

## Copilot OAuth Research (Task #30)

| Repo | URL | License | What we studied |
|------|-----|---------|-----------------|
| Graphicator | `C:\Users\p362329\OneDrive\Coding\Projects\tool.graphicator` | (own project) | Device-flow OAuth implementation for GitHub Copilot API |

## PydanticAI Integration Research (Tasks #37–#45)

| Source | URL | License | What we studied | Where Used | Date |
|--------|-----|---------|-----------------|------------|------|
| PydanticAI | <https://github.com/pydantic/pydantic-ai> | MIT | Agent class, messages.py, tools.py, providers/openai.py, FunctionToolset, TypeAdapter serialization | `src/owlbear/core/agent.py`, `src/owlbear/memory/session.py`, validation tests | 2026-02-26 |
| pydantic-deepagents | <https://github.com/vstorm-co/pydantic-deepagents> | MIT | HookEvent/HookRegistry pattern (middleware/hooks.py), SkillsToolset pattern, MEMORY.md persistence, agent factory anti-pattern | `src/owlbear/core/hooks.py` (adapted HookEvent/HookRegistry pattern) | 2026-02-26 |
