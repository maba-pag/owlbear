"""Entity deduplication for the knowledge graph.

Finds near-duplicate entity names using :func:`difflib.SequenceMatcher`,
merges them into a canonical entity (longest description wins, ties broken
alphabetically), redirects all edges, and deletes duplicates.
"""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from owlbear.memory.knowledge.graph import GraphStore
    from owlbear.memory.knowledge.models import Entity


class DeduplicationResult(BaseModel):
    """Outcome of an entity deduplication run."""

    model_config = ConfigDict(frozen=True)

    merged_count: int
    canonical_ids: list[str] = Field(default_factory=list)


def _pick_canonical(entities: list[Entity]) -> Entity:
    """Choose the canonical entity from a group of near-duplicates.

    Selection rules (in order):
    1. Longest description wins.
    2. Tie-break: alphabetically first name.
    """
    return min(entities, key=lambda e: (-len(e.description), e.name))


def _find_duplicate_groups(
    entities: list[Entity],
    threshold: float,
) -> list[list[Entity]]:
    """Return connected-component groups of near-duplicate entities.

    Uses union-find on entity pairs whose name similarity (via
    :class:`~difflib.SequenceMatcher`) meets *threshold*.
    """
    n = len(entities)
    parent: dict[str, str] = {e.id: e.id for e in entities}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]  # path compression
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    # Compare all pairs
    for i in range(n):
        for j in range(i + 1, n):
            ratio = SequenceMatcher(
                None,
                entities[i].name,
                entities[j].name,
            ).ratio()
            if ratio >= threshold:
                union(entities[i].id, entities[j].id)

    # Build groups
    groups: dict[str, list[Entity]] = {}
    for e in entities:
        root = find(e.id)
        groups.setdefault(root, []).append(e)

    # Only return groups with actual duplicates (size > 1)
    return [g for g in groups.values() if len(g) > 1]


def deduplicate_entities(
    graph: GraphStore,
    threshold: float = 0.85,
) -> DeduplicationResult:
    """Deduplicate near-identical entities in *graph*.

    Parameters
    ----------
    graph:
        A :class:`~owlbear.memory.knowledge.graph.GraphStore` instance.
    threshold:
        Minimum :class:`~difflib.SequenceMatcher` ratio to consider two
        entity names as duplicates.  Default ``0.85``.

    Returns
    -------
    DeduplicationResult
        Number of merges performed and IDs of canonical entities that
        received merges.
    """
    entities = graph.list_entities()
    groups = _find_duplicate_groups(entities, threshold)

    if not groups:
        return DeduplicationResult(merged_count=0, canonical_ids=[])

    merged_count = 0
    canonical_ids: list[str] = []

    for group in groups:
        canonical = _pick_canonical(group)
        duplicates = [e for e in group if e.id != canonical.id]
        canonical_ids.append(canonical.id)

        # Merge metadata: duplicate's keys first, then canonical overwrites
        merged_meta: dict[str, object] = {}
        for dup in duplicates:
            merged_meta.update(dup.metadata)
        merged_meta.update(canonical.metadata)

        # Update canonical entity metadata in-place via SQL
        graph._conn.execute(  # noqa: SLF001
            "UPDATE entities SET metadata = ? WHERE id = ?",
            (graph._dump_meta(merged_meta), canonical.id),  # noqa: SLF001
        )

        for dup in duplicates:
            # Redirect edges: source_id
            graph._conn.execute(  # noqa: SLF001
                "UPDATE edges SET source_id = ? WHERE source_id = ?",
                (canonical.id, dup.id),
            )
            # Redirect edges: target_id
            graph._conn.execute(  # noqa: SLF001
                "UPDATE edges SET target_id = ? WHERE target_id = ?",
                (canonical.id, dup.id),
            )
            # Delete duplicate entity (cascade is safe — no edges reference it now)
            graph.delete_entity(dup.id)
            merged_count += 1

        graph._conn.commit()  # noqa: SLF001

    return DeduplicationResult(merged_count=merged_count, canonical_ids=canonical_ids)
