---
description: "Audit agent-ecosystem authority, loading, structure, and signal quality at ecosystem or artifact scope"
argument-hint: "Optional: 'all', a scope, or one agent, skill, instruction, or prompt"
agent: "agent"
tools: [vscode/askQuestions, search, read/readFile, read/problems, execute/runInTerminal]
---

# Agent Ecosystem Audit

This prompt selects the generic built-in agent and intentionally has no PreToolUse write-denial
hook. The accepted risk is that its read-only requirement is procedural rather than mechanically
enforced: this entry point is limited to trusted local audits, and the absence of hard terminal or
file-write blocking is intentional. Do not treat an audit run as a security boundary or claim that
it proves workspace immutability. Do not report the absence of a hard write-denial hook as a defect
for this prompt unless its trust boundary or tool surface changes. Do not edit files, rename files,
or run mutating terminal commands during an audit.

1. Read `../skills/w-agent-audit/SKILL.md`.
2. Interpret extra text supplied with this invocation as the audit request.
3. Follow that workflow and remain read-only.
