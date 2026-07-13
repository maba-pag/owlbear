"""Static contract for pipeline task reads through the kanban MCP boundary."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PIPELINE_PROTOCOL = ROOT / "share/skills/r-pipeline-protocol/SKILL.md"
KANBAN_HANDBOOK = ROOT / "share/skills/h-mcp-kanban/SKILL.md"


def _normalized(path: Path) -> str:
    lines = (line.removeprefix("> ") for line in path.read_text(encoding="utf-8").splitlines())
    return " ".join(" ".join(lines).split())


def test_pipeline_protocol_distinguishes_assigned_and_related_task_reads() -> None:
    """Assigned work is claimed once; related tasks remain read-only lookups."""
    protocol = _normalized(PIPELINE_PROTOCOL)

    assert "make `start_work` the first read of the assigned task" in protocol
    assert "`show_task(section=...)`" in protocol
    assert "Never use `start_work` merely to" in protocol
    assert "storage representations" in protocol


def test_kanban_handbook_repeats_the_task_context_boundary() -> None:
    """Tool guidance must not narrow the prohibition back to show_task alone."""
    handbook = _normalized(KANBAN_HANDBOOK)

    assert "before any other read of the assigned task" in handbook
    assert "direct read of the task Markdown is redundant" in handbook
    assert "never claim them merely to inspect them" in handbook
    assert "investigating storage, serialization, corruption, or filesystem behavior" in handbook
