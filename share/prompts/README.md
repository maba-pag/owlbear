# prompts/

8 prompt files (`.prompt.md`) in the default VS Code discovery location. Prompts are user-invocable one-shot commands — unlike agents and skills, they are triggered directly by the user from the VS Code chat interface and do not require explicit `read_file` loading.

## Invocation Pattern

Prompts appear in the VS Code chat command palette. The user selects a prompt to inject a pre-built instruction into the chat. Many prompts accept `${input:...}` variable substitution — VS Code collects the value at invocation time.

## Naming Convention

| Pattern | Meaning |
|---------|---------|
| `{verb}.prompt.md` | Single-purpose action (e.g., `orchestrate`) |
| `{scope}-{verb}.prompt.md` | Scoped action (e.g., `frontend-audit`, `doc-audit`) |

## Current Prompts

| Group | Prompts |
|-------|---------|
| Orchestration | `orchestrate` |
| Audits | `agent-audit`, `doc-audit`, `frontend-audit` |
| Frontend | `frontend-normalize`, `frontend-polish`, `design-context` |
| Curation | `test-curation` |

See `h-agent-structure` for structural standards and the distinction between prompts, agents, and skills.
