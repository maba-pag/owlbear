---
description: "Audit agent-ecosystem authority, loading, structure, and signal quality at ecosystem or artifact scope"
argument-hint: "Optional: 'all', a scope, or one agent, skill, instruction, or prompt"
agent: "agent"
tools: [vscode/askQuestions, search, read/readFile, read/problems, execute/runInTerminal]
---

# Agent Ecosystem Audit

1. Read `../skills/w-agent-audit/SKILL.md`.
2. Interpret extra text supplied with this invocation as the audit request.
3. If no request was supplied, ask one concise question for the whole ecosystem, a scope, or a
   specific target, then wait for the answer before scanning.
4. Follow **Broad Audit** for the whole ecosystem, a directory, an artifact class, or a multi-file
   scope. Follow **Deep Audit** for one named artifact or path.
5. Remain read-only. Do not edit files, mutate memory, or create tasks.
6. Return the report defined by the selected mode, grouped by meaningful change rather than by
   sentence.
