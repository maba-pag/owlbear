---
description: "Create logically structured git commits — groups related changes into cohesive packages"
---

Commit: ${input:scope_hint:What changed — e.g. 'phase-6 implementation', 'agent refactors + docs', 'everything since last push'}

**Workflow:**

1. Run `git status --short` and `git log --oneline -5` to see the full picture
2. Group related files into logical commit packages — think "what story does each commit tell?"
3. For each package, stage only its files and commit with a conventional-commits message

**Grouping heuristics (order of priority):**

- **Feature cohesion:** source + tests + config for the same feature go together
- **Layer separation:** infra/tooling changes separate from feature code
- **Kanban board separate:** task file updates are a `chore:` commit on their own
- **Docs together:** README, copilot-instructions, sources.md grouped as `docs:`
- **Agent definitions together:** agent `.md` files + matching prompts as one commit

**Commit message format:** `type: concise summary`

| Type       | When                                          |
|------------|-----------------------------------------------|
| `feat:`    | New feature (source + tests)                  |
| `fix:`     | Bug fix                                       |
| `refactor:`| Code restructuring, no behavior change        |
| `test:`    | Test-only changes                             |
| `chore:`   | Tooling, kanban board, config, infra          |
| `docs:`    | Documentation updates                         |

**Rules:**

- Never create a single "initial commit" with all files — that defeats the purpose
- Each commit should be independently meaningful (could be reverted on its own)
- Multi-line body for commits with 5+ files: list what's included
- After all commits: `git push` and report the final log
- If working tree is clean, say so and stop
