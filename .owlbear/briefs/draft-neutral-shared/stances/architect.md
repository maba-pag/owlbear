# Architectural Stance — Neutral Shared Layer

## Position

The `{variable, e.g. example}` placeholder notation is structurally sound for the ~8 prose/example contexts, with one hard constraint: **never use placeholders inside executable shell commands or tool-input templates.** Commands retain concrete paths with a prose header documenting the substitution point. The LLM context window IS the resolution mechanism — `copilot-instructions.md` provides concrete values, skills provide labeled slots, and the model sees both simultaneously.

The split boundaries are clean for `owlbear-system.instructions.md` (extract directory structure table only; MCP/pipeline/tech-stack content is consumer product, not OwlBear-specific). For `r-architecture-standards`, the boundary is: **keep the pattern, extract the instance** — generic conventions stay, specific `serve/` package names in examples and guard-file lists get replaced with placeholder-style illustrations.

The `doc-standards` pair should NOT simply leave shared — it should be **split**, not moved. Generic doc rules (required sections, cross-reference checks, audience fitness) remain in shared with genericized paths. OwlBear-specific scope (the `serve/` README enumeration, applyTo patterns) moves to `.owlbear/instructions/`.

## Key Risks

1. **Unresolved binding (critical).** A consumer who installs without customizing `copilot-instructions.md` gets placeholders as false context. Mitigation: `setup/init.py` must generate a project-appropriate starter file with binding values pre-filled.

2. **Partial application drift (high).** All 10 files must be modified atomically. The research notes already document contradictions between `h-pytest-and-linting` and `h-python-conventions` regarding test paths — evidence that piecemeal extraction creates semantic inconsistencies.

3. **Command-context leakage (moderate).** Placeholders in shell commands or subagent payloads will leak as literal text into tool inputs. Constraint: prose-only placeholders; commands use concrete examples with a human-readable "adjust for your layout" annotation.

4. **Orphaned binding after shared updates (low).** When shared skills are updated upstream, new placeholders may appear that the consumer's `copilot-instructions.md` doesn't define. Acceptable because: (a) LLMs degrade gracefully with unresolved placeholders (the `e.g.` provides a fallback), (b) setup/init.py can be re-run.

## Recommendations

1. **Placeholder scope rule:** `{name, e.g. value}` in prose and example blocks only. Shell commands, `lint_paths` arrays, tool invocation templates use concrete illustrative paths with an adjacent comment: `# adjust: your source root`.

2. **Binding authority:** `copilot-instructions.md` is the single binding source. Skills MUST remain independently readable (the `e.g.` is there for exactly this case — standalone comprehension without binding).

3. **Atomic implementation:** Ship all 10 file modifications + the `setup/init.py` binding generation + any OwlBear-dev local overrides in one coordinated effort. Do not merge a partially-neutralized state.

4. **doc-standards split, not move:** Keep generic quality rules in shared (genericized applyTo, no `serve/` paths). Move OwlBear-specific scope enumeration to `.owlbear/instructions/owlbear-doc-standards.instructions.md`.

5. **copilot-instructions.md placement test:** Only content that benefits ≥80% of agent interactions goes there (directory structure, primary test paths). Architecture overview goes to `.owlbear/instructions/` as conditional context — it benefits only builder/reviewer/architect, not doc-writer/test-curation/ideation.

6. **r-architecture-standards extraction depth:** Beyond the v2 overview and namespace table, also extract specific guard-file names (`py.typed`, `__init__.py` stubs referencing `serve/`) and reference implementation paths. Keep the RULES (naming patterns, error-contract shape, config-loading protocol).

## Confidence

0.78

Hardened through one Critic cycle. The notation approach is sound given the LLM-context-window resolution model. Main residual uncertainty: whether `setup/init.py` binding generation will actually be implemented as part of this scope (it's critical but feels like a prerequisite task that could slip).
