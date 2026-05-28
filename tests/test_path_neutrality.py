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


