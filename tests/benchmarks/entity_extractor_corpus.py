"""Static benchmark corpus fixtures for EntityExtractor contract tests.

The corpus is intentionally embedded as plain Python data so loading stays
deterministic and pure-data (no filesystem crawl, no live reads, no model calls).
"""

from typing import NamedTuple


class GoldEntity(NamedTuple):
    """Expected entity annotation for a corpus sample."""

    normalized_name: str
    entity_type: str


class CorpusSample(NamedTuple):
    """A static corpus sample for benchmark contract validation."""

    source_label: str
    source_kind: str
    origin_path: str
    text: str
    gold_entities: list[GoldEntity]


ENTITY_EXTRACTOR_CORPUS: list[CorpusSample] = [
    CorpusSample(
        source_label="daemon-run-loop",
        source_kind="python",
        origin_path="src/owlbear/daemon.py",
        text="_TRANSIENT_MAX_RETRIES = 3",
        gold_entities=[
            GoldEntity(normalized_name="run_daemon", entity_type="function"),
            GoldEntity(normalized_name="retry executor", entity_type="pattern"),
        ],
    ),
    CorpusSample(
        source_label="hook-reaction-router",
        source_kind="python",
        origin_path="src/owlbear/core/hook_reaction_router.py",
        text='__all__ = ["HookReactionRouter", "HookReactionRule"]',
        gold_entities=[
            GoldEntity(normalized_name="HookReactionRouter", entity_type="class_"),
            GoldEntity(normalized_name="hook reaction rule", entity_type="concept"),
        ],
    ),
    CorpusSample(
        source_label="ask-user-toolset",
        source_kind="python",
        origin_path="src/owlbear/tools/ask_user.py",
        text="class AskUserToolset(FunctionToolset):",
        gold_entities=[
            GoldEntity(normalized_name="AskUserToolset", entity_type="class_"),
            GoldEntity(normalized_name="question pending", entity_type="decision"),
        ],
    ),
    CorpusSample(
        source_label="board-context-provider",
        source_kind="python",
        origin_path="src/owlbear/core/board_context.py",
        text="_DEFAULT_CMD: list[str] = [",
        gold_entities=[
            GoldEntity(normalized_name="BoardContextProvider", entity_type="class_"),
            GoldEntity(normalized_name="board context", entity_type="concept"),
        ],
    ),
    CorpusSample(
        source_label="architecture-layering-guidelines",
        source_kind="markdown",
        origin_path="src/owlbear/agents/architect.md",
        text="1. Read the task body and any linked research documents.",
        gold_entities=[
            GoldEntity(normalized_name="dependency injection", entity_type="pattern"),
            GoldEntity(normalized_name="module layering", entity_type="concept"),
        ],
    ),
    CorpusSample(
        source_label="security-guardrails-overview",
        source_kind="markdown",
        origin_path="src/owlbear/agents/reviewer.md",
        text="- You must not create, modify, or delete any source files.",
        gold_entities=[
            GoldEntity(normalized_name="command safety", entity_type="decision"),
            GoldEntity(normalized_name="workspace confinement", entity_type="pattern"),
        ],
    ),
    CorpusSample(
        source_label="entity-benchmark-method",
        source_kind="markdown",
        origin_path="src/owlbear/agents/researcher.md",
        text="1. Clarify the research question and scope before starting.",
        gold_entities=[
            GoldEntity(normalized_name="gold annotation", entity_type="concept"),
            GoldEntity(normalized_name="EntityType", entity_type="class_"),
        ],
    ),
    CorpusSample(
        source_label="retry-policy-notes",
        source_kind="markdown",
        origin_path="src/owlbear/agents/builder.md",
        text="Output: working code, passing tests, and lint-clean confirmation.",
        gold_entities=[
            GoldEntity(normalized_name="schedule task retry", entity_type="function"),
            GoldEntity(normalized_name="idempotent retry", entity_type="pattern"),
        ],
    ),
]


def load_corpus() -> list[CorpusSample]:
    """Return a deterministic list copy of the static benchmark corpus."""

    return list(ENTITY_EXTRACTOR_CORPUS)
