---
description: "Agent ecosystem conventions — structural standards and file interconnections for agent/skill/instruction/prompt development"
applyTo: "share/agents/**,share/skills/**,share/instructions/**,.owlbear/agents/**,.owlbear/skills/**,.owlbear/instructions/**"
---

When creating or modifying agent ecosystem files, read `share/README.md` for the loading model, tier definitions, and file interconnections. For structural standards (required sections, naming grammar, implicit encoding), read the `h-agent-structure` skill.

Keep workspace agents, skills and instructions in `share/` and `.owlbear/`, loaded through VS Code's location
settings. Decline any offer from VS Code to move them to `.github/` and dismiss the notice.
After moving the shaper, use its next real shaping chat to verify that the runtime selects it, preloads its skill,
grants working tools and restores the owner's settings. You may remove the old copies first; fix any problems
in that run.
