"""Checked-in corpus fixtures for EntityExtractor benchmark contract tests.

Task: #911
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GoldEntity:
    """Gold annotation key represented as normalized name + entity type."""

    normalized_name: str
    entity_type: str


@dataclass(frozen=True, slots=True)
class CorpusSample:
    """Single checked-in benchmark sample.

    Attributes:
        source_label: Stable human-readable sample identifier.
        source_kind: Source language/content category (python or markdown).
        origin_path: Provenance path for the sample snippet.
        text: Trimmed source excerpt text.
        gold_entities: Gold entity keys for recall evaluation.
    """

    source_label: str
    source_kind: str
    origin_path: str
    text: str
    gold_entities: list[GoldEntity]


ENTITY_EXTRACTOR_CORPUS: list[CorpusSample] = [
    CorpusSample(
        source_label="daemon-bootstrap-taskgroup",
        source_kind="python",
        origin_path="src/owlbear/daemon.py",
        text=(
            "async with asyncio.TaskGroup() as tg:\n"
            "    tg.create_task(channel_loop())\n"
            "    tg.create_task(poll_loop())"
        ),
        gold_entities=[
            GoldEntity("taskgroup", "concept"),
            GoldEntity("channel_loop", "function"),
            GoldEntity("poll_loop", "function"),
        ],
    ),
    CorpusSample(
        source_label="hook-supervisor-scheduling",
        source_kind="python",
        origin_path="src/owlbear/core/hook_worker_supervisor.py",
        text=(
            "class HookWorkerSupervisor:\n"
            "    def schedule(self, coro: Awaitable[object]) -> None:\n"
            "        self._tasks.add(asyncio.create_task(coro))"
        ),
        gold_entities=[
            GoldEntity("hookworkersupervisor", "class_"),
            GoldEntity("schedule", "function"),
            GoldEntity("asyncio.create_task", "pattern"),
        ],
    ),
    CorpusSample(
        source_label="knowledge-entity-model",
        source_kind="python",
        origin_path="src/owlbear/memory/knowledge/models.py",
        text=(
            "class Entity(BaseModel):\n"
            "    id: str = Field(default_factory=_uuid_hex)\n"
            "    name: str\n"
            "    entity_type: EntityType"
        ),
        gold_entities=[
            GoldEntity("entity", "class_"),
            GoldEntity("entitytype", "concept"),
            GoldEntity("_uuid_hex", "function"),
        ],
    ),
    CorpusSample(
        source_label="approval-gate-tool-call",
        source_kind="python",
        origin_path="src/owlbear/tools/approval_gate.py",
        text=(
            "if approval_required and not pre_granted:\n"
            "    hooks.emit('QUESTION_PENDING', source='approval_gate')\n"
            "    return channel.receive()"
        ),
        gold_entities=[
            GoldEntity("approvalgatetoolset", "class_"),
            GoldEntity("question_pending", "decision"),
            GoldEntity("channel.receive", "function"),
        ],
    ),
    CorpusSample(
        source_label="research-workflow-checklist",
        source_kind="markdown",
        origin_path=".github/skills/research-workflow/SKILL.md",
        text=(
            "Research workflow:\n"
            "1. Clarify scope\n"
            "2. Gather sources\n"
            "3. Analyze trade-offs\n"
            "4. Create follow-up tasks"
        ),
        gold_entities=[
            GoldEntity("research workflow", "pattern"),
            GoldEntity("follow-up tasks", "decision"),
        ],
    ),
    CorpusSample(
        source_label="security-layer-policy",
        source_kind="markdown",
        origin_path="SECURITY.md",
        text=(
            "Safety stack includes role policy allow-lists, approval gates, "
            "sandbox path confinement, command safety guards, and content "
            "injection scanning."
        ),
        gold_entities=[
            GoldEntity("approval gates", "pattern"),
            GoldEntity("sandbox path confinement", "pattern"),
            GoldEntity("content injection guard", "pattern"),
        ],
    ),
    CorpusSample(
        source_label="architecture-layering-note",
        source_kind="markdown",
        origin_path="docs/architecture.md",
        text=(
            "Architecture favors explicit boundaries: CLI entry points, core "
            "orchestration services, and tool wrappers with dependency injection."
        ),
        gold_entities=[
            GoldEntity("dependency injection", "pattern"),
            GoldEntity("tool wrappers", "concept"),
            GoldEntity("cli entry points", "file"),
        ],
    ),
    CorpusSample(
        source_label="kanban-lifecycle-pipeline",
        source_kind="markdown",
        origin_path=".github/instructions/agent-common.instructions.md",
        text=(
            "Pipeline lifecycle: ideation to backlog to todo to in-progress to "
            "review to docs to done to archived."
        ),
        gold_entities=[
            GoldEntity("pipeline lifecycle", "pattern"),
            GoldEntity("in-progress", "decision"),
            GoldEntity("archived", "decision"),
        ],
    ),
]


def load_corpus() -> list[CorpusSample]:
    """Return the checked-in corpus in manifest order.

    Returns:
        Shallow list copy preserving the exact sample order of
        `ENTITY_EXTRACTOR_CORPUS`.
    """

    return list(ENTITY_EXTRACTOR_CORPUS)
