# Mermaid Chat Setting and Diagram Rendering Paths

> **Owning task:** #691 — Verify mermaid-chat.enabled and document diagram rendering paths for agents
> **Date:** 2026-04-08  **Status:** Complete

## 1. Context and Question

Task #683 research concluded v2 already has diagram rendering via three existing paths, but agents may not know about them. This task verifies the `mermaid-chat.enabled` setting is active and determines where to document the rendering paths for agent awareness.

Two sub-questions:
1. Is `mermaid-chat.enabled` currently active in workspace or user settings?
2. Where should rendering path documentation live so agents discover it?

## 2. Sources Studied

| # | Source | URL / Location | Relevance |
|---|--------|----------------|-----------|
| 1 | VS Code Copilot cheat sheet | <https://code.visualstudio.com/docs/copilot/reference/copilot-vscode-features> | .95 — confirms setting name and opt-in nature |
| 2 | Prior research #683 | `.owlbear/research/diagram-rendering-tool-v2.md` | .95 — comprehensive rendering path analysis |
| 3 | Seed settings template | `seed/.vscode/settings.json` | .90 — current template contents verified |
| 4 | OwlBear code profile | `Owlbear.code-profile` | .85 — extensions list, no settings for mermaid-chat |
| 5 | agent-common.instructions.md | `share/instructions/agent-common.instructions.md` | .90 — confirmed no diagram content |
| 6 | h-visual-output skill | `share/skills/h-visual-output/SKILL.md` | .85 — existing HTML+Mermaid CDN path |
| 7 | h-excalidraw-diagram skill | `share/skills/h-excalidraw-diagram/SKILL.md` | .85 — existing Excalidraw JSON path |

## 3. Analysis

### 3.1 Current State of `mermaid-chat.enabled`

| Location | Contains `mermaid-chat.enabled`? |
|----------|----------------------------------|
| `seed/.vscode/settings.json` (consumer template) | **No** — only has `chat.*Locations` keys |
| `Owlbear.code-profile` | **No** — has `bierner.markdown-mermaid` extension but no settings |
| `.vscode/settings.json` (workspace) | **Does not exist** in OwlBear dev workspace |
| User settings | Not verified — user-specific |

The VS Code docs describe the setting as opt-in: "Enable with `mermaid-chat.enabled`." Without explicit activation, Mermaid code blocks in chat responses render as plain text.

### 3.2 Where to Enable the Setting

| Option | Scope | Pros | Cons |
|--------|-------|------|------|
| A: `seed/.vscode/settings.json` | Consumer projects | Automatic for all new setups; idempotent merge via init.py | Existing consumers need re-run or manual add |
| B: `agent-common.instructions.md` note | Agent awareness | Agents know to tell users if not set | Does not actually enable the setting |
| C: Setup guide mention | User docs | Discoverable for manual setup | Same as B |

**Recommendation:** A + B — add to seed template AND document in agent instructions. (.90 confidence)

### 3.3 Where to Document Rendering Paths

| Option | Pros | Cons |
|--------|------|------|
| `agent-common.instructions.md` | Read by all agents; brief routing table fits | File grows; rendering is not a "convention" |
| New skill `h-diagram-routing` | Clean separation | Over-engineered for a 10-line table; YAGNI |
| Add to `h-visual-output` skill | Related content; already exists | Not all agents load this skill |

**Recommendation:** Add a brief section to `agent-common.instructions.md` — a 3-row routing table pointing agents to the right skill. (.85 confidence)

### 3.4 Rendering Path Summary (for doc section)

| Use case | Path | Skill/Setting |
|----------|------|---------------|
| Show diagram in chat response | Mermaid code block | `mermaid-chat.enabled` (VS Code setting) |
| Persistent styled HTML diagram | HTML file + Mermaid CDN | `h-visual-output` skill |
| Free-form architecture diagram | `.excalidraw` JSON file | `h-excalidraw-diagram` skill |

## 4. Recommendation (.88 confidence)

Two follow-up tasks, both T1 autonomous:

1. **Enable `mermaid-chat.enabled: true`** in `seed/.vscode/settings.json`. This propagates to new consumer projects via `init.py`. Existing consumers add it manually or re-run init.
2. **Add a ~10-line "Diagram Rendering" section** to `agent-common.instructions.md` with the 3-row routing table from §3.4.

No architectural change, no new capability, no security impact.

Challenge: FALLBACK — T1 autonomous config/doc task, no architectural decision to challenge.

### Tier Classification: T1 — Autonomous

Config setting + instruction documentation. No new capability, no architecture change.

## 5. Follow-up Tasks

- Enable `mermaid-chat.enabled` in seed settings template and add diagram rendering section to agent-common.instructions.md
