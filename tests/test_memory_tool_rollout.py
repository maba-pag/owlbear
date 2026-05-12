"""Failing tests for task #1313: save_memory / recall_memory rollout to pipeline consumers.

All AC lines except AC6 are (td:0). This file covers AC6 only:

AC6 (td:1): Negative grep — 13 in-scope agent files + r-pipeline-protocol/SKILL.md must
            contain none of the stale/banned tool names after the builder migration.

Banned terms (per AC6):
    query_memory, store_learning, add_memory, update_entry, delete_entry,
    scope_agents, vscode/memory, 'ob-memory/*'

In-scope files (13 agents + 1 skill = 14 total):
    Pipeline agents (10): researcher, architect, builder, reviewer, auditor,
                          doc-writer, orchestrator, planner, test-writer, test-curator
    Subagents (3):        challenger, code-reader, quality-runner
    Skill (1):            share/skills/r-pipeline-protocol/SKILL.md
"""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PIPELINE_AGENT_NAMES: tuple[str, ...] = (
    "researcher",
    "architect",
    "builder",
    "reviewer",
    "auditor",
    "doc-writer",
    "orchestrator",
    "planner",
    "test-writer",
    "test-curator",
)

_SUBAGENT_NAMES: tuple[str, ...] = (
    "challenger",
    "code-reader",
    "quality-runner",
)

# Terms that must NOT appear in any in-scope file after the migration.
_BANNED_TERMS: tuple[str, ...] = (
    "query_memory",
    "store_learning",
    "add_memory",
    "update_entry",
    "delete_entry",
    "scope_agents",
    "vscode/memory",
    "'ob-memory/*'",
)


def _in_scope_paths(project_root: Path) -> list[Path]:
    """Return the 14 in-scope file paths for AC6."""
    agents_dir = project_root / "share" / "agents"
    paths: list[Path] = [
        agents_dir / f"{name}.agent.md"
        for name in (*_PIPELINE_AGENT_NAMES, *_SUBAGENT_NAMES)
    ]
    paths.append(project_root / "share" / "skills" / "r-pipeline-protocol" / "SKILL.md")
    return paths


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFromAC_MemoryToolMigration:
    """AC6: Negative grep — no banned stale tool names in any in-scope file."""

    def test_no_banned_terms_in_in_scope_files(self, project_root: Path) -> None:
        """AC6: All 13 agent files + r-pipeline-protocol/SKILL.md are free of banned terms.

        Banned terms: query_memory, store_learning, add_memory, update_entry,
        delete_entry, scope_agents, vscode/memory, 'ob-memory/*'
        """
        paths = _in_scope_paths(project_root)

        # Verify every path exists — a missing file is itself a failure.
        missing = [p for p in paths if not p.exists()]
        assert not missing, (
            f"In-scope files missing from repo: {[str(p) for p in missing]}"
        )

        violations: list[str] = []
        for path in paths:
            content = path.read_text(encoding="utf-8")
            rel = path.relative_to(project_root)
            for term in _BANNED_TERMS:
                if term in content:
                    violations.append(f"{rel}: found banned term {term!r}")

        assert not violations, (
            "Banned terms found in in-scope files after migration:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )
