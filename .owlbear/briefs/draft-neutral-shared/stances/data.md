# Data Quality Stance — Neutral Shared Layer

## Position

Path strings in skill files function as **implicit data contracts** between the file (producer) and the LLM agent (consumer). The refactoring is fundamentally a **data-authority migration**: moving facts from a shared schema (consumed by all) to a project-local schema (consumed by one), while preserving referential integrity across the boundary.

The proposed `{variable, e.g. example}` notation is viable but carries specific integrity risks that must be mitigated by convention, not by machinery (since no resolution engine exists). The notation is not intrinsically broken — template-style syntax already appears in agent-facing materials (`w-code-review` lint_paths, prompt variables, agent structure templates) and LLMs handle it. The risk is not "LLMs can't parse this" but rather "nothing prevents silent degradation when examples drift or definitions are absent."

**Core data-quality framing:** This is not a path-correctness problem — `serve/cockpit/web/` is perfectly correct *in OwlBear-dev*. It's a **data-authority problem**: a project-specific fact is stored in a shared layer, creating false universality. The refactoring must treat each hardcoded path as a datum that needs to migrate to its authoritative owner.

## Integrity Risks

### 1. Silent Example Literalization (Medium Risk)

When a skill says `{frontend_root, e.g. serve/cockpit/web/}` and the consumer's `copilot-instructions.md` defines `frontend_root = client/`, the LLM must correlate across two documents. Since copilot-instructions.md is always loaded, the context is reliably present — the failure mode is not missing data but **attentional**: the LLM may use the nearby concrete example over the distant abstract definition when under reasoning pressure. Practically: this fails in a minority of interactions, not categorically.

**Mitigation:** The research notes already identify the right answer — use prose ("your frontend package root") for inline generics. Reserve concrete examples for clearly-separated reference blocks or the project's own copilot-instructions.md where they are authoritative.

### 2. Cross-Reference Breakage (High Risk)

Moving `r-doc-standards` out of `share/` breaks `doc-audit.prompt.md`'s dependency chain. This is a confirmed foreign-key violation — the prompt explicitly loads that skill. Similarly, moving `doc-standards.instructions.md` orphans its `applyTo` wiring.

**Affected chains:**
- `doc-audit.prompt.md` → `r-doc-standards` (skill reference)
- `doc-standards.instructions.md` → `r-doc-standards` (points agents to the skill)
- `h-agent-structure` "Current stubs" table → `doc-standards.instructions.md` (documentation reference)

These must be migrated as a unit or the references updated. Partial migration = dangling pointers.

### 3. Stale Example Drift (Medium Risk, Long-term)

If OwlBear-dev restructures (e.g., renames `serve/cockpit/web/` to `serve/frontend/`), the example in the shared skill becomes misleading. However: both consumers are user-controlled, the update cadence is manual and acknowledged, and the examples live in a small number of files (10 with genuine issues). This is manageable maintenance, not systemic rot — *provided the examples are clearly marked as examples, not as the canonical path*.

### 4. Incomplete Authority Migration (High Risk)

The most dangerous data-integrity failure is **partial extraction**: moving some OwlBear-dev facts to copilot-instructions.md while leaving others embedded in shared skills. This creates a split-brain state where an agent receives contradictory signals about project layout. The directory structure table (owlbear-system.instructions.md) must move as a complete unit alongside the architecture overview (r-architecture-standards) and file placement table (r-project-standards §2). If any one of these stays while others move, the agent builds an inconsistent mental model.

### 5. Scope Classification Ambiguity (Low Risk)

The audit correctly identified four categories: move (2 prompts), split (2 mixed files), genericize paths (8 files), cosmetic (4 files). The data-integrity risk is misclassifying a "split" as a "genericize" — e.g., treating `r-architecture-standards`' namespace table as something to parameterize rather than extract. That table is not a generic pattern with OwlBear examples; it IS OwlBear's architecture. Parameterizing it would produce meaningless prose for consumers.

## Recommendations

1. **Prefer prose over template notation** for path generics in command examples. "Your project's test paths" is unambiguous. `{test_paths, e.g. tests/ serve/}` adds syntactic overhead without resolution machinery to back it. Reserve `{variable}` syntax for the project's copilot-instructions.md where the value IS concrete.

2. **Migrate cross-reference chains as atomic units.** `r-doc-standards` + `doc-standards.instructions.md` + `doc-audit.prompt.md` move together. Update `h-agent-structure`'s stubs table in the same commit.

3. **Validate completeness of the authority split.** After extraction, grep shared files for `serve/` — any remaining occurrence is either (a) a product name reference (MCP server skill mentioning the server's own path — valid) or (b) an incomplete migration. The post-migration validation is: `grep -r 'serve/' share/ | grep -v 'mcp-'` should return zero non-product hits.

4. **Mark examples as non-authoritative where they appear.** In the rare cases where an inline example helps comprehension, use a clear frame: "Example (OwlBear-dev): `serve/cockpit/web/`" — this signals "illustrative, not your path" unambiguously to an LLM.

5. **copilot-instructions.md becomes the single source of truth for project layout.** Validate that after refactoring, ALL project-specific path facts live there and nowhere else. This is the schema contract: shared skills reference abstract concepts; copilot-instructions.md resolves them to concrete paths.

## Confidence

**0.80**

Strong on the authority-migration framing and cross-reference integrity analysis. Moderate uncertainty on the exact failure rate of template notation (practical evidence from existing template usage in the codebase suggests it works adequately, reducing the severity of Risk 1). The primary risk is not notation choice but incomplete migration and dangling references.
