"""Checked-in corpus fixtures for EntityExtractor benchmark contract tests.

Task: #911
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GoldEntity:
    """Gold annotation keyed by normalized name and entity type string."""

    normalized_name: str
    entity_type: str


@dataclass(frozen=True, slots=True)
class CorpusSample:
    """Single checked-in corpus sample for entity extraction benchmarking."""

    source_label: str
    source_kind: str
    origin_path: str
    text: str
    gold_entities: list[GoldEntity]


def _trimmed(text: str) -> str:
    """Normalize sample text by trimming surrounding whitespace."""
    return text.strip()


ENTITY_EXTRACTOR_CORPUS: list[CorpusSample] = [
    CorpusSample(
        source_label="settings-singleton-pattern",
        source_kind="python",
        origin_path="src/owlbear/config.py",
        text=_trimmed(
            """
            from pydantic_settings import BaseSettings

            _SETTINGS: OwlBearSettings | None = None

            def get_settings() -> OwlBearSettings:
                global _SETTINGS
                if _SETTINGS is None:
                    _SETTINGS = OwlBearSettings()
                return _SETTINGS
            """,
        ),
        gold_entities=[
            GoldEntity(normalized_name="OwlBearSettings", entity_type="class_"),
            GoldEntity(normalized_name="get_settings", entity_type="function"),
            GoldEntity(normalized_name="singleton configuration", entity_type="pattern"),
        ],
    ),
    CorpusSample(
        source_label="toolset-approval-gate",
        source_kind="python",
        origin_path="src/owlbear/tools/approval_gate.py",
        text=_trimmed(
            """
            class ApprovalGateToolset:
                async def call_tool(self, ctx, name, args):
                    if self._needs_approval(name):
                        await self._channel.receive()
            """,
        ),
        gold_entities=[
            GoldEntity(normalized_name="ApprovalGateToolset", entity_type="class_"),
            GoldEntity(normalized_name="call_tool", entity_type="function"),
            GoldEntity(normalized_name="approval gate", entity_type="concept"),
        ],
    ),
    CorpusSample(
        source_label="hook-reaction-routing",
        source_kind="python",
        origin_path="src/owlbear/core/hook_reaction_router.py",
        text=_trimmed(
            """
            class HookReactionRouter:
                def register(self, rule):
                    self._rules.append(rule)

                async def dispatch(self, event, payload):
                    for rule in self._rules:
                        if rule.matches(event, payload):
                            await rule.executor(event, payload)
            """,
        ),
        gold_entities=[
            GoldEntity(normalized_name="HookReactionRouter", entity_type="class_"),
            GoldEntity(normalized_name="dispatch", entity_type="function"),
            GoldEntity(normalized_name="event reaction rule", entity_type="pattern"),
        ],
    ),
    CorpusSample(
        source_label="entity-model-contract",
        source_kind="python",
        origin_path="src/owlbear/memory/knowledge/models.py",
        text=_trimmed(
            """
            class Entity(BaseModel):
                id: str = Field(default_factory=_uuid_hex)
                name: str
                entity_type: EntityType
                metadata: dict[str, Any] = Field(default_factory=dict)
            """,
        ),
        gold_entities=[
            GoldEntity(normalized_name="Entity", entity_type="class_"),
            GoldEntity(normalized_name="EntityType", entity_type="class_"),
            GoldEntity(normalized_name="knowledge graph entity", entity_type="concept"),
        ],
    ),
    CorpusSample(
        source_label="bootstrap-cleanup-lifecycle",
        source_kind="python",
        origin_path="src/owlbear/bootstrap.py",
        text=_trimmed(
            """
            @dataclass(frozen=True)
            class BootstrapResult:
                cleanup: list[Callable[[], Awaitable[None]]]

            async def bootstrap_app() -> BootstrapResult:
                cleanup: list[Callable[[], Awaitable[None]]] = []
                return BootstrapResult(cleanup=cleanup)
            """,
        ),
        gold_entities=[
            GoldEntity(normalized_name="BootstrapResult", entity_type="class_"),
            GoldEntity(normalized_name="bootstrap_app", entity_type="function"),
            GoldEntity(normalized_name="resource cleanup", entity_type="pattern"),
        ],
    ),
    CorpusSample(
        source_label="architecture-layering-guideline",
        source_kind="markdown",
        origin_path="docs/architecture.md",
        text=_trimmed(
            """
            The codebase uses strict layering:
            1. CLI and channel adapters
            2. Core orchestration services
            3. Infrastructure integrations

            Dependencies flow inward and never bypass service boundaries.
            """,
        ),
        gold_entities=[
            GoldEntity(normalized_name="layered architecture", entity_type="pattern"),
            GoldEntity(normalized_name="service boundary", entity_type="concept"),
        ],
    ),
    CorpusSample(
        source_label="security-approval-gates",
        source_kind="markdown",
        origin_path="SECURITY.md",
        text=_trimmed(
            """
            OwlBear applies approval gates before destructive operations.
            CommandSafetyGuard blocks risky shell fragments, and tool allow-lists
            constrain what each role can execute.
            """,
        ),
        gold_entities=[
            GoldEntity(normalized_name="approval gate", entity_type="concept"),
            GoldEntity(normalized_name="CommandSafetyGuard", entity_type="class_"),
        ],
    ),
    CorpusSample(
        source_label="kanban-pipeline-stages",
        source_kind="markdown",
        origin_path="README.md",
        text=_trimmed(
            """
            Task lifecycle: ideation to backlog to todo to in-progress to review to docs to done.
            Each stage has an owning agent and an explicit quality gate.
            """,
        ),
        gold_entities=[
            GoldEntity(normalized_name="task lifecycle", entity_type="concept"),
            GoldEntity(normalized_name="quality gate", entity_type="concept"),
        ],
    ),
]


def load_corpus() -> list[CorpusSample]:
    """Return the checked-in corpus in manifest order.

    The loader is intentionally pure-data only: no filesystem crawl,
    no network, and no model calls.
    """
    return list(ENTITY_EXTRACTOR_CORPUS)
