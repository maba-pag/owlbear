# Context — Agent-Audit Prompt Rework

## Origin
- User moved `agent-audit.prompt.md` from `share/prompts/` → `.github/prompts/` (dev-only, not consumer-facing). Placement is correct: this prompt audits OwlBear's own agent ecosystem.
- Prompt has been run multiple times and drove real edits. Working baseline.
- User is leveraging Opus 4.7's sharper reviewing eye, not fixing a broken artifact.

## Why this is critical
Agents/skills/instructions/memory are the foundation of every consuming OwlBear project.
This prompt is the quality gate for that foundation. Worth maximum effort.

## Confirmed scope
- **Single-file artifact** preserved. No skill split. Used ~every other week, single-purpose.
- Quality over size. Bloat allowed if it serves quality.
- Audit must cover: agents, skills, instructions, **memory** (currently missing — `/memories/`, `/memories/repo/`, mcp-memory `owlbearMemory`, lessons-learned dual-write).
- New behavior: **continuous loop**. Run → present finding → `askQuestions` → fix → verify → next finding. When all findings done, `askQuestions` "audit again from the top?" Never silent stall.
- All user-facing prompts use `askQuestions`.

## Tier
Lite. Panel: Architect + End-User + Pragmatist. (Security/Data not relevant.)

## Known gaps to ensure are covered (user-identified)
1. Memory dimension entirely absent from current prompt.
2. "Run from the top again" loop mechanic missing.

## Confirmed outcomes
- Audit complete quality surface: agents + skills + instructions + copilot-instructions + memory.
- Toughest reviewing standard — rule-conformance + signal quality + blind spots + 2nd-order effects.
- Continuous loop: finding → askQuestions approval → implement → verify → next.
- When queue empty: askQuestions "run from the top?"
- Single self-contained file.
- Findings are concrete edits, not discussions.
- **Top-down AND bottom-up:** find what's missing (negative space), not just what's wrong.
- **Dual memory sources:** file-based (`/memories/repo/inbox/`) NOW + `owlbearMemory` MCP SOON. Forward-compatible.
- Memory scope: both governance AND content (contradictions, staleness, dupes).
- Loop stop: exhausted OR user-bail via askQuestions (no hard cap).
