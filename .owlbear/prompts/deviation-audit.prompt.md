---
description: "Audit selected process observations and classify their correct owning surface"
argument-hint: "Optional: one observation path, Change/task/result identity, or a bounded review scope"
agent: "agent"
tools: [vscode/askQuestions, search, read/readFile, read/problems, execute/runInTerminal]
---

# Deviation Audit

This prompt selects the generic built-in agent for a bounded, read-only review of process-observation
sidecars. It does not authorize workspace mutation or Delivery lifecycle changes. Its read-only rule
is procedural rather than a hard write-denial boundary; do not claim that an audit run proves
workspace immutability.

1. Read `../skills/w-deviation-audit/SKILL.md`.
2. Interpret extra text supplied with this invocation as the bounded observation or review scope.
3. Follow that workflow, preserve the evidence boundary, and return its report without editing files.
