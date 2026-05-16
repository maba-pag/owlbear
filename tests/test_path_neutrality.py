"""Failing tests for task #1285: P2-01 — path neutrality verification for share/skills/.

All tests must FAIL on the current codebase; they pass once the GREEN tasks (#1286-#1291)
are complete.

AC coverage:
  AC2 (td:2) — test_no_serve_path_refs_in_skill_files,
                test_r_arch_standards_no_serve_path_refs
  AC3 (td:1) — test_quality_runner_skill_references_copilot_instructions
  AC4 (td:1) — test_r_arch_standards_no_legacy_section_headers
  AC5 (td:2) — test_r_doc_standards_skill_references_instructions_stub,
                test_doc_standards_instructions_stub_references_audit_prompt,
                test_doc_audit_prompt_exists_at_chain_target,
                test_r_doc_standards_full_chain_resolved
  AC6 (td:1) — test_audit_prompts_relocated_to_owlbear_prompts
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_SHARE_ROOT = _REPO_ROOT / "share"
_SKILLS_ROOT = _SHARE_ROOT / "skills"
_SHARE_INSTRUCTIONS_ROOT = _SHARE_ROOT / "instructions"
_SHARE_PROMPTS_ROOT = _SHARE_ROOT / "prompts"
_OWLBEAR_PROMPTS_ROOT = _REPO_ROOT / ".owlbear" / "prompts"

# Regex for detecting serve/ path references in skill markdown (word-boundary anchored).
# Equivalent to the grep pattern in AC2.
_SERVE_REF_RE = re.compile(r"\bserve/")

# Lines matching any of these patterns are excluded from the serve/ reference scan per AC2,
# equivalent to: grep -v 'mcp-\|Example ('
_SERVE_REF_EXCLUSION_RES = (re.compile(r"mcp-"), re.compile(r"Example \("))

# Section headers that must be absent from r-architecture-standards/SKILL.md per AC4.
_LEGACY_SECTION_HEADERS = (
    "## v2 Architecture Overview",
    "## Package Dependency Rules",
    "## Domain Taxonomy",
)

# Audit prompts that must be relocated from share/prompts/ to .owlbear/prompts/ per AC6.
_AUDIT_PROMPTS = (
    "doc-audit.prompt.md",
    "arch-audit.prompt.md",
)


def _collect_serve_ref_violations(root: Path) -> list[tuple[Path, int, str]]:
    """Return (file, lineno, line) tuples for each serve/ reference not excluded by AC2 filters.

    ``root`` may be a single ``.md`` file or a directory (scanned recursively).
    """
    violations: list[tuple[Path, int, str]] = []
    md_files: list[Path] = [root] if root.is_file() else sorted(root.rglob("*.md"))
    for md_file in md_files:
        for lineno, line in enumerate(md_file.read_text(encoding="utf-8").splitlines(), start=1):
            if not _SERVE_REF_RE.search(line):
                continue
            if any(pat.search(line) for pat in _SERVE_REF_EXCLUSION_RES):
                continue
            violations.append((md_file, lineno, line))
    return violations


class TestFromAC_PathNeutrality:
    """Verification tests for P2-01 path neutrality of share/skills/. Task #1285."""

    # ---- AC2 (td:2): no serve/ path references in skill markdown ---------------------------

    def test_no_serve_path_refs_in_skill_files(self) -> None:
        """All share/skills/**/*.md files must have zero serve/ path references.

        Lines containing 'mcp-' or 'Example (' are excluded per AC2 spec.
        Equivalent to: grep -r 'serve/' share/skills/ | grep -v 'mcp-\\|Example ('
        """
        violations = _collect_serve_ref_violations(_SKILLS_ROOT)
        assert violations == [], (
            f"{len(violations)} serve/ reference(s) found in share/skills/ (after exclusions):\n"
            + "\n".join(f"  {f.relative_to(_REPO_ROOT)}:{n}  {ln.strip()}" for f, n, ln in violations)
        )

    def test_r_arch_standards_no_serve_path_refs(self) -> None:
        """r-architecture-standards/SKILL.md must have zero serve/ path references.

        Known current violator — ensures this specific high-impact file is covered by the
        GREEN task before the suite-wide test passes.
        """
        skill_file = _SKILLS_ROOT / "r-architecture-standards" / "SKILL.md"
        assert skill_file.exists(), f"Expected {skill_file.relative_to(_REPO_ROOT)} to exist"
        violations = _collect_serve_ref_violations(skill_file)
        assert violations == [], (
            f"{len(violations)} serve/ reference(s) in r-architecture-standards/SKILL.md "
            f"(after exclusions):\n" + "\n".join(f"  line {n}: {ln.strip()}" for _, n, ln in violations)
        )

    # ---- AC3 (td:1): h-quality-runner references copilot-instructions.md -----------------

    def test_quality_runner_skill_references_copilot_instructions(self) -> None:
        """h-quality-runner/SKILL.md must contain both the routing-authority phrase
        ('Routing authority for frontend root and test-path mode selection') and the
        filename 'copilot-instructions.md', each as independent file-content substrings.
        """
        skill_file = _SKILLS_ROOT / "h-quality-runner" / "SKILL.md"
        content = skill_file.read_text(encoding="utf-8")
        assert "Routing authority for frontend root and test-path mode selection is" in content, (
            "h-quality-runner/SKILL.md must contain the routing authority directive "
            "('Routing authority for frontend root and test-path mode selection is …') — not found"
        )
        assert "copilot-instructions.md" in content, (
            "h-quality-runner/SKILL.md must name copilot-instructions.md in the routing authority directive — not found"
        )

    # ---- AC4 (td:1): r-architecture-standards has no legacy section headers ---------------

    def test_r_arch_standards_no_legacy_section_headers(self) -> None:
        """r-architecture-standards/SKILL.md must not contain any of the three legacy
        section headers that are being removed as part of P2 genericization:
          - ## v2 Architecture Overview
          - ## Package Dependency Rules
          - ## Domain Taxonomy
        """
        skill_file = _SKILLS_ROOT / "r-architecture-standards" / "SKILL.md"
        content = skill_file.read_text(encoding="utf-8")
        found = [h for h in _LEGACY_SECTION_HEADERS if h in content]
        assert found == [], "Legacy section header(s) still present in r-architecture-standards/SKILL.md: " + ", ".join(
            repr(h) for h in found
        )

    # ---- AC5 (td:2): r-doc-standards cross-reference chain --------------------------------

    def test_r_doc_standards_skill_references_instructions_stub(self) -> None:
        """r-doc-standards/SKILL.md must contain the exact canonical path substring
        'share/instructions/doc-standards.instructions.md' in its file content.
        """
        skill_file = _SKILLS_ROOT / "r-doc-standards" / "SKILL.md"
        content = skill_file.read_text(encoding="utf-8")
        assert "share/instructions/doc-standards.instructions.md" in content, (
            "Chain broken at link 1: r-doc-standards/SKILL.md does not reference "
            "share/instructions/doc-standards.instructions.md (exact path required)"
        )

    def test_doc_standards_instructions_stub_references_audit_prompt(self) -> None:
        """share/instructions/doc-standards.instructions.md must exist on disk and
        contain the exact canonical path substring '.owlbear/prompts/doc-audit.prompt.md'
        in its file content.
        """
        instructions_file = _SHARE_INSTRUCTIONS_ROOT / "doc-standards.instructions.md"
        assert instructions_file.exists(), (
            f"share/instructions/doc-standards.instructions.md not found at {instructions_file.relative_to(_REPO_ROOT)}"
        )
        content = instructions_file.read_text(encoding="utf-8")
        assert ".owlbear/prompts/doc-audit.prompt.md" in content, (
            "Chain broken at link 2: doc-standards.instructions.md does not reference "
            ".owlbear/prompts/doc-audit.prompt.md (exact path required)"
        )

    def test_doc_audit_prompt_exists_at_chain_target(self) -> None:
        """doc-audit.prompt.md must exist at .owlbear/prompts/ — the post-move target path
        per AC6. Verified by file existence at the expected canonical location.
        """
        prompt_file = _OWLBEAR_PROMPTS_ROOT / "doc-audit.prompt.md"
        assert prompt_file.exists(), (
            f"Chain broken at link 3: doc-audit.prompt.md not found at "
            f"{prompt_file.relative_to(_REPO_ROOT)} — file must be relocated to .owlbear/prompts/"
        )

    def test_r_doc_standards_full_chain_resolved(self) -> None:
        """The r-doc-standards cross-reference chain has no dangling targets, verified by:
        (a) r-doc-standards/SKILL.md contains the exact canonical path substring
            'share/instructions/doc-standards.instructions.md';
        (b) doc-standards.instructions.md exists on disk and contains the exact canonical
            path substring '.owlbear/prompts/doc-audit.prompt.md';
        (c) doc-audit.prompt.md exists at .owlbear/prompts/.
        """
        skill_file = _SKILLS_ROOT / "r-doc-standards" / "SKILL.md"
        instructions_file = _SHARE_INSTRUCTIONS_ROOT / "doc-standards.instructions.md"
        prompt_file = _OWLBEAR_PROMPTS_ROOT / "doc-audit.prompt.md"

        skill_content = skill_file.read_text(encoding="utf-8")
        assert "share/instructions/doc-standards.instructions.md" in skill_content, (
            "Full-chain check: link 1 broken — r-doc-standards/SKILL.md does not reference "
            "share/instructions/doc-standards.instructions.md (exact path required)"
        )
        assert instructions_file.exists(), (
            f"Full-chain check: link 2a broken — {instructions_file.relative_to(_REPO_ROOT)} not found"
        )
        instructions_content = instructions_file.read_text(encoding="utf-8")
        assert ".owlbear/prompts/doc-audit.prompt.md" in instructions_content, (
            "Full-chain check: link 2 broken — doc-standards.instructions.md does not "
            "reference .owlbear/prompts/doc-audit.prompt.md (exact path required)"
        )
        assert prompt_file.exists(), (
            f"Full-chain check: link 3 broken — doc-audit.prompt.md not found at {prompt_file.relative_to(_REPO_ROOT)}"
        )

    # ---- AC6 (td:1): audit prompts relocated to .owlbear/prompts/ -------------------------

    def test_audit_prompts_relocated_to_owlbear_prompts(self) -> None:
        """doc-audit.prompt.md and arch-audit.prompt.md must each
        exist in .owlbear/prompts/ and must NOT exist in share/prompts/.
        """
        for prompt_name in _AUDIT_PROMPTS:
            owlbear_path = _OWLBEAR_PROMPTS_ROOT / prompt_name
            share_path = _SHARE_PROMPTS_ROOT / prompt_name
            assert owlbear_path.exists(), (
                f"{prompt_name} not found at .owlbear/prompts/ — must be relocated there from share/prompts/"
            )
            assert not share_path.exists(), (
                f"{prompt_name} still exists at share/prompts/ — must be removed after relocation to .owlbear/prompts/"
            )
