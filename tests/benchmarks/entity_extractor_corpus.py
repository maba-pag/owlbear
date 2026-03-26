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
        text=(
            "The daemon poll loop dispatches builder runs and retries tasks based "
            "on orchestrator state transitions."
        ),
        gold_entities=[
            GoldEntity(normalized_name="run_daemon", entity_type="function"),
            GoldEntity(normalized_name="retry executor", entity_type="pattern"),
        ],
    ),
    CorpusSample(
        source_label="hook-reaction-router",
        source_kind="python",
        origin_path="src/owlbear/core/hook_reaction_router.py",
        text=(
            "HookReactionRouter applies ordered reaction rules and calls notify, "
            "retry, or escalate executors from shallow scalar predicates."
        ),
        gold_entities=[
            GoldEntity(normalized_name="HookReactionRouter", entity_type="class_"),
            GoldEntity(normalized_name="hook reaction rule", entity_type="concept"),
        ],
    ),
    CorpusSample(
        source_label="approval-gate-toolset",
        source_kind="python",
        origin_path="src/owlbear/tools/approval_gate.py",
        text=(
            "ApprovalGateToolset emits QUESTION_PENDING before waiting for channel "
            "approval when a gated tool invocation requires explicit consent."
        ),
        gold_entities=[
            GoldEntity(normalized_name="ApprovalGateToolset", entity_type="class_"),
            GoldEntity(normalized_name="question pending", entity_type="decision"),
        ],
    ),
    CorpusSample(
        source_label="board-context-provider",
        source_kind="python",
        origin_path="src/owlbear/core/board_context.py",
        text=(
            "BoardContextProvider injects live kanban board context into agent runs "
            "with a short time-to-live cache for repeated access."
        ),
        gold_entities=[
            GoldEntity(normalized_name="BoardContextProvider", entity_type="class_"),
            GoldEntity(normalized_name="board context", entity_type="concept"),
        ],
    ),
    CorpusSample(
        source_label="architecture-layering-guidelines",
        source_kind="markdown",
        origin_path="tests/benchmarks/fixtures/architecture-layering.md",
        text=(
            "Module layering keeps interfaces thin and dependency injection explicit "
            "to avoid cross-layer import cycles."
        ),
        gold_entities=[
            GoldEntity(normalized_name="dependency injection", entity_type="pattern"),
            GoldEntity(normalized_name="module layering", entity_type="concept"),
        ],
    ),
    CorpusSample(
        source_label="security-guardrails-overview",
        source_kind="markdown",
        origin_path="tests/benchmarks/fixtures/security-guardrails.md",
        text=(
            "Command safety, approval policy, and workspace confinement form layered "
            "defenses for high-risk tool executions."
        ),
        gold_entities=[
            GoldEntity(normalized_name="command safety", entity_type="decision"),
            GoldEntity(normalized_name="workspace confinement", entity_type="pattern"),
        ],
    ),
    CorpusSample(
        source_label="entity-benchmark-method",
        source_kind="markdown",
        origin_path="tests/benchmarks/fixtures/entity-benchmark-method.md",
        text=(
            "Benchmark fixtures compare extracted entities against checked-in gold "
            "annotations and avoid live model requests during loading."
        ),
        gold_entities=[
            GoldEntity(normalized_name="gold annotation", entity_type="concept"),
            GoldEntity(normalized_name="EntityType", entity_type="class_"),
        ],
    ),
    CorpusSample(
        source_label="retry-policy-notes",
        source_kind="markdown",
        origin_path="tests/benchmarks/fixtures/retry-policy.md",
        text=(
            "Retry scheduling records task retry entries idempotently so repeated "
            "failure events do not create duplicate retry state."
        ),
        gold_entities=[
            GoldEntity(normalized_name="schedule task retry", entity_type="function"),
            GoldEntity(normalized_name="idempotent retry", entity_type="pattern"),
        ],
    ),
]


def load_corpus() -> list[CorpusSample]:
    """Return a deterministic list copy of the static benchmark corpus."""

    return list(ENTITY_EXTRACTOR_CORPUS)
