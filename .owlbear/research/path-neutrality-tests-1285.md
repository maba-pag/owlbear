# Path Neutrality Verification Tests

> **Owning task:** #1285 — P2-01: Test — path neutrality verification for share/skills/
> **Date:** 2026-05-03 **Status:** Complete

## 1. Context and Question

Task #1285 is a RED-phase test task: write pytest tests that verify P2 completion conditions from the "Neutral Shared Layer" brief. Tests must fail against the current codebase and pass once #1286–#1291 land.

**Question:** What is the correct test approach for each AC line, and what are the edge cases?

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `.owlbear/briefs/draft-neutral-shared/brief.md` | Brief | 1.0 — defines P2 AC |
| `tests/test_dead_code_sweep_1296.py` | Codebase pattern | 0.9 — identical test pattern (RED-phase filesystem assertions) |
| `share/skills/h-quality-runner/SKILL.md` | Target file | 0.9 — AC3 verification target |
| `share/skills/r-architecture-standards/SKILL.md` | Target file | 0.9 — AC4 verification target |
| `share/skills/r-doc-standards/SKILL.md` | Target file | 0.8 — AC5 cross-ref chain |
| `share/instructions/doc-standards.instructions.md` | Target file | 0.8 — AC5 cross-ref chain |
| `share/prompts/` directory listing | Target dir | 0.8 — AC6 verification |

## 3. Analysis

### Current State (pre-P2)

| AC | What test checks | Current state | Will fail? |
|----|-----------------|---------------|------------|
| AC2 | `serve/` refs in share/skills/ (excl mcp-/Example) | 51 matches across 14 files | Yes ✓ |
| AC3 | h-quality-runner routing prose | No project-config directive exists | Yes ✓ |
| AC4 | r-arch-standards has only generic rules | Has v2 overview + domain taxonomy + pkg dep rules | Yes ✓ |
| AC5 | r-doc-standards chain no dangling refs | Chain intact but 3 prompts will move | Yes ✓ (after prompt move) |
| AC6 | 3 prompts in .owlbear/prompts/ | All 3 in share/prompts/; .owlbear/prompts/ doesn't exist | Yes ✓ |

### Implementation Approach

**File:** `tests/test_path_neutrality_1285.py`
**Pattern:** Same as `test_dead_code_sweep_1296.py` — `_REPO_ROOT = Path(__file__).parent.parent`, one function per AC.

| AC | Test function | Technique |
|----|--------------|-----------|
| AC2 | `test_no_serve_paths_in_shared_skills` | `pathlib.rglob("*.md")` + regex `r'\bserve/'` with exclusion for `mcp-` and `Example (` on same line |
| AC3 | `test_quality_runner_has_routing_prose` | Read SKILL.md, assert contains project-config routing directive |
| AC4 | `test_arch_standards_generic_only` | Read SKILL.md, assert no `## v2 Architecture Overview`, `## Domain Taxonomy`, `## Package Dependency Rules` headers |
| AC5 | `test_doc_standards_chain_no_dangling_refs` | Scan share/ for `r-doc-standards` refs → verify skill exists; scan for prompt refs → verify prompt files exist |
| AC6 | `test_audit_prompts_in_owlbear_not_share` | Assert 3 files exist in `.owlbear/prompts/` AND not in `share/prompts/` |

### Edge Cases

1. **AC2 exclusion regex:** Shell `grep -v 'mcp-\|Example ('` matches lines containing either pattern. Python equivalent: skip lines where `re.search(r'mcp-|Example \(', line)` matches. Must handle multi-pattern exclusion correctly.
2. **AC4 section headers:** The brief says "no namespace table" — in current file this is the v2 overview's indented code block listing `serve/mcp-*` paths. Test should check for `## v2 Architecture Overview` and `## Domain Taxonomy` headers (the two that contain serve/ paths).
3. **AC5 reference definition:** A "reference" = any mention of `r-doc-standards` as a skill name, `doc-standards.instructions` as a file, or `doc-audit`/`agent-audit`/`arch-audit` as prompt names in `.md` files under `share/`. A "dangling" ref = the referenced target doesn't exist in the expected location under `share/`.

## 4. Recommendation (confidence: 0.90)

Proceed with implementation. All AC lines map to straightforward filesystem content assertions using established test patterns. No external dependencies, no special tooling.

**Challenge:** Skipped — trivial test-mapping research with no architectural trade-offs to challenge.

**Risk:** AC5 cross-reference check is the most nuanced — scope it to the specific chain (r-doc-standards ↔ doc-standards.instructions ↔ doc-audit/agent-audit/arch-audit) rather than a generic share/-wide cross-ref scanner. A generic scanner would be over-engineering for this AC.

## 5. Follow-up Tasks

No new follow-ups needed — task #1285 itself is the follow-up (test-writing at todo). Sibling tasks #1286–#1291 cover the GREEN implementation.
