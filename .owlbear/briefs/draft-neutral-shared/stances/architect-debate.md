# Architect Debate Log — Neutral Shared Layer

## Cycle 1

### Draft Position (pre-Critic)

1. Placeholder notation `{variable, e.g. example}` is architecturally sound — grep-able, self-documenting, combines semantic label with concrete exemplar.
2. Split boundaries for `owlbear-system.instructions.md` (extract directory table only) and `r-architecture-standards` (extract v2 overview + namespace table) are clean.
3. Dependency chains are safe because cross-references use skill names, not file paths.
4. File placement: `copilot-instructions.md` for always-needed context, `.owlbear/` for conditional workflow knowledge.
5. Key risks: doc-standards gap, binding protocol undocumented, over-extraction.

### Critic Challenges (7 total, 4 critical)

1. **Critical — "binding contract" has no mechanism.** No resolution engine exists. Skills currently use literal paths, not indirection. The placeholder is advisory text, not executable.
2. **Moderate — brace syntax overloaded.** Corpus already uses `{placeholder}` for template vars, rule IDs, and executable paths. Fourth meaning creates ambiguity.
3. **Critical — owlbear-system split boundary isn't clean.** MCP tool IDs, setup wiring, memory backend labels remain in the file after extracting only the directory table.
4. **Critical — r-architecture-standards has deeper specifics.** Package guard files, server names, reference implementations scattered beyond the overview section.
5. **Critical — dependency chain is semantic, not just referential.** Test-path drift already happening across h-pytest-and-linting, h-python-conventions. Multiple skills contain contradictory `serve/` path guidance.
6. **Moderate — copilot-instructions.md placement violates 80% threshold rule.** Architecture overview doesn't benefit 80% of agents.
7. **Critical — unresolved binding.** Consumer who installs but doesn't customize gets dangling placeholders as false context.

Critic confidence in original position: 0.29 (high pressure).

### Architect Response

**Accepted (refined position):**

- Challenge 2 (syntax): Valid. The `, e.g.` suffix differentiates from bare `{var}` patterns, but I add a constraint: placeholders ONLY in prose/example contexts, NEVER inside executable shell commands or tool-input templates. Commands keep concrete paths with a prose header saying "adjust to your layout."
- Challenge 5 (semantic drift): Valid. All 10 files must be modified atomically. Partial application creates contradictions that already exist in-progress today (e.g., h-pytest-and-linting line 36 vs line 79). This is a constraint on implementation ordering.
- Challenge 7 (unresolved binding): Valid and the most important risk. Mitigation: `setup/init.py` MUST generate a starter `copilot-instructions.md` with binding values pre-filled from the project template. This makes the binding protocol automatic for new consumers.
- Challenge 6 (80% threshold): Partially valid. Architecture overview goes to `.owlbear/instructions/` not `copilot-instructions.md`. Directory structure table IS 80%+ relevant (builder, reviewer, test-writer, doc-writer all need file layout).

**Rebutted:**

- Challenge 1 (no mechanism): The "contract" doesn't need a resolution engine. LLMs read ALL loaded context (skills + copilot-instructions.md) together. When `copilot-instructions.md` says "Frontend root: `serve/cockpit/web/`" and a skill says "`{frontend_root, e.g. serve/cockpit/web/}`", the LLM resolves it semantically in-context. That IS the mechanism — LLM context window. No variable substitution needed.
- Challenge 3 (owlbear-system deeper specifics): The Critic conflated "OwlBear-specific" with "detailed." The MCP bootstrap table (tool IDs, search queries), pipeline diagram, tech stack, and memory governance ARE consumer product — consumers have the same MCP servers, follow the same pipeline. These are NOT OwlBear-dev-specific. Only the directory structure table is. The split boundary IS clean.
- Challenge 4 (r-architecture-standards deeper specifics): Partially rebutted. Generic MCP server conventions, module quality rules, error-handling patterns ARE consumer-useful. But specific `serve/` package names in guard-file examples and reference implementations need extraction. The boundary is: keep the PATTERN, extract the INSTANCE.

**Net result:** Position hardened with three new constraints (no placeholders in commands, atomic implementation, setup/init.py binding generation). Core structural approach unchanged.
