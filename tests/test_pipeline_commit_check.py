"""Failing tests for task #1412: Pre-end_work scoped commit check.

All tests must FAIL on the current codebase — they pass once the builder adds the
"Pre-advance verification" rule to r-pipeline-protocol/SKILL.md.

AC coverage:
  P1 — test_pre_advance_verification_heading_exists
  P2 (per-agent domain check) — test_researcher_domain_paths_present,
                                 test_test_writer_domain_paths_present,
                                 test_builder_domain_paths_present,
                                 test_doc_writer_domain_paths_present
  P2 (domain-scoped, not raw) — test_verification_command_uses_pathspec_syntax
  P2 (pre-end_work, not hook) — test_rule_placed_in_who_commits_what_section
  P2 (self-heal, not gate)   — test_self_heal_action_not_blocking_gate
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_SKILL_FILE = _REPO_ROOT / "share" / "skills" / "r-pipeline-protocol" / "SKILL.md"

_WHO_COMMITS_HEADING = "### Who Commits What"
_PRE_ADVANCE_HEADING = "Pre-advance verification"


def _read_skill() -> str:
    return _SKILL_FILE.read_text(encoding="utf-8")


def _section_after(content: str, heading: str) -> str:
    """Return all text after `heading` up to the next same-level heading."""
    lines = content.splitlines()
    start: int | None = None
    level = heading.lstrip("#").count("#") if heading.startswith("#") else 0
    prefix = "#" * (level + 1) if level else "###"

    for i, line in enumerate(lines):
        if heading in line:
            start = i
        elif start is not None and line.startswith(prefix) and line != heading:
            return "\n".join(lines[start:i])
    if start is not None:
        return "\n".join(lines[start:])
    return ""


class TestFromAC_PreAdvanceCommitCheck:
    """AC coverage for #1412: domain-scoped pre-end_work commit verification rule."""

    # ── P1: rule exists ──────────────────────────────────────────────────────

    def test_pre_advance_verification_heading_exists(self) -> None:
        """P1: r-pipeline-protocol contains a 'Pre-advance verification' rule."""
        content = _read_skill()
        assert _PRE_ADVANCE_HEADING in content, (
            "r-pipeline-protocol/SKILL.md must contain a 'Pre-advance verification' rule "
            "in § 4 Closing → Who Commits What → Rules"
        )

    # ── P2: per-agent domain paths ───────────────────────────────────────────

    def test_researcher_domain_paths_present(self) -> None:
        """P2: Researcher's domain paths (.owlbear/research/ and .owlbear/sources/) are listed."""
        content = _read_skill()
        # The domain table must include the researcher's sources path (not already in protocol).
        # .owlbear/research/ is already mentioned in the existing Commits table, so we
        # specifically require .owlbear/sources/ which only appears in the new domain table.
        assert ".owlbear/sources/" in content or "owlbear/sources" in content, (
            "Domain table must list researcher path '.owlbear/sources/' "
            "(the sources directory is a researcher deliverable not yet listed in the protocol)"
        )

    def test_test_writer_domain_paths_present(self) -> None:
        """P2: Test-writer's domain path (tests/) is listed in the domain table."""
        content = _read_skill()
        # The domain table should map test-writer → tests/
        assert re.search(r"test.writer.*tests/|tests/.*test.writer", content, re.IGNORECASE), (
            "Domain table must map 'test-writer' to 'tests/' so the test-writer knows which files to check"
        )

    def test_builder_domain_paths_present(self) -> None:
        """P2: Builder's domain path (serve/) is listed in the domain table."""
        content = _read_skill()
        assert re.search(r"[Bb]uilder.*serve/|serve/.*[Bb]uilder", content), (
            "Domain table must map 'builder' to 'serve/' so the builder knows which files to check"
        )

    def test_doc_writer_domain_paths_present(self) -> None:
        """P2: Doc-writer's domain paths (README.md or similar) are listed in the domain table."""
        content = _read_skill()
        assert re.search(r"[Dd]oc.writer.*README|README.*[Dd]oc.writer", content), (
            "Domain table must map 'doc-writer' to its doc paths (README.md, etc.) "
            "so the doc-writer knows which files to check"
        )

    # ── P2: domain-scoped verification command ───────────────────────────────

    def test_verification_command_uses_pathspec_syntax(self) -> None:
        """P2: Verification uses 'git status --porcelain -- <paths>' (domain-scoped, not raw)."""
        content = _read_skill()
        # Must use -- to separate pathspecs (domain-scoped), not bare git status --porcelain
        assert "git status --porcelain --" in content, (
            "Verification command must use 'git status --porcelain -- <domain-paths>' "
            "with the '--' pathspec separator to scope the check to the agent's domain, "
            "not raw 'git status --porcelain' which shows all dirty files"
        )

    # ── P2: rule placement (pre-end_work, not PostToolUse hook) ──────────────

    def test_rule_placed_in_who_commits_what_section(self) -> None:
        """P2: Pre-advance verification rule appears in '### Who Commits What' section."""
        content = _read_skill()
        section = _section_after(content, _WHO_COMMITS_HEADING)
        assert _PRE_ADVANCE_HEADING in section, (
            "The 'Pre-advance verification' rule must appear inside the "
            "'### Who Commits What' section, specifying the check happens "
            "before end_work (not as a PostToolUse hook)"
        )

    # ── P2: self-heal action, not a blocking gate ─────────────────────────────

    def test_self_heal_action_not_blocking_gate(self) -> None:
        """P2: Protocol specifies commit-and-continue (self-heal), not fail/block on dirty domain."""
        content = _read_skill()
        section = _section_after(content, _PRE_ADVANCE_HEADING)
        # Self-heal: stage and commit the missed files, then proceed — NOT a hard gate
        has_self_heal = re.search(
            r"commit|stage.*commit|git add",
            section,
            re.IGNORECASE,
        )
        assert has_self_heal, (
            "Pre-advance verification rule must specify a self-heal action "
            "(stage and commit the missed files, then proceed to end_work) — "
            "not a blocking gate that fails the task"
        )
